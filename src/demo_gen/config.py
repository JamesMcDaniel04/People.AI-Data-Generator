"""Configuration schema and validation for demo-gen"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


class DateRange(BaseModel):
    start: str
    end: str

    @field_validator("start", "end")
    def validate_date_format(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError("close_date_range must use YYYY-MM-DD format") from exc
        return v

    @model_validator(mode="after")
    def validate_date_order(self):
        start_date = datetime.strptime(self.start, "%Y-%m-%d")
        end_date = datetime.strptime(self.end, "%Y-%m-%d")
        if start_date > end_date:
            raise ValueError("close_date_range.start must be on or before close_date_range.end")
        return self


class SalesforceQueryConfig(BaseModel):
    opportunity_type: str = "new_business"
    stages_allowed: List[str] = Field(default_factory=lambda: ["Discovery", "Evaluation", "Negotiation"])
    exclude_if_omitted_field: Optional[str] = "Omitted_from_Demo__c"
    close_date_range: DateRange
    limit: int = 100

    @model_validator(mode="after")
    def validate_limits(self):
        if self.limit <= 0:
            raise ValueError("salesforce.query.limit must be greater than 0")
        return self


class SalesforceConfig(BaseModel):
    instance_url: str
    auth: Literal["oauth", "jwt"] = "oauth"
    query: SalesforceQueryConfig


class PeopleAIConfig(BaseModel):
    ingestion_mode: Literal["crm_activity", "email_dropbox", "calendar"] = "crm_activity"
    verify_mode: Literal["manual", "api"] = "manual"
    expected_latency_minutes: int = 60


class MeetingsConfig(BaseModel):
    past_min: int = 3
    past_max: int = 8
    future_min: int = 1
    future_max: int = 3
    duration_minutes: List[int] = Field(default_factory=lambda: [25, 30, 45, 60])

    @model_validator(mode="after")
    def validate_meeting_bounds(self):
        if self.past_min < 0 or self.past_max < 0 or self.future_min < 0 or self.future_max < 0:
            raise ValueError("meeting min/max values must be non-negative")
        if self.past_min > self.past_max:
            raise ValueError("meetings.past_min must be <= meetings.past_max")
        if self.future_min > self.future_max:
            raise ValueError("meetings.future_min must be <= meetings.future_max")
        if not self.duration_minutes or any(d <= 0 for d in self.duration_minutes):
            raise ValueError("meetings.duration_minutes must contain positive values")
        return self


class EmailsConfig(BaseModel):
    min: int = 5
    max: int = 20

    @model_validator(mode="after")
    def validate_email_bounds(self):
        if self.min < 0 or self.max < 0:
            raise ValueError("emails.min and emails.max must be non-negative")
        if self.min > self.max:
            raise ValueError("emails.min must be <= emails.max")
        return self


class ActivityConfig(BaseModel):
    past_days: int = 45
    future_days: int = 21
    meetings: MeetingsConfig
    emails: EmailsConfig
    participant_roles: List[str] = Field(
        default_factory=lambda: ["Champion", "Economic Buyer", "Technical Buyer", "Influencer"]
    )
    realism_level: Literal["none", "light", "heavy"] = "light"

    @model_validator(mode="after")
    def validate_activity_config(self):
        if self.past_days < 0 or self.future_days < 0:
            raise ValueError("activity.past_days and activity.future_days must be non-negative")
        if not self.participant_roles:
            raise ValueError("activity.participant_roles must not be empty")
        return self


class LLMConfig(BaseModel):
    provider: Literal["openai", "azure_openai"] = "openai"
    model: str = "gpt-4.1-mini"
    temperature: float = 0.4
    max_tokens: int = 500
    enabled: bool = True


class ScorecardsConfig(BaseModel):
    templates: List[str] = Field(default_factory=lambda: ["MEDDICC"])
    coverage_target: float = 0.8
    confidence_floor: float = 0.55
    mode: Literal["heuristic", "llm", "hybrid"] = "hybrid"

    @model_validator(mode="after")
    def validate_templates(self):
        if not self.templates:
            raise ValueError("scorecards.templates must not be empty")
        return self


class RunConfig(BaseModel):
    name: str = "se-demo-pack"
    seed: int = 42
    idempotency_mode: Literal["tag", "external_state"] = "external_state"
    run_tag_field: Optional[str] = "Demo_Run_Id__c"
    dry_run: bool = False

    @model_validator(mode="after")
    def validate_idempotency(self):
        if self.idempotency_mode == "tag":
            if not self.run_tag_field or not self.run_tag_field.strip():
                raise ValueError("run.run_tag_field is required when idempotency_mode is 'tag'")
        return self


class DemoGenConfig(BaseModel):
    run: RunConfig
    salesforce: SalesforceConfig
    peopleai: PeopleAIConfig
    activity: ActivityConfig
    llm: LLMConfig
    scorecards: ScorecardsConfig

    @field_validator("salesforce")
    def validate_salesforce(cls, v):
        if not v.instance_url.startswith("https://"):
            raise ValueError("instance_url must start with https://")
        return v

    @field_validator("scorecards")
    def validate_scorecards(cls, v):
        if not 0 <= v.coverage_target <= 1:
            raise ValueError("coverage_target must be between 0 and 1")
        if not 0 <= v.confidence_floor <= 1:
            raise ValueError("confidence_floor must be between 0 and 1")
        return v


class ResolvedConfig:
    """Resolved configuration with runtime metadata"""

    def __init__(self, config: DemoGenConfig, config_path: Path, env: str, log_dir: Path):
        self.config = config
        self.config_path = config_path
        self.env = env
        self.log_dir = log_dir
        self.run_id = self._generate_run_id()
        self.run_dir = log_dir / f"{datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%SZ')}_{config.run.name}_{self.run_id}"

    def _generate_run_id(self) -> str:
        """Generate a unique run ID"""
        return f"run-{uuid.uuid4().hex[:8]}"

    def save_resolved_config(self) -> None:
        """Save the resolved configuration to the run directory"""
        self.run_dir.mkdir(parents=True, exist_ok=True)

        resolved_path = self.run_dir / "config.resolved.yaml"
        with open(resolved_path, "w") as f:
            yaml.dump(
                {
                    "run_id": self.run_id,
                    "env": self.env,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "config_path": str(self.config_path),
                    "config": self.config.model_dump(),
                },
                f,
                default_flow_style=False,
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            "run_id": self.run_id,
            "env": self.env,
            "run_dir": str(self.run_dir),
            "config": self.config.model_dump(),
        }


def load_config(config_path: Path, env: str = "sandbox", log_dir: Optional[Path] = None) -> ResolvedConfig:
    """Load and validate configuration from YAML file"""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path) as f:
        raw_config = yaml.safe_load(f)

    config = DemoGenConfig(**raw_config)

    if log_dir is None:
        log_dir = Path("./runs")

    return ResolvedConfig(config, config_path, env, log_dir)

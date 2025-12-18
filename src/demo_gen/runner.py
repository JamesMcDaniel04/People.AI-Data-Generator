"""Main orchestration runner for demo-gen"""

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

from demo_gen.activity_planner import ActivityPlanner
from demo_gen.config import DemoGenConfig, ResolvedConfig
from demo_gen.content_gen import ContentGenerator
from demo_gen.logger import DemoGenLogger, DryRunLogger
from demo_gen.scorecard_client import ScorecardClient
from demo_gen.sf_client import SalesforceClient
from demo_gen.state_store import StateStore


class DemoGenRunner:
    """Main runner that orchestrates the demo data generation"""

    def __init__(
        self,
        config: ResolvedConfig,
        concurrency: int = 5,
        max_opps: int = 200,
    ):
        self.config = config
        self.concurrency = concurrency
        self.max_opps = max_opps

        is_dry_run = config.config.run.dry_run
        self._dry_run = is_dry_run
        self._tag_mode = config.config.run.idempotency_mode == "tag"
        self._run_tag_field = config.config.run.run_tag_field if self._tag_mode else None
        self._thread_local = threading.local()

        if is_dry_run:
            self.logger = DryRunLogger(config.run_id, config.run_dir)
        else:
            self.logger = DemoGenLogger(config.run_id, config.run_dir)
            config.save_resolved_config()

        self.sf_client = SalesforceClient(config.config.salesforce, dry_run=is_dry_run)

        if config.config.llm.enabled:
            self.content_gen = ContentGenerator(config.config.llm)
        else:
            self.content_gen = None

        self.activity_planner = ActivityPlanner(
            config.config.activity, seed=config.config.run.seed
        )

        self.scorecard_client = ScorecardClient(
            config.config.scorecards,
            content_generator=self.content_gen,
            dry_run=is_dry_run,
        )

        if config.config.run.idempotency_mode == "external_state" and not is_dry_run:
            state_db_path = config.run_dir / "state.sqlite"
            self.state_store = StateStore(state_db_path)
        else:
            self.state_store = None

    def run(self) -> Dict[str, Any]:
        """Execute the full demo data generation pipeline"""
        try:
            opportunities = self._select_opportunities()

            self.logger.set_stat("opps_selected", len(opportunities))

            if self.concurrency > 1 and len(opportunities) > 1:
                with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
                    futures = [executor.submit(self._process_opportunity, opp) for opp in opportunities]
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            self.logger.log_error(
                                stage="opportunity_processing",
                                error=str(e),
                                retryable=False,
                            )
            else:
                for opp in opportunities:
                    self._process_opportunity(opp)

            stats = self.logger.finalize(status="completed")
            return stats

        except Exception as e:
            self.logger.log_error(
                stage="pipeline", error=str(e), retryable=False
            )
            self.logger.finalize(status="failed")
            raise
        finally:
            if self.state_store:
                self.state_store.close()

    def _select_opportunities(self) -> List[Dict[str, Any]]:
        """Query and select opportunities"""
        opportunities = self.sf_client.query_opportunities()

        if len(opportunities) > self.max_opps:
            opportunities = opportunities[: self.max_opps]
            self.logger.log_event(
                "opportunity_truncated",
                reason="max_opps_limit",
                limit=self.max_opps,
            )

        for opp in opportunities:
            self.logger.log_event("opportunity_selected", opportunity_id=opp["Id"])

        return opportunities

    def _get_sf_client(self) -> SalesforceClient:
        """Get a thread-local Salesforce client for concurrent processing"""
        if self.concurrency <= 1:
            return self.sf_client

        client = getattr(self._thread_local, "sf_client", None)
        if client is None:
            client = SalesforceClient(self.config.config.salesforce, dry_run=self._dry_run)
            self._thread_local.sf_client = client
        return client

    def _process_opportunity(self, opportunity: Dict[str, Any]) -> None:
        """Process a single opportunity: create activities and scorecards"""
        opp_id = opportunity["Id"]

        try:
            if self.state_store and self.state_store.has_opportunity(
                self.config.run_id, opp_id
            ):
                self.logger.log_event(
                    "opportunity_skipped", opportunity_id=opp_id, reason="already_processed"
                )
                return

            self._create_activities(opportunity)
            self._create_scorecards(opportunity)

            if self.state_store:
                self.state_store.record_opportunity(
                    self.config.run_id,
                    opp_id,
                    datetime.utcnow().isoformat() + "Z",
                )

        except Exception as e:
            self.logger.log_error(
                stage="opportunity_processing",
                error=str(e),
                opportunity_id=opp_id,
                retryable=False,
            )

    def _create_activities(self, opportunity: Dict[str, Any]) -> None:
        """Create meetings and emails for an opportunity"""
        opp_id = opportunity["Id"]
        plan = self.activity_planner.create_plan(opportunity)

        for meeting in plan.meetings:
            self._create_meeting(opportunity, meeting)

        for email in plan.emails:
            self._create_email(opportunity, email)

    def _create_meeting(self, opportunity: Dict[str, Any], meeting) -> None:
        """Create a single meeting"""
        opp_id = opportunity["Id"]

        if self.state_store and self.state_store.has_activity(
            self.config.run_id,
            opp_id,
            "meeting",
            meeting.start_datetime,
            meeting.subject,
        ):
            self.logger.log_event(
                "meeting_skipped",
                opportunity_id=opp_id,
                when=meeting.when,
                reason="already_created",
            )
            return

        description = None
        if self.content_gen and self.config.config.activity.realism_level != "none":
            description = self.content_gen.generate_meeting_notes(
                subject=meeting.subject,
                opportunity_name=opportunity.get("Name", ""),
                stage=opportunity.get("StageName", ""),
                participants=meeting.participants,
                when=meeting.when,
            )

        sf_client = self._get_sf_client()
        try:
            activity_id = sf_client.create_event(
                subject=meeting.subject,
                start_datetime=meeting.start_datetime,
                duration_minutes=meeting.duration_minutes,
                related_to_id=opp_id,
                owner_id=opportunity.get("OwnerId"),
                description=description,
                run_id=self.config.run_id if self._tag_mode else None,
                tag_field=self._run_tag_field if self._tag_mode else None,
            )
        except Exception as e:
            self.logger.log_error(
                stage="meeting_creation",
                error=str(e),
                opportunity_id=opp_id,
                retryable=False,
                when=meeting.when,
            )
            return

        self.logger.log_event(
            "meeting_created",
            opportunity_id=opp_id,
            activity_id=activity_id,
            when=meeting.when,
            start=meeting.start_datetime,
        )
        self.logger.increment_stat("meetings_created")

        if self.state_store:
            self.state_store.record_activity(
                self.config.run_id,
                opp_id,
                "meeting",
                meeting.start_datetime,
                meeting.subject,
                activity_id,
                datetime.utcnow().isoformat() + "Z",
            )

    def _create_email(self, opportunity: Dict[str, Any], email) -> None:
        """Create a single email"""
        opp_id = opportunity["Id"]

        if self.state_store and self.state_store.has_activity(
            self.config.run_id,
            opp_id,
            "email",
            email.activity_date,
            email.subject,
        ):
            self.logger.log_event(
                "email_skipped",
                opportunity_id=opp_id,
                when=email.when,
                reason="already_created",
            )
            return

        description = None
        if self.content_gen and self.config.config.activity.realism_level != "none":
            description = self.content_gen.generate_email_body(
                subject=email.subject,
                opportunity_name=opportunity.get("Name", ""),
                stage=opportunity.get("StageName", ""),
                when=email.when,
            )

        sf_client = self._get_sf_client()
        try:
            activity_id = sf_client.create_task(
                subject=email.subject,
                activity_date=email.activity_date,
                related_to_id=opp_id,
                owner_id=opportunity.get("OwnerId"),
                description=description,
                task_subtype="Email",
                run_id=self.config.run_id if self._tag_mode else None,
                tag_field=self._run_tag_field if self._tag_mode else None,
            )
        except Exception as e:
            self.logger.log_error(
                stage="email_creation",
                error=str(e),
                opportunity_id=opp_id,
                retryable=False,
                when=email.when,
            )
            return

        self.logger.log_event(
            "email_created",
            opportunity_id=opp_id,
            activity_id=activity_id,
            when=email.when,
        )
        self.logger.increment_stat("emails_created")

        if self.state_store:
            self.state_store.record_activity(
                self.config.run_id,
                opp_id,
                "email",
                email.activity_date,
                email.subject,
                activity_id,
                datetime.utcnow().isoformat() + "Z",
            )

    def _create_scorecards(self, opportunity: Dict[str, Any]) -> None:
        """Create and populate scorecards for an opportunity"""
        opp_id = opportunity["Id"]

        for template_name in self.config.config.scorecards.templates:
            if self.state_store and self.state_store.has_scorecard(
                self.config.run_id, opp_id, template_name
            ):
                self.logger.log_event(
                    "scorecard_skipped",
                    opportunity_id=opp_id,
                    template=template_name,
                    reason="already_created",
                )
                continue

            try:
                scorecard_data = self.scorecard_client.upsert_scorecard(
                    opportunity_id=opp_id,
                    template_name=template_name,
                    opportunity=opportunity,
                    seed=self.config.config.run.seed,
                )
            except Exception as e:
                self.logger.log_error(
                    stage="scorecard_generation",
                    error=str(e),
                    opportunity_id=opp_id,
                    retryable=False,
                    template=template_name,
                )
                continue

            scorecard_id = scorecard_data["scorecard_id"]

            self.logger.log_event(
                "scorecard_upserted",
                opportunity_id=opp_id,
                scorecard_id=scorecard_id,
                template=template_name,
            )
            self.logger.increment_stat("scorecards_created")

            if self.state_store:
                self.state_store.record_scorecard(
                    self.config.run_id,
                    opp_id,
                    scorecard_id,
                    template_name,
                    datetime.utcnow().isoformat() + "Z",
                )

            for answer in scorecard_data["answers"]:
                self.logger.log_event(
                    "scorecard_answer_written",
                    opportunity_id=opp_id,
                    scorecard_id=scorecard_id,
                    question_id=answer["question_id"],
                    confidence=answer["confidence"],
                )
                self.logger.increment_stat("scorecard_answers_written")

                if self.state_store:
                    self.state_store.record_scorecard_answer(
                        self.config.run_id,
                        scorecard_id,
                        answer["question_id"],
                        answer["confidence"],
                        datetime.utcnow().isoformat() + "Z",
                    )

            coverage = scorecard_data.get("coverage", 0.0)
            current_coverage = self.logger.get_stats().get("coverage", 0.0)
            self.logger.set_stat("coverage", max(current_coverage, coverage))

    def smoke_test(self, opp_id: str) -> Dict[str, Any]:
        """Run a smoke test on a single opportunity"""
        sf_client = self._get_sf_client()
        opportunities = sf_client.query_opportunities()

        target_opp = None
        for opp in opportunities:
            if opp["Id"] == opp_id:
                target_opp = opp
                break

        if not target_opp:
            raise ValueError(f"Opportunity {opp_id} not found in query results")

        plan = self.activity_planner.create_plan(target_opp)

        meeting = plan.meetings[0] if plan.meetings else None
        email = plan.emails[0] if plan.emails else None

        meeting_id = None
        email_id = None

        if meeting:
            meeting_id = sf_client.create_event(
                subject=meeting.subject,
                start_datetime=meeting.start_datetime,
                duration_minutes=meeting.duration_minutes,
                related_to_id=opp_id,
                owner_id=target_opp.get("OwnerId"),
            )

        if email:
            email_id = sf_client.create_task(
                subject=email.subject,
                activity_date=email.activity_date,
                related_to_id=opp_id,
                owner_id=target_opp.get("OwnerId"),
                task_subtype="Email",
            )

        scorecard_data = self.scorecard_client.upsert_scorecard(
            opportunity_id=opp_id,
            template_name=self.config.config.scorecards.templates[0],
            opportunity=target_opp,
            seed=self.config.config.run.seed,
        )

        return {
            "opportunity_id": opp_id,
            "meeting_id": meeting_id,
            "meeting_subject": meeting.subject if meeting else None,
            "email_id": email_id,
            "email_subject": email.subject if email else None,
            "scorecard_id": scorecard_data["scorecard_id"],
            "scorecard_score": scorecard_data["score"],
        }

    @staticmethod
    def cleanup_run(run_dir: Path) -> Dict[str, int]:
        """Best-effort cleanup of a run"""
        run_file = run_dir / "run.json"
        config_file = run_dir / "config.resolved.yaml"

        if not run_file.exists():
            raise ValueError(f"Cannot cleanup run: {run_file} not found")
        if not config_file.exists():
            raise ValueError(f"Cannot cleanup run: {config_file} not found")

        with open(run_file) as f:
            run_metadata = json.load(f)
        run_id = run_metadata.get("run_id")
        if not run_id:
            raise ValueError("Cannot cleanup run: run_id missing from run.json")

        with open(config_file) as f:
            resolved_config = yaml.safe_load(f)
        config_payload = resolved_config.get("config") if resolved_config else None
        if not config_payload:
            raise ValueError("Cannot cleanup run: resolved config missing 'config' section")

        config = DemoGenConfig(**config_payload)
        sf_client = SalesforceClient(config.salesforce, dry_run=False)

        deleted_events = 0
        deleted_tasks = 0

        if config.run.idempotency_mode == "tag":
            tag_field = config.run.run_tag_field
            if not tag_field:
                raise ValueError("Cannot cleanup run: run_tag_field not configured")

            deleted_events = sf_client.delete_records_by_run_id("Event", tag_field, run_id)
            deleted_tasks = sf_client.delete_records_by_run_id("Task", tag_field, run_id)
        else:
            state_db = run_dir / "state.sqlite"
            if not state_db.exists():
                raise ValueError(
                    "Cannot cleanup run: state.sqlite not found. "
                    "Cleanup requires tag mode or external_state with state.sqlite."
                )

            state_store = StateStore(state_db)
            activities = state_store.get_run_activities(run_id)

            for activity_id, activity_type in activities:
                object_name = None
                if activity_type == "meeting":
                    object_name = "Event"
                elif activity_type == "email":
                    object_name = "Task"

                if not object_name:
                    continue

                try:
                    sf_client.delete_record(object_name, activity_id)
                    if object_name == "Event":
                        deleted_events += 1
                    else:
                        deleted_tasks += 1
                except Exception:
                    continue

            state_store.close()

        return {"Event": deleted_events, "Task": deleted_tasks}

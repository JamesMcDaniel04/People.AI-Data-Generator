"""Logging infrastructure for demo-gen (JSONL + summary)"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class DemoGenLogger:
    """Structured logger for demo-gen operations"""

    def __init__(self, run_id: str, run_dir: Path):
        self.run_id = run_id
        self.run_dir = run_dir
        self.events_file = run_dir / "events.jsonl"
        self.errors_file = run_dir / "errors.jsonl"
        self.run_file = run_dir / "run.json"
        self.summary_file = run_dir / "summary.json"

        # Statistics tracking
        self.stats = {
            "run_id": run_id,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "finished_at": None,
            "opps_selected": 0,
            "meetings_created": 0,
            "emails_created": 0,
            "scorecards_created": 0,
            "scorecard_answers_written": 0,
            "failures": 0,
            "coverage": 0.0,
        }

        # Ensure run directory exists
        run_dir.mkdir(parents=True, exist_ok=True)

        # Initialize run metadata
        self._write_run_metadata()

    def _write_run_metadata(self) -> None:
        """Write initial run metadata"""
        with open(self.run_file, "w") as f:
            json.dump(
                {
                    "run_id": self.run_id,
                    "started_at": self.stats["started_at"],
                    "status": "running",
                },
                f,
                indent=2,
            )

    def _timestamp(self) -> str:
        """Generate ISO8601 timestamp"""
        return datetime.utcnow().isoformat() + "Z"

    def log_event(
        self,
        action: str,
        opportunity_id: Optional[str] = None,
        activity_id: Optional[str] = None,
        scorecard_id: Optional[str] = None,
        **kwargs,
    ) -> None:
        """Log an event to events.jsonl"""
        event = {
            "ts": self._timestamp(),
            "run_id": self.run_id,
            "action": action,
        }

        if opportunity_id:
            event["opportunity_id"] = opportunity_id
        if activity_id:
            event["activity_id"] = activity_id
        if scorecard_id:
            event["scorecard_id"] = scorecard_id

        event.update(kwargs)

        with open(self.events_file, "a") as f:
            f.write(json.dumps(event) + "\n")

    def log_error(
        self,
        stage: str,
        error: str,
        opportunity_id: Optional[str] = None,
        retryable: bool = False,
        **kwargs,
    ) -> None:
        """Log an error to errors.jsonl"""
        error_event = {
            "ts": self._timestamp(),
            "run_id": self.run_id,
            "stage": stage,
            "error": error,
            "retryable": retryable,
        }

        if opportunity_id:
            error_event["opportunity_id"] = opportunity_id

        error_event.update(kwargs)

        with open(self.errors_file, "a") as f:
            f.write(json.dumps(error_event) + "\n")

        # Increment failure count
        self.stats["failures"] += 1

    def increment_stat(self, stat_name: str, amount: int = 1) -> None:
        """Increment a statistic"""
        if stat_name in self.stats:
            self.stats[stat_name] += amount

    def set_stat(self, stat_name: str, value: Any) -> None:
        """Set a statistic value"""
        self.stats[stat_name] = value

    def finalize(self, status: str = "completed") -> Dict[str, Any]:
        """Finalize the run and write summary"""
        self.stats["finished_at"] = self._timestamp()

        # Update run.json with final status
        with open(self.run_file, "w") as f:
            json.dump(
                {
                    "run_id": self.run_id,
                    "started_at": self.stats["started_at"],
                    "finished_at": self.stats["finished_at"],
                    "status": status,
                },
                f,
                indent=2,
            )

        # Write summary.json
        with open(self.summary_file, "w") as f:
            json.dump(self.stats, f, indent=2)

        return self.stats

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        return self.stats.copy()


class DryRunLogger(DemoGenLogger):
    """Logger that simulates logging without writing files"""

    def __init__(self, run_id: str, run_dir: Path):
        self.run_id = run_id
        self.run_dir = run_dir
        self.stats = {
            "run_id": run_id,
            "started_at": datetime.utcnow().isoformat() + "Z",
            "finished_at": None,
            "opps_selected": 0,
            "meetings_created": 0,
            "emails_created": 0,
            "scorecards_created": 0,
            "scorecard_answers_written": 0,
            "failures": 0,
            "coverage": 0.0,
        }

    def _write_run_metadata(self) -> None:
        pass

    def log_event(self, action: str, **kwargs) -> None:
        pass

    def log_error(self, stage: str, error: str, **kwargs) -> None:
        self.stats["failures"] += 1

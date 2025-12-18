"""State management for idempotency using SQLite"""

import hashlib
import sqlite3
from pathlib import Path
from typing import Optional


class StateStore:
    """SQLite-backed state store for idempotency"""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        """Create necessary tables"""
        cursor = self.conn.cursor()

        # Opportunities table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
                run_id TEXT NOT NULL,
                opp_id TEXT NOT NULL,
                selected_at TEXT NOT NULL,
                PRIMARY KEY (run_id, opp_id)
            )
        """
        )

        # Activities table (meetings + emails)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                run_id TEXT NOT NULL,
                opp_id TEXT NOT NULL,
                signature TEXT NOT NULL,
                activity_id TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (run_id, opp_id, signature)
            )
        """
        )

        # Scorecards table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scorecards (
                run_id TEXT NOT NULL,
                opp_id TEXT NOT NULL,
                scorecard_id TEXT NOT NULL,
                template TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (run_id, opp_id, template)
            )
        """
        )

        # Scorecard answers table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scorecard_answers (
                run_id TEXT NOT NULL,
                scorecard_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (run_id, scorecard_id, question_id)
            )
        """
        )

        self.conn.commit()

    def _generate_activity_signature(
        self, activity_type: str, timestamp: str, subject: str
    ) -> str:
        """Generate a deterministic signature for an activity"""
        data = f"{activity_type}:{timestamp}:{subject}"
        return hashlib.md5(data.encode()).hexdigest()

    def has_opportunity(self, run_id: str, opp_id: str) -> bool:
        """Check if opportunity has already been selected"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM opportunities WHERE run_id = ? AND opp_id = ?",
            (run_id, opp_id),
        )
        return cursor.fetchone() is not None

    def record_opportunity(self, run_id: str, opp_id: str, selected_at: str) -> None:
        """Record opportunity selection"""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO opportunities (run_id, opp_id, selected_at) VALUES (?, ?, ?)",
            (run_id, opp_id, selected_at),
        )
        self.conn.commit()

    def has_activity(
        self, run_id: str, opp_id: str, activity_type: str, timestamp: str, subject: str
    ) -> bool:
        """Check if activity has already been created"""
        signature = self._generate_activity_signature(activity_type, timestamp, subject)
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM activities WHERE run_id = ? AND opp_id = ? AND signature = ?",
            (run_id, opp_id, signature),
        )
        return cursor.fetchone() is not None

    def record_activity(
        self,
        run_id: str,
        opp_id: str,
        activity_type: str,
        timestamp: str,
        subject: str,
        activity_id: str,
        created_at: str,
    ) -> None:
        """Record activity creation"""
        signature = self._generate_activity_signature(activity_type, timestamp, subject)
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO activities
            (run_id, opp_id, signature, activity_id, activity_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, opp_id, signature, activity_id, activity_type, created_at),
        )
        self.conn.commit()

    def has_scorecard(self, run_id: str, opp_id: str, template: str) -> bool:
        """Check if scorecard has already been created"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT 1 FROM scorecards WHERE run_id = ? AND opp_id = ? AND template = ?",
            (run_id, opp_id, template),
        )
        return cursor.fetchone() is not None

    def record_scorecard(
        self, run_id: str, opp_id: str, scorecard_id: str, template: str, created_at: str
    ) -> None:
        """Record scorecard creation"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO scorecards
            (run_id, opp_id, scorecard_id, template, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, opp_id, scorecard_id, template, created_at),
        )
        self.conn.commit()

    def has_scorecard_answer(
        self, run_id: str, scorecard_id: str, question_id: str
    ) -> bool:
        """Check if scorecard answer has already been written"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT 1 FROM scorecard_answers
            WHERE run_id = ? AND scorecard_id = ? AND question_id = ?
            """,
            (run_id, scorecard_id, question_id),
        )
        return cursor.fetchone() is not None

    def record_scorecard_answer(
        self,
        run_id: str,
        scorecard_id: str,
        question_id: str,
        confidence: float,
        created_at: str,
    ) -> None:
        """Record scorecard answer"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO scorecard_answers
            (run_id, scorecard_id, question_id, confidence, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run_id, scorecard_id, question_id, confidence, created_at),
        )
        self.conn.commit()

    def get_run_activities(self, run_id: str):
        """Get all activities for a run (for cleanup/reset)"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT activity_id, activity_type FROM activities WHERE run_id = ?",
            (run_id,),
        )
        return cursor.fetchall()

    def get_run_scorecards(self, run_id: str):
        """Get all scorecards for a run (for cleanup/reset)"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT scorecard_id FROM scorecards WHERE run_id = ?",
            (run_id,),
        )
        return cursor.fetchall()

    def close(self) -> None:
        """Close database connection"""
        self.conn.close()

"""Activity planner that generates deterministic activity plans for opportunities"""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List

from demo_gen.config import ActivityConfig


@dataclass
class PlannedMeeting:
    """A planned meeting activity"""

    subject: str
    start_datetime: str
    duration_minutes: int
    when: str  # "past" or "future"
    participants: List[str]


@dataclass
class PlannedEmail:
    """A planned email activity"""

    subject: str
    activity_date: str
    when: str  # "past" or "future"
    participants: List[str]


@dataclass
class ActivityPlan:
    """Complete activity plan for an opportunity"""

    opportunity_id: str
    meetings: List[PlannedMeeting]
    emails: List[PlannedEmail]


class ActivityPlanner:
    """Generates deterministic activity plans using seeded randomization"""

    def __init__(self, config: ActivityConfig, seed: int = 42):
        self.config = config
        self.base_seed = seed
        self.meeting_subjects = self._load_meeting_subjects()
        self.email_subjects = self._load_email_subjects()

    def _load_meeting_subjects(self) -> List[str]:
        """Load realistic meeting subject templates"""
        return [
            "Discovery Call",
            "Product Demo",
            "Technical Deep Dive",
            "Stakeholder Alignment",
            "Executive Briefing",
            "Solution Architecture Review",
            "Business Requirements Discussion",
            "Evaluation Planning",
            "Security & Compliance Review",
            "Pricing Discussion",
            "Implementation Planning",
            "Next Steps & Timeline Review",
        ]

    def _load_email_subjects(self) -> List[str]:
        """Load realistic email subject templates"""
        return [
            "Re: Follow-up from our call",
            "Demo recording and materials",
            "Next steps and action items",
            "Proposal for review",
            "Re: Technical questions",
            "Scheduling our next meeting",
            "Additional resources",
            "Re: Security documentation",
            "Pricing information",
            "Re: Timeline and implementation",
            "Introduction to our team",
            "Re: Contract review",
        ]

    def create_plan(self, opportunity: Dict[str, Any]) -> ActivityPlan:
        """Create a deterministic activity plan for an opportunity"""
        opp_id = opportunity["Id"]

        # Create a deterministic RNG for this opportunity
        rng = random.Random(f"{self.base_seed}:{opp_id}")

        # Determine number of activities
        num_past_meetings = rng.randint(
            self.config.meetings.past_min, self.config.meetings.past_max
        )
        num_future_meetings = rng.randint(
            self.config.meetings.future_min, self.config.meetings.future_max
        )
        num_emails = rng.randint(self.config.emails.min, self.config.emails.max)

        meetings = []
        emails = []

        # Generate past meetings
        for i in range(num_past_meetings):
            meetings.append(
                self._generate_meeting(
                    rng, when="past", index=i, total=num_past_meetings
                )
            )

        # Generate future meetings
        for i in range(num_future_meetings):
            meetings.append(
                self._generate_meeting(
                    rng, when="future", index=i, total=num_future_meetings
                )
            )

        # Generate emails (mixed past and occasional future)
        past_email_ratio = 0.85
        num_past_emails = int(num_emails * past_email_ratio)

        for i in range(num_past_emails):
            emails.append(self._generate_email(rng, when="past", index=i))

        for i in range(num_emails - num_past_emails):
            emails.append(self._generate_email(rng, when="future", index=i))

        return ActivityPlan(
            opportunity_id=opp_id,
            meetings=meetings,
            emails=emails,
        )

    def _generate_meeting(
        self, rng: random.Random, when: str, index: int, total: int
    ) -> PlannedMeeting:
        """Generate a single meeting"""
        subject = rng.choice(self.meeting_subjects)
        duration = rng.choice(self.config.meetings.duration_minutes)

        # Generate timestamp
        if when == "past":
            # Spread past meetings across the past_days window
            days_ago = int(
                (self.config.past_days / total) * (index + 1)
            )  # Spread them out
            hours_offset = rng.randint(9, 17)  # Business hours
            delta = timedelta(days=-days_ago, hours=hours_offset)
        else:
            # Spread future meetings across future_days window
            days_ahead = int((self.config.future_days / total) * (index + 1))
            hours_offset = rng.randint(9, 17)
            delta = timedelta(days=days_ahead, hours=hours_offset)

        meeting_time = datetime.utcnow() + delta
        start_datetime = meeting_time.isoformat() + "Z"

        # Generate participants
        num_participants = rng.randint(1, min(3, len(self.config.participant_roles)))
        participants = rng.sample(self.config.participant_roles, num_participants)

        return PlannedMeeting(
            subject=subject,
            start_datetime=start_datetime,
            duration_minutes=duration,
            when=when,
            participants=participants,
        )

    def _generate_email(
        self, rng: random.Random, when: str, index: int
    ) -> PlannedEmail:
        """Generate a single email"""
        subject = rng.choice(self.email_subjects)

        # Generate date
        if when == "past":
            days_ago = rng.randint(1, self.config.past_days)
            delta = timedelta(days=-days_ago)
        else:
            days_ahead = rng.randint(1, self.config.future_days)
            delta = timedelta(days=days_ahead)

        email_date = datetime.utcnow() + delta
        activity_date = email_date.strftime("%Y-%m-%d")

        # Generate participants
        num_participants = rng.randint(1, min(2, len(self.config.participant_roles)))
        participants = rng.sample(self.config.participant_roles, num_participants)

        return PlannedEmail(
            subject=subject,
            activity_date=activity_date,
            when=when,
            participants=participants,
        )

    def get_plan_summary(self, plan: ActivityPlan) -> Dict[str, Any]:
        """Get a summary of an activity plan"""
        past_meetings = [m for m in plan.meetings if m.when == "past"]
        future_meetings = [m for m in plan.meetings if m.when == "future"]
        past_emails = [e for e in plan.emails if e.when == "past"]
        future_emails = [e for e in plan.emails if e.when == "future"]

        return {
            "opportunity_id": plan.opportunity_id,
            "total_meetings": len(plan.meetings),
            "past_meetings": len(past_meetings),
            "future_meetings": len(future_meetings),
            "total_emails": len(plan.emails),
            "past_emails": len(past_emails),
            "future_emails": len(future_emails),
        }

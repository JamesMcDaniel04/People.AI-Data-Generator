"""Tests for activity planner"""

import pytest
from demo_gen.activity_planner import ActivityPlanner
from demo_gen.config import ActivityConfig, MeetingsConfig, EmailsConfig


def test_deterministic_plan_generation():
    """Test that same seed produces same activity plan"""
    config = ActivityConfig(
        past_days=45,
        future_days=21,
        meetings=MeetingsConfig(past_min=3, past_max=8, future_min=1, future_max=3),
        emails=EmailsConfig(min=5, max=20),
        participant_roles=["Champion", "Economic Buyer"],
        realism_level="light",
    )

    opportunity = {
        "Id": "006TEST00000001",
        "Name": "Test Opp",
        "StageName": "Discovery",
    }

    planner1 = ActivityPlanner(config, seed=42)
    planner2 = ActivityPlanner(config, seed=42)

    plan1 = planner1.create_plan(opportunity)
    plan2 = planner2.create_plan(opportunity)

    # Same seed should produce identical plans
    assert len(plan1.meetings) == len(plan2.meetings)
    assert len(plan1.emails) == len(plan2.emails)

    # Check first meeting is identical
    assert plan1.meetings[0].subject == plan2.meetings[0].subject
    assert plan1.meetings[0].start_datetime == plan2.meetings[0].start_datetime


def test_different_seeds_produce_different_plans():
    """Test that different seeds produce different plans"""
    config = ActivityConfig(
        past_days=45,
        future_days=21,
        meetings=MeetingsConfig(past_min=3, past_max=8, future_min=1, future_max=3),
        emails=EmailsConfig(min=5, max=20),
        participant_roles=["Champion", "Economic Buyer"],
        realism_level="light",
    )

    opportunity = {
        "Id": "006TEST00000001",
        "Name": "Test Opp",
        "StageName": "Discovery",
    }

    planner1 = ActivityPlanner(config, seed=42)
    planner2 = ActivityPlanner(config, seed=99)

    plan1 = planner1.create_plan(opportunity)
    plan2 = planner2.create_plan(opportunity)

    # Different seeds should produce different plans
    # (highly unlikely to be the same by chance)
    assert (
        plan1.meetings[0].subject != plan2.meetings[0].subject
        or plan1.meetings[0].start_datetime != plan2.meetings[0].start_datetime
    )


def test_plan_respects_config_bounds():
    """Test that generated plan respects configured min/max bounds"""
    config = ActivityConfig(
        past_days=45,
        future_days=21,
        meetings=MeetingsConfig(past_min=3, past_max=5, future_min=1, future_max=2),
        emails=EmailsConfig(min=5, max=10),
        participant_roles=["Champion", "Economic Buyer"],
        realism_level="light",
    )

    opportunity = {
        "Id": "006TEST00000001",
        "Name": "Test Opp",
        "StageName": "Discovery",
    }

    planner = ActivityPlanner(config, seed=42)
    plan = planner.create_plan(opportunity)

    past_meetings = [m for m in plan.meetings if m.when == "past"]
    future_meetings = [m for m in plan.meetings if m.when == "future"]

    assert config.meetings.past_min <= len(past_meetings) <= config.meetings.past_max
    assert config.meetings.future_min <= len(future_meetings) <= config.meetings.future_max
    assert config.emails.min <= len(plan.emails) <= config.emails.max

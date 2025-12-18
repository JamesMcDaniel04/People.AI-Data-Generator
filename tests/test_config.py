"""Tests for configuration loading and validation"""

import pytest
from pathlib import Path
from demo_gen.config import load_config, DemoGenConfig
import yaml


def test_load_example_config():
    """Test that the example config loads and validates correctly"""
    config_path = Path(__file__).parent.parent / "demo.example.yaml"

    with open(config_path) as f:
        raw_config = yaml.safe_load(f)

    # Should parse without errors
    config = DemoGenConfig(**raw_config)

    assert config.run.name == "se-demo-pack"
    assert config.run.seed == 42
    assert config.salesforce.auth in ["oauth", "jwt"]
    assert len(config.scorecards.templates) > 0


def test_config_validation_instance_url():
    """Test that instance_url must start with https://"""
    with open(Path(__file__).parent.parent / "demo.example.yaml") as f:
        raw_config = yaml.safe_load(f)

    # Invalid instance URL (no https)
    raw_config["salesforce"]["instance_url"] = "http://example.com"

    with pytest.raises(ValueError, match="instance_url must start with https://"):
        DemoGenConfig(**raw_config)


def test_config_validation_coverage():
    """Test that coverage_target must be between 0 and 1"""
    with open(Path(__file__).parent.parent / "demo.example.yaml") as f:
        raw_config = yaml.safe_load(f)

    # Invalid coverage (> 1)
    raw_config["scorecards"]["coverage_target"] = 1.5

    with pytest.raises(ValueError, match="coverage_target must be between 0 and 1"):
        DemoGenConfig(**raw_config)


def test_config_validation_tag_requires_field():
    """Test that tag mode requires run_tag_field"""
    with open(Path(__file__).parent.parent / "demo.example.yaml") as f:
        raw_config = yaml.safe_load(f)

    raw_config["run"]["idempotency_mode"] = "tag"
    raw_config["run"]["run_tag_field"] = ""

    with pytest.raises(ValueError, match="run.run_tag_field is required"):
        DemoGenConfig(**raw_config)


def test_config_validation_date_range_order():
    """Test that close_date_range start must be before end"""
    with open(Path(__file__).parent.parent / "demo.example.yaml") as f:
        raw_config = yaml.safe_load(f)

    raw_config["salesforce"]["query"]["close_date_range"]["start"] = "2025-12-31"
    raw_config["salesforce"]["query"]["close_date_range"]["end"] = "2025-10-01"

    with pytest.raises(ValueError, match="close_date_range.start must be on or before"):
        DemoGenConfig(**raw_config)


def test_resolved_config_run_id():
    """Test that resolved config generates unique run IDs"""
    config_path = Path(__file__).parent.parent / "demo.example.yaml"
    log_dir = Path("/tmp/demo-gen-test")

    resolved1 = load_config(config_path, "sandbox", log_dir)
    resolved2 = load_config(config_path, "sandbox", log_dir)

    # Each load should generate a unique run ID
    assert resolved1.run_id != resolved2.run_id
    assert resolved1.run_id.startswith("run-")

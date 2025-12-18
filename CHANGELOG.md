# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-18

### Added

**Core Features**
- CLI interface with commands: `run`, `dry-run`, `status`, `reset`, `smoke`
- YAML-based configuration with Pydantic validation
- Structured JSONL logging with summary statistics
- SQLite-based idempotency (external_state mode)
- Tag-based idempotency support (requires custom field)

**Salesforce Integration**
- Opportunity querying with configurable filters
- Event (meeting) creation
- Task (email) creation
- Contact lookup
- Record tagging for cleanup

**Activity Generation**
- Deterministic activity planning with seeded RNG
- Configurable past/future time windows
- Realistic meeting and email subjects
- Participant role assignment

**Content Generation**
- OpenAI integration for realistic content
- Meeting notes generation
- Email body generation
- Scorecard answer generation
- Heuristic fallback when LLM disabled

**Scorecard Support**
- MEDDICC template implementation
- Hybrid mode (LLM + heuristic)
- Confidence scoring
- Coverage tracking

**Documentation**
- Comprehensive README
- Quick start guide
- Architecture documentation
- Example configuration
- Unit tests

### Technical Details
- Python 3.9+ support
- Click CLI framework
- Rich terminal output
- Makefile for common tasks
- VSCode configuration

## [Unreleased]

### Added
- Thread-safe logging and state store for concurrent runs
- Opportunity-level concurrency via `--concurrency`
- Tag-mode run tagging on Event/Task creation
- Reset cleanup for tag mode and external_state using `state.sqlite`
- Config validation for date ranges and min/max bounds
- Automatic `.env` loading in CLI

### Changed
- Scorecard scoring now uses template question counts
- Scorecard generation guarantees at least one answer when coverage_target > 0
- SOQL generation now escapes string literals and quotes dates

### Planned for 0.2.0
- Progress bars during runs
- People.ai API verification
- Additional scorecard templates (BANT, MEDDPICC)
- Custom activity subjects via configuration
- Better error recovery and retry logic

### Planned for 0.3.0
- Web UI for configuration
- Scheduled runs
- Diff mode for state comparison
- Export/import state functionality
- Cloud deployment options

### Future Considerations
- Contact auto-generation
- Account hierarchy support
- Multi-org orchestration
- Reporting dashboard
- Slack/Teams notifications
- Webhook support for integrations

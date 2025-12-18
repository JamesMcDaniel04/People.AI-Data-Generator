# Architecture Overview

This document describes the internal architecture of the demo data generator.

## Project Structure

```
People.AI-Data-Generator/
├── src/demo_gen/              # Main source code
│   ├── __init__.py
│   ├── cli.py                 # CLI interface (Click)
│   ├── config.py              # Configuration schema (Pydantic)
│   ├── logger.py              # Structured logging (JSONL + summary)
│   ├── state_store.py         # SQLite idempotency tracker
│   ├── sf_client.py           # Salesforce API wrapper
│   ├── activity_planner.py    # Deterministic activity generation
│   ├── content_gen.py         # LLM content generation
│   ├── scorecard_client.py    # Scorecard creation & population
│   └── runner.py              # Main orchestration logic
├── tests/                     # Unit tests
├── runs/                      # Generated run logs (gitignored)
├── demo.example.yaml          # Example configuration
├── .env.example               # Example environment variables
├── pyproject.toml             # Package metadata
├── setup.py                   # Package setup
├── requirements.txt           # Dependencies
├── Makefile                   # Convenience commands
├── README.md                  # User documentation
├── QUICKSTART.md              # Getting started guide
└── ARCHITECTURE.md            # This file
```

## Module Responsibilities

### CLI Layer ([cli.py](src/demo_gen/cli.py))

**Purpose:** Command-line interface and user interaction

**Commands:**
- `run` - Full pipeline execution
- `dry-run` - Preview without changes
- `status` - View run summary
- `reset` - Cleanup run data
- `smoke` - Single-opp validation

**Dependencies:** runner.py, config.py, logger.py

### Configuration ([config.py](src/demo_gen/config.py))

**Purpose:** Load, validate, and resolve configuration

**Key Classes:**
- `DemoGenConfig` - Main configuration schema (Pydantic)
- `ResolvedConfig` - Runtime-resolved config with run metadata
- Various sub-configs for each section

**Validation:**
- HTTPS URLs required
- Coverage targets 0-1
- Required fields present

### Orchestration ([runner.py](src/demo_gen/runner.py))

**Purpose:** Main pipeline coordination

**Flow:**
1. Query opportunities (via sf_client)
2. For each opportunity:
   - Plan activities (via activity_planner)
   - Generate content (via content_gen, optional)
   - Create Salesforce records (via sf_client)
   - Create scorecards (via scorecard_client)
   - Log events (via logger)
   - Track state (via state_store, optional)

**Methods:**
- `run()` - Main pipeline
- `smoke_test()` - Single-opp test
- `cleanup_run()` - Reset helper

### Salesforce Client ([sf_client.py](src/demo_gen/sf_client.py))

**Purpose:** Abstract Salesforce API interactions

**Operations:**
- Query opportunities (SOQL)
- Create Events (meetings)
- Create Tasks (emails)
- Query Contacts
- Tag records (for cleanup)
- Delete by run ID

**Authentication:** OAuth via simple-salesforce library

### Activity Planner ([activity_planner.py](src/demo_gen/activity_planner.py))

**Purpose:** Generate deterministic activity plans

**Key Features:**
- Seeded random generation
- Configurable min/max counts
- Past/future time windows
- Realistic subject lines
- Participant role assignment

**Output:** `ActivityPlan` with lists of `PlannedMeeting` and `PlannedEmail`

### Content Generator ([content_gen.py](src/demo_gen/content_gen.py))

**Purpose:** Generate realistic text via LLM

**Capabilities:**
- Meeting notes (agenda/summary based on timing)
- Email bodies
- Scorecard answers

**Fallback:** Returns `None` if LLM fails; caller uses heuristics

### Scorecard Client ([scorecard_client.py](src/demo_gen/scorecard_client.py))

**Purpose:** Create and populate scorecards

**Templates:**
- MEDDICC (currently)
- Extensible for others

**Modes:**
- `heuristic` - Rule-based answers
- `llm` - AI-generated answers
- `hybrid` - LLM with heuristic fallback

**Scoring:** Coverage + confidence weighted average

### State Store ([state_store.py](src/demo_gen/state_store.py))

**Purpose:** Track created records for idempotency

**Schema:**
- `opportunities` - Selected opps
- `activities` - Created meetings/emails (by signature)
- `scorecards` - Created scorecards
- `scorecard_answers` - Populated answers

**Signature:** MD5 hash of (type, timestamp, subject)

### Logger ([logger.py](src/demo_gen/logger.py))

**Purpose:** Structured event and error logging

**Outputs:**
- `events.jsonl` - One JSON per action
- `errors.jsonl` - One JSON per error
- `run.json` - Run metadata
- `summary.json` - Final statistics

**Classes:**
- `DemoGenLogger` - Full logging
- `DryRunLogger` - No-op for dry runs

## Data Flow

```
                    ┌─────────────┐
                    │   CLI       │
                    │  (cli.py)   │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Config     │
                    │(config.py)  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   Runner    │◄───────────┐
                    │ (runner.py) │            │
                    └──────┬──────┘            │
                           │                   │
        ┌──────────────────┼──────────────────┼────────────┐
        │                  │                   │            │
        ▼                  ▼                   ▼            ▼
┌──────────────┐   ┌──────────────┐   ┌──────────┐  ┌──────────┐
│  SF Client   │   │Activity      │   │ Content  │  │Scorecard │
│ (sf_client)  │   │  Planner     │   │   Gen    │  │ Client   │
└──────┬───────┘   └──────┬───────┘   └────┬─────┘  └────┬─────┘
       │                  │                 │             │
       │                  └─────────────────┴─────────────┘
       │                            │
       ▼                            ▼
┌──────────────┐           ┌──────────────┐
│ Salesforce   │           │  OpenAI API  │
│     API      │           │              │
└──────────────┘           └──────────────┘

        Logging (logger.py) ──► events.jsonl, summary.json
        State (state_store.py) ──► state.sqlite
```

## Key Design Decisions

### 1. Deterministic Generation

**Why:** Reproducibility and debugging
- Same seed → same activity plan
- Predictable demo environments
- Easy to verify what changed

**How:** Seeded random number generator keyed by `seed:opp_id`

### 2. Idempotency

**Why:** Safe reruns without duplicates

**Options:**
- External state (SQLite) - No Salesforce changes needed
- Tag-based - Requires custom field, enables cleanup

**Trade-off:** External state more compatible, tag-based more powerful

### 3. Dry-Run Mode

**Why:** Preview before execution, validate config

**Implementation:** `dry_run` flag propagates through all clients
- SF client returns mock data
- No writes to Salesforce or state DB
- Logger is no-op variant

### 4. LLM Optional

**Why:** Cost control, offline operation, reliability

**Fallback:** Heuristic content if LLM fails or disabled
- Still creates activities with subjects
- Uses template-based scorecard answers

### 5. Structured Logging

**Why:** Debugging, auditing, analytics

**Format:** JSONL for easy parsing, streaming
- One event per line
- Greppable, jq-friendly
- Summary JSON for quick stats

## Extension Points

### Adding a New Scorecard Template

1. Create class inheriting `ScorecardTemplate` in [scorecard_client.py](src/demo_gen/scorecard_client.py)
2. Define questions with IDs and categories
3. Add to `_load_templates()` method
4. Optionally add heuristic answers

### Adding a New Activity Type

1. Extend `ActivityPlan` dataclass in [activity_planner.py](src/demo_gen/activity_planner.py)
2. Add generation logic to `create_plan()`
3. Add creation method to [sf_client.py](src/demo_gen/sf_client.py)
4. Add processing to `_create_activities()` in [runner.py](src/demo_gen/runner.py)

### Custom Content Generation

Replace or extend `ContentGenerator`:
- Could add Azure OpenAI support
- Could integrate with other LLMs
- Could use templates with variable substitution

## Testing Strategy

### Unit Tests

- **Config validation:** Ensure constraints enforced
- **Deterministic generation:** Same seed → same output
- **Bounds checking:** Min/max respected

### Integration Tests (Manual)

- **Smoke test:** `demo-gen smoke` validates end-to-end
- **Dry run:** Preview without side effects
- **Idempotency:** Run twice, verify no duplicates

### Production Validation

1. Run smoke test with single opp
2. Verify in Salesforce
3. Wait for People.ai ingestion
4. Confirm activities appear
5. Then run full generation

## Dependencies

### Core
- `click` - CLI framework
- `pyyaml` - Config parsing
- `pydantic` - Schema validation
- `simple-salesforce` - SF API client
- `openai` - LLM integration
- `python-dotenv` - Environment loading
- `rich` - Terminal formatting

### Dev
- `pytest` - Testing
- `black` - Code formatting
- `ruff` - Linting

## Performance Considerations

### Concurrency

- Configurable via `--concurrency` flag
- Default: 5 parallel API calls
- Implemented with ThreadPoolExecutor at opportunity level
- Future: finer-grained concurrency for per-activity writes

### Rate Limiting

- Salesforce: 15K API calls/day (typical)
- OpenAI: Depends on tier
- Safety: `--max-opps` hard cap

### Scalability

Current design handles:
- 100-200 opportunities comfortably
- 5-20 activities per opp
- Total: ~2000 API calls per run

For larger scale:
- Batch API calls
- Implement true concurrency
- Add progress bars
- Consider async/await pattern

## Security

### Credentials

- Never commit `.env` to git
- Use environment variables only
- Support OAuth (preferred) and JWT

### Salesforce Permissions

Minimal required:
- Read: Opportunity, Account, Contact
- Create: Event, Task
- API Enabled

### LLM API

- API key via environment only
- No PII sent to OpenAI
- Opportunity names/stages only (demo data)

## Future Enhancements

### Phase 2

- [ ] Progress bars (rich.progress)
- [ ] People.ai API verification
- [ ] More scorecard templates (BANT, MEDDPICC)
- [ ] Custom activity subjects via config

### Phase 3

- [ ] Web UI for configuration
- [ ] Scheduled runs (cron-style)
- [ ] Diff mode (show what changed)
- [ ] Export/import state
- [ ] Cloud deployment (Lambda/Cloud Run)

### Nice-to-Have

- [ ] Contact auto-generation
- [ ] Account hierarchy support
- [ ] Multi-org orchestration
- [ ] Reporting dashboard
- [ ] Slack notifications

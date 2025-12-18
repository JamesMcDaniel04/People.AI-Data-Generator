# Demo Data Generator for People.ai

A reliable, internal tool to generate demo-ready sales data for your People.ai product demo environment. Create realistic opportunities with populated activities and scorecards on demand.

## Goals

This tool helps you:

- **Generate predictable demo datasets on demand** - Press one button and get a known-good demo org
- **Control which opportunities get coverage** - Target specific new business opportunities in chosen date ranges
- **Create coherent activity history** - Past/future meetings and emails that People.ai can ingest
- **Pre-populate scorecards** - MEDDICC or other frameworks with realistic, consistent answers
- **Make it repeatable** - Re-run whenever a sandbox gets stale, broken, or reset

## Features

- **Deterministic generation** - Same seed produces same results
- **Idempotent reruns** - Safe to run multiple times without duplicates
- **Dry-run mode** - Preview what would be created without making changes
- **Structured logging** - JSONL event logs + summary JSON for auditability
- **LLM-powered content** - Optional realistic meeting notes and email bodies
- **Smoke testing** - Quick validation with a single opportunity

## Installation

### Prerequisites

- Python 3.9 or higher
- Salesforce credentials with API access
- OpenAI API key (optional, for LLM-generated content)

### Quick Setup (Automated)

For the fastest setup, use the automated script:

```bash
./setup_dev.sh
```

This will:
- Create virtual environment
- Install all dependencies
- Copy example configuration files
- Verify installation

### Manual Setup

1. Clone the repository:

```bash
git clone <repository-url>
cd People.AI-Data-Generator
```

2. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package in development mode:

```bash
pip install -e .
```

4. Create your configuration:

```bash
cp demo.example.yaml demo.yaml
cp .env.example .env
```

5. Edit `.env` with your credentials:

```bash
SF_USERNAME=your.email@company.com
SF_PASSWORD=your_password
SF_SECURITY_TOKEN=your_security_token
OPENAI_API_KEY=sk-...  # Optional
```

6. Edit `demo.yaml` with your Salesforce instance and preferences.

## Configuration

The configuration file (`demo.yaml`) controls all aspects of data generation:

### Key Configuration Sections

**Run Settings**
- `name`: Identifier for this demo pack
- `seed`: Random seed for deterministic generation
- `idempotency_mode`: Use `external_state` (SQLite) or `tag` (custom field)

**Salesforce Query**
- `instance_url`: Your Salesforce instance
- `opportunity_type`: Filter by type (e.g., "New Business")
- `stages_allowed`: List of stages to include
- `close_date_range`: Date range for opportunities

**Activity Generation**
- `past_days` / `future_days`: Time windows for activity generation
- `meetings.past_min` / `past_max`: Number of past meetings per opp
- `emails.min` / `max`: Number of emails per opp
- `realism_level`: `none`, `light`, or `heavy` (controls LLM usage)

**Scorecards**
- `templates`: List of templates (currently supports "MEDDICC")
- `coverage_target`: Percentage of questions to answer (0.0-1.0)
- `confidence_floor`: Minimum confidence score for answers
- `mode`: `heuristic`, `llm`, or `hybrid`

See [demo.example.yaml](demo.example.yaml) for full configuration options.

## Usage

### Basic Commands

**Run full generation:**
```bash
demo-gen run -c demo.yaml
```

**Preview without changes (dry-run):**
```bash
demo-gen dry-run -c demo.yaml
```

**Check status of a previous run:**
```bash
demo-gen status --run-id run-8f3a
```

**Smoke test (single opportunity):**
```bash
demo-gen smoke -c demo.yaml --opp-id 006...
```

**Reset/cleanup a run (tag mode or external_state with state.sqlite):**
```bash
demo-gen reset --run-id run-8f3a
```

### Command Options

**Environment selection:**
```bash
demo-gen run -c demo.yaml --env sandbox  # or staging, prod-demo
```

**Custom log directory:**
```bash
demo-gen run -c demo.yaml --log-dir ./my-runs
```

**Concurrency and safety limits:**
```bash
demo-gen run -c demo.yaml --concurrency 10 --max-opps 150
```

## Output Structure

Each run creates a directory under `runs/` with the following structure:

```
runs/
  2025-12-18T14-32-10Z_se-demo-pack_run-8f3a/
    config.resolved.yaml   # Full resolved configuration
    run.json              # Run metadata and status
    events.jsonl          # Detailed event log (one JSON per line)
    errors.jsonl          # Error log
    summary.json          # Final statistics
    state.sqlite          # Idempotency state (if using external_state mode)
```

### Example Events

**events.jsonl:**
```json
{"ts":"2025-12-18T14:33:01Z","run_id":"run-8f3a","opportunity_id":"006...","action":"opportunity_selected"}
{"ts":"2025-12-18T14:33:10Z","run_id":"run-8f3a","opportunity_id":"006...","action":"meeting_created","activity_id":"00U...","when":"past"}
{"ts":"2025-12-18T14:34:10Z","run_id":"run-8f3a","opportunity_id":"006...","action":"scorecard_upserted","scorecard_id":"sc_..."}
```

**summary.json:**
```json
{
  "run_id": "run-8f3a",
  "started_at": "2025-12-18T14:32:10Z",
  "finished_at": "2025-12-18T14:41:55Z",
  "opps_selected": 50,
  "meetings_created": 280,
  "emails_created": 640,
  "scorecards_created": 50,
  "scorecard_answers_written": 950,
  "failures": 3,
  "coverage": 0.86
}
```

## Workflow Examples

### First-Time Demo Setup

1. Configure your target opportunities in `demo.yaml`
2. Run dry-run to preview:
   ```bash
   demo-gen dry-run -c demo.yaml
   ```
3. Execute the generation:
   ```bash
   demo-gen run -c demo.yaml
   ```
4. Wait for People.ai ingestion (check `peopleai.expected_latency_minutes`)
5. Verify in People.ai that activities appear on opportunities

### Smoke Test Before Full Run

Test ingestion pipeline with a single opportunity first:

```bash
demo-gen smoke -c demo.yaml --opp-id 006ABC123000001
```

Check the output for created record IDs, then verify they appear in People.ai.

### Refreshing Stale Demo Data

If your demo environment has been reset or gone stale:

1. Update `close_date_range` in `demo.yaml` if needed
2. Run with same seed for consistency:
   ```bash
   demo-gen run -c demo.yaml
   ```
3. Idempotency ensures only new/missing data is created

## Idempotency Modes

### External State (Recommended)

Uses SQLite database to track created records:

```yaml
run:
  idempotency_mode: "external_state"
```

- **Pros:** Works with any Salesforce org, no custom fields needed
- **Cons:** Cleanup/reset only deletes Events/Tasks tracked in state.sqlite

### Tag-Based

Tags records with run ID using a custom field:

```yaml
run:
  idempotency_mode: "tag"
  run_tag_field: "Demo_Run_Id__c"
```

- **Pros:** Enables cleanup of tagged Events/Tasks via `reset` command
- **Cons:** Requires custom field on Activity objects

## Troubleshooting

### Activities Not Appearing in People.ai

1. Verify activities were created in Salesforce (check event logs)
2. Confirm activities have correct `WhatId` (opportunity) and `OwnerId`
3. Check People.ai ingestion settings - ensure CRM activities are enabled
4. Wait for `expected_latency_minutes` before checking

### LLM Content Generation Failing

1. Verify `OPENAI_API_KEY` is set correctly
2. Check API quota/rate limits
3. Set `llm.enabled: false` to use heuristic content only

### Salesforce Authentication Issues

1. Verify credentials in `.env` are correct
2. Check security token is current (reset if IP changed)
3. Ensure API access is enabled for your user
4. Verify instance URL format: `https://your-instance.my.salesforce.com`

### Permission Errors

Ensure your Salesforce user has:
- Read access to Opportunities, Accounts, Contacts
- Create access to Events and Tasks
- API Enabled permission

## Architecture

### Module Overview

- **[config.py](src/demo_gen/config.py)** - Configuration schema and validation
- **[logger.py](src/demo_gen/logger.py)** - JSONL structured logging
- **[state_store.py](src/demo_gen/state_store.py)** - SQLite-based idempotency
- **[sf_client.py](src/demo_gen/sf_client.py)** - Salesforce API wrapper
- **[activity_planner.py](src/demo_gen/activity_planner.py)** - Deterministic activity planning
- **[content_gen.py](src/demo_gen/content_gen.py)** - LLM content generation
- **[scorecard_client.py](src/demo_gen/scorecard_client.py)** - Scorecard creation and population
- **[runner.py](src/demo_gen/runner.py)** - Main orchestration logic
- **[cli.py](src/demo_gen/cli.py)** - Command-line interface

### Data Flow

```
Load Config → Query Opportunities → For each Opportunity:
  ├─ Plan Activities (deterministic)
  ├─ Generate Content (LLM optional)
  ├─ Create Meetings & Emails in Salesforce
  ├─ Create Scorecards
  └─ Log Events & Update State
```

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest
```

### Code Formatting

```bash
black src/
ruff check src/
```

## Contributing

This is an internal tool. Contact the Sales Engineering team for questions or enhancement requests.

## License

Internal use only.

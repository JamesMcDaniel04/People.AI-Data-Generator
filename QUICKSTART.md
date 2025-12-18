# Quick Start Guide

Get your demo environment up and running in 5 minutes.

## Installation

```bash
# 1. Clone and enter directory
git clone <repo-url>
cd People.AI-Data-Generator

# 2. Set up Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install
pip install -e .
```

## Configuration

```bash
# 1. Copy example files
cp demo.example.yaml demo.yaml
cp .env.example .env

# 2. Edit .env with your credentials
# Required:
SF_USERNAME=your.email@company.com
SF_PASSWORD=your_password
SF_SECURITY_TOKEN=your_security_token

# Optional (for realistic content):
OPENAI_API_KEY=sk-...

# 3. Edit demo.yaml
# At minimum, update:
# - salesforce.instance_url
# - salesforce.query.close_date_range
```

## First Run

### Step 1: Dry Run

Preview what will be created:

```bash
demo-gen dry-run -c demo.yaml
```

This shows you how many opportunities will be selected and what activities would be created.

### Step 2: Smoke Test

Test with a single opportunity to verify Salesforce + People.ai integration:

```bash
# Find an opportunity ID from your sandbox
demo-gen smoke -c demo.yaml --opp-id 006YOUROPPIDHERE
```

This creates:
- 1 meeting
- 1 email
- 1 scorecard

**Wait 60 minutes** (or your configured `peopleai.expected_latency_minutes`), then check People.ai to confirm the activities appear.

### Step 3: Full Run

Once smoke test confirms ingestion works:

```bash
demo-gen run -c demo.yaml
```

This processes all opportunities matching your query criteria.

### Step 4: Check Results

```bash
# View summary
demo-gen status --run-id <run-id-from-output>

# Or inspect the detailed logs
ls runs/
cat runs/2025-12-18T14-32-10Z_se-demo-pack_run-8f3a/summary.json
```

## Common Configurations

### Minimal (No LLM)

For quick testing without OpenAI:

```yaml
llm:
  enabled: false

activity:
  realism_level: "none"

scorecards:
  mode: "heuristic"
```

### Maximum Realism

For demos where content quality matters:

```yaml
llm:
  enabled: true
  model: "gpt-4o"

activity:
  realism_level: "heavy"
  meetings:
    past_max: 12
  emails:
    max: 30

scorecards:
  mode: "llm"
  coverage_target: 0.95
```

### Safe Production

Conservative settings for production demo environments:

```yaml
run:
  idempotency_mode: "external_state"

salesforce:
  query:
    limit: 50  # Cap total opportunities

activity:
  meetings:
    past_max: 5
  emails:
    max: 10

# Add to CLI:
# demo-gen run -c demo.yaml --max-opps 50 --concurrency 3
```

## Troubleshooting

### Issue: "Missing Salesforce credentials"

**Solution:** Ensure `.env` file exists and contains all three SF variables.

### Issue: Activities created but not in People.ai

**Solution:**
1. Check Salesforce - do the activities have correct WhatId/OwnerId?
2. Verify People.ai CRM activity ingestion is enabled
3. Wait the full `expected_latency_minutes`
4. Check People.ai ingestion logs for errors

### Issue: "No opportunities found"

**Solution:**
1. Verify your query criteria in `demo.yaml`
2. Check close_date_range includes valid dates
3. Ensure opportunities exist in those stages
4. Try running query directly in Salesforce workbench

### Issue: LLM generation fails

**Solution:**
1. Verify OPENAI_API_KEY is valid
2. Set `llm.enabled: false` to continue without LLM
3. Check OpenAI API status and rate limits

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Customize activity subjects in [activity_planner.py](src/demo_gen/activity_planner.py)
- Add custom scorecard templates in [scorecard_client.py](src/demo_gen/scorecard_client.py)
- Set up scheduled runs for automatic demo refresh

## Getting Help

- Check logs in `runs/<run-directory>/errors.jsonl`
- Review configuration against [demo.example.yaml](demo.example.yaml)
- Contact Sales Engineering team for assistance

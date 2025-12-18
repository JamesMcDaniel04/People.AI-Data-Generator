# Future Enhancements

This file tracks potential improvements and features for future versions.

## High Priority (Next Sprint)

- [ ] **Add progress bars** - Show real-time progress during runs (rich.progress)
- [x] **Implement true parallelization** - Use ThreadPoolExecutor for concurrent API calls
- [ ] **People.ai API integration** - Verify activities are ingested (if API available)
- [ ] **Better error recovery** - Retry logic for transient failures
- [x] **Complete reset command** - Full cleanup implementation for tag mode

## Medium Priority (Next Month)

- [ ] **Additional scorecard templates**
  - [ ] BANT
  - [ ] MEDDPICC (extended MEDDICC)
  - [ ] Custom template support via YAML
- [ ] **Contact auto-generation** - Create contacts if none exist
- [ ] **Activity subject customization** - User-defined subject templates in config
- [ ] **Enhanced content generation**
  - [ ] Context awareness across activities
  - [ ] Deal stage-appropriate content
  - [ ] Company/industry-specific language
- [ ] **Reporting dashboard** - HTML report generation with charts
- [ ] **Configuration validation** - Pre-flight checks before run
- [ ] **Incremental updates** - Only update changed opportunities

## Low Priority (Future)

- [ ] **Web UI** - Browser-based configuration and monitoring
- [ ] **Scheduled runs** - Cron-style automation
- [ ] **Multi-org support** - Orchestrate across multiple Salesforce orgs
- [ ] **State export/import** - Share state between environments
- [ ] **Diff mode** - Compare runs and show what changed
- [ ] **Notifications** - Slack/Teams integration
- [ ] **Webhooks** - Trigger external workflows
- [ ] **Cloud deployment** - AWS Lambda / Google Cloud Run
- [ ] **Account hierarchy** - Support parent/child accounts
- [ ] **Product configuration** - Add opportunity products
- [ ] **Custom object support** - Beyond standard objects

## Technical Debt

- [ ] **Add integration tests** - End-to-end testing with mock Salesforce
- [ ] **Improve test coverage** - Aim for 80%+ coverage
- [ ] **Add type hints everywhere** - Full mypy compliance
- [ ] **Performance profiling** - Identify bottlenecks
- [ ] **Memory optimization** - Handle large datasets efficiently
- [ ] **Logging levels** - Configurable verbosity (DEBUG, INFO, WARN, ERROR)
- [ ] **Config schema docs** - Auto-generate from Pydantic models
- [ ] **CLI help improvements** - Better examples and usage info

## Documentation Improvements

- [ ] **Video walkthrough** - Screen recording of setup and usage
- [ ] **Troubleshooting guide** - Common issues and solutions (expand current section)
- [ ] **FAQ** - Frequently asked questions
- [ ] **API documentation** - For extending with custom modules
- [ ] **Best practices guide** - Recommendations for production use
- [ ] **Migration guide** - Upgrading between versions

## Ideas / Discussion Needed

- [ ] **Activity sequencing** - Ensure emails follow logical meeting flow
- [ ] **Deal momentum simulation** - Vary activity frequency by stage
- [ ] **Negative cases** - Include stalled/lost deals with appropriate patterns
- [ ] **Competitive intelligence** - Track competitor mentions in activities
- [ ] **Multi-threading config** - Per-module concurrency controls
- [ ] **Plugin system** - Allow custom activity generators
- [ ] **Template marketplace** - Share scorecard/activity templates
- [ ] **AI coach integration** - Generate coaching insights for demo

## Known Issues

- [ ] **Rate limiting** - Add backoff/retry for API rate limits
- [ ] **Timezone handling** - Currently uses UTC, may need local TZ support
- [ ] **Large dataset memory** - Loading 1000+ opps could be problematic
- [ ] **Error messages** - Some errors could be more user-friendly
- [ ] **Windows compatibility** - Test and fix path issues

## Community Requests

(Add requests from users here as they come in)

---

## Contributing

When adding to this file:
1. Choose appropriate priority level
2. Add checkbox for tracking
3. Include brief description
4. Link to related issues/PRs if applicable

When implementing:
1. Check off the item
2. Update CHANGELOG.md
3. Add to release notes
4. Consider if docs need updates

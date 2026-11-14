# Quiz — AWS CloudWatch Observability

Test yourself. No peeking — answers are collapsed at the bottom.

## Questions

**1. Metrics, logs, traces: which pillar answers "which microservice made this request slow"?**

- A. Metrics
- B. Logs
- C. Traces (X-Ray)
- D. Alarms

**2. Your log group has the default retention setting. What is the billing risk?**

- A. None — CloudWatch deletes logs after 7 days by default
- B. Logs are kept forever (`Never Expire`) and the storage bill grows silently
- C. Logs stop being ingested after 30 days
- D. Retention only applies to metrics, not logs

**3. An alarm fires every Monday at 09:00 when traffic spikes, and the team now ignores it. What is the *right* fix?**

- A. Delete the alarm
- B. Mute it on Mondays
- C. Replace the fixed threshold with anomaly detection (or a threshold that accounts for the weekly pattern), so it only fires on genuinely abnormal Mondays
- D. Raise the threshold to a value it never reaches

**4. Why should an alarm trigger on error *rate* (errors / requests) rather than raw error count?**

- A. Raw counts are not supported by CloudWatch alarms
- B. A raw count fires during normal traffic growth even when the system is healthy; the rate stays meaningful as traffic scales
- C. Error rate is cheaper to evaluate
- D. Metric math alarms cannot use raw counts

**5. You need to find the 10 slowest requests in the last hour from application logs. What is the fastest way?**

- A. Download all log files and grep them locally
- B. A CloudWatch Logs Insights query with `sort` and `limit`
- C. Create a metric filter for every request
- D. Enable X-Ray sampling at 100% and wait an hour

---

## Answers

<details>
<summary>Click to reveal answers</summary>

**1. C — Traces (X-Ray).** Metrics tell you *something* is slow, logs tell you *what* happened, traces show *where* the time went across services.

**2. B — Logs are kept forever.** The default retention is `Never Expire`. Set an explicit retention (e.g. 30 days) and archive to S3 for anything you must keep longer.

**3. C — Anomaly detection / pattern-aware threshold.** A noisy alarm trains the team to ignore all alarms. Fix the signal, not the messenger — deleting it (A) or muting it (B) hides real incidents too.

**4. B — Raw counts scale with traffic.** 100 errors out of 1,000 requests is a 10% outage; 100 errors out of 1,000,000 requests is noise. The rate is what matters.

**5. B — Logs Insights.** It queries centralised logs in seconds with a SQL-like syntax — no downloading, no grep across dead instances.

</details>

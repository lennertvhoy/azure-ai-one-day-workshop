# Incident Report IR-002

Incident ID: IR-002
Date: 2026-02-09
System: Internal Knowledge Search
Severity: Medium

## Summary
Search latency exceeded SLO for 42 minutes due to index hot partitioning.

## Impact
- Slower response times for internal users
- No data loss

## Corrective Actions
- Re-balance partition strategy
- Add alert for partition skew
- Review chunking policy for large ingests
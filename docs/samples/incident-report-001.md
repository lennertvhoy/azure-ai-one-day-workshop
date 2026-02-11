# Incident Report IR-001

Incident ID: IR-001
Date: 2026-02-08
System: Customer Portal API
Severity: High

## Summary
Users experienced intermittent 500 errors for 27 minutes.

## Timeline
```mermaid
flowchart TD
  A[09:03 Alert Triggered] --> B[09:07 On-call Acknowledged]
  B --> C[09:12 Root Cause Isolated]
  C --> D[09:30 Fix Deployed]
  D --> E[09:32 Service Stable]
```

## Root Cause
A stale cache key mapping caused invalid downstream routing.

## Corrective Actions
- Add cache key schema validation
- Add synthetic health probes
- Update rollback runbook
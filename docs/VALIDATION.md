# Validation record

Date: 1 November 2026. This records observed checks, not a production-readiness certificate.

## Executed locally

- Python 3.11+ standard-library test suite: **28 tests passed** on Windows. Includes real HTTP requests against a temporary loopback server, role boundaries, browser-Origin/Host rejection, request limits, invoice arithmetic, business duplicates, idempotent conflicts, concurrent delivery, two-reviewer policy, final rejections, input minimisation, malformed model output/timeouts, HMAC modification detection and retention deletion.
- Node.js native test runner: **6 tests passed**. Executes the actual exported n8n Code-node JavaScript with the n8n input shape, checks metadata/credential removal and unknown-field rejection, and validates workflow graph, authentication settings and inactive import state.
- Offline end-to-end domain demo: both flows create records, invoice enters `awaiting_second_review` after the first approval and `approved` after the second; retained audit signatures verify.
- Anthropic HTTP adapter tested using mocked responses and captured outbound request objects. These tests verify fixed host, timeout, feature-only payload, rejection of oversized/incomplete/tool output and redirect denial. **No live Anthropic request or billable model call has been made.**

## Separate n8n runtime gate

Workflow JSON uses native Webhook, Code, HTTP Request and Respond to Webhook nodes. Target for import validation: n8n 2.45.7. Native n8n installation/import is checked separately from the JavaScript tests; its final result must be recorded here before claiming a runtime import or full workflow execution.

Neither a structural graph check nor execution of a Code-node script proves a complete live n8n workflow. No authenticated live webhook-to-model-to-client delivery is claimed. The examples deliberately have no client delivery action.

## Not tested / not supplied

- Real provider model quality, external account configuration or provider processing terms.
- Production hosting, TLS termination, multiple tenants, scale/failover, identity lifecycle, operational alerting, encryption-at-rest or backup restore.
- Legal invoice/GDPR assessment, tax correctness, supplier verification or actual payments.
- Audit deletion/truncation resistance: individual signatures cannot provide this property.

## Reproduce

```sh
python -m unittest discover -v
node --test tests/workflows.test.mjs
python scripts/build_workflows.py
git diff --exit-code -- workflows
python -m automation.demo
```

Use only synthetic input when evaluating the optional n8n runtime. Do not place real secrets or customer examples in an exported workflow or test report.

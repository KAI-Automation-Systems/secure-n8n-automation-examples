# Security properties and limits

Scope: these two portfolio demos and their local gateway. No security certification or independent audit has been performed.

## Trust boundaries

Source JSON, model outputs and retries are untrusted. n8n is an orchestrator with an ingest-only credential. The gateway owns all state transitions. Two separate reviewer credentials map to fixed server-side identities. OS administrators, the repository developer, the local filesystem and secret holders are trusted for this demo. There is no multi-tenant isolation claim.

## Implemented controls

- Constant-time token comparison, distinct mandatory secrets and no default server credentials.
- Ingest tokens cannot read or approve jobs; reviewer tokens cannot create them. Actor identity is not client-controlled.
- Loopback bind, host allowlist and browser-Origin rejection. No CORS. Service is not suitable for internet exposure.
- Strict field sets, body and text limits, duplicate JSON key / nonfinite number rejection, bounded identifiers.
- No arbitrary URLs, callbacks, file paths, shell execution, model tools, uploads, bank details or automatic sending.
- Model egress only contains three booleans. The optional provider host is fixed; redirects/proxy inheritance are disabled. Timeout, response-size limit and allowlisted output schema fail to manual review.
- SQLite parameterised values and atomic transactions for deduplication, business invoice uniqueness, decisions and audit events.
- Two approvals above the configured EUR 1,000 threshold. No self-supplied approver IDs; repeated same-actor approval doesn't count twice. This is not enterprise SSO separation of duties.
- No request/provider/body logging. Workflow payload persistence disabled. No secrets or pinned data in exports.
- Per-event HMAC audit signatures. Anyone with database access but without the key can delete records; the signature check does **not** detect deletion or prove completeness.
- Offline maintenance supports deletion of jobs and related records. Operator must schedule retention and cover backups/WAL files.
- CI has read-only repository permission; checkout action is commit-pinned and does not persist a Git credential. No third-party Python package dependencies.

## Known limitations and deployment requirements

The HTTP server is intentionally a single-process local reference service. Its per-process, global 120-requests/minute guard is not a distributed rate limiter; malformed unauthenticated traffic can consume the budget. A slow connection/model call can delay other work. TLS, proxy-level limits, durable queues, retries/backoff and monitoring are production work, not hidden assumptions.

SQLite/HMAC do not encrypt invoice data. Use encrypted storage and strict ACLs. Rotation of `AUDIT_KEY` breaks old audit verification and idempotency lookup unless migrated; coordinate key rotation with retained records. Dedupe lasts only as long as its retained job. Purging a job allows replay afterwards; upstream event retention and replay windows must be designed for production.

Reviewer tokens are long-lived shared demo secrets. A real deployment needs individual short-lived identities, MFA, revocation, role lifecycle and per-tenant authorisation. The second reviewer must be a real different person in the organisation; two secret strings cannot establish that fact.

The invoice gate validates arithmetic and workflow policy, not supplier authenticity, legal invoice requirements, VAT entitlement, fraud, OCR accuracy or authority to pay. `approved` has no external side effect. Do not connect it to a payment system without a separate design and review.

The LLM sees no raw message. Boolean features still reveal coarse business context and are not a legal guarantee of anonymisation. Prompt-injection text cannot become a model instruction because no input text is forwarded; it may still manipulate the keyword signals and produce incorrect suggestions. Human reviewers must check the authoritative source separately.

n8n editor users may change workflows. Credentials and logging depend on the operator's n8n setup. Workflow-level settings do not retroactively delete earlier logs or suppress upstream monitoring. Do not use real personal data for a manual demo.

## Reporting

Do not put secrets or personal data in public issues. Report a reproducible issue without sensitive data to `kevin@kai-automation.com`. This contact instruction is not consent to send unsolicited messages.

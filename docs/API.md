# Reference API

Run on `127.0.0.1:8080` only. JSON POSTs require `Content-Type: application/json`, one Content-Length, at most 12 KiB, and `Authorization: Bearer <role token>`. No query strings, Origin, transfer encoding or arbitrary fields are accepted.

## Request triage

`POST /v1/intakes` with ingest credential:

```json
{"event_id":"request-demo-001","subject":"API Fehler","body":"Synthetische Anfrage: der Workflow hat einen Fehler."}
```

Response: job `id`, `kind`, `state`, and category/priority only. Raw input is discarded after processing. Model errors return `manual_review`; successful suggestions return `pending_review`. Neither state authorises external action.

## Invoice review

`POST /v1/invoices` with ingest credential:

```json
{"event_id":"invoice-demo-001","supplier_ref":"supplier-demo","invoice_ref":"invoice-demo-001","currency":"EUR","net":"1000.00","tax":"200.00","gross":"1200.00"}
```

Use opaque supplier/invoice references, not names, addresses, IBANs or document content. Amounts must be decimal **strings** with exactly two places, no signs or separators, and no more than seven integer digits. Gross must be positive. Net plus tax must equal gross. Amounts are stored as integer cents. An invoice of EUR 1,000 or more requires two reviews; smaller ones require one. This is a demonstration policy, not a legal rule.

## Review

`GET /v1/jobs/{id}` requires a reviewer credential. `POST /v1/jobs/{id}/decision` accepts only `{"decision":"approve"}` or `{"decision":"reject"}`. Actor is inferred from the token, never from JSON. Repeating the same actor/decision is idempotent. A conflicting decision or decision after a final state returns 409. A rejection is final.

Common status codes: 200 success/replay, 400 malformed framing/JSON, 401 bad/missing authentication, 403 wrong role/origin, 404 unknown route/job, 409 duplicate/conflict, 413 body too large, 415 wrong content type, 422 invalid fields/amounts, 429 local budget exhausted, 500 internal failure with no details. Unknown fields, including `approved`, `actor`, `callback_url` and `iban`, are rejected.

Same event and same validated full input returns the current job without reclassification. Same event with changed input returns 409. Same supplier/invoice reference with a new event returns 409 even if the amount changes. Dedupe is scoped to this single local database, not multiple independent deployments.

## Maintenance

After loading gateway environment variables, from the repository root:

```sh
python -m scripts.maintenance verify
python -m scripts.maintenance purge --older-than-days 7
```

Purge deletes retained jobs, their decisions and audit events. It is not a legal archival mechanism; do not use real accounting records. Secure deletion from SSDs, SQLite WAL, OS backups and external monitoring is outside this command. Configure those layers separately.

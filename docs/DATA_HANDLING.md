# Data handling and deployment checklist

These demos implement technical controls relevant to privacy-conscious automation. They do not establish a lawful basis or certify GDPR compliance. No real personal data is needed to run or assess them.

## Request example

Subject and body exist transiently in the source, n8n execution memory and gateway memory. They are used for local keyword signals. The database stores only category, priority, status, random job ID, keyed input/event fingerprints and audit metadata. The optional model provider receives three boolean signals only. Keyed fingerprints reduce guessing without the key; they are still not a guarantee of anonymisation.

The demo discards contact information and has no message-delivery capability. Reviewers must consult their authoritative source outside this demo. A customer implementation would need an access-controlled reference to that source and its retention process; it should not duplicate the raw text by default.

## Invoice example

The database stores opaque supplier/invoice references, EUR amounts in cents, state, timestamps, fingerprints and demo reviewer decisions. The caller is responsible for using opaque references; validation alone cannot prove a reference contains no personal data. No PDF, bank details or tax identity is accepted. This is not a legally required invoice archive.

## Retention

Synthetic demo databases can be deleted completely after evaluation. For a longer demo, schedule `python -m scripts.maintenance purge --older-than-days 7` under the same restricted account. Nothing runs this automatically. Seven days is a demo configuration, not a lawful retention recommendation. Deletion expires deduplication. Include WAL files, replicas, exports, logs and backups in any real deletion procedure.

## Before using real data

Establish controller/processor roles and purpose, lawful basis, minimisation, access/identity controls, retention, rights handling, incident response, audit completeness and contractual arrangements. For external models, review the provider agreement, processing location, transfers, retention, account settings and subprocessor list before enabling egress. Assess whether a DPIA or sector-specific requirements apply to the actual deployment. These are unresolved operator decisions, not assurances supplied by this code.

Use TLS and network restrictions, a maintained production server, encrypted storage, individual reviewer accounts, reliable backups, monitoring without payload leakage, tested restore/rotation procedures and appropriate tenancy boundaries. Do not treat a green test suite as evidence that these organisational and legal requirements have been met.

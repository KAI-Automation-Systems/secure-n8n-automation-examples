"""Validation, minimisation and transaction boundaries shared by both examples."""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path


class Rejected(Exception):
    def __init__(self, code: str, status: int = 422):
        self.code, self.status = code, status
        super().__init__(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def strict_json(raw: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Rejected("duplicate_json_key", 400)
            result[key] = value
        return result
    try:
        return json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise Rejected("invalid_json", 400) from None


def exact(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise Rejected("invalid_fields")


def text(value, limit):
    if not isinstance(value, str) or not 1 <= len(value) <= limit:
        raise Rejected("invalid_text")
    if any(ord(c) < 32 and c not in "\n\t\r" for c in value):
        raise Rejected("control_character")
    return value


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", value):
        raise Rejected("invalid_identifier")
    return value


def intake_features(payload):
    exact(payload, {"event_id", "subject", "body"})
    event = identifier(payload["event_id"])
    content = (text(payload["subject"], 160) + " " + text(payload["body"], 8000)).casefold()
    # Only booleans cross the model boundary. Names, addresses, body and subject
    # never leave this process. This is feature minimisation, not PII detection.
    features = {
        "billing": bool(re.search(r"\b(invoice|rechnung|zahlung|billing)\b", content)),
        "technical": bool(re.search(r"\b(api|webhook|workflow|fehler|error)\b", content)),
        "urgent": bool(re.search(r"\b(urgent|dringend|ausfall|outage)\b", content)),
    }
    return event, features


def classify(features, provider):
    try:
        result = provider.classify(features)
        exact(result, {"category", "priority"})
        if result["category"] not in {"billing", "technical", "general"}:
            raise Rejected("invalid_model_output")
        if result["priority"] not in {"normal", "high"}:
            raise Rejected("invalid_model_output")
        return result, "pending_review"
    except Exception:
        # No raw model output, exception or provider response is persisted/logged.
        return {"category": "general", "priority": "normal"}, "manual_review"


def cents(value):
    if not isinstance(value, str) or not re.fullmatch(r"(?:0|[1-9][0-9]{0,6})\.[0-9]{2}", value):
        raise Rejected("invalid_money")
    return int(Decimal(value) * 100)


def invoice_data(payload):
    exact(payload, {"event_id", "supplier_ref", "invoice_ref", "currency", "net", "tax", "gross"})
    event = identifier(payload["event_id"])
    supplier, reference = identifier(payload["supplier_ref"]), identifier(payload["invoice_ref"])
    if payload["currency"] != "EUR":
        raise Rejected("unsupported_currency")
    net, tax, gross = (cents(payload[k]) for k in ("net", "tax", "gross"))
    if net + tax != gross or gross <= 0:
        raise Rejected("totals_mismatch")
    # Arithmetic check only: tax entitlement/rates and supplier authenticity are
    # not inferred. No IBAN, account details, OCR upload or payment instruction.
    return event, {"supplier_ref": supplier, "invoice_ref": reference,
                   "currency": "EUR", "net_cents": net, "tax_cents": tax,
                   "gross_cents": gross, "requires_dual_review": gross >= 100000}


class Store:
    def __init__(self, path: str, key: bytes):
        if len(key) < 32:
            raise ValueError("A separate >=32-byte HMAC key is required")
        self.path, self.key = str(path), key
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS jobs (
              id TEXT PRIMARY KEY, kind TEXT NOT NULL, event_hash TEXT NOT NULL,
              fingerprint TEXT NOT NULL, business_hash TEXT UNIQUE,
              data TEXT NOT NULL, state TEXT NOT NULL, created INTEGER NOT NULL,
              UNIQUE(kind,event_hash));
            CREATE TABLE IF NOT EXISTS decisions (
              job_id TEXT NOT NULL, actor TEXT NOT NULL, decision TEXT NOT NULL,
              UNIQUE(job_id,actor));
            CREATE TABLE IF NOT EXISTS audit (
              id INTEGER PRIMARY KEY, event TEXT NOT NULL, signature TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def digest(self, value):
        return hmac.new(self.key, value.encode(), hashlib.sha256).hexdigest()

    def audit(self, db, action, job_id, actor="system"):
        event = canonical({"action": action, "job_id": job_id, "actor": actor,
                           "at": int(time.time())})
        db.execute("INSERT INTO audit(event,signature) VALUES (?,?)", (event, self.digest(event)))

    def ingest(self, kind, payload, provider):
        if kind == "intake":
            event, data = intake_features(payload)
            business_hash = None
        elif kind == "invoice":
            event, data = invoice_data(payload)
            business_hash = self.digest("invoice:" + data["supplier_ref"] + ":" + data["invoice_ref"])
        else:
            raise Rejected("unknown_kind", 404)
        # Bind the key to the complete validated input, not just reduced features.
        fingerprint = self.digest(canonical(payload))
        event_hash = self.digest(kind + ":" + event)
        with self.connect() as db:
            # Serialises duplicate checks, model invocation and insert. Intended
            # for low-volume local demos; not a distributed queue implementation.
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute("SELECT * FROM jobs WHERE kind=? AND event_hash=?", (kind, event_hash)).fetchone()
            if existing:
                if existing["fingerprint"] != fingerprint:
                    raise Rejected("idempotency_conflict", 409)
                return self.public(existing)
            if business_hash and db.execute("SELECT 1 FROM jobs WHERE business_hash=?", (business_hash,)).fetchone():
                raise Rejected("duplicate_invoice", 409)
            state = "pending_review"
            if kind == "intake":
                data, state = classify(data, provider)
            job_id = str(uuid.uuid4())
            db.execute("INSERT INTO jobs(id,kind,event_hash,fingerprint,business_hash,data,state,created) VALUES (?,?,?,?,?,?,?,?)",
                       (job_id, kind, event_hash, fingerprint, business_hash,
                        canonical(data), state, int(time.time())))
            self.audit(db, "created", job_id)
            return self.public(db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())

    @staticmethod
    def public(row):
        return {"id": row["id"], "kind": row["kind"], "state": row["state"],
                "data": json.loads(row["data"])}

    def get(self, job_id):
        with self.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise Rejected("not_found", 404)
            return self.public(row)

    def decide(self, job_id, actor, decision):
        if not isinstance(actor, str) or not isinstance(decision, str) or actor not in {"reviewer_a", "reviewer_b"} or decision not in {"approve", "reject"}:
            raise Rejected("invalid_decision")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                raise Rejected("not_found", 404)
            prior = db.execute("SELECT decision FROM decisions WHERE job_id=? AND actor=?", (job_id, actor)).fetchone()
            if prior:
                if prior["decision"] != decision:
                    raise Rejected("decision_conflict", 409)
                return self.public(row)
            if row["state"] in {"approved", "rejected"}:
                raise Rejected("already_final", 409)
            db.execute("INSERT INTO decisions VALUES (?,?,?)", (job_id, actor, decision))
            approvals = db.execute("SELECT COUNT(*) FROM decisions WHERE job_id=? AND decision='approve'", (job_id,)).fetchone()[0]
            needed = 2 if json.loads(row["data"]).get("requires_dual_review") else 1
            state = "rejected" if decision == "reject" else ("approved" if approvals >= needed else "awaiting_second_review")
            db.execute("UPDATE jobs SET state=? WHERE id=?", (state, job_id))
            self.audit(db, decision, job_id, actor)
            return self.public(db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())

    def verify_audit(self):
        with self.connect() as db:
            return all(hmac.compare_digest(self.digest(r["event"]), r["signature"])
                       for r in db.execute("SELECT * FROM audit"))

    def purge(self, before):
        # Bounded demo retention: delete all three record types, including final
        # jobs. This is not a statutory invoice archive. Caller supplies cutoff.
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            ids = [r[0] for r in db.execute("SELECT id FROM jobs WHERE created < ?", (before,))]
            for job_id in ids:
                db.execute("DELETE FROM decisions WHERE job_id=?", (job_id,))
                # Audit event structure is owned here, not supplied by clients.
                db.execute("DELETE FROM audit WHERE json_extract(event,'$.job_id')=?", (job_id,))
                db.execute("DELETE FROM jobs WHERE id=?", (job_id,))
            return len(ids)

"""Offline demonstration using synthetic data; no server or secrets needed."""
import json
import tempfile
from pathlib import Path

from .core import Store
from .providers import OfflineProvider


def main():
    with tempfile.TemporaryDirectory() as directory:
        store = Store(str(Path(directory) / "demo.sqlite"), b"local-demo-only-not-a-deployment-key")
        triage = store.ingest("intake", {"event_id": "demo-request-001", "subject": "Webhook Fehler",
                            "body": "Synthetisches Beispiel: unser Workflow hat einen Fehler."}, OfflineProvider())
        invoice = store.ingest("invoice", {"event_id": "demo-invoice-001", "supplier_ref": "supplier_demo",
                            "invoice_ref": "invoice_demo_001", "currency": "EUR", "net": "1000.00",
                            "tax": "200.00", "gross": "1200.00"}, OfflineProvider())
        first = store.decide(invoice["id"], "reviewer_a", "approve")
        final = store.decide(invoice["id"], "reviewer_b", "approve")
        print(json.dumps({"triage": triage, "invoice_first_review": first,
                          "invoice_final_review": final, "audit_valid": store.verify_audit()}, indent=2))


if __name__ == "__main__":
    main()

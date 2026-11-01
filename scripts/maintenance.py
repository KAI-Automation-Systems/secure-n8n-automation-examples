"""Offline administrative maintenance, explicitly separate from the HTTP API."""
import argparse
import os
import time

from automation.core import Store

p = argparse.ArgumentParser()
p.add_argument('action', choices=['verify', 'purge'])
p.add_argument('--older-than-days', type=int, default=7)
args = p.parse_args()
if not 1 <= args.older_than_days <= 365:
    p.error('Retention must be between 1 and 365 days')
store = Store(os.environ.get('DATABASE_PATH', 'var/demo.sqlite'), os.environ['AUDIT_KEY'].encode())
if args.action == 'verify':
    if not store.verify_audit():
        raise SystemExit('Audit signature mismatch')
    print('All retained audit event signatures match. Deletion/truncation is not detectable.')
else:
    print('Purged jobs:', store.purge(int(time.time()) - args.older_than_days * 86400))

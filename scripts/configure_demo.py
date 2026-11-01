"""Generate a local ignored PowerShell secret file, without printing secrets."""
import secrets
from pathlib import Path

target = Path('var') / 'secrets.ps1'
target.parent.mkdir(exist_ok=True)
if target.exists():
    raise SystemExit('Secret file already exists; rotate deliberately, never overwrite silently.')
target.write_text('\n'.join("$env:" + key + "='" + secrets.token_urlsafe(36) + "'"
                           for key in ['INGEST_TOKEN', 'REVIEWER_A_TOKEN', 'REVIEWER_B_TOKEN', 'AUDIT_KEY']) + '\n', encoding='utf-8')
try:
    target.chmod(0o600)
except OSError:
    pass
print('Created var/secrets.ps1. On Windows restrict its ACL to your own account. Never commit it.')

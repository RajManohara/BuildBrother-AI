"""Create local-only credentials without printing or committing them."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if not target.exists():
    text = (root / ".env.example").read_text(encoding="utf-8")
    text = text.replace("replace-with-local-password", secrets.token_urlsafe(24))
    text = text.replace("replace-with-ingest-token", secrets.token_urlsafe(32))
    text = text.replace("replace-with-app-key", secrets.token_urlsafe(32))
    target.write_text(text, encoding="utf-8")
    print("Created .env with local random credentials.")
else:
    print("Preserved existing .env.")
values = {}
for line in target.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.startswith("#"):
        key, value = line.split("=", 1)
        values[key] = value
frontend = root / "frontend" / ".env.local"
if not frontend.exists():
    frontend.write_text("\n".join(f"{key}={values.get(key, '')}" for key in
        ("BACKEND_URL", "APP_API_KEY", "INGEST_TOKEN")) + "\n", encoding="utf-8")
    print("Created frontend/.env.local with matching server-side credentials.")
else:
    print("Preserved existing frontend/.env.local; keep its keys aligned with .env.")

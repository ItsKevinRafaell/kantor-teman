#!/usr/bin/env python3
"""
Sync /home/qqwtlphb/backend/uploads -> Cloudflare R2.

Run via cron on VPS temanumkm-vps (NOT on shared hosting).
Env:
  R2_ENDPOINT  (e.g. https://<accountid>.r2.cloudflarestorage.com)
  R2_ACCESS_KEY_ID
  R2_SECRET_ACCESS_KEY
  R2_BUCKET    (default: kantorteman-uploads)
  LOCAL_UPLOADS_DIR (default: /home/qqwtlphb/backend/uploads)
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

try:
    import boto3
except ImportError:
    print("boto3 not installed. pip install boto3", file=sys.stderr)
    sys.exit(1)

LOCAL = Path(os.environ.get("LOCAL_UPLOADS_DIR", "/home/qqwtlphb/backend/uploads"))
BUCKET = os.environ.get("R2_BUCKET", "kantorteman-uploads")
ENDPOINT = os.environ.get("R2_ENDPOINT", "")
KEY = os.environ.get("R2_ACCESS_KEY_ID", "")
SECRET = os.environ.get("R2_SECRET_ACCESS_KEY", "")

if not ENDPOINT or not KEY or not SECRET:
    print("Missing R2 env vars. Set R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY.", file=sys.stderr)
    sys.exit(1)

if not LOCAL.exists():
    print(f"Local uploads dir not found: {LOCAL}", file=sys.stderr)
    sys.exit(1)

s3 = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    aws_access_key_id=KEY,
    aws_secret_access_key=SECRET,
    region_name="auto",
)

uploaded = 0
skipped = 0
errors = 0
start = datetime.now(timezone.utc).isoformat()

print(f"[{start}] Starting sync {LOCAL} -> r2://{BUCKET}/")

for path in LOCAL.rglob("*"):
    if not path.is_file():
        continue
    rel = path.relative_to(LOCAL)
    key = str(rel).replace(os.sep, "/")
    try:
        s3.upload_file(str(path), BUCKET, key)
        uploaded += 1
    except Exception as e:
        errors += 1
        print(f"  ERROR {key}: {e}", file=sys.stderr)

duration = datetime.now(timezone.utc).isoformat()
print(f"[{duration}] Done. uploaded={uploaded} skipped={skipped} errors={errors}")
sys.exit(1 if errors > 0 else 0)

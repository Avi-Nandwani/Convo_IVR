#!/usr/bin/env python3
"""
demo/simulate_call.py

Usage:
  python demo/simulate_call.py --call-id call123 --from +15550001111 --to +15550002222 --media demo/recordings/sample.wav

This script POSTs a webhook to /webhook/call on your running app. If you pass a local file path
it will send media_url as file://<abs_path>. If a paired .txt exists (same name with .txt),
the ASR client stub will pick it up as a fallback transcript.
"""
import argparse
import json
import os
import time
import requests
from pathlib import Path

DEFAULT_BASE = "http://localhost:8000"

def build_payload(call_id, from_number, to_number, media_path=None):
    payload = {
        "call_id": call_id,
        "from": from_number,
        "to": to_number,
        "direction": "inbound",
    }
    if media_path:
        p = Path(media_path).absolute()
        if p.exists():
            payload["media_url"] = f"file://{p}"
        else:
            print(f"[warn] media path {media_path} not found; sending webhook without media_url")
    return payload

def post_webhook(base_url, payload, webhook_secret=None):
    url = f"{base_url.rstrip('/')}/webhook/call"
    headers = {"Content-Type": "application/json"}
    if webhook_secret:
        headers["X-Webhook-Secret"] = webhook_secret
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()

def poll_session(base_url, call_id, timeout=10, interval=1):
    url = f"{base_url.rstrip('/')}/api/sessions/{call_id}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(interval)
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=os.environ.get("BASE_URL", DEFAULT_BASE))
    parser.add_argument("--call-id", required=True)
    parser.add_argument("--from", dest="from_number", required=True)
    parser.add_argument("--to", dest="to_number", required=True)
    parser.add_argument("--media", default=None, help="Local file path to send as file:// URL")
    parser.add_argument("--webhook-secret", default=os.environ.get("WEBHOOK_SECRET"))
    parser.add_argument("--poll-timeout", type=int, default=10)
    args = parser.parse_args()

    payload = build_payload(args.call_id, args.from_number, args.to_number, args.media)
    print(f"[info] Posting webhook to {args.base}/webhook/call payload={json.dumps(payload)}")
    resp = post_webhook(args.base, payload, webhook_secret=args.webhook_secret)
    print("[info] webhook POST response:", resp)

    print("[info] polling session for result...")
    session = poll_session(args.base, args.call_id, timeout=args.poll_timeout)
    if session:
        print("[info] session:", json.dumps(session, indent=2))
    else:
        print("[warn] session not found / not ready within timeout. Check logs at server side.")

if __name__ == "__main__":
    main()

#!/usr/bin/env bash
# demo/test_integration.sh
# quick smoke test: posts flow, triggers call, queries transcripts
BASE=${BASE_URL:-http://localhost:8000}
CALL_ID=${1:-test-call-1}

/usr/bin/env curl -s -X POST "$BASE/api/flows" -H "Content-Type: application/json" --data-binary @demo/flows/simple_faq.json >/dev/null

python3 demo/simulate_call.py --call-id "$CALL_ID" --from +911234567890 --to +911098765432 --media demo/recordings/sample.wav --base $BASE

echo
echo "Sleeping 2s before querying transcripts..."
sleep 2

echo "Transcripts:"
curl -s "$BASE/api/transcripts?call_id=$CALL_ID" | jq

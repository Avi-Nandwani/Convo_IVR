#!/usr/bin/env bash
# demo/run_demo.sh
# Simple convenience script to post the example flow and trigger a simulated call.
BASE=${BASE_URL:-http://localhost:8000}
echo "Posting sample flow to $BASE/api/flows"
curl -s -X POST "$BASE/api/flows" -H "Content-Type: application/json" --data-binary @demo/flows/simple_faq.json | jq

echo
echo "Triggering simulated call (demo/simulate_call.py) ..."
python3 demo/simulate_call.py --call-id demo-call-1 --from +911234567890 --to +911098765432 --media demo/recordings/sample.wav --base $BASE

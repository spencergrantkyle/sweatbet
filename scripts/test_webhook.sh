#!/bin/bash
# Test script to simulate a Strava webhook event
# Usage: bash scripts/test_webhook.sh [create|update|delete]

BASE_URL="${SWEATBET_URL:-http://localhost:5000}"
ASPECT_TYPE="${1:-create}"
ACTIVITY_ID="${2:-9876543210}"
ATHLETE_ID="${3:-12345678}"
EVENT_TIME=$(date +%s)

echo "Simulating Strava webhook: ${ASPECT_TYPE} activity ${ACTIVITY_ID} for athlete ${ATHLETE_ID}"
echo "---"

curl -s -X POST "${BASE_URL}/webhooks/strava" \
  -H "Content-Type: application/json" \
  -d "{
    \"object_type\": \"activity\",
    \"object_id\": ${ACTIVITY_ID},
    \"aspect_type\": \"${ASPECT_TYPE}\",
    \"owner_id\": ${ATHLETE_ID},
    \"subscription_id\": 1,
    \"event_time\": ${EVENT_TIME}
  }" | python3 -m json.tool 2>/dev/null || echo "(no JSON response)"

echo ""
echo "---"
echo "Webhook test complete."

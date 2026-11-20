
"""Upload generated KRX market data to Firestore using OIDC."""

import json
import firebase_admin
from firebase_admin import firestore

PROJECT_ID = "kr-stock-signal"

# Load generated stock data
with open("data.json", "r", encoding="utf-8") as f:
    payload = json.load(f)

# Prevent overwriting valid data with empty results
if not payload.get("stocks"):
    raise RuntimeError(
        "No stocks available; refusing to overwrite Firestore data"
    )

# Use Google Cloud credentials from GitHub Actions OIDC
if not firebase_admin._apps:
    firebase_admin.initialize_app(
        options={"projectId": PROJECT_ID}
    )

db = firestore.client()

# Preserve existing Firestore document structure
db.collection("market").document("latest").set(payload)

print(
    f"Successfully uploaded {len(payload['stocks'])} stocks to Firestore"
)

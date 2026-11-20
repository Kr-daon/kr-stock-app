"""Upload generated market data to Firestore using GitHub Actions secret."""
import json, os
import firebase_admin
from firebase_admin import credentials, firestore

raw = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
if not raw:
    raise RuntimeError('FIREBASE_SERVICE_ACCOUNT_JSON secret is required')
with open('data.json', encoding='utf-8') as f:
    payload = json.load(f)
if not payload.get('stocks'):
    raise RuntimeError('No stocks available; refusing to overwrite Firestore data')
app = firebase_admin.initialize_app(credentials.Certificate(json.loads(raw)))
firestore.client(app).collection('market').document('latest').set(payload)
print('Uploaded', len(payload['stocks']), 'stocks to Firestore')

import json
import requests
import time
from google.oauth2 import service_account
import google.auth.transport.requests
import firebase_admin
from firebase_admin import credentials as fb_credentials, db

# ===== STEP 1: Set your values =====
SERVICE_ACCOUNT_FILE = r'rbl.json'
PROJECT_ID = 'rbl-server-1'
FIREBASE_DB_URL = 'https://rbl-server-1-default-rtdb.europe-west1.firebasedatabase.app'  # Change to your DB URL

# ===== STEP 2: Authenticate and get access token =====
SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
request = google.auth.transport.requests.Request()
credentials.refresh(request)
access_token = credentials.token

# ===== STEP 3: Init Firebase Admin for DB =====
if not firebase_admin._apps:
    cred = fb_credentials.Certificate(SERVICE_ACCOUNT_FILE)
    firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DB_URL})

def get_device_token_and_id():
    ref = db.reference("request")
    data = ref.get()
    if not data:
        return None, None
    for device_id, info in data.items():
        token = info.get("token")
        if token:
            return device_id, token
    return None, None

def send_fcm(device_token):
    url = f"https://fcm.googleapis.com/v1/projects/{PROJECT_ID}/messages:send"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json; UTF-8',
    }
    message = {
        "message": {
            "token": device_token,
            "data": {
                "start_service": "1"
            }
        }
    }
    response = requests.post(url, headers=headers, data=json.dumps(message))
    print("Response Code:", response.status_code)
    print("Response Body:", response.text)
    return response.status_code

def store_result(device_id, result_code):
    ref = db.reference(f"request/{device_id}/result")
    ref.set(result_code)

def store_status(device_id, status):
    ref = db.reference(f"request/{device_id}/result")
    ref.set(status)

def delete_device_id(device_id):
    ref = db.reference(f"request/{device_id}")
    ref.delete()

# ===== STEP 4: Poll for token and send FCM =====
print("Waiting for device token at request/<device_id>/token ...")
while True:
    device_id, token = get_device_token_and_id()
    if device_id and token:
        print(f"Found device token for {device_id}: {token}")
        result_code = send_fcm(token)
        if result_code == 200:
            store_status(device_id, "yes")
        elif result_code == 404:
            store_status(device_id, "no")
        else:
            store_status(device_id, f"result_{result_code}")
        time.sleep(2)  # Wait 2 seconds before deleting
        delete_device_id(device_id)  # ✅ Delete after 2

# ./test_api.py
import json
import os
import sys
import time

import requests

# --- Configuration ---
# These URLs should point to where your services are running locally via docker-compose
AUTH_SERVICE_URL = "http://localhost:8001"
SUPER_ID_SERVICE_URL = "http://localhost:8002"
ANALYSIS_SERVICE_URL = "http://localhost:8000"
# ANALYSIS_SERVICE_URL = "https://image-condition-analysis.supersami.com"

# --- M2M Client Credentials ---
# These must match a client that exists in your auth_service database
# This is the client this script will authenticate as.
M2M_CLIENT_ID = "a4b1c2d3-e4f5-4a5b-8c6d-7e8f9a0b1c2d"
M2M_CLIENT_SECRET = "dev-image-condition-analysis-service-secret"


def get_auth_token():
    """Step 1: Get an authentication token from the Auth Service."""
    print(f"--- Step 1: Authenticating with Auth Service at {AUTH_SERVICE_URL} ---")
    url = f"{AUTH_SERVICE_URL}/api/v1/auth/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": M2M_CLIENT_ID,
        "client_secret": M2M_CLIENT_SECRET,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            print("ERROR: 'access_token' not found in auth response.")
            return None
        print("SUCCESS: Authentication successful.")
        return token
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Could not connect to Auth Service. Is it running? Details: {e}")
        return None


def get_super_id(token: str):
    """Step 2: Get a Super ID from the Super ID Service."""
    print(f"\n--- Step 2: Requesting Super ID from {SUPER_ID_SERVICE_URL} ---")
    url = f"{SUPER_ID_SERVICE_URL}/api/v1/super_ids"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"count": 1, "metadata": {"description": "Test run from test_api.py"}}
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        super_id = response.json().get("super_id")
        if not super_id:
            print("ERROR: 'super_id' not found in service response.")
            return None
        print(f"SUCCESS: Super ID received: {super_id}")
        return super_id
    except requests.exceptions.RequestException as e:
        print(
            f"ERROR: Could not connect to Super ID Service. Is it running? Details: {e}"
        )
        return None


def trigger_analysis(token: str, super_id: str):
    """Step 3: Trigger the Analysis Service."""
    print(f"\n--- Step 3: Triggering Analysis Service at {ANALYSIS_SERVICE_URL} ---")

    # The endpoint for the analysis task
    endpoint = f"{ANALYSIS_SERVICE_URL}/api/image-condition-analysis/analyze/"

    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "super_id": super_id,
        "image_urls": [
            "https://media.rightmove.co.uk/46k/45021/164254985/45021_CLM250119_IMG_00_0000.jpeg"
        ],
        "notes": {"source": "test_api.py"},
    }

    print(f"Sending request to: {endpoint}")
    print("Payload:")
    print(json.dumps(payload, indent=2))

    try:
        response = requests.post(endpoint, headers=headers, json=payload)
        print("\n--- Response ---")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 202:
            print("SUCCESS: Analysis task was accepted by the server.")
            print("Response JSON:")
            print(response.json())
        else:
            print("ERROR: Received an unexpected status code.")
            print("Response Content:")
            print(response.text)

    except requests.exceptions.RequestException as e:
        print(f"\n--- CONNECTION ERROR ---")
        print(f"Could not connect to the Analysis Service. Details: {e}")


def run_test():
    """Orchestrates the full M2M test flow."""
    token = get_auth_token()
    if not token:
        sys.exit(1)

    super_id = get_super_id(token)
    if not super_id:
        sys.exit(1)

    trigger_analysis(token, super_id)


if __name__ == "__main__":
    run_test()

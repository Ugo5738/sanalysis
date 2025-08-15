import json
import time

import requests

# --- Configuration ---
# The base URL of your running service
# This works because Docker maps port 8000 on the container to port 8000 on your machine
BASE_URL = "http://localhost:8000"

# The endpoint for the analysis task
ANALYZE_ENDPOINT = f"{BASE_URL}/api/image-condition-analysis/analyze/"

# IMPORTANT: Get a valid JWT from your Supabase dashboard
# Go to API -> JWT Verifier -> copy the "signed" token
# This is a long-lived token perfect for testing
SUPABASE_JWT = "PASTE_YOUR_TEST_JWT_HERE"

# The payload with image URLs to send
TEST_PAYLOAD = {
    "super_id": f"test-run-{int(time.time())}",  # A unique ID for each test run
    "image_urls": [
        "https://i.imgur.com/g4R5b2j.jpeg",  # Excellent Kitchen
        "https://i.imgur.com/5l3otwV.jpeg",  # Poor Kitchen
        "https://i.imgur.com/4JjA5fK.jpeg",  # Excellent Living Room
        "https://i.imgur.com/vHqB3z0.jpeg",  # Poor Living Room
    ],
    "notes": {"source": "test_api.py"},
}

# --- Test Execution ---


def run_test():
    """
    Sends a request to the analyze endpoint and prints the response.
    """
    if "PASTE_YOUR_TEST_JWT_HERE" in SUPABASE_JWT:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!! ERROR: Please paste a valid Supabase JWT into      !!!")
        print("!!! the SUPABASE_JWT variable in this script.          !!!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        return

    print(f"--- Sending request to: {ANALYZE_ENDPOINT} ---")
    print("Payload:")
    print(json.dumps(TEST_PAYLOAD, indent=2))

    # Set up the authorization header
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SUPABASE_JWT}",
    }

    try:
        # Make the POST request
        response = requests.post(ANALYZE_ENDPOINT, headers=headers, json=TEST_PAYLOAD)

        # Check the response
        print(f"\n--- Response ---")
        print(f"Status Code: {response.status_code}")

        if response.status_code == 202:
            print("SUCCESS: Task was accepted by the server.")
            print("Response JSON:")
            print(response.json())
            print(
                "\n>>> Check your Celery worker terminal to see the task running! <<<"
            )
        else:
            print("ERROR: Received an unexpected status code.")
            print("Response Content:")
            print(response.text)

    except requests.exceptions.ConnectionError as e:
        print("\n--- CONNECTION ERROR ---")
        print("Could not connect to the server. Is the Docker service running?")
        print(f"Error details: {e}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")


if __name__ == "__main__":
    run_test()

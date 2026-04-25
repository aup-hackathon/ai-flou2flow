import base64
import requests
import json
import os

# Image path from previous step
IMAGE_PATH = "/home/younesbensafia/.gemini/antigravity/brain/aab02d36-64ce-4cbd-878c-6e64d17ee8e5/whiteboard_flow_1777095419844.png"

def test_image_route():
    with open(IMAGE_PATH, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "session_id": "test-image-session",
        "input_text": "Extract the flow from this whiteboard photo.",
        "image_data": img_base64,
        "workflow": "process",
        "model": "llava:7b" # Force llava for vision
    }

    print("Sending request to /api/workflow/generate...")
    try:
        response = requests.post("http://localhost:8001/api/workflow/generate", json=payload, timeout=120)
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_image_route()

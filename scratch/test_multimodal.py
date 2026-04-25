import base64
import requests
import json
import os

# Paths from previous steps
WHITEBOARD_PATH = "/home/younesbensafia/.gemini/antigravity/brain/aab02d36-64ce-4cbd-878c-6e64d17ee8e5/whiteboard_flow_1777095419844.png"
FORMAL_DOC_PATH = "/home/younesbensafia/.gemini/antigravity/brain/aab02d36-64ce-4cbd-878c-6e64d17ee8e5/formal_doc_page_1777095756612.png"

def test_image_route():
    print("\n--- TEST: Image Only (Whiteboard) ---")
    with open(WHITEBOARD_PATH, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "session_id": "test-image-session",
        "input_text": "Extract the flow from this whiteboard photo.",
        "image_data": img_base64,
        "workflow": "process",
        "model": "llava:7b"
    }

    send_request(payload)

def test_pdf_route():
    print("\n--- TEST: PDF (Simulated via Formal Doc) ---")
    with open(FORMAL_DOC_PATH, "rb") as f:
        img_base64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "session_id": "test-pdf-session",
        "input_text": "Analyze this document and extract the procurement steps.",
        "image_data": img_base64,
        "workflow": "process",
        "model": "llava:7b"
    }

    send_request(payload)

def test_voice_route():
    print("\n--- TEST: Voice (Simulated Transcript) ---")
    # Messy transcript with disfluencies and background noise markers
    messy_transcript = (
        "[BEEP] Uh, okay so, the process starts with, um, the employee fills the form, "
        "wait no, they first need to ask their manager. Yeah. So manager says yes, "
        "then they fill the form... uh, [COUGH] then HR reviews it. If HR says no, "
        "they have to start over. If yes, it's booked. [SILENCE]"
    )

    payload = {
        "session_id": "test-voice-session",
        "input_text": messy_transcript,
        "workflow": "process",
        "model": "mistral:latest" # Use mistral for text cleaning
    }

    send_request(payload)

def send_request(payload):
    print("Sending request to /api/workflow/generate...")
    try:
        response = requests.post("http://localhost:8001/api/workflow/generate", json=payload, timeout=120)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print("Summary:", data.get("ai_summary", "No summary"))
        if "entities" in data:
            print("Tasks extracted:", [t["name"] for t in data["entities"].get("tasks", [])])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_image_route()
    test_pdf_route()
    test_voice_route()

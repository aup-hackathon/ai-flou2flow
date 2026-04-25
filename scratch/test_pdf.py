import base64
import httpx
import json
import fitz # PyMuPDF
import io

def create_test_pdf():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "PDF Extraction Test. This is a procurement process.")
    page.insert_text((50, 70), "Step 1: Create Requisition.")
    page.insert_text((50, 90), "Step 2: Manager Review.")
    
    pdf_bytes = doc.write()
    doc.close()
    return base64.b64encode(pdf_bytes).decode("utf-8")

def test_multimodal_complex():
    pdf_b64 = create_test_pdf()
    
    payload = {
        "session_id": "test-complex-session",
        "input_text": "Process this PDF.",
        "pdf_data": pdf_b64,
        "workflow": "process",
        "model": "qwen2:1.5b"
    }

    print("\n--- TEST: PDF Extraction ---")
    try:
        with httpx.Client() as client:
            response = client.post("http://localhost:8001/api/workflow/generate", json=payload, timeout=httpx.Timeout(180.0))
            print(f"Status Code: {response.status_code}")
            data = response.json()
            if "elements_json" in data:
                print("Context extracted:", data["elements_json"].get("context", {}).get("domain"))
                print("Tasks extracted:", [t["name"] for t in data["elements_json"].get("entities", {}).get("tasks", [])])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_multimodal_complex()

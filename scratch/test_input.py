import httpx
import json
import base64

def test_input_preprocessing():
    # A messy voice-like input
    messy_input = "Euh, alors, je voulais dire que, genre, le client il arrive à 8h et puis, enfin, il faut lui donner le café."
    
    payload = {
        "input_text": messy_input
    }

    print("\n--- TEST: Pro-Context Input Preprocessing ---")
    try:
        with httpx.Client() as client:
            # Using port 8001 as configured in .env
            response = client.post("http://localhost:8001/api/input", json=payload, timeout=httpx.Timeout(30.0))
            print(f"Status: {response.status_code}")
            
            data = response.json()
            if data.get("success"):
                print(f"Detected Type: {data['type']}")
                print(f"Original Length: {len(messy_input)} chars")
                print(f"Optimized Length: {len(data['optimized_text'])} chars")
                print(f"\n[Optimized Text]:\n{data['optimized_text']}")
            else:
                print(f"Error: {data.get('error')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_input_preprocessing()

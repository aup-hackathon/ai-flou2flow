import httpx
import json

def test_french_daily_summary():
    # A messy French "Daily Summary" typical of a voice note
    messy_input = """
    Alors, euh, aujourd'hui pour ma journée, j'ai d'abord commencé par, genre, ouvrir le magasin à 8h. 
    Ensuite, enfin, j'ai vérifié les stocks de café, voilà. 
    Après j'ai dû appeler le fournisseur parce qu'il manquait des trucs. 
    Il m'a dit qu'il livre demain. Du coup j'ai noté ça dans le registre.
    En fin de journée, j'ai fait la caisse et j'ai fermé. C'est tout.
    """
    
    payload = {
        "workflow": "process",
        "input_text": messy_input,
        "mode": "auto"
    }

    print("\n--- TEST: French Daily Summary (Voice-like Text) ---")
    try:
        with httpx.Client() as client:
            # Using port 8001 as configured in .env
            response = client.post("http://localhost:8001/api/workflow/generate", json=payload, timeout=httpx.Timeout(180.0))
            print(f"Status: {response.status_code}")
            
            data = response.json()
            if "context" in data and data["context"]:
                print(f"\n[AI Summary]: {data['context']['summary']}")
                print(f"[Detected Language]: {data['context']['language']}")
                print(f"[Domain]: {data['context']['domain']}")
            else:
                print("\n[Raw Response]:")
                print(json.dumps(data, indent=2))
            
            if "entities" in data:
                print("\n[Tasks Extracted]:")
                for task in data['entities']['tasks']:
                    print(f"- {task['name']} (By: {task['actor_id']})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_french_daily_summary()

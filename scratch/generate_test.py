import asyncio
import json
from flou2flow.pipeline import run_pipeline
from flou2flow.mermaid import generate_mermaid_diagram

async def main():
    text = "The service contractor sends the project cahier des charges to the sectorial market commission secretariat. The dossier must be enregistered before it can be transmitted."
    
    result = await run_pipeline(text)
    
    workflow_json = result.elsa_workflow or {}
    mermaid_diagram = ""
    if result.entities and result.flow:
        try:
            mermaid_diagram = generate_mermaid_diagram(result.entities, result.flow)
        except Exception as e:
            print("Mermaid error:", e)
            
    output = {
        "success": len(result.errors) == 0,
        "steps_completed": result.steps_completed,
        "errors": result.errors,
        "context": result.context.model_dump() if result.context else None,
        "entities": result.entities.model_dump() if result.entities else None,
        "flow": result.flow.model_dump() if result.flow else None,
        "elsa_workflow": workflow_json,
        "mermaid_diagram": mermaid_diagram,
    }
    
    with open("full_process_example.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
        
    print("Done")

if __name__ == "__main__":
    asyncio.run(main())

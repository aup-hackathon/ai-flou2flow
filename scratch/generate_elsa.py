import asyncio
import json
from flou2flow.pipeline import run_pipeline

async def main():
    input_text = "We receive an order, check stock, and then ship the product."
    print(f"Generating workflow for: {input_text}")
    result = await run_pipeline(input_text)
    if result.errors:
        print("Errors occurred:")
        for error in result.errors:
            print(f"- {error}")
    else:
        print("\nGenerated Elsa JSON:\n")
        print(json.dumps(result.elsa_workflow, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())

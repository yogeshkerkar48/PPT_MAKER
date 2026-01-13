import asyncio
import os
import inspect
from dotenv import load_dotenv
from runware import Runware

async def test():
    load_dotenv()
    api_key = os.getenv("RUNWARE_API_KEY")
    try:
        runware = Runware(api_key=api_key)
        method = runware.imageInference
        print(f"Method Signature: {inspect.signature(method)}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())

import asyncio
import os
from dotenv import load_dotenv
from runware import Runware

async def test():
    load_dotenv()
    api_key = os.getenv("RUNWARE_API_KEY")
    try:
        runware = Runware(api_key=api_key)
        print(f"Runware Object Type: {type(runware)}")
        print("Available Methods:", [m for m in dir(runware) if not m.startswith("_")])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())

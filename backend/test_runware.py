import asyncio
import os
from dotenv import load_dotenv
from runware import Runware
from runware.types import IImageInference

async def test():
    load_dotenv()
    api_key = os.getenv("RUNWARE_API_KEY")
    print(f"Testing with Key: {api_key[:5]}***")
    
    try:
        runware = Runware(api_key=api_key)
        await runware.connect()
        print("✅ Connection Successful!")
        
        print("⏳ Testing Image Generation...")
        # Instantiate the correct request class with a verified valid model ID
        request = IImageInference(
            positivePrompt="A professional futuristic office background, cinematic",
            model="civitai:133005@471120",
            numberResults=1,
            width=1280,
            height=704, # 704 is a multiple of 64, 720 is not.
            outputType="URL"
        )
        
        images = await runware.imageInference(requestImage=request)
        
        if images and len(images) > 0:
            print(f"✅ Image Generated! URL: {images[0].imageURL}")
        else:
            print("❌ No image returned.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
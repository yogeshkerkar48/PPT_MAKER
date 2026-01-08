"""
Test Client for HTML to PowerPoint Converter
Tests the API endpoint with sample data
"""
import requests
from pathlib import Path


def test_generate_pptx():
    """Test the generate-pptx endpoint"""
    
    # API endpoint
    url = "http://127.0.0.1:8000/generate-pptx"
    
    # Read HTML content from ppt_data.txt
    html_file = Path("ppt_data.txt")
    if not html_file.exists():
        print("Error: ppt_data.txt not found!")
        return
    
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Check for sample image
    image_file = Path("sample_image.png")
    if not image_file.exists():
        print("Warning: sample_image.png not found. Please provide an image file.")
        print("You can use any PNG or JPG image for testing.")
        return
    
    # Prepare form data
    files = {
        'image': ('sample_image.png', open(image_file, 'rb'), 'image/png')
    }
    
    data = {
        'html_content': html_content,
        'background_color': '2E5A88'  # Nice blue color
    }
    
    print("Sending request to API...")
    print(f"HTML content length: {len(html_content)} characters")
    print(f"Background color: {data['background_color']}")
    
    try:
        # Send POST request
        response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            # Save the generated PPTX file
            output_file = "generated_presentation.pptx"
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            print(f"\n✅ Success! PowerPoint generated: {output_file}")
            print(f"File size: {len(response.content)} bytes")
            print("\nYou can now open the file in PowerPoint or Google Slides!")
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
    
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API server.")
        print("Make sure the server is running with: uvicorn main:app --reload")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
    finally:
        # Close the file
        files['image'][1].close()


if __name__ == "__main__":
    test_generate_pptx()

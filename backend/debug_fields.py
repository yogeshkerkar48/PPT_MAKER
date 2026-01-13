from runware.types import IImageInference
from dataclasses import fields

try:
    print("Fields in IImageInference:")
    for field in fields(IImageInference):
        print(f"- {field.name}: {field.type}")
except Exception as e:
    print(f"Error: {e}")

import pytesseract
import os

# Set the path to tesseract executable
tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
pytesseract.pytesseract.tesseract_cmd = tesseract_path

# Verify Tesseract is accessible
try:
    print("Testing Tesseract installation...")
    version = pytesseract.get_tesseract_version()
    print(f"Tesseract version: {version}")
    print("Tesseract is working correctly!")
except Exception as e:
    print(f"Error accessing Tesseract: {str(e)}")
    print(f"Make sure Tesseract is installed at: {tesseract_path}")
    
# Check if the file exists
if os.path.exists(tesseract_path):
    print("\nTesseract executable found at the specified path.")
else:
    print("\nERROR: Tesseract executable not found at the specified path.")
    print("Please verify the installation path.")

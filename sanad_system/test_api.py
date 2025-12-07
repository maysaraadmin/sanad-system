import requests
import json

# Test the document analysis API
BASE_URL = "http://127.0.0.1:8000"

def test_document_analysis():
    """Test the document analysis endpoints"""
    
    # Test 1: Get list of analyses (should be empty initially)
    print("Testing GET /api/document-analysis/analyses/")
    try:
        response = requests.get(f"{BASE_URL}/api/document-analysis/analyses/")
        print(f"Status: {response.status_code}")
        if response.status_code == 401:
            print("Authentication required - this is expected")
        else:
            print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Check if dashboard is accessible
    print("Testing GET /api/document-analysis/dashboard/")
    try:
        response = requests.get(f"{BASE_URL}/api/document-analysis/dashboard/")
        print(f"Status: {response.status_code}")
        if response.status_code == 302:
            print("Redirect to login - this is expected")
        else:
            print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Check the correct dashboard URL
    print("Testing GET /api/document-analysis/dashboard/ (without /api/)")
    try:
        response = requests.get(f"{BASE_URL}/api/document-analysis/dashboard/")
        print(f"Status: {response.status_code}")
        if response.status_code == 302:
            print("Redirect to login - this is expected")
        else:
            print(f"Response: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Testing Document Analysis API")
    print("="*50)
    test_document_analysis()

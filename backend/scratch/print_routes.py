import urllib.request
import json

print("Fetching active OpenAPI from running server...")
try:
    with urllib.request.urlopen("http://127.0.0.1:8000/openapi.json") as response:
        data = json.loads(response.read().decode())
        paths = data.get("paths", {})
        print("Active endpoints on port 8000:")
        for path, methods in paths.items():
            print(f"Path: {path} Methods: {list(methods.keys())}")
except Exception as e:
    print(f"Failed to fetch openapi.json: {e}")

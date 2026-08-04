import urllib.request
import json

url = "http://127.0.0.1:8000/auth/register"
payload = {
    "name": "Test User",
    "email": "testuser_new@example.com",
    "password": "testpassword123"
}
headers = {
    "Content-Type": "application/json"
}

req = urllib.request.Request(
    url, 
    data=json.dumps(payload).encode('utf-8'), 
    headers=headers,
    method='POST'
)

print("Registering user via HTTP POST...")
try:
    with urllib.request.urlopen(req) as response:
        print("Success! Status code:", response.status)
        print("Response data:", response.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.reason)
    print("Response payload:", e.read().decode())
except Exception as e:
    print("Error:", e)

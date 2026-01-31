
import urllib.request
import urllib.parse
import json

url = "http://localhost:8000/token"
data = urllib.parse.urlencode({'username': 'admin', 'password': 'admin123'}).encode()
req = urllib.request.Request(url, data=data)
try:
    with urllib.request.urlopen(req) as response:
        print(response.read().decode())
except Exception as e:
    print(f"Error: {e}")

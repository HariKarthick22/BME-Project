import requests

resp = requests.get("http://localhost:8000/api/models/status", timeout=10)
print("status:", resp.status_code)
print(resp.text)
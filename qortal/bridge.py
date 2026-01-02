import requests, base64

QORTAL_API="http://localhost:62391/api"

def publish_json(name, data):
    payload = base64.b64encode(data.encode()).decode()
    body = {
      "requestType": "publishResource",
      "name": name,
      "service": "JSON",
      "resource": payload,
      "feeQNT":"100000"
    }
    return requests.post(QORTAL_API, json=body).json()

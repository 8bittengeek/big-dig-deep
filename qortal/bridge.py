#********************************************************************************
#          ___  _     _ _                  _                 _                  *
#         / _ \| |   (_) |                | |               | |                 *
#        | (_) | |__  _| |_ __ _  ___  ___| | __  _ __   ___| |_                *
#         > _ <| '_ \| | __/ _` |/ _ \/ _ \ |/ / | '_ \ / _ \ __|               *
#        | (_) | |_) | | || (_| |  __/  __/   < _| | | |  __/ |_                *
#         \___/|_.__/|_|\__\__, |\___|\___|_|\_(_)_| |_|\___|\__|               *
#                           __/ |                                               *
#                          |___/                                                *
#                                                                               *
#*******************************************************************************/

import requests
import base64

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

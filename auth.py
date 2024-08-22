import requests

url = "https://api.sandbox.co.in/authenticate"

headers = {
    "accept": "application/json",
    "x-api-version": "1.0",
    "x-api-key": "key_live_XnpJNBV30xDSHZlqO4TOj5v2Q7Z499QM",
    "x-api-secret": "secret_live_jcgLLyPDjJeNDW7rKM9QMhPAsx0XXQRd"
}

response = requests.post(url, headers=headers)

print(response.text)

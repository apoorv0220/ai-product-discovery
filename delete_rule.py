import requests

url = "http://localhost:7099/api/v1/merchandising/rules/10"
headers = {
    "Authorization": "Bearer ak_live_djl6lrgmy25xzffkawal55j9utbpfkbw",
}

response = requests.delete(url, headers=headers)
print(f"Status: {response.status_code}")
print(response.text)


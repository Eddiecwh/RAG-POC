import requests
import os
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

email = os.getenv("CONFLUENCE_EMAIL")
api_token = os.getenv("CONFLUENCE_API_TOKEN")
base_url = "https://eddiecwh.atlassian.net"

response = requests.get(
    f"{base_url}/wiki/rest/api/content?spaceKey=ragpoc",
    auth=HTTPBasicAuth(email, api_token)
)

print(response.json()["size"])
print(response.json())
import pickle
import requests
import os
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer

load_dotenv()

CONFLUENCE_BASE_URL = "https://eddiecwh.atlassian.net"
CONFLUENCE_SPACE_KEY = "ragpoc"
CONFLUENCE_EMAIL = os.getenv("CONFLUENCE_EMAIL")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
MODEL = "all-MiniLM-L6-v2"

INDEX_FILE = "index.pkl"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

def get_all_pages(base_url, space_key, auth):
  pages = []
  url = f"{base_url}/wiki/rest/api/content?spaceKey={space_key}&limit=25"

  while url:
    response = requests.get(url, auth=auth)
    data = response.json()
    pages.extend(data["results"])

    next_link = data.get("_links", {}).get("next")
    if next_link:
      url = f"{base_url}{next_link}"
    else:
      url = None
    
  return pages

def get_page_content(base_url, page_id, auth):
  response = requests.get(f"{base_url}/wiki/rest/api/content/{page_id}?expand=body.storage",
                          auth=auth
                          )
  html = response.json()["body"]["storage"]["value"]
  soup = BeautifulSoup(html, "html.parser")
  return soup.get_text(separator="\n", strip=True)

def chunk_text(text, chunk_size, overlap):
  chunks = []
  start = 0
  while start < len(text):
    end = start + chunk_size
    chunks.append(text[start:end])
    start += chunk_size - overlap
  return chunks
  
def ingest():
  auth = HTTPBasicAuth(CONFLUENCE_EMAIL, CONFLUENCE_API_TOKEN)
  model = SentenceTransformer(MODEL)

  print("Fetching pages from confluence...")
  pages = get_all_pages(CONFLUENCE_BASE_URL, CONFLUENCE_SPACE_KEY, auth)
  print(f"Found {len(pages)} pages")

  print("Chunking and Embedding")
  all_chunks = []
  for page in pages:
    page_id = page["id"]
    page_title = page["title"]

    text = get_page_content(CONFLUENCE_BASE_URL, page_id, auth)

    chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
    for chunk in chunks:
      all_chunks.append({
        "text": chunk,
        "source": page_title,
        "page_id": page_id
      })
    
  print(f"Total chunks: {len(all_chunks)}")
    
  texts = [c["text"] for c in all_chunks]
  embeddings = model.encode(texts, show_progress_bar=True)
    
  print("Saving index...")
  with open(INDEX_FILE, "wb") as f:
    pickle.dump({"chunks": all_chunks, "embeddings": embeddings}, f)
    
  print(f"Done — saved {len(all_chunks)} chunks to {INDEX_FILE}")

if __name__ == "__main__":
    ingest()


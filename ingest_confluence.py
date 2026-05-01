import requests
import os
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from db import get_connection, save_to_documents

load_dotenv()

CONFLUENCE_BASE_URL = "https://eddiecwh.atlassian.net"
CONFLUENCE_SPACE_KEY = "ragpoc"
CONFLUENCE_EMAIL = os.getenv("CONFLUENCE_EMAIL")
CONFLUENCE_API_TOKEN = os.getenv("CONFLUENCE_API_TOKEN")
MODEL = "all-MiniLM-L6-v2"

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

  table_text = parse_tables(soup)

  for table in soup.find_all("table"):
    table.decompose()

  return table_text + "\n" + soup.get_text(separator="\n", strip=True)

def parse_tables(soup) -> str:
  result = []
  
  for table in soup.find_all("table"):
    rows = table.find_all("tr")

    headers = []
    for cell in rows[0].find_all("th"):
      headers.append(cell.get_text(strip=True))

    for row in rows[1:]:
      cells = []
      for cell in row.find_all("td"):
        cells.append(cell.get_text(strip=True))
      row_dict = dict(zip(headers, cells))

      pairs = []
      
      for key, value in row_dict.items():
        pairs.append(f"{key}: {value}")
    
      row_str = " | ".join(pairs) 
      result.append(row_str)

  return "\n".join(result)

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
        "page_id": page_id,
        "domain": "confluence"
      })
    
  print(f"Total chunks: {len(all_chunks)}")
    
  texts = [c["text"] for c in all_chunks]
  embeddings = model.encode(texts, show_progress_bar=True)

  save_to_documents(conn, all_chunks, embeddings, "confluence")

  print(f"Done — saved {len(all_chunks)} chunks to rag_poc::documents")

  conn.close()
  
  # - DEPRECATED - not saving to pickle file

  # print("Saving index...")
  # with open(INDEX_FILE, "wb") as f:
  #   pickle.dump({"chunks": all_chunks, "embeddings": embeddings}, f)

if __name__ == "__main__":
    conn = get_connection()
    ingest()


import os
import pickle
from sentence_transformers import SentenceTransformer

DOCS_DIR = "docs"
INDEX_FILE = "index.pkl"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

def load_docs(docs_dir):
  docs = []
  for filename in os.listdir(docs_dir):
    if filename.endswith(".md"):
      filepath = os.path.join(docs_dir, filename)
      with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
        docs.append({"filename" : filename, "text": text})
      print(f"Loaded: {filename}")
  return docs

def chunk_text(text, chunk_size, overlap):
  chunks = []
  start = 0
  while start < len(text):
    end = start + chunk_size
    chunks.append(text[start:end])
    start += chunk_size - overlap
  return chunks

def ingest():
  print("Loading docs...")
  docs = load_docs(DOCS_DIR)

  print("Chunking...")
  chunks = []
  for doc in docs:
    doc_chunks = chunk_text(doc["text"], CHUNK_SIZE, CHUNK_OVERLAP)
    for chunk in doc_chunks:
      chunks.append({"text": chunk, "source": doc["filename"]})

  print(f"Total chunks: {len(chunks)}")

  print("Embedding chunks...")
  model = SentenceTransformer("all-MiniLM-L6-v2")
  texts = [c["text"] for c in chunks]
  embeddings = model.encode(texts, show_progress_bar=True)

  print("Saving index...")
  with open(INDEX_FILE, "wb") as f:
    pickle.dump({"chunks" : chunks, "embeddings" : embeddings}, f)

  print(f"Done - saaved {len(chunks)} chunks to {INDEX_FILE}")

if __name__ == "__main__":
    ingest()
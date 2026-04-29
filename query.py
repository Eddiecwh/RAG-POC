import requests
from sentence_transformers import SentenceTransformer
from db import get_connection, find_matching_chunks_from_db

INDEX_FILE = "index.pkl"
MODEL_NAME = "all-MiniLM-L6-v2"
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2"
TOP_K = 3

CONFLUENCE_BASE_URL = "https://eddiecwh.atlassian.net"
CONFLUENCE_SPACE_KEY = "ragpoc"

# deprecated - now using vector DB

# def load_index(index_file):
#   with open(index_file, "rb") as f:
#     data = pickle.load(f)
#   return data["chunks"], data["embeddings"]


# def find_relevant_chunks(query, chunks, embeddings, model, top_k):
#   query_embedding = model.encode([query])

#   scores = np.dot(embeddings, query_embedding.T).flatten()

#   top_indices = np.argsort(scores)[::-1][:top_k]

#   return [chunks[i] for i in top_indices]


def build_prompt(query, relevant_chunks):
  context = ""
  for chunk in relevant_chunks:
    context += f"Source: {chunk['source']}\n{chunk['text']}\n\n"

  prompt = f"""You are a helpful assistant. Answer the question using only the context below. If the answer is not in the context, say you don't know.

  Context:
  {context}

  Question: {query}
  """

  return prompt

def ask_ollama(prompt):
  response = requests.post(OLLAMA_URL, json= {
    "model": OLLAMA_MODEL,
    "messages": [{"role": "user", "content": prompt}],
    "stream": False
  })
  return response.json()["message"]["content"]

if __name__ == "__main__":
  conn = get_connection()

  model = SentenceTransformer(MODEL_NAME)
  
  query = input("Ask a question: ")

  relevant_chunks = find_matching_chunks_from_db(conn, query, model, TOP_K)
  prompt = build_prompt(query, relevant_chunks)
  answer = ask_ollama(prompt)
  
  print("\nAnswer:", answer)
  print("\nSources:")
  for chunk in relevant_chunks:
    print(f" - {chunk['source']}")
    print(f"    - {CONFLUENCE_BASE_URL}/wiki/spaces/{CONFLUENCE_SPACE_KEY}/pages/{chunk['page_id']}")
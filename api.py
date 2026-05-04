from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from db import get_connection
from query import find_matching_chunks_from_db, build_prompt, ask_ollama, MODEL_NAME, TOP_K

app = FastAPI()

class QueryRequest(BaseModel):
  question: str
  domain: str = None
  session_id: str = None

@app.post("/api/query")
async def query(request: QueryRequest):

  conn = get_connection()

  model = SentenceTransformer(MODEL_NAME)

  question = request.question
  domain = request.domain

  relevant_chunks = find_matching_chunks_from_db(conn, question, model, TOP_K, domain)
  prompt = build_prompt(question, relevant_chunks)
  answer = ask_ollama(prompt)

  return {"answer": answer, 
          "sources": [{"source": chunk['source'], "page_id": chunk['page_id']} for chunk in relevant_chunks]
          }
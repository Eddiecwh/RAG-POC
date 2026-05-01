import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
  return psycopg2.connect(
    host = os.getenv("DB_HOST"),
    port = os.getenv("DB_PORT"),
    dbname = os.getenv("DB_NAME"),
    user = os.getenv("DB_USER"),
    password = os.getenv("DB_PASSWORD")
  )

def save_to_documents(conn, all_chunks, embeddings, domain):
  cursor = conn.cursor()

  cursor.execute("DELETE FROM documents where domain = %s", (domain,))

  # Saving to Documents table instead of pkl file
  for i, chunk in enumerate(all_chunks):
    cursor.execute("""
                   INSERT into documents (text, source, page_id, domain, embedding) 
                   values (%s, %s, %s, %s, %s)""",
                   (chunk["text"], 
                    chunk["source"], 
                    chunk["page_id"], 
                    chunk["domain"], 
                    embeddings[i].tolist()))
    
  conn.commit()

def vector_search(conn, query, model, limit) -> list:
  query_embedding = model.encode([query])[0]
  embedding_str = "[" + ",".join(map(str, query_embedding.tolist())) + "]"

  cursor = conn.cursor()

  cursor.execute("""
                 SELECT id, text, source, page_id
                 FROM documents
                 ORDER BY embedding <=> %s::vector
                 LIMIT %s
                 """, (embedding_str, limit))
  
  results = cursor.fetchall()
  return [{"id": result[0], "text": result[1], "source": result[2], "page_id": result[3]} for result in results]

def keyword_search(conn, query, limit) -> list:
  cursor = conn.cursor()

  cursor.execute("""
                 SELECT id, text, source, page_id
                 FROM documents
                 WHERE textsearch @@ plainto_tsquery('english', %s)
                 ORDER BY ts_rank(textsearch, plainto_tsquery('english', %s))
                 DESC LIMIT %s
                 """, (query, query, limit))
  
  results = cursor.fetchall()
  return [{"id": result[0], "text": result[1], "source": result[2], "page_id": result[3]} for result in results]


def reciprocal_rank_fusion(vector_results, keyword_results, top_k, k=60) -> list:
  # declare a dict of results
  # it should hold: id: RRF
  scores = {}
  chunks = {}

  # loop through vector result
  for rank, chunk in enumerate(vector_results):
    chunk_id = chunk["id"]
    # calculate RRF contribution
    rrf_score = 1/(rank + k)
    scores[chunk_id] = scores.get(chunk_id, 0) + rrf_score
    chunks[chunk_id] = chunk
  
  for rank, chunk in enumerate(keyword_results):
    chunk_id = chunk["id"]
    # calculate RRF contribution
    rrf_score = 1/(rank + k)
    scores[chunk_id] = scores.get(chunk_id, 0) + rrf_score
    chunks[chunk_id] = chunk

  sorted_scores = sorted(scores.items(), key=lambda x : x[1], reverse=True)
  top_ids = sorted_scores[:top_k]

  result = []
  for id in top_ids:
    result.append(chunks.get(id[0]))
  return result

def find_matching_chunks_from_db(conn, query, model, top_k):
  vs = vector_search(conn, query, model, limit=20)
  ks = keyword_search(conn, query, limit=20)
  
  return reciprocal_rank_fusion(vs, ks, top_k)
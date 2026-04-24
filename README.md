# RAG Internal Chatbot POC

A RAG (Retrieval-Augmented Generation) pipeline that ingests Confluence docs, Slack messages, and code repositories to provide contextual answers via a local LLM.

## Prerequisites

- Python 3.9+
- PostgreSQL 18+
- pgvector extension
- Ollama

## Setup

### 1. Install system dependencies
- Install Python from python.org
- Install Postgres from postgresql.org
- Install pgvector (see pgvector Windows install guide)
- Install Ollama from ollama.com and pull the model:
```bash
  ollama pull llama3.2
```

### 2. Create the database
In pgAdmin or psql, run:
```sql
CREATE DATABASE rag_poc;
\c rag_poc
CREATE EXTENSION vector;

CREATE TABLE documents (
    id        SERIAL PRIMARY KEY,
    text      TEXT,
    source    VARCHAR(255),
    page_id   VARCHAR(50),
    domain    VARCHAR(50),
    embedding vector(384)
);

CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);
```

### 3. Clone the repo and set up the environment
```bash
git clone https://github.com/Eddiecwh/RAG-POC.git
cd RAG-POC
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure credentials
Create a `.env` file in the project root
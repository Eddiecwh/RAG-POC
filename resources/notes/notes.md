# RAG POC — Dev Log

## April 23, 2026

- Experimented with reading PDF files using pymupdf, library had a hard time reading tables
  content wasn't lost, but columns were jumbled around. Could clean it, but too many variables
  to account for not worth it

- trying confluence API instead

- set up a sample page, and moved over the test files (config.md) and onboarding.md
```python
response = requests.get(
    f"{base_url}/wiki/rest/api/content/884737?expand=body.storage",
    auth=HTTPBasicAuth(email, api_token)
)
```
  we are getting back the html, we will use beautiful soup to strip the html tags

- Some considerations: with our old mock files, we individually made the config.md/onboarding.md
  files, we dont want to manually make each one of these documents and link them - so how can we fetch
  all docs at once? Confluence API supports us grabbing everything from a confluence page (ragpoc) in our case

  from there we can paginate the response if we have a large subset of data (pages), and
  process the pages individually into .md files

- Need to think about future RAG strategies, we have regular naive rag for now, but we should
  look to incorporate advanced RAG/Hybrid search rag and most importantly, when we get to the slack integration step
  we need to conversational rag, must be able to keep state and remember context from previous questions

- For Anurag tomorrow morning:
  - Show current POC buildout
  - Ask about using actual context from Relatient (confluence, slack, codebase, etc)
  - Ask about SD requirements for tools
  - Ask about Ollama, Llama 3.2 for current POC (runs on local GPU/CPU)
  - Future ideas: API layer w/ Spring boot, Slack App Integration

---
 
## April 24, 2026

 
### Roadmap

Next Steps:

Roadmap proposed by Claude:

| Step | Title | Description |
|---|---|---|
| Step 1 | Upgrading Our Datastore |Swap index.pkl for pgvector Get a real vector database in place first. Everything else gets easier once you have proper persistent storage with metadata filtering. This is also where your Spring Boot background becomes relevant — pgvector is just Postgres |
| Step 2 | Adding Hybrid Search | Once you're on pgvector you can add keyword search alongside vector search almost for free — Postgres has full text search built in. This immediately improves retrieval quality before you add more data |
| Step 3 | Adding more data sources | Now that the foundation is solid, add the codebase first — it's simpler than Slack because it's just files. Slack is the messiest source — short messages, lots of noise, threading makes chunking tricky. Save it for last |
| Step 4 | Spring Boot API layer | Wrap everything in an API so it's not just scripts anymore |
| Step 5 | Slack integration | Now you have something worth wiring up to Slack |



Today's work: Step 1 has been completed - we have succesfully migrated over from a index.pkl file -> using a pgvector database which our RAG application succesfully calls to retrieve context. our previous process of loading the index file, then finding the relevant chunks is now streamlined into 1 function where we embed the query and directly use cosine similarity to find the the top_k relevant contexts. 

To do: we'll have to figure out how to avoid storing duplicate context - because everyime we run ingest_confluence.py, we will just add the same information again

---
 
## April 27, 2026
 
### Focus: Hybrid Search
 
#### Why Hybrid Search?

 Todays focus: Adding hybrid search
 - want to attempt combining vector search (currently implemented) and keyword search
    - for example if we search specific system_config_keys: Athena_no_days_out, ConfiguredDaysToPull, etc.
    - currently pure vector search looks for meaning, and not exact key words
    - solution: with pgvector store, we can add a tsvector column to the documents table, and we'll query it along with vector search

current pipeline:

```
query -> embed -> vector search -> top_k (3) -> LLM
```

combining hybrid search and vector search (using arrows to diagram because I dont know how to embed images lol):

```
vector search  → top 20 candidates ─┐
                                    ├─→ merge → re-rank → top_k (3) → LLM
keyword search → top 20 candidates ─┘
```

In our documents table, I added a column `embeddings` that would store our embeddings and created a HNSW index on it

Here's how I understand how it works: 
Our `embedding` column stores vectors, which essentially is a list of 384 numbers, so when we do our query matching logic
we are trying to find which stored vectors are closest to our query vectors.

Using `HNSW (Hierachical Navigable Small World)` builds a smart graph structure on top of those vectors, so we can find the nearest neighbors withought having to check every row.

to implement keyword search, our new column `textsearch` of the type `tsvector` , will have an index created with `GIN - Generealized Inverted Index` which searches inside values rather than comparing whole values.

so that turns our vector into something like this: 
```
"appointment sync is enabled" → ['appoint', 'enabl', 'sync']
```

`GIN` builds an index that maps each word to which row contains it, which is what we need for keyword search

TLDR: 
`HNSW` — find vectors that point in a similar direction
`GIN` — find rows that contain specific words

To populate the `textsearch` column, we are converting `text` into a tsvector using `to_tsvector`, since postgres supports this method we don't have to implement it in `save_to_documents`, we can create a trigger (which is new to me), so that everytime a new entry is created, we'll run the method on the text column

The function:
```
CREATE OR REPLACE FUNCTION update_textsearch()
RETURNS trigger AS $$
BEGIN
  NEW.textsearch := to_tsvector('english', NEW.text);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

The trigger:
```
CREATE TRIGGER textsearch_update
BEFORE INSERT OR UPDATE ON documents
FOR EACH ROW EXECUTE FUNCTION update_textsearch();
```

Pros of using the trigger:
- We don't have to implement the method to_tsvector at the code level within `save_to_documents`

Cons:
- Since it's not in the code, other developers who might reuse the code might not know straight away (not looking at db functions) that the textsearch column population (or the keyword search as a whole) is dependent on this trigger

While testing the trigger, (re-running `ingest_confluence.py`) I realized that I did not add anything in to deal with handling duplicates, so I am just stacking on new data on top of the old pre-existing data.

I'm not sure if this is the best way to deal with it, but it's a band-aid solution for now, I'll just modify `save_to_documents` and truncate all pre-existing data so anytime we run the script - we start building context from scratch

Is it the best idea? Probably not, will it work for now? Yeah!

---

## April 28th, 2026

### Designing the Hybrid Search approach (Vector Search + Keyword Search)

Diving into the flow for the hybrid search, here's what I'm thinking in terms of the workflow:

1. Embed The query (no changes here)
2. Run the vector search (this time, we're grabbing top 20, again by cosine similarity)
3. Run the keyword search (get top 20 by text match)
4. Merge the two lists, and remove duplicate ids
5. Re-rank, our list of candidates using an algorithm
6. Return the `top_k` elements from our reranked results

So in terms of reranking (sorting algorithms) Claude recommends using `RRF - Reciprocal Rank Fusion`, other alternatives include `Linear Combination`, `Cross-encoder re-ranking` let's see why RRF is recommended and what it does:

The formula: 
```
RRF score = 1/(rank_in_vector_results + k) + 1/(rank_in_keyword_results + k)
```
*k is usually 60, a constant that softens the impact of top rankings so first place isnt overwhelmingly dominant*

So example, let's say we have 2 chunks

1. Ranked 1st in vector search and 5th in keyword search

```
1/(1+60) + 1/(5+60) = 0.0164 + 0.0154 = 0.0318
```

2. 2nd in both searches
```
1/(2+60) + 1/(2+60) = 0.0161 + 0.0161 = 0.0323
```

The chunk ranked 2nd in both scores higher than one ranked 1st in one and 5th in the other. So this algorithm actually favors situations where there is a balance of both searches

`Linear Combination` would be the opposite of this where we decide how much weight we want to attribute to each search

```
final_score = 0.7 * vector_score + 0.3 * keyword_score
```

*^ Favoring a 70% weight on vector score, vs 30% on keyword score*

`Cross-encoder` re-ranking would have us pass each chunk + query into a seperate more powerful model, which would be more accurate - but we're adding a whole new model call for each candidate chunk. I think we'll skip that for now

--- 

### Having issues with Tables (cont..)

After implementation of the hybrid search, I am noticing that the LLM is still having issues with retrieving context from table data sources:

e.g - prompt: 
```
what is the average Athena response time
```

Response:
```
Answer: I don't know. The context only mentions that Athena is the slowest of our integrations under load, frequently hitting the ehr_timeout_seconds limit, but it doesn't provide information about the average Athena response time.
```
Context:

| EHR | Auth Method | Data Format | Avg Response Time |
| --- | --- | --- | --- |
| Athena | API Key | REST/JSON | 800ms | 

It is still not parsing tables correctly, and looks like it is unable to properly utilize our newly added keyword search and associate the `EHR` with the corresponding `Avg Response Time`

To try and work around this, I've implemented a helper method within `ingest_confluence.py` to utilize beautiful soup to find tables in a given document, and preprocess it into a data row that can be paired with the right headers.


```
EHR: Athena | Auth Method: API Key | Data Format: REST/JSON | Avg Response Time: 800ms
```
The method returns a string with associated values tied to their corresponding headers:

the html parsing script will also need to be modified to accomodate html tables already being happenned so they are not parsed twice

Testing the results with the fix:

```
Fetching pages from confluence...
Found 5 pages
Chunking and Embedding
Total chunks: 25
```
Fetching 25 instead of 21 chunks now, looks like we are parsing the table correctly...

```
(venv) PS C:\Users\Eddie PC\Documents\Coding\python\rag-poc> python .\query.py                                                                                                                                     
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|██████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 103/103 [00:00<00:00, 8067.32it/s]
Ask a question: what is the average Athena response time

Answer: The average Athena response time is 800ms.

Sources:
 - EHR Integration Overview
    - https://eddiecwh.atlassian.net/wiki/spaces/ragpoc/pages/1048577
 - EHR Integration Overview
    - https://eddiecwh.atlassian.net/wiki/spaces/ragpoc/pages/1048577
 - Configuration
    - https://eddiecwh.atlassian.net/wiki/spaces/ragpoc/pages/884737
```

<div style="text-align: center">
  <img src="../images/great-success.jpg" width="30%" alt="title">
</div>
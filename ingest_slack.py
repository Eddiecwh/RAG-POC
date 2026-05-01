import os
import json
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from db import get_connection, save_to_documents

load_dotenv()

def ingest():
  data_dir = "./resources/mock_data/"

  model = SentenceTransformer("all-MiniLM-L6-v2")
  conn = get_connection()

  all_chunks = []

  for file in os.listdir(data_dir):
    if file.endswith(".json"):
      filepath = os.path.join(data_dir, file)
      with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

        for channel in data["channels"]:
          channel_name = channel["name"]
          messages = channel["messages"]

          print(channel_name)
          print(messages)

          message_dict = {}

          for message in messages:
            thread_ts = message["thread_ts"]
            if thread_ts not in message_dict:
              message_dict[thread_ts] = []
            message_dict[thread_ts].append(message)

          threads = []
          standalone = []
          
          for thread_ts, msgs in message_dict.items():
            if len(msgs) > 1:
              # this is a thread
              threads.append(msgs)
            else:
              # this is a standalone message
              standalone.append(msgs[0])

          for thread in threads:
            text = flatten_thread(thread)
            all_chunks.append({"text": text, 
                               "source": channel_name, 
                               "page_id": thread[0]["thread_ts"], 
                               "domain": "slack"})
          
          standalone_groups = group_standalone(standalone)
          for group in standalone_groups:
            text = flatten_thread(group)
            all_chunks.append({"text": text, 
                               "source": channel_name, 
                               "page_id": group[0]["thread_ts"],
                               "domain": "slack"})   

          texts = [c["text"] for c in all_chunks]
          embeddings = model.encode(texts, show_progress_bar = True)

  save_to_documents(conn, all_chunks, embeddings, "slack")
  print(f"Done - saved {len(all_chunks)} chunks to rag_poc::documents")

  conn.close()


def flatten_thread(threads):
  result = []
  for thread in threads:
    user = thread["user"]
    text = thread["text"]
    row_str = f"{user}: {text}"
    result.append(row_str)

  return "\n".join(result)

def group_standalone(standalone):
  groups = []
  current_group = []

  for message in standalone:
    if not current_group:
      current_group.append(message)
    else:
      basetime = float(current_group[0]["ts"])
      current_ts = float(message["ts"])

      if current_ts - basetime <= 300:
        current_group.append(message)
      else:
        groups.append(current_group)
        current_group = [message]
  
  if current_group:
        groups.append(current_group)
    
  return groups

if __name__ == "__main__":
    ingest()

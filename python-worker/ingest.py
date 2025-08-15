# import os
# import json
# import hashlib
# import pymongo
# from dotenv import load_dotenv
# from langchain_openai import OpenAIEmbeddings
# from langchain_community.document_loaders import PyPDFLoader
# from langchain.text_splitter import RecursiveCharacterTextSplitter

# # --- Load Environment Variables ---
# load_dotenv(dotenv_path=".env.local")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# MONGO_URI = os.getenv("MONGO_URI")

# # --- MongoDB Connection ---
# print("Connecting to MongoDB...")
# mongo_client = pymongo.MongoClient(MONGO_URI)
# db = mongo_client.get_default_database()
# chunks_collection = db.get_collection("icaichunks")
# embeddings_collection = db.get_collection("icaiembeddings")
# print("MongoDB connected.")

# # --- LangChain Embedder ---
# embedder = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

# # --- Hashing and Tracking ---
# def get_file_hash(file_path):
#     hasher = hashlib.md5()
#     with open(file_path, "rb") as f:
#         hasher.update(f.read())
#     return hasher.hexdigest()

# TRACK_FILE = "ingested.json"
# ingested = json.load(open(TRACK_FILE)) if os.path.exists(TRACK_FILE) else {}

# # --- PDF Ingestion Logic ---
# splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

# data_root = "data" # Assumes you run this from inside the python-worker directory
# new_files = []
# failed_files = []

# print("\n=== SCANNING FOR FILES ===")
# for level in os.listdir(data_root):
#     level_path = os.path.join(data_root, level)
#     if not os.path.isdir(level_path): continue

#     for subject in os.listdir(level_path):
#         subject_path = os.path.join(level_path, subject)
#         if not os.path.isdir(subject_path): continue

#         for file_name in os.listdir(subject_path):
#             if not file_name.lower().endswith(".pdf"): continue

#             file_path = os.path.join(subject_path, file_name)
#             file_hash = get_file_hash(file_path)

#             if file_name in ingested and ingested.get(file_name) == file_hash:
#                 print(f"Skipping {file_name} (already ingested)")
#                 continue

#             print(f"\n📘 Ingesting {file_path}")
#             try:
#                 loader = PyPDFLoader(file_path)
#                 pages = loader.load_and_split(text_splitter=splitter)
                
#                 chunk_docs_to_insert = []
#                 for i, page in enumerate(pages):
#                     chunk_docs_to_insert.append({
#                         "source": file_name, "text": page.page_content,
#                         "level": level, "subject": subject, "chunk_index": i
#                     })
                
#                 result = chunks_collection.insert_many(chunk_docs_to_insert)
#                 print(f"  Saved {len(result.inserted_ids)} text chunks to MongoDB.")

#                 texts_to_embed = [doc['text'] for doc in chunk_docs_to_insert]
#                 vectors = embedder.embed_documents(texts_to_embed)
                
#                 embeddings_to_insert = []
#                 # Retrieve the inserted documents to get their _ids
#                 saved_docs = list(chunks_collection.find({"_id": {"$in": result.inserted_ids}}))
#                 for i, doc in enumerate(saved_docs):
#                     embeddings_to_insert.append({
#                         "_id": doc["_id"], "vector": vectors[i]
#                     })
                
#                 embeddings_collection.insert_many(embeddings_to_insert)
#                 print(f"  Saved {len(embeddings_to_insert)} vectors to MongoDB.")

#                 ingested[file_name] = file_hash
#                 new_files.append(file_name)

#             except Exception as e:
#                 print(f"❌ Error ingesting {file_name}: {e}")
#                 failed_files.append(file_name)

# with open(TRACK_FILE, "w") as f:
#     json.dump(ingested, f, indent=4)
    
# print("\n======= INGESTION COMPLETE =======")




import os
import json
import hashlib
import pymongo
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

# --- Load Environment Variables ---
load_dotenv(dotenv_path=".env.local")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# --- MongoDB Connection ---
print("Connecting to MongoDB...")
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client.get_default_database()
chunks_collection = db.get_collection("icaichunks") # We only need this one collection
print("MongoDB connected.")

# --- LangChain Embedder ---
embedder = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model="text-embedding-ada-002")

# --- Hashing and Tracking ---
TRACK_FILE = "ingested.json"
ingested = json.load(open(TRACK_FILE)) if os.path.exists(TRACK_FILE) else {}
def get_file_hash(fp):
    return hashlib.md5(open(fp, "rb").read()).hexdigest()

# --- PDF Ingestion Logic ---
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
data_root = "data"

print("\n=== SCANNING FOR FILES FOR INGESTION ===")
for level in os.listdir(data_root):
    level_path = os.path.join(data_root, level)
    if not os.path.isdir(level_path): continue
    for subject in os.listdir(level_path):
        subject_path = os.path.join(level_path, subject)
        if not os.path.isdir(subject_path): continue
        for file_name in os.listdir(subject_path):
            if not file_name.lower().endswith(".pdf"): continue
            file_path = os.path.join(subject_path, file_name)
            file_hash = get_file_hash(file_path)

            if file_name in ingested and ingested.get(file_name) == file_hash:
                print(f"Skipping {file_name} (already ingested)")
                continue

            print(f"\n📘 Ingesting {file_path}")
            try:
                loader = PyPDFLoader(file_path)
                pages = loader.load_and_split(text_splitter=splitter)
                
                texts_to_embed = [p.page_content for p in pages]
                print(f"  Created {len(texts_to_embed)} chunks. Generating embeddings...")
                vectors = embedder.embed_documents(texts_to_embed)
                print(f"  Generated {len(vectors)} vectors.")

                # Combine text, metadata, and vector into one document
                docs_to_insert = []
                for i, page in enumerate(pages):
                    docs_to_insert.append({
                        "source": file_name, "text": page.page_content,
                        "level": level, "subject": subject,
                        "embedding": vectors[i] # <-- COMBINE VECTOR HERE
                    })
                
                # Save everything to the 'icaichunks' collection
                chunks_collection.insert_many(docs_to_insert)
                print(f"  Saved {len(docs_to_insert)} documents (with vectors) to MongoDB.")
                ingested[file_name] = file_hash
            except Exception as e:
                print(f"❌ Error ingesting {file_name}: {e}")

with open(TRACK_FILE, "w") as f:
    json.dump(ingested, f, indent=4)
    
print("\n======= INGESTION COMPLETE =======")
import os
import redis
import pymongo
import time
import fitz # Using PyMuPDF
from bson import ObjectId
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings

# --- Load Environment Variables ---
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
QUEUE_NAME = "processing_queue"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Connections & Clients ---
print("--- Python Worker Starting ---")
try:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client.get_default_database()
    mongo_client.admin.command('ping')
    print("MongoDB connected successfully.")
    datasources_collection = db.get_collection("icaidatasources")
    chunks_collection = db.get_collection("icaichunks")
    embeddings_collection = db.get_collection("icaiembeddings")

    redis_conn = redis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)
    redis_conn.ping()
    print("Redis connected successfully.")

    embedder = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    print("OpenAI Embedder initialized.")

except Exception as e:
    print(f"FATAL: Could not initialize connections. Exiting. Error: {e}")
    exit(1)


def get_text_from_pdf_content(pdf_content: bytes) -> str:
    """Extracts text from PDF content using fitz."""
    pdf_text = ""
    with fitz.open(stream=pdf_content, filetype="pdf") as doc:
        for page in doc:
            pdf_text += page.get_text()
    return pdf_text


def process_job(dataSourceId):
    print(f"\nProcessing job for dataSourceId: {dataSourceId}")
    try:
        data_source = datasources_collection.find_one({"_id": ObjectId(dataSourceId)})
        if not data_source:
            print(f"  Error: DataSource with ID {dataSourceId} not found.")
            return

        # Assumes raw PDF content is stored in a field named 'rawContent' as bytes.
        # If not, this needs to be adapted to fetch the file from storage.
        # For our Node.js API, 'rawContent' is the extracted text, so we can use it directly.
        raw_text = data_source.get('rawContent', '')
        if not raw_text:
            datasources_collection.update_one({"_id": data_source["_id"]}, {"$set": {"processingStatus": "PROCESSED"}})
            print(f"  Warning: No rawContent found. Marked as processed.")
            return

        print("  Chunking document...")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=200)
        text_chunks = text_splitter.split_text(raw_text)
        print(f"  Document split into {len(text_chunks)} chunks.")

        chunk_docs_to_insert = []
        for chunk_text in text_chunks:
            chunk_docs_to_insert.append({
                "knowledgeBaseId": data_source["knowledgeBaseId"],
                "dataSourceId": data_source["_id"],
                "chunkText": chunk_text,
                "level": data_source["level"], "paperName": data_source["paperName"],
                "chapter": data_source["chapter"], "documentType": data_source["documentType"],
                "attemptYear": data_source["attemptYear"], "attemptMonth": data_source["attemptMonth"],
            })

        result = chunks_collection.insert_many(chunk_docs_to_insert)
        print(f"  Saved {len(result.inserted_ids)} text chunks to MongoDB.")
        
        saved_chunks = list(chunks_collection.find({"_id": {"$in": result.inserted_ids}}))

        print("  Generating vectors with OpenAI...")
        texts_to_embed = [chunk['chunkText'] for chunk in saved_chunks]
        vectors = embedder.embed_documents(texts_to_embed)

        embeddings_to_insert = []
        for i, chunk in enumerate(saved_chunks):
            embeddings_to_insert.append({
                "_id": chunk["_id"],
                "vector": vectors[i]
            })
        
        if embeddings_to_insert:
            embeddings_collection.insert_many(embeddings_to_insert)
            print(f"  Generated and saved {len(embeddings_to_insert)} vectors to MongoDB.")

        datasources_collection.update_one({"_id": data_source["_id"]}, {"$set": {"processingStatus": "PROCESSED"}})
        print(f"  Successfully processed and updated status for {dataSourceId}")

    except Exception as e:
        print(f"  An unexpected error occurred: {e}")
        datasources_collection.update_one({"_id": ObjectId(dataSourceId)}, {"$set": {"processingStatus": "FAILED"}})


if __name__ == "__main__":
    print(f"Worker listening on Redis queue: '{QUEUE_NAME}'...")
    while True:
        try:
            job = redis_conn.brpop(QUEUE_NAME, timeout=0)
            if job:
                process_job(job[1])
        except Exception as e:
            print(f"A top-level error occurred during listen: {e}")
            time.sleep(5)
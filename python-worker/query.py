import os
import sys
import pymongo
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from langchain.schema import Document

# --- Load Environment Variables ---
load_dotenv(dotenv_path=".env.local")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# Override MongoDB URI to use local instance
MONGO_URI = "mongodb://localhost:27017"

if not OPENAI_API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY in .env.local")

# --- LangChain Clients ---
embedder = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model="text-embedding-ada-002")
llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, temperature=0, model_name="gpt-4o-mini")

# --- Prompt ---
prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template="""
You are a CA Assistant helping students understand accounting concepts.
Use the context from the ICAI material provided to answer the question accurately and in a step-by-step manner.
If the context does not contain the answer, state that the information is not available in the provided documents.

Context:
{context}

Question:
{question}

Answer:
"""
)

def get_answer(level, subject, query):
    print(f"🔍 Searching for '{query}' in Level: {level}, Subject: {subject}...")
    mongo_client = None

    try:
        # Connect to MongoDB
        mongo_client = pymongo.MongoClient(MONGO_URI)
        db = mongo_client["icai-rag-db"]  # Specify the database name explicitly
        # The search runs on the collection that has the index
        chunks_collection = db["icaichunks"]
        print("✅ MongoDB connected.")

        # 1. Create an embedding for the user's query
        question_embedding = embedder.embed_query(query)

                # 2. Perform simple text search with filtering
        # Since we don't have vector search in local MongoDB, we'll use text search
        pipeline = [
            {
                '$match': {
                    'level': level,
                    'paperName': subject  # Use paperName instead of subject
                }
            },
            {
                '$limit': 5
            }
        ]
        
        print(f"🔍 Executing MongoDB query with level: '{level}' and paperName: '{subject}'")
        print(f"🔍 Pipeline: {pipeline}")
        
        # Test query to see if we can get any results
        test_results = list(chunks_collection.find({}))
        print(f"🔍 Total documents in collection: {len(test_results)}")
        
        # Try simple find query first
        simple_results = list(chunks_collection.find({'level': level, 'paperName': subject}))
        print(f"🔍 Simple find query returned: {len(simple_results)} results")
        
        # Get a sample document to see its structure
        sample_doc = chunks_collection.find_one({})
        if sample_doc:
            print(f"🔍 Sample document keys: {list(sample_doc.keys())}")
            print(f"🔍 Sample level: '{sample_doc.get('level', 'NOT_FOUND')}'")
            print(f"🔍 Sample paperName: '{sample_doc.get('paperName', 'NOT_FOUND')}'")
            print(f"🔍 Sample chunkText length: {len(sample_doc.get('chunkText', ''))}")
        
        results = list(chunks_collection.aggregate(pipeline))
        print(f"🔍 Aggregation query returned: {len(results)} results")

        if not results:
            return "❌ No relevant documents found for your query in the specified subject."

        # --- ADDED FOR DEBUGGING ---
        # Print the sources that were found
        print(f"\n📄 Found {len(results)} relevant source chunks:")
        for i, doc in enumerate(results):
            print(f"  --- Source {i+1} ---")
            print(f"  {doc['chunkText'][:350]}...") # Print the first 350 characters
        # ---------------------------

        # Convert results to LangChain Documents
        docs = [Document(page_content=res['chunkText']) for res in results]

        # 3. Run QA Chain
        chain = load_qa_chain(llm=llm, chain_type="stuff", prompt=prompt_template)
        result = chain.invoke({"input_documents": docs, "question": query})

        return result['output_text']

    except Exception as e:
        return f"❌ An error occurred: {str(e)}"

    finally:
        if mongo_client:
            mongo_client.close()
            print("🔌 MongoDB connection closed.")

# --- CLI Execution ---
if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python query.py <Level> <Subject> \"<Your Question>\"")
        sys.exit(1)

    level, subject, question = sys.argv[1], sys.argv[2], sys.argv[3]
    print("\n💭 Thinking...\n")
    answer = get_answer(level, subject, question)
    print("\n--- Answer ---")
    print(answer)
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

if not OPENAI_API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY in .env.local")
if not MONGO_URI:
    raise ValueError("❌ Missing MONGO_URI in .env.local")

# --- LangChain Clients ---
embedder = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model="text-embedding-ada-002")
llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, temperature=0, model_name="gpt-4o-mini")

# --- Prompt ---
prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are a CA Assistant helping students understand accounting and CA concepts.
If the provided ICAI context contains the answer, use it and cite it.
If the context does not contain the answer, answer from your own knowledge as a CA expert.

Context:
{context}

Question:
{question}

Answer:"""
)

def get_answer(level, subject, query):
    print(f"🔍 Searching for '{query}' in Level: {level}, Subject: {subject}...")
    mongo_client = None

    try:
        mongo_client = pymongo.MongoClient(MONGO_URI)
        db = mongo_client["icai-rag-db"]
        chunks_collection = db["icaichunks"]

        # 1. Embed the query
        question_embedding = embedder.embed_query(query)

        # 2. Atlas Vector Search — uses vector_index with pre-filter on level + subject
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": question_embedding,
                    "numCandidates": 100,
                    "limit": 5,
                    "filter": {
                        "level": level,
                        "subject": subject
                    }
                }
            },
            {
                "$project": {
                    "text": 1,
                    "topic_name": 1,
                    "chapter_number": 1,
                    "score": {"$meta": "vectorSearchScore"},
                    "embedding": 0
                }
            }
        ]

        results = list(chunks_collection.aggregate(pipeline))
        print(f"✅ Vector search returned {len(results)} results")

        if not results:
            print("⚠️ No relevant ICAI material found. Answering from general CA knowledge.")
            try:
                response = llm.invoke(query)
                return response.content if hasattr(response, "content") else response
            except Exception as e:
                return f"❌ LLM error: {str(e)}"

        docs = [Document(page_content=res["text"]) for res in results]

        # 3. Run QA Chain
        chain = load_qa_chain(llm=llm, chain_type="stuff", prompt=prompt_template)
        result = chain.invoke({"input_documents": docs, "question": query})
        return result["output_text"]

    except Exception as e:
        return f"❌ An error occurred: {str(e)}"

    finally:
        if mongo_client:
            mongo_client.close()

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
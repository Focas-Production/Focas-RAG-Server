import os
import sys
import pymongo
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from langchain.schema import Document

load_dotenv()
load_dotenv(".env.local", override=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

if not OPENAI_API_KEY:
    raise ValueError("❌ Missing OPENAI_API_KEY")
if not MONGO_URI:
    raise ValueError("❌ Missing MONGO_URI")

# ── Config (all overridable via .env.local) ──────────────────────────────────
QUERY_MODEL        = os.getenv("QUERY_MODEL",        "gpt-4.1-mini")
QUERY_MAX_TOKENS   = int(os.getenv("QUERY_MAX_TOKENS",   "600"))
QUERY_TEMPERATURE  = float(os.getenv("QUERY_TEMPERATURE", "0"))
# Must match the model used at ingest time — switching models requires full re-ingest
EMBEDDING_MODEL    = os.getenv("EMBEDDING_MODEL",    "text-embedding-ada-002")
QUERY_TOP_K        = int(os.getenv("QUERY_TOP_K",    "4"))   # chunks to retrieve

# Pricing per 1K tokens (input, output)
_MODEL_PRICING = {
    "gpt-4.1":          (0.00200, 0.00800),
    "gpt-4.1-mini":     (0.00040, 0.00160),
    "gpt-4o":           (0.00250, 0.01000),
    "gpt-4o-mini":      (0.00015, 0.00060),
}
# Embedding pricing per 1K tokens
_EMBED_PRICING = {
    "text-embedding-3-small": 0.00002,
    "text-embedding-3-large": 0.00013,
    "text-embedding-ada-002": 0.00010,
}

embedder = OpenAIEmbeddings(
    openai_api_key=OPENAI_API_KEY,
    model=EMBEDDING_MODEL,
)
llm = ChatOpenAI(
    openai_api_key=OPENAI_API_KEY,
    temperature=QUERY_TEMPERATURE,
    model_name=QUERY_MODEL,
    max_tokens=QUERY_MAX_TOKENS,
)

prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template="""You are a CA exam assistant. Use only the ICAI source content below.
If the answer is in the content, cite the relevant concept. Be concise.

Content:
{context}

Question: {question}

Answer:"""
)


def _estimate_query_cost(input_tokens: int, output_tokens: int, embed_tokens: int) -> float:
    in_rate, out_rate = _MODEL_PRICING.get(QUERY_MODEL, (0, 0))
    emb_rate = _EMBED_PRICING.get(EMBEDDING_MODEL, 0)
    return (
        (input_tokens / 1000) * in_rate
        + (output_tokens / 1000) * out_rate
        + (embed_tokens / 1000) * emb_rate
    )


def get_answer(level, subject, query):
    print(f"🔍 Searching: '{query}'  [level={level}  subject={subject}]")
    print(f"   Model: {QUERY_MODEL} | max_tokens: {QUERY_MAX_TOKENS} | embed: {EMBEDDING_MODEL}")
    mongo_client = None

    try:
        mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = mongo_client.get_default_database()
        chunks_collection = db["icaichunks"]

        # 1. Embed the query
        embed_tokens = max(1, len(query.split()) + 5)   # rough estimate
        question_embedding = embedder.embed_query(query)

        # 2. Atlas Vector Search
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": question_embedding,
                    "numCandidates": 50,
                    "limit": QUERY_TOP_K,
                    "filter": {"level": level, "subject": subject},
                }
            },
            {
                "$project": {
                    "text": 1, "topic_name": 1,
                    "chapter_number": 1, "chapter_name": 1,
                    "score": {"$meta": "vectorSearchScore"},
                    "embedding": 0,
                }
            },
        ]

        results = list(chunks_collection.aggregate(pipeline))
        print(f"✅ Retrieved {len(results)} chunks")

        if not results:
            print("⚠️ No ICAI material found — answering from general knowledge")
            response = llm.invoke(query)
            answer = response.content if hasattr(response, "content") else str(response)
            return answer

        docs = [Document(page_content=r["text"]) for r in results]

        # 3. QA chain
        chain = load_qa_chain(llm=llm, chain_type="stuff", prompt=prompt_template)
        result = chain.invoke({"input_documents": docs, "question": query})
        answer = result["output_text"]

        # Cost estimate
        context_chars = sum(len(r["text"]) for r in results)
        input_tokens  = max(1, int((context_chars + len(query) + 200) / 4))
        output_tokens = max(1, int(len(answer) / 4))
        cost = _estimate_query_cost(input_tokens, output_tokens, embed_tokens)
        print(f"💰 Est. cost: ${cost:.5f}  (in≈{input_tokens} out≈{output_tokens} tokens)")

        return answer

    except Exception as e:
        err = str(e)
        if "insufficient_quota" in err or "exceeded your current quota" in err:
            return "❌ OpenAI quota exhausted — add credits at platform.openai.com/account/billing"
        return f"❌ Error: {err}"

    finally:
        if mongo_client:
            mongo_client.close()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python query.py <Level> <Subject> \"<Question>\"")
        sys.exit(1)

    level, subject, question = sys.argv[1], sys.argv[2], sys.argv[3]
    print("\n💭 Thinking...\n")
    answer = get_answer(level, subject, question)
    print("\n--- Answer ---")
    print(answer)

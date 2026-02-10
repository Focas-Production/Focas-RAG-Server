import os
import json
import re
import hashlib
import pymongo
from datetime import datetime, timezone
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
import fitz
from typing import List, Dict, Tuple, Optional

# --- Load Environment Variables ---
load_dotenv(dotenv_path=".env.local")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# --- MongoDB Connection ---
print("Connecting to MongoDB...")
mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client.get_default_database()
chunks_collection = db.get_collection("icaichunks")
print("✅ MongoDB connected.\n")

# --- PRODUCTION INDEXES ---
def create_production_indexes():
    print("📍 Creating Production Indexes...\n")
    
    indexes = [
        ([("level", 1), ("subject", 1)], "1. level + subject (PRIMARY)"),
        ([("topic_number", 1)], "2. topic_number"),
        ([("topic_name", 1)], "3. topic_name"),
        ([("chapter_number", 1)], "4. chapter_number"),
        ([("chunk_id", 1)], "5. chunk_id (unique)"),
        ([("source", 1)], "6. source"),
    ]
    
    count = 0
    for index_spec, description in indexes:
        try:
            chunks_collection.create_index(index_spec)
            print(f"  ✅ {description}")
            count += 1
        except Exception as e:
            if "already exists" in str(e):
                print(f"  ℹ️  {description} (exists)")
            else:
                print(f"  ⚠️ {description}")
            count += 1
    
    print(f"\n✅ Total: {count} Indexes Created\n")

create_production_indexes()

# --- LangChain Clients ---
embedder = OpenAIEmbeddings(
    openai_api_key=OPENAI_API_KEY,
    model="text-embedding-3-small"

)

llm = ChatOpenAI(
    openai_api_key=OPENAI_API_KEY,
    temperature=0,
    model_name="gpt-4-turbo",
    max_tokens=4096
)

# --- Tracking ---
TRACK_FILE = "ingested.json"
ingested = json.load(open(TRACK_FILE)) if os.path.exists(TRACK_FILE) else {}

def get_file_hash(fp):
    return hashlib.md5(open(fp, "rb").read()).hexdigest()

# ===== INTELLIGENT TOPIC DETECTION =====

class IntelligentTopicDetector:
    """Detects topics by analyzing text structure and using LLM for validation"""

    @classmethod
    def extract_topics_with_regex(cls, full_text: str) -> List[Dict]:
        """Fallback topic extraction using regex for numbered headings"""
        pattern = re.compile(r"^\s*((?:\d+\.)*\d+)\s+([^\n]{3,160})", re.MULTILINE)
        topics = []
        seen = set()

        for match in pattern.finditer(full_text):
            number = match.group(1).rstrip('.')
            title = match.group(2).strip()
            position = match.start()

            # Skip if title is too short or we've already captured this position
            if len(title) < 4 or position in seen:
                continue

            seen.add(position)
            topics.append({
                "full_number": number,
                "name": title,
                "position": position
            })

        if topics:
            print(f"     🔍 Regex fallback detected {len(topics)} topics\n")

        return topics

    @classmethod
    def extract_all_topics_with_llm(cls, full_text: str) -> List[Dict]:
        """
        Ask LLM to extract ALL topics from entire document
        Returns structured list of all topics found
        """
        prompt = f"""Analyze this entire academic document and extract EVERY section header/topic.

DOCUMENT TEXT:
{full_text}

TASK:
1. Find ALL numbered sections (1.1, 1.2, 1.3, 1.4, etc.)
2. Extract topic number and exact title from the document
3. Do NOT invent topics - only extract what exists
4. Be thorough - include every section you see

OUTPUT FORMAT (one per line):
TOPICNUMBER|EXACT_TITLE

Example output:
1.1|SCOPE OF THE ACT
1.2|DEFINITIONS
1.3|SALE AND AGREEMENT TO SELL
1.4|DISTINCTION BETWEEN SALE AND AN AGREEMENT TO SELL
1.5|SALE DISTINGUISHED FROM OTHER SIMILAR CONTRACTS

Return ONLY the list, no other text or explanation."""

        try:
            response = llm.invoke(prompt)
            topics_text = response.content
            
            topics = []
            for line in topics_text.split('\n'):
                line = line.strip()
                if not line or '|' not in line:
                    continue
                
                try:
                    parts = line.split('|', 1)
                    number = parts[0].strip()
                    title = parts[1].strip() if len(parts) > 1 else ""
                    
                    if number and title and 3 < len(title) < 150:
                        topics.append({
                            "number": number,
                            "title": title
                        })
                except:
                    continue
            
            return topics
        except Exception as e:
            print(f"  ⚠️  LLM extraction failed: {e}")
            return []
    
    @classmethod
    def find_topic_positions(cls, topics: List[Dict], full_text: str) -> List[Dict]:
        """
        Find exact character positions for each topic in the text
        Uses flexible pattern matching
        """
        positioned_topics = []
        
        for topic in topics:
            number = topic["number"]
            title = topic["title"]
            
            # Try multiple search patterns
            patterns = [
                # Pattern 1: Number + Title on same line
                rf'\b{re.escape(number)}\s+{re.escape(title[:20])}',
                # Pattern 2: Number on one line, title nearby
                rf'\b{re.escape(number)}\s+[^\n]*{re.escape(title[:15])}',
                # Pattern 3: Just the number
                rf'\b{re.escape(number)}\s+[A-Z]',
            ]
            
            position = -1
            for pattern in patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    position = match.start()
                    break
            
            if position >= 0:
                positioned_topics.append({
                    "full_number": number,
                    "name": title,
                    "position": position
                })
        
        # Sort by position
        positioned_topics = sorted(positioned_topics, key=lambda x: x["position"])
        return positioned_topics
    
    @classmethod
    def detect_topics(cls, full_text: str) -> List[Dict]:
        """Main detection method"""
        print(f"  🧠 Using LLM to extract all topics from document...\n")
        
        # Extract topics using LLM
        llm_topics = cls.extract_all_topics_with_llm(full_text)
        print(f"     LLM extracted: {len(llm_topics)} topics")
        
        if not llm_topics:
            print(f"     ⚠️  No topics found\n")
            return []
        
        # Find positions for each topic
        positioned_topics = cls.find_topic_positions(llm_topics, full_text)
        print(f"     Positioned: {len(positioned_topics)} topics\n")

        if not positioned_topics:
            regex_topics = cls.extract_topics_with_regex(full_text)
            if regex_topics:
                positioned_topics = regex_topics

        # Print detected topics
        if positioned_topics:
            print(f"     ✅ Detected topics:\n")
            for i, t in enumerate(positioned_topics, 1):
                print(f"        {i}. [{t['full_number']}] {t['name'][:70]}")
            print()
        
        return positioned_topics

# ===== TOPIC-WISE CHUNKING =====

class TopicWiseChunker:
    """Chunks content strictly within topic boundaries"""
    
    def __init__(self, chunk_size: int = 1500, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n\n", "\n\n", "\n", ". ", "! ", "? ", " ", ""]
        )
    
    def create_chunks(self, full_text: str, topics: List[Dict]) -> List[Dict]:
        """Create chunks strictly within topic boundaries"""
        all_chunks = []
        chunk_id = 0
        min_chunk_length = 30

        def append_segment(segment_text: str, *, chunk_type: str, topic_number: str = "", topic_name: str = "") -> int:
            nonlocal chunk_id

            if not segment_text:
                return 0

            cleaned = segment_text.strip()
            if len(cleaned) < min_chunk_length:
                return 0

            raw_chunks = self.text_splitter.split_text(cleaned)
            filtered_chunks = [c.strip() for c in raw_chunks if len(c.strip()) >= min_chunk_length]

            total = len(filtered_chunks)
            for order, chunk_text in enumerate(filtered_chunks):
                all_chunks.append({
                    "text": chunk_text,
                    "topic_number": topic_number,
                    "topic_name": topic_name,
                    "chunk_id": chunk_id,
                    "chunk_order": order,
                    "total_chunks_in_topic": total if total else 1,
                    "is_topic_start": chunk_type == "topic_content" and order == 0,
                    "chunk_type": chunk_type
                })
                chunk_id += 1

            return total

        if not topics:
            print("  ⚠️  No topics found - using standard chunking\n")
            append_segment(full_text, chunk_type="standard", topic_name="Standard Chunk")
            
            return all_chunks
        
        print(f"  ✂️  Chunking {len(topics)} topics...\n")
        cursor = 0
        total_length = len(full_text)

        # Process each topic and capture any gaps between them
        for idx, topic in enumerate(topics):
            start = topic["position"]

            if start > cursor:
                gap_type = "preface" if cursor == 0 else "gap_content"
                gap_name = "Preface / Introduction" if gap_type == "preface" else "Unassigned Gap"
                created = append_segment(
                    full_text[cursor:start],
                    chunk_type=gap_type,
                    topic_name=gap_name
                )
                if created:
                    label = "Preface" if gap_type == "preface" else "Gap"
                    print(f"     ℹ️  {label} segment captured → {created} chunks")

            if idx + 1 < len(topics):
                end = topics[idx + 1]["position"]
            else:
                end = total_length

            topic_content = full_text[start:end]
            created = append_segment(
                topic_content,
                chunk_type="topic_content",
                topic_number=topic["full_number"],
                topic_name=topic["name"]
            )

            if created:
                print(f"     ✅ [{topic['full_number']}] {topic['name'][:50]} → {created} chunks")
            else:
                print(f"     ⚠️  [{topic['full_number']}] {topic['name'][:50]} - no sizable content")

            cursor = end

        if cursor < total_length:
            created = append_segment(
                full_text[cursor:],
                chunk_type="postface",
                topic_name="Post-topic Tail"
            )
            if created:
                print(f"     ℹ️  Post-topic tail captured → {created} chunks")

        print()
        return all_chunks

# ===== PDF EXTRACTION =====

def extract_text_from_pdf(pdf_path: str) -> Tuple[str, List[Dict]]:
    """Extract text from PDF and detect topics"""
    print(f"  📖 Extracting text from PDF...")
    
    try:
        with fitz.open(pdf_path) as doc:
            full_text = ""
            
            for page in doc:
                full_text += page.get_text() + "\n"
            
            print(f"  ✅ Extracted {len(doc)} pages ({len(full_text)} characters)\n")
            
            # Detect topics using LLM
            topics = IntelligentTopicDetector.detect_topics(full_text)
            
            return full_text, topics
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return "", []

# ===== FILENAME PARSING =====

def parse_filename(file_name: str) -> dict:
    """Parse PDF filename"""
    metadata = {
        "chapter_number": "",
        "chapter_name": "",
        "unit_number": "",
        "unit_name": "",
        "level": "",
        "subject": ""
    }
    
    name = file_name.replace(".pdf", "").strip()
    
    pattern1 = r"Chapter_(\d+)_(.+?)_Unit_(\d+)_(.+)"
    match = re.match(pattern1, name, re.IGNORECASE)
    if match:
        metadata["chapter_number"] = match.group(1)
        metadata["chapter_name"] = match.group(2).replace("_", " ")
        metadata["unit_number"] = match.group(3)
        metadata["unit_name"] = match.group(4).replace("_", " ")
        return metadata
    
    pattern2 = r"Chapter_(\d+)_(.+)"
    match = re.match(pattern2, name, re.IGNORECASE)
    if match:
        metadata["chapter_number"] = match.group(1)
        metadata["chapter_name"] = match.group(2).replace("_", " ")
        return metadata
    
    return metadata

# ===== MAIN INGESTION =====

def process_pdf_file(file_path: str, file_name: str, level: str, subject: str) -> bool:
    """Process PDF with topic-wise chunking"""
    try:
        meta = parse_filename(file_name)
        if not meta["chapter_number"]:
            print(f"  ⚠️  Could not parse filename")
            return False
        
        level_extracted = meta.get("level") or level
        subject_extracted = meta.get("subject") or subject
        
        print(f"  📊 Chapter: {meta['chapter_number']} | Level: {level_extracted} | Subject: {subject_extracted}\n")
        
        # Extract text and detect topics
        full_text, topics = extract_text_from_pdf(file_path)
        
        if not full_text:
            print(f"  ❌ Failed to extract text\n")
            return False
        
        # Create topic-wise chunks
        chunker = TopicWiseChunker(chunk_size=1500, chunk_overlap=200)
        chunks = chunker.create_chunks(full_text, topics)
        
        if not chunks:
            print(f"  ⚠️  No chunks created\n")
            return False
        
        # Generate embeddings
        print(f"  🧠 Generating {len(chunks)} embeddings...")
        texts = [chunk["text"] for chunk in chunks]
        embeddings = embedder.embed_documents(texts)
        
        # Prepare documents
        print(f"  💾 Preparing documents for database...")
        docs_to_insert = []
        
        for i, chunk in enumerate(chunks):
            doc = {
                "source": file_name,
                "text": chunk["text"],
                "chunk_id": chunk["chunk_id"],
                "chunk_order": chunk["chunk_order"],
                "level": level_extracted,
                "subject": subject_extracted,
                
                "chapter_number": meta.get("chapter_number", ""),
                "chapter_name": meta.get("chapter_name", ""),
                "unit_number": meta.get("unit_number", ""),
                "unit_name": meta.get("unit_name", ""),
                
                "topic_number": chunk["topic_number"],
                "topic_name": chunk["topic_name"],
                
                "total_chunks_in_topic": chunk.get("total_chunks_in_topic", 1),
                "is_topic_start": chunk.get("is_topic_start", False),
                "chunk_type": chunk.get("chunk_type", "standard"),
                
                "embedding": embeddings[i],
                "created_at": datetime.now(timezone.utc),
                "text_length": len(chunk["text"]),
                "word_count": len(chunk["text"].split())
            }
            docs_to_insert.append(doc)
        
        # Insert into MongoDB
        result = chunks_collection.insert_many(docs_to_insert)
        
        # Summary
        topic_chunks = [c for c in chunks if c["topic_number"]]
        unique_topics = set([c["topic_number"] for c in chunks if c["topic_number"]])
        
        print(f"\n  📊 INGESTION SUMMARY:")
        print(f"     ✅ Total chunks: {len(chunks)}")
        print(f"     📚 Topic chunks: {len(topic_chunks)}")
        print(f"     🎯 Unique topics: {len(unique_topics)}")
        print(f"     💾 DB inserts: {len(result.inserted_ids)}\n")
        
        return True
        
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

# ===== MAIN EXECUTION =====

data_root = "data"

print("\n" + "="*80)
print("🚀 PRODUCTION RAG - LLM-POWERED TOPIC-WISE CHUNKING")
print("="*80 + "\n")

total_processed = 0
total_failed = 0

for level in os.listdir(data_root):
    level_path = os.path.join(data_root, level)
    if not os.path.isdir(level_path):
        continue
    
    for subject in os.listdir(level_path):
        subject_path = os.path.join(level_path, subject)
        if not os.path.isdir(subject_path):
            continue
        
        print(f"📁 {level} / {subject}")
        print("-" * 80)
        
        for file_name in os.listdir(subject_path):
            if not file_name.lower().endswith(".pdf"):
                continue
            
            file_path = os.path.join(subject_path, file_name)
            file_hash = get_file_hash(file_path)

            if file_name in ingested and ingested.get(file_name) == file_hash:
                print(f"⏭️  SKIP: {file_name}\n")
                continue

            print(f"📘 {file_name}\n")
            
            success = process_pdf_file(file_path, file_name, level, subject)
            
            if success:
                ingested[file_name] = file_hash
                total_processed += 1
                print(f"✅ SUCCESS\n")
            else:
                total_failed += 1
                print(f"❌ FAILED\n")

# Save tracking
with open(TRACK_FILE, "w") as f:
    json.dump(ingested, f, indent=4)

print("="*80)
print(f"📊 Processed: {total_processed} | Failed: {total_failed} | Tracked: {len(ingested)}")
print("="*80)

if chunks_collection.count_documents({}) > 0:
    total_chunks = chunks_collection.count_documents({})
    total_topics = len(chunks_collection.distinct("topic_number")) - 1
    
    print(f"\n📈 DATABASE:")
    print(f"   Total chunks: {total_chunks}")
    print(f"   Total topics: {total_topics}")
    print("="*80)
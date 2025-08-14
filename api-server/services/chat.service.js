const { OpenAI } = require("openai");
const { OpenAIEmbeddings } = require("@langchain/openai");
const Icaichunk = require('../models/icaiChunk.schema');

// Initialize OpenAI client
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const embeddings = new OpenAIEmbeddings({ openAIApiKey: process.env.OPENAI_API_KEY, model: "text-embedding-ada-002" });

async function getRagResponse(userMessage, filters = {}) {
    console.log(`[RAG Service] Getting response for: "${userMessage}" with filters:`, filters);

    try {
        // For now, use Express RAG service directly
        // TODO: Add Python worker integration back once axios is properly installed
        console.log("  Using Express RAG service...");
        const questionEmbedding = await embeddings.embedQuery(userMessage);
        console.log("  Step 1: Created embedding for the user's question.");

        const sourceChunks = await findSimilarChunks(questionEmbedding, filters);
        console.log(`  Step 2: Found ${sourceChunks.length} relevant source chunks from MongoDB.`);

        if (sourceChunks.length === 0) {
            return { aiAnswer: "I'm sorry, I couldn't find any relevant information to answer your question.", sourceChunks: [] };
        }

        const context = sourceChunks.map(chunk => chunk.chunkText || chunk.text).join('\n---\n');
        const prompt = `Based ONLY on the following context from the ICAI syllabus, answer the user's question concisely. Context:\n${context}\n\nQuestion: ${userMessage}`;
        
        const completion = await openai.chat.completions.create({
            model: "gpt-4o-mini",
            messages: [{ role: "user", content: prompt }],
            temperature: 0.2,
        });
        const aiAnswer = completion.choices[0].message.content;
        console.log("  Step 4: Received final answer from the LLM.");

        // Normalize the source chunks to have consistent field names
        const sourcesForUI = sourceChunks.map(chunk => ({
            ...chunk,
            chunkText: chunk.chunkText || chunk.text || 'No text available',
            source: chunk.sourceFileName || chunk.paperName || 'Unknown source'
        }));

        return { aiAnswer, sourceChunks: sourcesForUI };
    } catch (error) {
        console.error("Error in getRagResponse:", error);
        return { 
            aiAnswer: "I'm sorry, I encountered an error while processing your question. Please try again.", 
            sourceChunks: [] 
        };
    }
}

async function findSimilarChunks(vector, filters) {
    try {
        const pipeline = [
            {
                '$vectorSearch': {
                    'index': 'vector_index',
                    'path': 'embedding', // The field name must match your index
                    'queryVector': vector,
                    'numCandidates': 150,
                    'limit': 5,
                    'filter': {}
                }
            }
        ];

        // Add metadata filters if they exist
        if (filters.level) {
            pipeline[0].$vectorSearch.filter.level = filters.level;
        }
        if (filters.subject) {
            pipeline[0].$vectorSearch.filter.subject = filters.subject;
        }
        
        // The search now runs directly on the 'Icaichunk' model/collection
        return await Icaichunk.aggregate(pipeline);

    } catch (error) {
        console.error("Error during vector search:", error);
        return [];
    }
}

module.exports = {
    getRagResponse,
};
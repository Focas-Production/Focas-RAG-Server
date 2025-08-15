const ChatSession = require('../models/chatSession.schema');
const User = require('../models/user.schema');
const chatService = require('../services/chat.service');

/**
 * Creates a new, empty chat session for a user.
 */
const createNewSession = async (req, res) => {
    try {
        const { userId, title, level, subject } = req.body;
        if (!userId) {
            return res.status(400).json({ message: 'User ID is required.' });
        }
        
        // Find or create user
        let user = await User.findOne({ userId: userId });
        if (!user) {
            user = new User({ userId: userId });
            await user.save();
        }
        
        // This creates a placeholder until we have a real KnowledgeBase model integrated
        const mockKnowledgeBaseId = '66883f3a5e3f7f2b1c3c5a6b'; // Replace with a real ID

        const newSession = new ChatSession({
            user: user._id, // Use the ObjectId from the User model
            sessionTitle: title || 'New ICAI Chat',
            knowledgeBaseId: mockKnowledgeBaseId,
            messages: [],
            chatContext: {
                level: level || 'Foundation',
                subject: subject || 'accounting'
            }
        });

        await newSession.save();
        res.status(201).json(newSession);
    } catch (error) {
        console.error('Error creating new session:', error);
        res.status(500).json({ message: 'Server error' });
    }
};

/**
 * Handles an incoming message from the user, gets an AI response, and saves it.
 */
const handleChatMessage = async (req, res) => {
    try {
        const { sessionId, userMessage, level, subject } = req.body;
        if (!sessionId || !userMessage) {
            return res.status(400).json({ message: 'Session ID and message are required.' });
        }

        // 1. Find the chat session
        const chatSession = await ChatSession.findById(sessionId);
        if (!chatSession) {
            return res.status(404).json({ message: 'Chat session not found.' });
        }

        // 2. Save the user's message first
        chatSession.messages.push({ role: 'user', content: userMessage });
        
        // 3. Get the AI's response using the RAG service
        // Use provided level/subject or fall back to session context
        const contextFilters = {
            level: level || chatSession.chatContext?.level || 'Foundation',
            subject: subject || chatSession.chatContext?.subject || 'accounting'
        };

        const { aiAnswer, sourceChunks } = await chatService.getRagResponse(userMessage, contextFilters);

        // 4. Save the AI's answer with its sources
        chatSession.messages.push({
            role: 'assistant',
            content: aiAnswer,
            sourceChunkIds: sourceChunks.map(chunk => chunk._id) // Store the source chunk IDs
        });

        // Update session context if new level/subject provided
        if (level || subject) {
            chatSession.chatContext = {
                ...chatSession.chatContext,
                level: level || chatSession.chatContext?.level,
                subject: subject || chatSession.chatContext?.subject
            };
        }

        await chatSession.save();

        // 5. Return the answer and sources to the UI for display
        res.status(200).json({
            answer: aiAnswer,
            sources: sourceChunks, // Send full source objects for citation
            context: contextFilters // Return the context used for the query
        });

    } catch (error) {
        console.error('Error handling chat message:', error);
        res.status(500).json({ message: 'Server error' });
    }
};

/**
 * New endpoint specifically for React Native app - simplified query without session management
 */
const handleDirectQuery = async (req, res) => {
    try {
        const { userMessage, level, subject, userId } = req.body;
        
        if (!userMessage || !level || !subject) {
            return res.status(400).json({ 
                message: 'userMessage, level, and subject are required.' 
            });
        }

        console.log(`[Direct Query] Processing: "${userMessage}" for ${level}/${subject}`);

        // Get the AI's response using the RAG service
        const { aiAnswer, sourceChunks } = await chatService.getRagResponse(userMessage, { level, subject });

        // If userId is provided, optionally save to a session for history
        if (userId) {
            try {
                // Find or create user
                let user = await User.findOne({ userId: userId });
                if (!user) {
                    user = new User({ userId: userId });
                    await user.save();
                }

                // Create or find existing session
                let chatSession = await ChatSession.findOne({ 
                    user: user._id, 
                    'chatContext.level': level,
                    'chatContext.subject': subject
                });

                if (!chatSession) {
                    const mockKnowledgeBaseId = '66883f3a5e3f7f2b1c3c5a6b';
                    chatSession = new ChatSession({
                        user: user._id,
                        sessionTitle: `${level} - ${subject} Chat`,
                        knowledgeBaseId: mockKnowledgeBaseId,
                        messages: [],
                        chatContext: { level, subject }
                    });
                }

                // Save the conversation
                chatSession.messages.push({ role: 'user', content: userMessage });
                chatSession.messages.push({ 
                    role: 'assistant', 
                    content: aiAnswer,
                    sourceChunkIds: sourceChunks.map(chunk => chunk._id)
                });

                await chatSession.save();
            } catch (sessionError) {
                console.log('Session save failed, but continuing with response:', sessionError.message);
            }
        }

        // Return the answer and sources
        res.status(200).json({
            answer: aiAnswer,
            sources: sourceChunks,
            context: { level, subject },
            timestamp: new Date().toISOString()
        });

    } catch (error) {
        console.error('Error handling direct query:', error);
        res.status(500).json({ message: 'Server error' });
    }
};

/**
 * Get available levels and subjects for the React Native app
 */
const getAvailableSubjects = async (req, res) => {
    try {
        const subjects = {
            "Foundation": ["accounting", "business_economics", "business_law", "quantitative_aptitude"],
            "Intermediate": ["advanced_accounting", "auditing_and_ethics", "corporate_and_other_laws", 
                           "cost_and_management_accounting", "financial_management", "idt", "it", "strategic_management"],
            "Final": ["auditing"]
        };

        res.status(200).json({
            subjects,
            message: "Available subjects retrieved successfully"
        });
    } catch (error) {
        console.error('Error getting subjects:', error);
        res.status(500).json({ message: 'Server error' });
    }
};

module.exports = {
    createNewSession,
    handleChatMessage,
    handleDirectQuery,
    getAvailableSubjects,
};
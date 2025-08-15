const express = require('express');
const router = express.Router();
const chatController = require('../controllers/chat.controller.js');

// Route to create a new chat session
router.post('/session', chatController.createNewSession);

// Route to handle a new message in an existing session
router.post('/message', chatController.handleChatMessage);

// New endpoint specifically for React Native app - simplified query without session management
router.post('/query', chatController.handleDirectQuery);

// New endpoint for React Native app - get available levels and subjects
router.get('/subjects', chatController.getAvailableSubjects);

module.exports = router;
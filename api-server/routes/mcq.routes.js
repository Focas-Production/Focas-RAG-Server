const express = require('express');
const router = express.Router();
const mcqController = require('../controllers/mcq.controller');

// Proxy to Python worker for MCQ generation
router.post('/generate', mcqController.generateMcq);

module.exports = router;

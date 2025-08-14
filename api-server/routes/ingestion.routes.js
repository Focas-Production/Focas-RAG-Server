const express = require('express');
const multer = require('multer');
const ingestionController = require('../controllers/ingestion.controller');

const router = express.Router();

// Configure multer for in-memory file storage
const storage = multer.memoryStorage();
const upload = multer({ storage: storage });

// Define the route for uploading and processing documents
// It expects a multipart/form-data request with a 'file' field and other metadata fields.
router.post(
  '/upload',
  upload.single('file'),
  ingestionController.uploadAndProcessDocument
);

module.exports = router;
const Icaidatasource = require('../models/icaiDataSource.schema');
const redisService = require('../services/redis.service');

const uploadAndProcessDocument = async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ message: 'No file uploaded.' });
    }

    const {
      knowledgeBaseId, level, group, paperNumber, paperName,
      chapter, topic, documentType, attemptYear, attemptMonth,
    } = req.body;

    if (!knowledgeBaseId || !level || !paperName || !attemptYear) {
      return res.status(400).json({ message: 'Missing required metadata fields.' });
    }
    
    // The Python worker will handle all text extraction.
    // We save the raw file buffer directly to the database.
    const newDataSource = new Icaidatasource({
      knowledgeBaseId, level, group, paperNumber, paperName,
      chapter, topic, documentType, attemptYear, attemptMonth,
      sourceFileName: req.file.originalname,
      rawContent: req.file.buffer, // Save the raw file buffer
      fileType: req.file.mimetype, // Save the file type (e.g., 'application/pdf')
      processingStatus: 'PENDING',
    });

    await newDataSource.save();
    console.log(`  Saved new data source with ID: ${newDataSource._id}`);

    await redisService.addJobToQueue(newDataSource._id.toString());
    
    res.status(202).json({
      message: 'File accepted and is being processed in the background.',
      dataSourceId: newDataSource._id,
    });

  } catch (error) {
    console.error('[Controller] Error during document upload:', error);
    res.status(500).json({ message: 'An internal server error occurred.' });
  }
};

module.exports = {
  uploadAndProcessDocument,
};
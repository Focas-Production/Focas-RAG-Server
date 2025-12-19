const mcqService = require('../services/mcq.service');

/**
 * Proxy endpoint to generate MCQs via the Python worker.
 * Simply forwards the request body and returns the worker's response.
 *  */
const generateMcq = async (req, res) => {
  try {
    const mcqResponse = await mcqService.generateMcq(req.body);
    return res.status(200).json(mcqResponse);
  } catch (error) {
    const status = error.status || 500;
    const fallback = { success: false, message: error.message || 'Failed to generate MCQ' };
    const body = error.data || fallback;
    return res.status(status).json(body);
  }
};

module.exports = {
  generateMcq,
};

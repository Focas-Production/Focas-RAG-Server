const axios = require('axios');

// Base URL for the Python worker. Default to local dev port if env not provided.
const PYTHON_API_BASE_URL = process.env.PYTHON_API_BASE_URL || 'http://localhost:5001';

/**
 * Calls the Python worker's MCQ generation endpoint and returns the raw response.
 * @param {object} payload The MCQ generation request body
 */
async function generateMcq(payload) {
  try {
    const response = await axios.post(`${PYTHON_API_BASE_URL}/mcq/generate`, payload, { timeout: 300000 });
    return response.data;
  } catch (error) {
    const status = error.response?.status || 500;
    const data = error.response?.data;
    const message = data?.error || data?.message || error.message || 'Failed to generate MCQ';

    const wrappedError = new Error(message);
    wrappedError.status = status;
    wrappedError.data = data;
    throw wrappedError;
  }
}

module.exports = {
  generateMcq,
};

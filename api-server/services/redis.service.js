const redis = require('redis');

let redisClient;
let isConnected = false;

async function getConnectedClient() {
    if (!isConnected) {
        console.log('[Redis Service] Client not connected, attempting to connect...');
        redisClient = redis.createClient({
            url: `redis://${process.env.REDIS_HOST || 'redis'}:${process.env.REDIS_PORT || 6379}`
        });

        redisClient.on('error', (err) => {
            console.error('Redis Client Error', err);
            isConnected = false; // Reset connection status on error
        });

        try {
            await redisClient.connect();
            isConnected = true;
            console.log('[Redis Service] Successfully connected to Redis.');
        } catch (err) {
            console.error('[Redis Service] Failed to connect to Redis:', err);
            isConnected = false;
            throw err; // Re-throw the error to be caught by the controller
        }
    }
    return redisClient;
}

/**
 * Adds a job to the processing queue.
 * @param {string} dataSourceId The ID of the document to be processed by the Python worker.
 */
async function addJobToQueue(dataSourceId) {
    const QUEUE_NAME = "processing_queue";
    try {
        const client = await getConnectedClient();
        await client.lPush(QUEUE_NAME, dataSourceId);
        console.log(`[Redis Service] Added job for dataSourceId: ${dataSourceId} to the queue.`);
    } catch (error) {
        console.error('Error adding job to Redis queue:', error);
        // We can re-throw the error so the controller knows something went wrong
        throw error;
    }
}

// Initial connection attempt
getConnectedClient();

module.exports = {
    addJobToQueue,
};
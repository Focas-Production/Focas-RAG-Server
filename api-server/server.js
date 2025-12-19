// const express = require('express');
// const mongoose = require('mongoose');
// const dotenv = require('dotenv');
// const cors = require('cors');

// // Load environment variables
// dotenv.config();

// // Import routes
// const ingestionRoutes = require('./routes/ingestion.routes');
// const chatRoutes = require('./routes/chat.routes.js')

// const app = express();
// const PORT = process.env.PORT || 5555;


// // Comprehensive CORS configuration for preview builds
// const corsOptions = {
//   origin: function (origin, callback) {
//     // Allow requests with no origin (like mobile apps, Postman, etc.)
//     if (!origin) return callback(null, true);
    
//     // Allow specific origins
//     const allowedOrigins = [
//       'http://localhost:3000',
//       'http://localhost:19006',
//       'exp://localhost:19000',
//       'https://expo.dev',
//       'https://expo.io',
//       'https://expo-development-client.netlify.app',
//       // Add your app's bundle identifier
//       'com.focas.caguru',
//       // Allow all Expo preview builds
//       /^https:\/\/.*\.expo\.dev$/,
//       /^https:\/\/.*\.expo\.io$/,
//       /^exp:\/\/.*\.expo\.dev$/,
//       /^exp:\/\/.*\.expo\.io$/
//     ];
    
//     // Check if origin is allowed
//     const isAllowed = allowedOrigins.some(allowedOrigin => {
//       if (typeof allowedOrigin === 'string') {
//         return origin === allowedOrigin;
//       }
//       if (allowedOrigin instanceof RegExp) {
//         return allowedOrigin.test(origin);
//       }
//       return false;
//     });
    
//     if (isAllowed) {
//       callback(null, true);
//     } else {
//       console.log(`🚫 CORS blocked origin: ${origin}`);
//       callback(new Error('Not allowed by CORS'));
//     }
//   },
//   credentials: true,
//   methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
//   allowedHeaders: [
//     'Origin', 
//     'X-Requested-With', 
//     'Content-Type', 
//     'Accept', 
//     'Authorization',
//     'X-API-Key',
//     'User-Agent'
//   ],
//   exposedHeaders: ['Content-Length', 'X-Requested-With'],
//   maxAge: 86400 // 24 hours
// };

// // Apply CORS middleware
// app.use(cors(corsOptions));

// // Additional security headers for mobile apps
// app.use((req, res, next) => {
//   // Allow all origins for mobile apps
//   res.header('Access-Control-Allow-Origin', '*');
//   res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, PATCH');
//   res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization, X-API-Key, User-Agent');
//   res.header('Access-Control-Max-Age', '86400');
  
//   // Handle preflight requests
//   if (req.method === 'OPTIONS') {
//     res.status(200).end();
//     return;
//   }
  
//   next();
// });
// app.use(express.json());
// app.use(express.urlencoded({ extended: true }));

// // Database Connection
// mongoose.connect(process.env.MONGO_URI)
//   .then(() => console.log('Successfully connected to MongoDB.'))
//   .catch(err => {
//     console.error('Database connection error:', err);
//     process.exit(1);
//   });

// // API Routes
// app.get('/', (req, res) => {
//     res.send('ICAI RAG System API is running...');
// });

// app.use('/api/ingestion', ingestionRoutes);
// app.use('/api/chat', chatRoutes);

// // Start Server
// app.listen(PORT, () => {
//   console.log(`Server is running on http://localhost:${PORT} API-SERVER`);
// });

const express = require('express');
const mongoose = require('mongoose');
const dotenv = require('dotenv');
const cors = require('cors');

// Load environment variables
dotenv.config();

// Import routes
const ingestionRoutes = require('./routes/ingestion.routes');
const chatRoutes = require('./routes/chat.routes.js')
const subjectDataRoutes = require('./routes/subjectData.routes.js');
const mcqRoutes = require('./routes/mcq.routes.js');

const app = express();
const PORT = process.env.PORT || 5555;


// Comprehensive CORS configuration for preview builds
const corsOptions = {
  origin: function (origin, callback) {
    // Allow requests with no origin (like mobile apps, Postman, etc.)
    if (!origin) return callback(null, true);
    
    // Allow specific origins
    const allowedOrigins = [
      'http://localhost:3000',
      'http://localhost:19006',
      'exp://localhost:19000',
      'https://expo.dev',
      'https://expo.io',
      'https://expo-development-client.netlify.app',
      // Add your app's bundle identifier
      'com.focas.caguru',
      // Allow all Expo preview builds
      /^https:\/\/.*\.expo\.dev$/,
      /^https:\/\/.*\.expo\.io$/,
      /^exp:\/\/.*\.expo\.dev$/,
      /^exp:\/\/.*\.expo\.io$/
    ];
    
    // Check if origin is allowed
    const isAllowed = allowedOrigins.some(allowedOrigin => {
      if (typeof allowedOrigin === 'string') {
        return origin === allowedOrigin;
      }
      if (allowedOrigin instanceof RegExp) {
        return allowedOrigin.test(origin);
      }
      return false;
    });
    
    if (isAllowed) {
      callback(null, true);
    } else {
      console.log(`🚫 CORS blocked origin: ${origin}`);
      callback(new Error('Not allowed by CORS'));
    }
  },
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
  allowedHeaders: [
    'Origin', 
    'X-Requested-With', 
    'Content-Type', 
    'Accept', 
    'Authorization',
    'X-API-Key',
    'User-Agent'
  ],
  exposedHeaders: ['Content-Length', 'X-Requested-With'],
  maxAge: 86400 // 24 hours
};

// Apply CORS middleware
app.use(cors(corsOptions));

// Additional security headers for mobile apps
app.use((req, res, next) => {
  // Allow all origins for mobile apps
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS, PATCH');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization, X-API-Key, User-Agent');
  res.header('Access-Control-Max-Age', '86400');
  
  // Handle preflight requests
  if (req.method === 'OPTIONS') {
    res.status(200).end();
    return;
  }
  
  next();
});
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Database Connection
mongoose.connect(process.env.MONGO_URI, {
  maxPoolSize: 10,           // Maximum number of connections in the pool
  minPoolSize: 2,            // Minimum number of connections in the pool
  maxIdleTimeMS: 30000,      // Close connections after 30 seconds of inactivity
  serverSelectionTimeoutMS: 5000,  // Timeout for server selection
  socketTimeoutMS: 30000,    // Socket timeout
  connectTimeoutMS: 10000,   // Connection timeout
  bufferCommands: false,     // Disable mongoose buffering
})
  .then(() => console.log('Successfully connected to MongoDB.'))
  .catch(err => {
    console.error('Database connection error:', err);
    process.exit(1);
});
// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n⚠️ SIGINT received. Closing MongoDB connection...');
  await mongoose.connection.close();
  console.log('MongoDB connection closed.');
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\n⚠️ SIGTERM received. Closing MongoDB connection...');
  await mongoose.connection.close();
  console.log('MongoDB connection closed.');
  process.exit(0);
});

// API Routes
app.get('/', (req, res) => {
    res.send('ICAI RAG System API is running...');
});

app.use('/api/ingestion', ingestionRoutes);
app.use('/api/chat', chatRoutes);
app.use('/api/data', subjectDataRoutes);
app.use('/api/mcq', mcqRoutes);

// Start Server
app.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT} API-SERVER`);
  console.log(process.env.MONGO_URI);
});

const mongoose = require('mongoose');
const Schema = mongoose.Schema;

const MessageSchema = new Schema({
  role: {
    type: String,
    enum: ['user', 'assistant'],
    required: true,
  },
  content: {
    type: String,
    required: true,
  },
  sourceChunkIds: [{
    type: Schema.Types.ObjectId,
    ref: 'Icaichunk'
  }],
}, {
  timestamps: true,
});

const ChatSessionSchema = new Schema({
  user: {
    type: Schema.Types.ObjectId,
    ref: 'User',
    required: true,
    index: true,
  },
  sessionTitle: {
    type: String,
    required: true,
    default: 'Untitled Session',
  },
  messages: [MessageSchema],
  isCompleted: {
    type: Boolean,
    default: false,
  },
  chatContext: {
    level: { type: String },
    subject: { type: String }, // Changed from paperName to subject
    paperName: { type: String },
    attemptYear: { type: Number }
  },
  knowledgeBaseId: {
    type: Schema.Types.ObjectId,
    ref: 'IcaiknowledgeBase',
    required: true
  },
}, {
  timestamps: true,
});

module.exports = mongoose.model('ChatSession', ChatSessionSchema);
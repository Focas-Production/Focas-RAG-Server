const mongoose = require('mongoose');
const Schema = mongoose.Schema;
const IcaiknowledgeBaseSchema = new Schema({
  name: { type: String, required: true, unique: true },
  description: { type: String },
  status: { type: String, enum: ['ACTIVE', 'ARCHIVED', 'MAINTENANCE'], default: 'ACTIVE' },
  owner: { type: Schema.Types.ObjectId, ref: 'User', required: true }
}, { timestamps: true });
module.exports = mongoose.model('IcaiknowledgeBase', IcaiknowledgeBaseSchema);
const mongoose = require('mongoose');
const Schema = mongoose.Schema;
const IcaidatasourceSchema = new Schema({
  knowledgeBaseId: { type: Schema.Types.ObjectId, ref: 'IcaiknowledgeBase', required: true },
  level: { type: String, enum: ['Foundation', 'Intermediate', 'Final'], required: true, index: true },
  group: { type: String, enum: ['Group I', 'Group II', 'N/A'], required: true },
  paperNumber: { type: Number, required: true },
  paperName: { type: String, required: true, index: true },
  chapter: { type: String, required: true },
  topic: { type: String },
  documentType: { type: String, enum: ['Study Material', 'RTP', 'MTP', 'Past Paper', 'Amendment', 'Standard', 'Guidance Note'], required: true, index: true },
  attemptYear: { type: Number, required: true, index: true },
  attemptMonth: { type: String, enum: ['May', 'November'], required: true },
  sourceFileName: { type: String, required: true },
  sourceUrl: { type: String },
  rawContent: { type: String, required: true },
  processingStatus: { type: String, enum: ['PENDING', 'PROCESSED', 'FAILED'], default: 'PENDING' }
}, { timestamps: true });
module.exports = mongoose.model('Icaidatasource', IcaidatasourceSchema);
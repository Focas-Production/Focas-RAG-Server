const mongoose = require('mongoose');
const Schema = mongoose.Schema;
const IcaichunkSchema = new Schema({
  knowledgeBaseId: { type: Schema.Types.ObjectId, ref: 'IcaiknowledgeBase', required: true },
  dataSourceId: { type: Schema.Types.ObjectId, ref: 'Icaidatasource', required: true },
  chunkText: { type: String, required: true },
  pageNumber: { type: Number },
  level: { type: String, required: true },
  group: { type: String, required: true },
  paperName: { type: String, required: true },
  chapter: { type: String, required: true },
  topic: { type: String },
  documentType: { type: String, required: true },
  attemptYear: { type: Number, required: true },
  attemptMonth: { type: String, required: true },
  sourceUrl: { type: String },
}, { timestamps: true });
module.exports = mongoose.model('Icaichunk', IcaichunkSchema);
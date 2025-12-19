const Chunk = require("../models/icaiChunk.schema");

// ✅ 1. Get all Levels
exports.getLevels = async (req, res) => {
  try {
    const levels = await Chunk.aggregate([
      { $group: { _id: "$level" } },
      { $sort: { _id: 1 } }
    ]);

    res.json(levels.map(l => l._id));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};


// ✅ 2. Get Subjects by Level
exports.getSubjectsByLevel = async (req, res) => {
  try {
    const { level } = req.query;

    const subjects = await Chunk.aggregate([
      { $match: { level } },
      { $group: { _id: "$subject" } },
      { $sort: { _id: 1 } }
    ]);

    res.json(subjects.map(s => s._id));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};


// ✅ 3. Get Chapters by Level + Subject
exports.getChaptersByLevelAndSubject = async (req, res) => {
  try {
    const { level, subject } = req.query;

    const chapters = await Chunk.aggregate([
      { $match: { level, subject } },
      { $group: { _id: "$chapter_name" } },
      { $sort: { _id: 1 } }
    ]);

    res.json(chapters.map(c => c._id));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};


// ✅ 4. Get Units by Chapter Name
exports.getUnitsByChapter = async (req, res) => {
  try {
    const { chapter_name } = req.query;

    const units = await Chunk.aggregate([
      { $match: { chapter_name } },
      {
        $group: {
          _id: "$unit_number",
          unit_name: { $first: "$unit_name" }
        }
      },
      { $sort: { _id: 1 } }
    ]);

    res.json(units);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

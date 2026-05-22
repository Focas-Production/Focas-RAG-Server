const Chunk = require("../models/icaiChunk.schema");

// ✅ 1. Get all Levels
exports.getLevels = async (req, res) => {
  try {
    const levels = await Chunk.aggregate([
      { $match: { level: { $exists: true, $ne: null, $ne: "" } } },
      { $group: { _id: { $trim: { input: "$level" } } } },
      { $match: { _id: { $ne: "" } } },
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
    if (!level) return res.status(400).json({ error: "level is required" });

    const subjects = await Chunk.aggregate([
      { $match: { level } },
      { $group: { _id: { $trim: { input: { $ifNull: ["$subject", ""] } } } } },
      { $match: { _id: { $ne: "" } } },
      { $sort: { _id: 1 } }
    ]);

    res.json(subjects.map(s => s._id));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};


// ✅ 3. Get Chapters by Level + Subject  (deduplicates via $trim)
exports.getChaptersByLevelAndSubject = async (req, res) => {
  try {
    const { level, subject } = req.query;
    if (!level || !subject) {
      return res.status(400).json({ error: "level and subject are required" });
    }

    const chapters = await Chunk.aggregate([
      { $match: { level, subject } },
      // Trim whitespace so "Chapter A " and "Chapter A" collapse to one entry
      {
        $group: {
          _id: { $trim: { input: { $ifNull: ["$chapter_name", ""] } } },
          chapter_number: { $first: "$chapter_number" }
        }
      },
      { $match: { _id: { $ne: "" } } },
      { $sort: { chapter_number: 1, _id: 1 } }
    ]);

    res.json(chapters.map(c => c._id));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};


// ✅ 4. Get Units by Level + Subject + Chapter Name  (deduplicates + returns structured list)
exports.getUnitsByChapter = async (req, res) => {
  try {
    const { level, subject, chapter_name } = req.query;

    if (!level || !subject || !chapter_name) {
      return res.status(400).json({ error: "level, subject, and chapter_name are required" });
    }

    const units = await Chunk.aggregate([
      { $match: { level, subject, chapter_name } },
      {
        $group: {
          _id: "$unit_number",
          unit_name: { $first: { $trim: { input: { $ifNull: ["$unit_name", ""] } } } }
        }
      },
      { $match: { _id: { $ne: null }, unit_name: { $ne: "" } } },
      { $sort: { _id: 1 } },
      {
        $project: {
          _id: 0,
          unit_number: "$_id",
          unit_name: 1
        }
      }
    ]);

    res.json(units);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};


// ✅ 5. MCQ Capabilities — tells the frontend what options are available
exports.getMCQCapabilities = async (req, res) => {
  res.json({
    question_types: [
      { value: "standard",       label: "General MCQ" },
      { value: "case_scenario",  label: "Case Study Based MCQ" }
    ],
    difficulties: [
      { value: "easy",      label: "Easy" },
      { value: "medium",    label: "Medium" },
      { value: "hard",      label: "Hard" },
      { value: "very-hard", label: "Very Hard" }
    ],
    unit_selection_available: true,
    max_questions: { standard: 10, case_scenario: 6 }
  });
};

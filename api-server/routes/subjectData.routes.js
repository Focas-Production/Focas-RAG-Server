const express = require("express");
const router = express.Router();
const {
  getLevels,
  getSubjectsByLevel,
  getChaptersByLevelAndSubject,
  getUnitsByChapter,
  getMCQCapabilities,
} = require("../controllers/subjectDataController.js");

// Get all levels
router.get("/levels", getLevels);

// Get subjects by level
router.get("/subjects", getSubjectsByLevel);

// Get chapters by level + subject
router.get("/chapters", getChaptersByLevelAndSubject);

// Get units by level + subject + chapter_name
router.get("/units", getUnitsByChapter);

// MCQ capabilities (question types, difficulties, limits)
router.get("/capabilities", getMCQCapabilities);

module.exports = router;

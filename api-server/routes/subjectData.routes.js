const express = require("express");
const router = express.Router();
const {
  getLevels,
  getSubjectsByLevel,
  getChaptersByLevelAndSubject,
  getUnitsByChapter
} = require("../controllers/subjectDataController.js");

// Get all levels
router.get("/levels", getLevels);

// Get subjects by level
router.get("/subjects", getSubjectsByLevel);

// Get chapters by level + subject
router.get("/chapters", getChaptersByLevelAndSubject);

// Get units by chapter name
router.get("/units", getUnitsByChapter);

module.exports = router;

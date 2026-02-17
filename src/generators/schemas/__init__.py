"""Pydantic schemas for structured content generation.

This package contains schema definitions for all 12 content types:
- VideoScriptSchema: WWHAA-structured video scripts
- ReadingSchema: Educational readings with sections and references
- QuizSchema: Multiple-choice quizzes with Bloom's taxonomy levels
- RubricSchema: 3-level scoring rubrics (Below/Meets/Exceeds Expectations)
- HOLSchema: Hands-on labs with 3-part structure and skill-based rubrics
- CoachSchema: Coach dialogues with 8-section conversational learning
- PracticeQuizSchema: Formative quizzes with hints (separate from graded QuizSchema)
- LabSchema: Labs with setup instructions and exercises
- DiscussionSchema: Discussion prompts with facilitation questions
- AssignmentSchema: Assignments with deliverables and grading criteria
- ProjectMilestoneSchema: Project milestones with A1/A2/A3 staging
- ScreencastSchema: Terminal screencast simulations (executable Python code)

All schemas are used with Claude's structured outputs API via BaseGenerator.
"""

from src.generators.schemas.video_script import VideoScriptSchema, VideoScriptSection
from src.generators.schemas.reading import ReadingSchema, ReadingSection, Reference
from src.generators.schemas.quiz import QuizSchema, QuizQuestion, QuizOption
from src.generators.schemas.rubric import RubricSchema, RubricCriterion
from src.generators.schemas.hol import HOLSchema, HOLPart, HOLRubricCriterion
from src.generators.schemas.coach import CoachSchema, ConversationStarter, SampleResponse
from src.generators.schemas.practice_quiz import PracticeQuizSchema, PracticeQuizQuestion, PracticeQuizOption
from src.generators.schemas.lab import LabSchema, SetupStep
from src.generators.schemas.discussion import DiscussionSchema
from src.generators.schemas.assignment import AssignmentSchema, AssignmentDeliverable, ChecklistItem
from src.generators.schemas.project import ProjectMilestoneSchema, MilestoneDeliverable
from src.generators.schemas.screencast import (
    ScreencastSchema, ScreencastScreen, ScreencastCommand,
    NarrationCue, ProgressBarDemo
)

__all__ = [
    # Video script
    "VideoScriptSchema",
    "VideoScriptSection",
    # Reading
    "ReadingSchema",
    "ReadingSection",
    "Reference",
    # Quiz
    "QuizSchema",
    "QuizQuestion",
    "QuizOption",
    # Rubric
    "RubricSchema",
    "RubricCriterion",
    # HOL
    "HOLSchema",
    "HOLPart",
    "HOLRubricCriterion",
    # Coach
    "CoachSchema",
    "ConversationStarter",
    "SampleResponse",
    # Practice Quiz
    "PracticeQuizSchema",
    "PracticeQuizQuestion",
    "PracticeQuizOption",
    # Lab
    "LabSchema",
    "SetupStep",
    # Discussion
    "DiscussionSchema",
    # Assignment
    "AssignmentSchema",
    "AssignmentDeliverable",
    "ChecklistItem",
    # Project
    "ProjectMilestoneSchema",
    "MilestoneDeliverable",
    # Screencast
    "ScreencastSchema",
    "ScreencastScreen",
    "ScreencastCommand",
    "NarrationCue",
    "ProgressBarDemo",
]

"""Convert AI-generated blueprints to Course dataclasses.

This module bridges Pydantic blueprint schemas with the existing Course/Module/Lesson/Activity
dataclasses from Phase 1, enabling seamless integration with ProjectStore.
"""

import uuid
from typing import Optional

from src.generators.blueprint_generator import (
    CourseBlueprint,
    ModuleBlueprint,
    LessonBlueprint,
    ActivityBlueprint
)
from src.core.models import (
    Course,
    Module,
    Lesson,
    Activity,
    ContentType,
    ActivityType,
    WWHAAPhase,
    BloomLevel,
    BuildState
)


def blueprint_to_course(
    blueprint: CourseBlueprint,
    course: Course
) -> Course:
    """Apply blueprint structure to an existing Course, replacing its modules.

    Converts Pydantic blueprint models to Course/Module/Lesson/Activity dataclasses.
    Preserves the course's existing ID, title, description, and other metadata.
    Replaces modules list entirely with the blueprint's structure.

    Args:
        blueprint: AI-generated CourseBlueprint (Pydantic model)
        course: Existing Course object to apply structure to

    Returns:
        The modified Course with new modules/lessons/activities
    """
    # Clear existing modules and create new ones from blueprint
    course.modules = []

    # Update target duration from blueprint
    course.target_duration_minutes = int(round(blueprint.total_duration_minutes))

    # Convert each module
    for module_order, module_bp in enumerate(blueprint.modules):
        module = _convert_module(module_bp, module_order)
        course.modules.append(module)

    return course


def _convert_module(module_bp: ModuleBlueprint, order: int) -> Module:
    """Convert ModuleBlueprint to Module dataclass."""
    module = Module(
        id=f"mod_{uuid.uuid4().hex[:8]}",
        title=module_bp.title,
        description=module_bp.description,
        order=order,
        lessons=[]
    )

    # Convert each lesson
    for lesson_order, lesson_bp in enumerate(module_bp.lessons):
        lesson = _convert_lesson(lesson_bp, lesson_order)
        module.lessons.append(lesson)

    return module


def _convert_lesson(lesson_bp: LessonBlueprint, order: int) -> Lesson:
    """Convert LessonBlueprint to Lesson dataclass."""
    lesson = Lesson(
        id=f"les_{uuid.uuid4().hex[:8]}",
        title=lesson_bp.title,
        description=lesson_bp.description,
        order=order,
        activities=[]
    )

    # Convert each activity
    for activity_order, activity_bp in enumerate(lesson_bp.activities):
        activity = _convert_activity(activity_bp, activity_order)
        lesson.activities.append(activity)

    return lesson


def _convert_activity(activity_bp: ActivityBlueprint, order: int) -> Activity:
    """Convert ActivityBlueprint to Activity dataclass."""
    activity = Activity(
        id=f"act_{uuid.uuid4().hex[:8]}",
        title=activity_bp.title,
        content_type=_map_content_type(activity_bp.content_type),
        activity_type=_map_activity_type(activity_bp.activity_type),
        wwhaa_phase=_map_wwhaa_phase(activity_bp.wwhaa_phase),
        bloom_level=_map_bloom_level(activity_bp.bloom_level),
        estimated_duration_minutes=activity_bp.estimated_duration_minutes,
        build_state=BuildState.DRAFT,  # All new activities start as draft
        order=order,
        content=""  # Content will be generated later
    )

    return activity


def _map_content_type(type_str: str) -> ContentType:
    """Map blueprint content type string to ContentType enum with fallback."""
    try:
        return ContentType(type_str)
    except ValueError:
        # Fallback to VIDEO for unknown types
        return ContentType.VIDEO


def _map_activity_type(type_str: str) -> ActivityType:
    """Map blueprint activity type string to ActivityType enum with fallback."""
    try:
        return ActivityType(type_str)
    except ValueError:
        # Fallback to VIDEO_LECTURE for unknown types
        return ActivityType.VIDEO_LECTURE


def _map_bloom_level(level_str: str) -> BloomLevel:
    """Map blueprint Bloom level string to BloomLevel enum with fallback."""
    try:
        return BloomLevel(level_str)
    except ValueError:
        # Fallback to APPLY for unknown levels
        return BloomLevel.APPLY


def _map_wwhaa_phase(phase_str: Optional[str]) -> WWHAAPhase:
    """Map blueprint WWHAA phase string to WWHAAPhase enum with fallback."""
    if phase_str is None:
        return WWHAAPhase.CONTENT

    try:
        return WWHAAPhase(phase_str)
    except ValueError:
        # Fallback to CONTENT for unknown phases
        return WWHAAPhase.CONTENT

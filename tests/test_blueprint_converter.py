"""Tests for blueprint-to-course converter."""

from src.generators.blueprint_converter import blueprint_to_course
from src.generators.blueprint_generator import (
    CourseBlueprint,
    ModuleBlueprint,
    LessonBlueprint,
    ActivityBlueprint
)
from src.core.models import (
    Course,
    ContentType,
    ActivityType,
    WWHAAPhase,
    BloomLevel,
    BuildState
)


def create_test_blueprint():
    """Create a test blueprint with 2 modules."""
    return CourseBlueprint(
        modules=[
            ModuleBlueprint(
                title="Module 1",
                description="First module",
                lessons=[
                    LessonBlueprint(
                        title="Lesson 1.1",
                        description="First lesson",
                        activities=[
                            ActivityBlueprint(
                                title="Video Introduction",
                                content_type="video",
                                activity_type="video_lecture",
                                wwhaa_phase="hook",
                                bloom_level="remember",
                                estimated_duration_minutes=5.0,
                                description="Intro video"
                            ),
                            ActivityBlueprint(
                                title="Reading Material",
                                content_type="reading",
                                activity_type="reading_material",
                                wwhaa_phase=None,
                                bloom_level="understand",
                                estimated_duration_minutes=10.0,
                                description="Reading"
                            )
                        ]
                    ),
                    LessonBlueprint(
                        title="Lesson 1.2",
                        description="Second lesson",
                        activities=[
                            ActivityBlueprint(
                                title="Practice Quiz",
                                content_type="quiz",
                                activity_type="practice_quiz",
                                bloom_level="apply",
                                estimated_duration_minutes=5.0,
                                description="Quiz"
                            ),
                            ActivityBlueprint(
                                title="Hands-on Lab",
                                content_type="lab",
                                activity_type="hands_on_lab",
                                bloom_level="analyze",
                                estimated_duration_minutes=20.0,
                                description="Lab exercise"
                            )
                        ]
                    ),
                    LessonBlueprint(
                        title="Lesson 1.3",
                        description="Third lesson",
                        activities=[
                            ActivityBlueprint(
                                title="Discussion",
                                content_type="discussion",
                                activity_type="discussion_prompt",
                                bloom_level="evaluate",
                                estimated_duration_minutes=10.0,
                                description="Discussion prompt"
                            ),
                            ActivityBlueprint(
                                title="Assignment",
                                content_type="assignment",
                                activity_type="assignment_submission",
                                bloom_level="create",
                                estimated_duration_minutes=30.0,
                                description="Final assignment"
                            )
                        ]
                    )
                ]
            ),
            ModuleBlueprint(
                title="Module 2",
                description="Second module",
                lessons=[
                    LessonBlueprint(
                        title="Lesson 2.1",
                        description="Fourth lesson",
                        activities=[
                            ActivityBlueprint(
                                title="Advanced Video",
                                content_type="video",
                                activity_type="video_lecture",
                                wwhaa_phase="content",
                                bloom_level="apply",
                                estimated_duration_minutes=8.0,
                                description="Advanced concepts"
                            ),
                            ActivityBlueprint(
                                title="Graded Quiz",
                                content_type="quiz",
                                activity_type="graded_quiz",
                                bloom_level="analyze",
                                estimated_duration_minutes=10.0,
                                description="Graded assessment"
                            )
                        ]
                    ),
                    LessonBlueprint(
                        title="Lesson 2.2",
                        description="Fifth lesson",
                        activities=[
                            ActivityBlueprint(
                                title="Project",
                                content_type="project",
                                activity_type="project_milestone",
                                bloom_level="create",
                                estimated_duration_minutes=40.0,
                                description="Final project"
                            ),
                            ActivityBlueprint(
                                title="Summary Video",
                                content_type="video",
                                activity_type="video_lecture",
                                wwhaa_phase="summary",
                                bloom_level="understand",
                                estimated_duration_minutes=5.0,
                                description="Course summary"
                            )
                        ]
                    ),
                    LessonBlueprint(
                        title="Lesson 2.3",
                        description="Sixth lesson",
                        activities=[
                            ActivityBlueprint(
                                title="Final Reading",
                                content_type="reading",
                                activity_type="reading_material",
                                bloom_level="remember",
                                estimated_duration_minutes=12.0,
                                description="Additional resources"
                            ),
                            ActivityBlueprint(
                                title="Course Feedback",
                                content_type="discussion",
                                activity_type="discussion_prompt",
                                bloom_level="evaluate",
                                estimated_duration_minutes=8.0,
                                description="Share feedback"
                            )
                        ]
                    )
                ]
            )
        ],
        total_duration_minutes=153.0,
        rationale="Comprehensive course with balanced content types and Bloom progression"
    )


def test_blueprint_to_course_creates_modules():
    """2-module blueprint should create 2 Module objects."""
    blueprint = create_test_blueprint()
    course = Course(title="Test Course", description="Test description")

    result = blueprint_to_course(blueprint, course)

    assert len(result.modules) == 2
    assert result.modules[0].title == "Module 1"
    assert result.modules[1].title == "Module 2"
    assert result.modules[0].order == 0
    assert result.modules[1].order == 1


def test_blueprint_to_course_creates_lessons():
    """Each module's lessons should be created with correct order."""
    blueprint = create_test_blueprint()
    course = Course(title="Test Course", description="Test description")

    result = blueprint_to_course(blueprint, course)

    # Module 1 should have 3 lessons
    assert len(result.modules[0].lessons) == 3
    assert result.modules[0].lessons[0].title == "Lesson 1.1"
    assert result.modules[0].lessons[1].title == "Lesson 1.2"
    assert result.modules[0].lessons[2].title == "Lesson 1.3"
    assert result.modules[0].lessons[0].order == 0
    assert result.modules[0].lessons[1].order == 1
    assert result.modules[0].lessons[2].order == 2

    # Module 2 should have 3 lessons
    assert len(result.modules[1].lessons) == 3
    assert result.modules[1].lessons[0].title == "Lesson 2.1"


def test_blueprint_to_course_creates_activities():
    """Activities should have correct content_type, activity_type, bloom_level enums."""
    blueprint = create_test_blueprint()
    course = Course(title="Test Course", description="Test description")

    result = blueprint_to_course(blueprint, course)

    # Check first activity (video)
    first_activity = result.modules[0].lessons[0].activities[0]
    assert first_activity.title == "Video Introduction"
    assert first_activity.content_type == ContentType.VIDEO
    assert first_activity.activity_type == ActivityType.VIDEO_LECTURE
    assert first_activity.bloom_level == BloomLevel.REMEMBER
    assert first_activity.estimated_duration_minutes == 5.0

    # Check second activity (reading)
    second_activity = result.modules[0].lessons[0].activities[1]
    assert second_activity.content_type == ContentType.READING
    assert second_activity.activity_type == ActivityType.READING_MATERIAL
    assert second_activity.bloom_level == BloomLevel.UNDERSTAND

    # Check quiz activity
    quiz_activity = result.modules[0].lessons[1].activities[0]
    assert quiz_activity.content_type == ContentType.QUIZ
    assert quiz_activity.activity_type == ActivityType.PRACTICE_QUIZ
    assert quiz_activity.bloom_level == BloomLevel.APPLY

    # Check lab activity
    lab_activity = result.modules[0].lessons[1].activities[1]
    assert lab_activity.content_type == ContentType.LAB
    assert lab_activity.activity_type == ActivityType.HANDS_ON_LAB
    assert lab_activity.bloom_level == BloomLevel.ANALYZE


def test_blueprint_to_course_maps_wwhaa_phase():
    """Video activities should get WWHAAPhase from blueprint, non-video get default."""
    blueprint = create_test_blueprint()
    course = Course(title="Test Course", description="Test description")

    result = blueprint_to_course(blueprint, course)

    # Video with hook phase
    first_video = result.modules[0].lessons[0].activities[0]
    assert first_video.content_type == ContentType.VIDEO
    assert first_video.wwhaa_phase == WWHAAPhase.HOOK

    # Reading with None should get CONTENT default
    reading = result.modules[0].lessons[0].activities[1]
    assert reading.content_type == ContentType.READING
    assert reading.wwhaa_phase == WWHAAPhase.CONTENT

    # Video with content phase
    second_video = result.modules[1].lessons[0].activities[0]
    assert second_video.wwhaa_phase == WWHAAPhase.CONTENT

    # Video with summary phase
    third_video = result.modules[1].lessons[1].activities[1]
    assert third_video.wwhaa_phase == WWHAAPhase.SUMMARY


def test_blueprint_to_course_preserves_course_metadata():
    """Course ID, title, description should be unchanged after conversion."""
    blueprint = create_test_blueprint()
    course = Course(
        id="course_test123",
        title="Original Title",
        description="Original Description",
        audience_level="advanced",
        prerequisites="Python basics"
    )

    result = blueprint_to_course(blueprint, course)

    assert result.id == "course_test123"
    assert result.title == "Original Title"
    assert result.description == "Original Description"
    assert result.audience_level == "advanced"
    assert result.prerequisites == "Python basics"


def test_blueprint_to_course_updates_duration():
    """Course target_duration_minutes should be updated from blueprint total."""
    blueprint = create_test_blueprint()
    course = Course(title="Test Course", target_duration_minutes=60)

    result = blueprint_to_course(blueprint, course)

    assert result.target_duration_minutes == 153  # Rounded from 153.0


def test_blueprint_to_course_all_activities_draft():
    """All activities should have BuildState.DRAFT."""
    blueprint = create_test_blueprint()
    course = Course(title="Test Course", description="Test description")

    result = blueprint_to_course(blueprint, course)

    # Check all activities in all lessons in all modules
    for module in result.modules:
        for lesson in module.lessons:
            for activity in lesson.activities:
                assert activity.build_state == BuildState.DRAFT


def test_blueprint_to_course_generates_unique_ids():
    """All module, lesson, activity IDs should be unique."""
    blueprint = create_test_blueprint()
    course = Course(title="Test Course", description="Test description")

    result = blueprint_to_course(blueprint, course)

    # Collect all IDs
    module_ids = [m.id for m in result.modules]
    lesson_ids = [l.id for m in result.modules for l in m.lessons]
    activity_ids = [a.id for m in result.modules for l in m.lessons for a in l.activities]

    # Check uniqueness
    assert len(module_ids) == len(set(module_ids))
    assert len(lesson_ids) == len(set(lesson_ids))
    assert len(activity_ids) == len(set(activity_ids))

    # Check ID prefixes
    assert all(mid.startswith("mod_") for mid in module_ids)
    assert all(lid.startswith("les_") for lid in lesson_ids)
    assert all(aid.startswith("act_") for aid in activity_ids)

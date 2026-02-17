"""Image generation API endpoints.

Provides REST endpoints for:
- Video slide generation from scripts
- Reading image generation from content
- Terminal screenshot generation for HOL
- CTA slide generation for videos
"""

from flask import Blueprint, request, jsonify, Response
from flask_login import login_required, current_user
import base64
from typing import Optional

from src.core.project_store import ProjectStore
from src.core.models import ContentType
from src.collab.models import Collaborator

# Import generators with graceful fallback
try:
    from src.utils.video_slide_generator import (
        VideoSlideGenerator, SlideSet, generate_video_slides
    )
    from src.utils.reading_image_generator import (
        ReadingImageGenerator, extract_image_concepts, generate_reading_images
    )
    from src.utils.terminal_image_generator import (
        TerminalImageGenerator, TerminalLine, generate_terminal_image
    )
    from src.utils.cta_slide_generator import (
        CTASlideGenerator, CTASlideContent, generate_cta_slide
    )
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


def init_images_bp(project_store: ProjectStore) -> Blueprint:
    """Initialize images blueprint with project store dependency."""

    bp = Blueprint("images", __name__, url_prefix="/api")

    def check_pillow():
        """Check if Pillow is available."""
        if not PILLOW_AVAILABLE:
            return jsonify({
                "error": "Pillow not installed",
                "message": "Image generation requires Pillow. Install with: pip install Pillow"
            }), 503
        return None

    @bp.route("/images/status", methods=["GET"])
    def get_status():
        """Check image generation availability."""
        return jsonify({
            "pillow_available": PILLOW_AVAILABLE,
            "generators": {
                "video_slides": PILLOW_AVAILABLE,
                "reading_images": PILLOW_AVAILABLE,
                "terminal_screenshots": PILLOW_AVAILABLE,
                "cta_slides": PILLOW_AVAILABLE
            }
        })

    # -------------------------------------------------------------------------
    # Video Slide Generation
    # -------------------------------------------------------------------------

    def _load_course(course_id: str):
        """Load course using owner lookup pattern."""
        owner_id = Collaborator.get_course_owner_id(course_id)
        if not owner_id:
            return None
        return project_store.load(owner_id, course_id)

    def _find_activity(course, activity_id: str):
        """Find activity in course hierarchy."""
        for module in course.modules:
            for lesson in module.lessons:
                for activity in lesson.activities:
                    if activity.id == activity_id:
                        return module, lesson, activity
        return None, None, None

    @bp.route("/courses/<course_id>/activities/<activity_id>/slides", methods=["POST"])
    @login_required
    def generate_activity_slides(course_id: str, activity_id: str):
        """Generate presentation slides from video script.

        Returns slides as base64-encoded PNG images.

        Request body (optional):
            {
                "format": "base64" | "binary",  # default: base64
                "include_metadata": true | false  # default: true
            }
        """
        error = check_pillow()
        if error:
            return error

        course = _load_course(course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        _, _, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        if activity.content_type != ContentType.VIDEO:
            return jsonify({
                "error": "Invalid content type",
                "message": "Slides can only be generated for video content"
            }), 400

        if not activity.generated_content:
            return jsonify({
                "error": "No content",
                "message": "Generate video content first before creating slides"
            }), 400

        data = request.get_json() or {}
        output_format = data.get("format", "base64")
        include_metadata = data.get("include_metadata", True)

        try:
            generator = VideoSlideGenerator()
            slide_set = generator.parse_script(activity.generated_content)

            slides = []
            for i, slide in enumerate(slide_set.slides):
                image = generator.generate_slide_image(slide)
                image_bytes = generator.to_bytes(image)

                slide_data = {
                    "index": i,
                    "type": slide.slide_type.value,
                    "title": slide.title
                }

                if output_format == "base64":
                    slide_data["image"] = base64.b64encode(image_bytes).decode("utf-8")
                    slide_data["format"] = "png"

                if include_metadata:
                    slide_data["subtitle"] = slide.subtitle
                    slide_data["content"] = slide.content
                    slide_data["speaker_notes"] = slide.speaker_notes
                    slide_data["visual_cue"] = slide.visual_cue

                slides.append(slide_data)

            return jsonify({
                "video_title": slide_set.video_title,
                "slide_count": len(slides),
                "slides": slides
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route("/courses/<course_id>/activities/<activity_id>/slides/<int:slide_index>", methods=["GET"])
    @login_required
    def get_slide_image(course_id: str, activity_id: str, slide_index: int):
        """Get a single slide image as binary PNG."""
        error = check_pillow()
        if error:
            return error

        course = _load_course(course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        _, _, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        if activity.content_type != ContentType.VIDEO:
            return jsonify({"error": "Invalid content type"}), 400

        if not activity.generated_content:
            return jsonify({"error": "No content"}), 400

        try:
            generator = VideoSlideGenerator()
            slide_set = generator.parse_script(activity.generated_content)

            if slide_index < 0 or slide_index >= len(slide_set.slides):
                return jsonify({"error": "Slide index out of range"}), 404

            slide = slide_set.slides[slide_index]
            image = generator.generate_slide_image(slide)
            image_bytes = generator.to_bytes(image)

            return Response(
                image_bytes,
                mimetype="image/png",
                headers={
                    "Content-Disposition": f"inline; filename=slide_{slide_index}.png"
                }
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # -------------------------------------------------------------------------
    # Reading Image Generation
    # -------------------------------------------------------------------------

    @bp.route("/courses/<course_id>/activities/<activity_id>/images", methods=["POST"])
    @login_required
    def generate_activity_images(course_id: str, activity_id: str):
        """Generate concept images for reading content.

        Request body:
            {
                "count": 1-5,  # number of images to generate (default: 3)
                "format": "base64" | "concepts_only",  # default: base64
                "include_prompts": true | false  # include AI prompts (default: true)
            }
        """
        error = check_pillow()
        if error:
            return error

        course = _load_course(course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        _, _, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        # Allow reading and other text-based content types
        text_types = {ContentType.READING, ContentType.DISCUSSION, ContentType.ASSIGNMENT}
        if activity.content_type not in text_types:
            return jsonify({
                "error": "Invalid content type",
                "message": "Images can only be generated for text-based content (reading, discussion, assignment)"
            }), 400

        if not activity.generated_content:
            return jsonify({
                "error": "No content",
                "message": "Generate content first before creating images"
            }), 400

        data = request.get_json() or {}
        count = max(1, min(5, data.get("count", 3)))
        output_format = data.get("format", "base64")
        include_prompts = data.get("include_prompts", True)

        try:
            generator = ReadingImageGenerator()

            # Extract concepts first
            concepts = generator.extract_concepts(activity.generated_content, count)

            if output_format == "concepts_only":
                # Return just the concepts without generating images
                return jsonify({
                    "count": len(concepts),
                    "concepts": [
                        {
                            "title": c.title,
                            "description": c.description,
                            "image_type": c.image_type.value,
                            "keywords": c.keywords,
                            "prompt": c.to_prompt() if include_prompts else None
                        }
                        for c in concepts
                    ]
                })

            # Generate images
            images = generator.generate_images(activity.generated_content, count)

            result_images = []
            for i, img in enumerate(images):
                image_data = {
                    "index": i,
                    "title": img.concept.title,
                    "description": img.concept.description,
                    "image_type": img.concept.image_type.value,
                    "keywords": img.concept.keywords,
                    "image": base64.b64encode(img.image_bytes).decode("utf-8"),
                    "format": "png",
                    "width": img.width,
                    "height": img.height
                }

                if include_prompts:
                    image_data["prompt"] = img.concept.to_prompt()

                result_images.append(image_data)

            return jsonify({
                "count": len(result_images),
                "images": result_images
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route("/images/reading/concepts", methods=["POST"])
    def extract_reading_concepts():
        """Extract image concepts from arbitrary text.

        Request body:
            {
                "content": "text content...",
                "count": 1-5  # default: 3
            }

        Returns concepts with AI generation prompts.
        """
        data = request.get_json()
        if not data or "content" not in data:
            return jsonify({"error": "content is required"}), 400

        content = data["content"]
        count = max(1, min(5, data.get("count", 3)))

        try:
            concepts = extract_image_concepts(content, count)
            return jsonify({
                "count": len(concepts),
                "concepts": concepts
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # -------------------------------------------------------------------------
    # Terminal Screenshot Generation
    # -------------------------------------------------------------------------

    @bp.route("/images/terminal", methods=["POST"])
    def generate_terminal_screenshot():
        """Generate a terminal screenshot image.

        Request body:
            {
                "command": "ls -la",
                "output": "file1.txt\nfile2.txt" | ["file1.txt", "file2.txt"],
                "format": "base64" | "binary"  # default: base64
            }

        Or for complex multi-line:
            {
                "lines": [
                    {"text": "$ pip install flask", "type": "prompt"},
                    {"text": "Successfully installed", "type": "success"},
                    {"text": "$ flask --version", "type": "prompt"},
                    {"text": "Flask 2.3.0", "type": "output"}
                ],
                "format": "base64"
            }
        """
        error = check_pillow()
        if error:
            return error

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400

        output_format = data.get("format", "base64")

        # Check required fields before creating generator
        if "command" not in data and "lines" not in data:
            return jsonify({
                "error": "Either 'command' or 'lines' is required"
            }), 400

        try:
            generator = TerminalImageGenerator()

            if "lines" in data:
                # Complex multi-line format
                lines = []
                for line_data in data["lines"]:
                    text = line_data.get("text", "")
                    line_type = line_data.get("type", "output")

                    if line_type == "prompt":
                        # Extract command from "$ command" format
                        cmd = text.lstrip("$ ").strip()
                        lines.append(TerminalLine.prompt(cmd))
                    elif line_type == "error":
                        lines.append(TerminalLine.error(text))
                    elif line_type == "success":
                        lines.append(TerminalLine.success(text))
                    elif line_type == "comment":
                        lines.append(TerminalLine.comment(text.lstrip("# ")))
                    else:
                        lines.append(TerminalLine.output(text))

                image = generator.generate(lines)

            else:
                # Simple command/output format
                command = data["command"]
                output = data.get("output", "")
                image = generator.generate_simple(command, output)

            image_bytes = generator.to_bytes(image)

            if output_format == "binary":
                return Response(
                    image_bytes,
                    mimetype="image/png",
                    headers={"Content-Disposition": "inline; filename=terminal.png"}
                )

            return jsonify({
                "image": base64.b64encode(image_bytes).decode("utf-8"),
                "format": "png",
                "width": image.width,
                "height": image.height
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # -------------------------------------------------------------------------
    # CTA Slide Generation
    # -------------------------------------------------------------------------

    @bp.route("/courses/<course_id>/activities/<activity_id>/cta-slide", methods=["POST"])
    @login_required
    def generate_activity_cta_slide(course_id: str, activity_id: str):
        """Generate a CTA slide for a video activity.

        Request body (optional overrides):
            {
                "course_label": "Module 1, Lesson 2",
                "tagline": "Ready to practice?",
                "footer": "Continue on Coursera",
                "format": "base64" | "binary"
            }
        """
        error = check_pillow()
        if error:
            return error

        course = _load_course(course_id)
        if not course:
            return jsonify({"error": "Course not found"}), 404

        module, lesson, activity = _find_activity(course, activity_id)
        if not activity:
            return jsonify({"error": "Activity not found"}), 404

        if activity.content_type != ContentType.VIDEO:
            return jsonify({
                "error": "Invalid content type",
                "message": "CTA slides are for video content"
            }), 400

        data = request.get_json() or {}
        output_format = data.get("format", "base64")

        # Build course label from hierarchy
        default_label = ""
        if module and lesson:
            module_index = course.modules.index(module) + 1
            lesson_index = module.lessons.index(lesson) + 1
            default_label = f"Module {module_index}, Lesson {lesson_index}"

        try:
            content = CTASlideContent(
                video_title=activity.title,
                course_label=data.get("course_label", default_label),
                tagline=data.get("tagline"),
                footer=data.get("footer", f"Continue learning: {course.title}")
            )

            generator = CTASlideGenerator()
            image = generator.generate(content)
            image_bytes = generator.to_bytes(image)

            if output_format == "binary":
                return Response(
                    image_bytes,
                    mimetype="image/png",
                    headers={"Content-Disposition": "inline; filename=cta_slide.png"}
                )

            return jsonify({
                "video_title": activity.title,
                "course_label": content.course_label,
                "image": base64.b64encode(image_bytes).decode("utf-8"),
                "format": "png",
                "width": 1280,
                "height": 720
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @bp.route("/images/cta", methods=["POST"])
    def generate_cta_slide_standalone():
        """Generate a standalone CTA slide.

        Request body:
            {
                "video_title": "Building REST APIs",
                "course_label": "Module 1",  # optional
                "tagline": "Ready to code?",  # optional
                "footer": "Continue on Coursera",  # optional
                "format": "base64" | "binary"
            }
        """
        error = check_pillow()
        if error:
            return error

        data = request.get_json()
        if not data or "video_title" not in data:
            return jsonify({"error": "video_title is required"}), 400

        output_format = data.get("format", "base64")

        try:
            image_bytes = generate_cta_slide(
                video_title=data["video_title"],
                course_label=data.get("course_label"),
                tagline=data.get("tagline"),
                footer=data.get("footer")
            )

            if output_format == "binary":
                return Response(
                    image_bytes,
                    mimetype="image/png",
                    headers={"Content-Disposition": "inline; filename=cta_slide.png"}
                )

            return jsonify({
                "video_title": data["video_title"],
                "image": base64.b64encode(image_bytes).decode("utf-8"),
                "format": "png",
                "width": 1280,
                "height": 720
            })

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return bp

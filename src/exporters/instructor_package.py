"""Instructor Package ZIP Exporter.

Creates ZIP bundles containing syllabus, lesson plans, rubrics,
quizzes with answer keys, and textbook for instructor use.
"""

import json
import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from src.core.models import Course, Module, Lesson, Activity, ContentType
from src.exporters.base_exporter import BaseExporter


class InstructorPackageExporter(BaseExporter):
    """Exporter for creating instructor package ZIP files.

    Generates a ZIP archive containing:
    - syllabus.txt: Course overview with module/lesson list
    - lesson_plans/: Per-lesson files with activities and timing
    - rubrics/: Rubric criteria for RUBRIC activities
    - quizzes/: Quiz questions only (student version)
    - answer_keys/: Quiz answers with explanations (instructor only)
    - textbook.docx: Combined textbook if chapters exist
    """

    @property
    def format_name(self) -> str:
        """Human-readable name of the export format."""
        return "Instructor Package"

    @property
    def file_extension(self) -> str:
        """File extension for exported files."""
        return ".zip"

    def export(self, course: Course, filename: Optional[str] = None) -> Tuple[BytesIO, str]:
        """Export course as instructor package ZIP.

        Args:
            course: Course object to export.
            filename: Optional filename (without extension). If None, uses course title.

        Returns:
            Tuple of (BytesIO buffer containing ZIP, filename with extension).
        """
        # Generate filename
        if filename is None:
            safe_title = self._sanitize_filename(course.title)
            filename = f"{safe_title}_instructor"

        full_filename = f"{filename}{self.file_extension}"

        # Create ZIP in memory
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add syllabus
            syllabus = self._generate_syllabus(course)
            zf.writestr("syllabus.txt", syllabus)

            # Add lesson plans
            self._add_lesson_plans(zf, course)

            # Add rubrics, quizzes, and answer keys
            self._add_rubrics(zf, course)
            self._add_quizzes_and_keys(zf, course)

            # Add textbook if chapters exist
            if course.textbook_chapters:
                self._add_textbook(zf, course)

        buffer.seek(0)
        return buffer, full_filename

    def _sanitize_filename(self, name: str) -> str:
        """Remove special characters and replace spaces with underscores.

        Args:
            name: Original filename or folder name.

        Returns:
            Sanitized string safe for filesystem use.
        """
        # Remove special characters except alphanumeric, space, hyphen, underscore
        sanitized = re.sub(r"[^\w\s\-]", "", name)
        # Replace spaces with underscores
        sanitized = sanitized.replace(" ", "_")
        # Remove multiple consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Strip leading/trailing underscores
        sanitized = sanitized.strip("_")
        return sanitized or "untitled"

    def _generate_syllabus(self, course: Course) -> str:
        """Generate syllabus text content.

        Args:
            course: Course object.

        Returns:
            Formatted syllabus text.
        """
        lines = [
            f"Course: {course.title}",
            f"Duration: {course.target_duration_minutes} minutes",
            f"Audience: {course.audience_level}",
            "",
            "Description:",
            course.description or "(No description provided)",
            "",
        ]

        # Add modules and lessons
        if course.modules:
            lines.append("Modules:")
            for i, module in enumerate(course.modules, 1):
                lines.append(f"{i}. {module.title}")
                for lesson in module.lessons:
                    activity_count = len(lesson.activities)
                    lines.append(f"   - {lesson.title}: {activity_count} activities")
            lines.append("")

        # Add learning outcomes
        if course.learning_outcomes:
            lines.append("Learning Outcomes:")
            for outcome in course.learning_outcomes:
                bloom = outcome.bloom_level.value.upper() if outcome.bloom_level else "N/A"
                lines.append(f"- {outcome.behavior} (Bloom's: {bloom})")
            lines.append("")

        return "\n".join(lines)

    def _add_lesson_plans(self, zf: zipfile.ZipFile, course: Course) -> None:
        """Add lesson plan files to ZIP.

        Args:
            zf: ZipFile to write to.
            course: Course object.
        """
        for module in course.modules:
            module_folder = self._sanitize_filename(module.title)
            for lesson in module.lessons:
                lesson_name = self._sanitize_filename(lesson.title)
                path = f"lesson_plans/{module_folder}/{lesson_name}.txt"
                content = self._generate_lesson_plan(lesson, module)
                zf.writestr(path, content)

    def _generate_lesson_plan(self, lesson: Lesson, module: Module) -> str:
        """Generate lesson plan text content.

        Args:
            lesson: Lesson object.
            module: Parent module.

        Returns:
            Formatted lesson plan text.
        """
        lines = [
            f"Lesson: {lesson.title}",
            f"Module: {module.title}",
            "",
            f"Description: {lesson.description or '(No description)'}",
            "",
            "Activities:",
        ]

        for i, activity in enumerate(lesson.activities, 1):
            content_type = activity.content_type.value if activity.content_type else "unknown"
            duration = activity.estimated_duration_minutes or 0
            build_state = activity.build_state.value if activity.build_state else "draft"
            lines.append(
                f"{i}. {activity.title} ({content_type}, {duration} min)"
            )
            lines.append(f"   Build State: {build_state}")

        return "\n".join(lines)

    def _add_rubrics(self, zf: zipfile.ZipFile, course: Course) -> None:
        """Add rubric files to ZIP for RUBRIC activities.

        Args:
            zf: ZipFile to write to.
            course: Course object.
        """
        for module in course.modules:
            for lesson in module.lessons:
                for activity in lesson.activities:
                    if activity.content_type == ContentType.RUBRIC:
                        rubric_content = self._format_rubric(activity)
                        if rubric_content:
                            filename = self._sanitize_filename(activity.title)
                            path = f"rubrics/{filename}.txt"
                            zf.writestr(path, rubric_content)

    def _format_rubric(self, activity: Activity) -> Optional[str]:
        """Format rubric activity content as text.

        Args:
            activity: Rubric activity.

        Returns:
            Formatted rubric text or None if parsing fails.
        """
        try:
            data = json.loads(activity.content)
        except (json.JSONDecodeError, TypeError):
            return None

        lines = [
            f"Rubric: {data.get('title', activity.title)}",
            "",
            "Criteria:",
        ]

        criteria = data.get("criteria", [])
        for criterion in criteria:
            name = criterion.get("name", "Unnamed")
            description = criterion.get("description", "")
            lines.append(f"\n{name}")
            if description:
                lines.append(f"  {description}")

            levels = criterion.get("levels", [])
            for level in levels:
                score = level.get("score", "")
                level_desc = level.get("description", "")
                lines.append(f"  - Score {score}: {level_desc}")

        return "\n".join(lines)

    def _add_quizzes_and_keys(self, zf: zipfile.ZipFile, course: Course) -> None:
        """Add quiz question files and answer key files to ZIP.

        Args:
            zf: ZipFile to write to.
            course: Course object.
        """
        for module in course.modules:
            for lesson in module.lessons:
                for activity in lesson.activities:
                    if activity.content_type == ContentType.QUIZ:
                        questions = self._format_quiz_questions(activity)
                        answer_key = self._format_answer_key(activity)

                        if questions:
                            filename = self._sanitize_filename(activity.title)
                            quiz_path = f"quizzes/{filename}_questions.txt"
                            zf.writestr(quiz_path, questions)

                        if answer_key:
                            filename = self._sanitize_filename(activity.title)
                            key_path = f"answer_keys/{filename}_key.txt"
                            zf.writestr(key_path, answer_key)

    def _format_quiz_questions(self, activity: Activity) -> Optional[str]:
        """Format quiz questions without answers (student version).

        Args:
            activity: Quiz activity.

        Returns:
            Formatted quiz text or None if parsing fails.
        """
        try:
            data = json.loads(activity.content)
        except (json.JSONDecodeError, TypeError):
            return None

        lines = [
            f"Quiz: {data.get('title', activity.title)}",
            "",
        ]

        questions = data.get("questions", [])
        for i, q in enumerate(questions, 1):
            lines.append(f"{i}. {q.get('question_text', '')}")
            options = q.get("options", [])
            for opt in options:
                label = opt.get("label", "")
                text = opt.get("text", "")
                lines.append(f"   {label}) {text}")
            lines.append("")

        return "\n".join(lines)

    def _format_answer_key(self, activity: Activity) -> Optional[str]:
        """Format quiz answer key with explanations (instructor version).

        Args:
            activity: Quiz activity.

        Returns:
            Formatted answer key text or None if parsing fails.
        """
        try:
            data = json.loads(activity.content)
        except (json.JSONDecodeError, TypeError):
            return None

        lines = [
            f"Answer Key: {data.get('title', activity.title)}",
            "",
        ]

        questions = data.get("questions", [])
        for i, q in enumerate(questions, 1):
            lines.append(f"{i}. {q.get('question_text', '')}")
            lines.append(f"   Correct: {q.get('correct_answer', 'N/A')}")
            feedback = q.get("feedback_correct", "")
            if feedback:
                lines.append(f"   Explanation: {feedback}")
            lines.append("")

        return "\n".join(lines)

    def _add_textbook(self, zf: zipfile.ZipFile, course: Course) -> None:
        """Add textbook.docx to ZIP if chapters exist.

        Creates a simple DOCX file containing all textbook chapters.

        Args:
            zf: ZipFile to write to.
            course: Course object.
        """
        if not course.textbook_chapters:
            return

        # Generate DOCX content
        docx_buffer = self._generate_textbook_docx(course)
        zf.writestr("textbook.docx", docx_buffer.getvalue())

    def _generate_textbook_docx(self, course: Course) -> BytesIO:
        """Generate a simple DOCX file for textbook chapters.

        Creates a minimal valid DOCX (which is actually a ZIP file
        with specific XML structure).

        Args:
            course: Course object with textbook_chapters.

        Returns:
            BytesIO buffer containing DOCX file.
        """
        # Build plain text content for textbook
        text_content = []
        for chapter in course.textbook_chapters:
            text_content.append(f"# {chapter.title}\n")
            for section in chapter.sections:
                heading = section.get("heading", "")
                content = section.get("content", "")
                if heading:
                    text_content.append(f"\n## {heading}\n")
                if content:
                    text_content.append(f"{content}\n")

            if chapter.glossary_terms:
                text_content.append("\n### Glossary\n")
                for term in chapter.glossary_terms:
                    term_name = term.get("term", "")
                    definition = term.get("definition", "")
                    text_content.append(f"- {term_name}: {definition}\n")

            text_content.append("\n---\n")

        full_text = "".join(text_content)

        # Create a minimal DOCX structure
        # DOCX is a ZIP file with specific XML files
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as docx:
            # [Content_Types].xml
            content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''
            docx.writestr("[Content_Types].xml", content_types)

            # _rels/.rels
            rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
            docx.writestr("_rels/.rels", rels)

            # word/_rels/document.xml.rels
            doc_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>'''
            docx.writestr("word/_rels/document.xml.rels", doc_rels)

            # word/document.xml - the actual content
            # Escape XML special characters
            escaped_text = (
                full_text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

            # Split into paragraphs
            paragraphs = escaped_text.split("\n")
            para_xml = ""
            for para in paragraphs:
                if para.strip():
                    para_xml += f'''<w:p><w:r><w:t>{para}</w:t></w:r></w:p>
'''

            document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        {para_xml}
    </w:body>
</w:document>'''
            docx.writestr("word/document.xml", document_xml)

        buffer.seek(0)
        return buffer

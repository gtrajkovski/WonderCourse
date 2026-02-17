"""
JSON parser for blueprint and course structure import.
Validates and maps blueprint JSON to Course/Module/Lesson/Activity structure.
"""

import json
from typing import Union
from datetime import datetime
from .base_parser import BaseParser, ParseResult


class JSONParser(BaseParser):
    """Parser for JSON blueprints and course structures."""

    # Expected blueprint structure keys
    BLUEPRINT_KEYS = {'course_title', 'description', 'modules'}
    MODULE_KEYS = {'title', 'lessons'}
    LESSON_KEYS = {'title', 'activities'}
    ACTIVITY_KEYS = {'title', 'content_type'}

    def can_parse(self, source: Union[str, bytes], filename: str = None) -> bool:
        """
        Detect if this is valid JSON with recognized structure.

        Args:
            source: Content to check
            filename: Optional filename

        Returns:
            True if valid JSON with blueprint keys
        """
        if isinstance(source, bytes):
            try:
                source = source.decode('utf-8')
            except UnicodeDecodeError:
                return False

        if not source or not source.strip():
            return False

        try:
            data = json.loads(source)
        except (json.JSONDecodeError, ValueError):
            return False

        # Check for blueprint structure
        if isinstance(data, dict):
            # Check for course blueprint keys
            if any(key in data for key in self.BLUEPRINT_KEYS):
                return True
            # Check for modules array at top level
            if 'modules' in data and isinstance(data['modules'], list):
                return True

        return False

    def parse(self, source: Union[str, bytes], filename: str = None) -> ParseResult:
        """
        Parse JSON blueprint into structured course format.

        Validates structure and maps to Course/Module/Lesson/Activity hierarchy.

        Args:
            source: JSON content to parse
            filename: Optional filename for provenance

        Returns:
            ParseResult with blueprint structure
        """
        if isinstance(source, bytes):
            source = source.decode('utf-8')

        try:
            data = json.loads(source)
        except json.JSONDecodeError as e:
            # Return error as warning
            return ParseResult(
                content_type='unknown',
                content={},
                metadata={'format': 'json', 'parse_error': str(e)},
                warnings=[f'JSON parse error: {str(e)}'],
                provenance={
                    'filename': filename,
                    'import_time': datetime.utcnow().isoformat() + 'Z',
                    'original_format': 'application/json'
                }
            )

        # Validate and extract structure
        warnings = []
        validation_results = self._validate_structure(data, warnings)

        # Build metadata
        metadata = {
            'format': 'json',
            'structure_valid': validation_results['valid'],
            'module_count': validation_results.get('module_count', 0),
            'lesson_count': validation_results.get('lesson_count', 0),
            'activity_count': validation_results.get('activity_count', 0)
        }

        # Build provenance
        provenance = {
            'filename': filename,
            'import_time': datetime.utcnow().isoformat() + 'Z',
            'original_format': 'application/json'
        }

        return ParseResult(
            content_type='blueprint',
            content=data,
            metadata=metadata,
            warnings=warnings,
            provenance=provenance
        )

    def _validate_structure(self, data: dict, warnings: list) -> dict:
        """
        Validate blueprint structure against expected schema.

        Args:
            data: Parsed JSON data
            warnings: List to append warnings to

        Returns:
            Dictionary with validation results and counts
        """
        results = {'valid': True}

        # Check for required top-level keys
        missing_keys = self.BLUEPRINT_KEYS - set(data.keys())
        if missing_keys:
            warnings.append(f'Missing blueprint keys: {", ".join(missing_keys)}')
            results['valid'] = False

        # Validate modules structure
        if 'modules' not in data:
            warnings.append('No modules found in blueprint')
            results['valid'] = False
            return results

        modules = data['modules']
        if not isinstance(modules, list):
            warnings.append('Modules should be a list')
            results['valid'] = False
            return results

        results['module_count'] = len(modules)
        lesson_count = 0
        activity_count = 0

        # Validate each module
        for i, module in enumerate(modules):
            if not isinstance(module, dict):
                warnings.append(f'Module {i} is not a dictionary')
                results['valid'] = False
                continue

            # Check module keys
            missing_module_keys = self.MODULE_KEYS - set(module.keys())
            if missing_module_keys:
                warnings.append(f'Module {i} missing keys: {", ".join(missing_module_keys)}')

            # Validate lessons
            if 'lessons' in module:
                lessons = module['lessons']
                if not isinstance(lessons, list):
                    warnings.append(f'Module {i} lessons should be a list')
                    continue

                lesson_count += len(lessons)

                # Validate each lesson
                for j, lesson in enumerate(lessons):
                    if not isinstance(lesson, dict):
                        warnings.append(f'Module {i} lesson {j} is not a dictionary')
                        continue

                    # Check lesson keys
                    missing_lesson_keys = self.LESSON_KEYS - set(lesson.keys())
                    if missing_lesson_keys:
                        warnings.append(f'Module {i} lesson {j} missing keys: {", ".join(missing_lesson_keys)}')

                    # Validate activities
                    if 'activities' in lesson:
                        activities = lesson['activities']
                        if not isinstance(activities, list):
                            warnings.append(f'Module {i} lesson {j} activities should be a list')
                            continue

                        activity_count += len(activities)

                        # Validate each activity
                        for k, activity in enumerate(activities):
                            if not isinstance(activity, dict):
                                warnings.append(f'Module {i} lesson {j} activity {k} is not a dictionary')
                                continue

                            # Check activity keys
                            missing_activity_keys = self.ACTIVITY_KEYS - set(activity.keys())
                            if missing_activity_keys:
                                warnings.append(f'Module {i} lesson {j} activity {k} missing keys: {", ".join(missing_activity_keys)}')

        results['lesson_count'] = lesson_count
        results['activity_count'] = activity_count

        return results

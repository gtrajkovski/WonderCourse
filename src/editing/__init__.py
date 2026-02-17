"""Text editing utilities with AI-powered suggestions and diff generation.

This package provides tools for inline text editing with AI assistance,
including suggestion generation, visual diff rendering, undo/redo history,
version management, autocomplete, and Bloom's taxonomy analysis.
"""

from src.editing.diff_generator import DiffGenerator, DiffResult
from src.editing.suggestions import SuggestionEngine, Suggestion
from src.editing.history import EditHistory, EditCommand, SessionHistoryManager, get_session_manager
from src.editing.version_store import VersionStore, Version
from src.editing.autocomplete import AutocompleteEngine, CompletionResult
from src.editing.bloom_analyzer import BloomAnalyzer, BloomAnalysis, AlignmentResult

__all__ = [
    'DiffGenerator',
    'DiffResult',
    'SuggestionEngine',
    'Suggestion',
    'EditHistory',
    'EditCommand',
    'SessionHistoryManager',
    'get_session_manager',
    'VersionStore',
    'Version',
    'AutocompleteEngine',
    'CompletionResult',
    'BloomAnalyzer',
    'BloomAnalysis',
    'AlignmentResult'
]

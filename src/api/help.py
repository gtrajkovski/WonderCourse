"""
Help API Blueprint
Provides access to help content, glossary, and documentation.
"""

import os
import json
from flask import Blueprint, jsonify, request, current_app


def init_help_bp():
    """Initialize help blueprint"""
    bp = Blueprint('help', __name__, url_prefix='/api/help')

    @bp.route('/glossary', methods=['GET'])
    def get_glossary():
        """
        Get all glossary terms
        Returns: JSON with all terms
        """
        try:
            glossary_path = os.path.join(
                current_app.root_path, 'static', 'data', 'glossary.json'
            )

            if not os.path.exists(glossary_path):
                return jsonify({
                    'error': 'Glossary file not found',
                    'terms': []
                }), 404

            with open(glossary_path, 'r', encoding='utf-8') as f:
                glossary = json.load(f)

            return jsonify(glossary), 200

        except Exception as e:
            return jsonify({
                'error': f'Error loading glossary: {str(e)}',
                'terms': []
            }), 500

    @bp.route('/glossary/<term_name>', methods=['GET'])
    def get_glossary_term(term_name):
        """
        Get a specific glossary term
        Args:
            term_name: The term to retrieve (case-insensitive)
        Returns: JSON with term details
        """
        try:
            glossary_path = os.path.join(
                current_app.root_path, 'static', 'data', 'glossary.json'
            )

            if not os.path.exists(glossary_path):
                return jsonify({'error': 'Glossary file not found'}), 404

            with open(glossary_path, 'r', encoding='utf-8') as f:
                glossary = json.load(f)

            # Search for term (case-insensitive)
            term_lower = term_name.lower()
            for term in glossary.get('terms', []):
                if term['term'].lower() == term_lower:
                    return jsonify(term), 200

            return jsonify({'error': f'Term "{term_name}" not found'}), 404

        except Exception as e:
            return jsonify({'error': f'Error loading term: {str(e)}'}), 500

    @bp.route('/search', methods=['GET'])
    def search_glossary():
        """
        Search glossary terms and definitions
        Query params:
            q: Search query
        Returns: JSON with matching terms
        """
        try:
            query = request.args.get('q', '').strip().lower()

            if not query:
                return jsonify({
                    'query': query,
                    'results': []
                }), 200

            glossary_path = os.path.join(
                current_app.root_path, 'static', 'data', 'glossary.json'
            )

            if not os.path.exists(glossary_path):
                return jsonify({
                    'error': 'Glossary file not found',
                    'results': []
                }), 404

            with open(glossary_path, 'r', encoding='utf-8') as f:
                glossary = json.load(f)

            # Search in term names and definitions
            results = []
            for term in glossary.get('terms', []):
                term_text = term['term'].lower()
                definition_text = term['definition'].lower()

                if query in term_text or query in definition_text:
                    results.append(term)

            return jsonify({
                'query': query,
                'count': len(results),
                'results': results
            }), 200

        except Exception as e:
            return jsonify({
                'error': f'Error searching glossary: {str(e)}',
                'results': []
            }), 500

    @bp.route('/topics', methods=['GET'])
    def get_help_topics():
        """
        Get list of available help topics
        Returns: JSON with topic list
        """
        topics = [
            {
                'id': 'bloom-taxonomy',
                'title': "Bloom's Taxonomy",
                'description': 'Learn about cognitive complexity levels'
            },
            {
                'id': 'wwhaa',
                'title': 'WWHAA Framework',
                'description': 'Video script structure for engaging content'
            },
            {
                'id': 'learning-outcomes',
                'title': 'Learning Outcomes',
                'description': 'Writing effective, measurable outcomes'
            },
            {
                'id': 'assessments',
                'title': 'Assessment Design',
                'description': 'Creating valid and reliable assessments'
            },
            {
                'id': 'course-structure',
                'title': 'Course Structure',
                'description': 'Organizing modules, lessons, and activities'
            }
        ]

        return jsonify({'topics': topics}), 200

    @bp.route('/<topic_id>', methods=['GET'])
    def get_help_topic(topic_id):
        """
        Get help content for a specific topic
        Args:
            topic_id: The help topic identifier
        Returns: JSON with help content
        """
        # This could be expanded to load from files or database
        # For now, return basic structure
        help_content = {
            'bloom-taxonomy': {
                'title': "Bloom's Taxonomy",
                'description': 'A framework for categorizing educational goals by cognitive complexity.',
                'sections': [
                    {
                        'title': 'The Six Levels',
                        'items': [
                            'Remember: Recall facts and basic concepts',
                            'Understand: Explain ideas or concepts',
                            'Apply: Use information in new situations',
                            'Analyze: Draw connections among ideas',
                            'Evaluate: Justify a decision or course of action',
                            'Create: Produce new or original work'
                        ]
                    },
                    {
                        'title': 'Using Bloom\'s in Course Design',
                        'content': 'Start with lower levels for foundational content, progress to higher levels for advanced topics. Mix levels within modules to maintain engagement.'
                    }
                ]
            },
            'wwhaa': {
                'title': 'WWHAA Framework',
                'description': 'A video script structure for creating engaging instructional videos.',
                'sections': [
                    {
                        'title': 'The Five Elements',
                        'items': [
                            'What: Introduce the concept clearly',
                            'Why: Explain why it matters to learners',
                            'How: Demonstrate the process step-by-step',
                            'Apply: Show practical real-world application',
                            'Action: Provide clear next steps for learners'
                        ]
                    }
                ]
            }
        }

        content = help_content.get(topic_id)
        if content:
            return jsonify(content), 200
        else:
            return jsonify({
                'error': f'Help topic "{topic_id}" not found',
                'title': 'Not Found',
                'description': 'This help topic is not available.'
            }), 404

    return bp

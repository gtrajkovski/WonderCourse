"""Mock AI API responses for E2E tests.

Provides canned responses for blueprint and content generation
to enable fast, deterministic E2E testing without real API calls.
"""

import json


# Mock blueprint with 2 modules, 3 lessons each
MOCK_BLUEPRINT = {
    "title": "Introduction to Python Programming",
    "description": "Learn Python fundamentals including syntax, data structures, and basic algorithms.",
    "duration_minutes": 180,
    "modules": [
        {
            "title": "Python Basics",
            "description": "Core Python syntax and concepts",
            "order": 0,
            "lessons": [
                {
                    "title": "Variables and Data Types",
                    "description": "Understanding Python data types",
                    "order": 0,
                    "activities": [
                        {
                            "title": "Python Data Types Video",
                            "content_type": "VIDEO",
                            "activity_type": "VIDEO_LECTURE",
                            "order": 0
                        },
                        {
                            "title": "Data Types Quiz",
                            "content_type": "QUIZ",
                            "activity_type": "GRADED_QUIZ",
                            "order": 1
                        }
                    ]
                },
                {
                    "title": "Control Flow",
                    "description": "If statements, loops, and logic",
                    "order": 1,
                    "activities": [
                        {
                            "title": "Control Flow Reading",
                            "content_type": "READING",
                            "activity_type": "READING",
                            "order": 0
                        }
                    ]
                },
                {
                    "title": "Functions",
                    "description": "Defining and calling functions",
                    "order": 2,
                    "activities": [
                        {
                            "title": "Functions Hands-On Lab",
                            "content_type": "HOL",
                            "activity_type": "HOL",
                            "order": 0
                        }
                    ]
                }
            ]
        },
        {
            "title": "Data Structures",
            "description": "Lists, dictionaries, sets, and tuples",
            "order": 1,
            "lessons": [
                {
                    "title": "Lists and Tuples",
                    "description": "Working with sequences",
                    "order": 0,
                    "activities": [
                        {
                            "title": "Lists Video",
                            "content_type": "VIDEO",
                            "activity_type": "VIDEO_LECTURE",
                            "order": 0
                        }
                    ]
                },
                {
                    "title": "Dictionaries",
                    "description": "Key-value data structures",
                    "order": 1,
                    "activities": [
                        {
                            "title": "Dictionary Reading",
                            "content_type": "READING",
                            "activity_type": "READING",
                            "order": 0
                        }
                    ]
                },
                {
                    "title": "Data Structure Practice",
                    "description": "Apply your knowledge",
                    "order": 2,
                    "activities": [
                        {
                            "title": "Data Structures Quiz",
                            "content_type": "QUIZ",
                            "activity_type": "PRACTICE_QUIZ",
                            "order": 0
                        }
                    ]
                }
            ]
        }
    ]
}


# Mock video script with WWHAA structure
MOCK_VIDEO_SCRIPT = {
    "hook": "Have you ever wondered how computers store and manipulate different types of information? Numbers, text, true or false values - they all have their place in Python programming.",
    "objective": "By the end of this video, you'll understand Python's core data types including integers, floats, strings, and booleans. You'll be able to identify when to use each type and how to convert between them.",
    "content": "Let's start with numbers. Python has two main numeric types: integers for whole numbers like 42, and floats for decimals like 3.14. You can perform arithmetic operations on both. Strings are sequences of characters enclosed in quotes, like 'hello' or \"world\". You can concatenate strings with the plus operator. Booleans represent truth values: True or False. They're essential for conditional logic. Python also lets you convert between types using functions like int(), float(), and str(). For example, int('42') converts the string '42' to the integer 42.",
    "ivq": "Which data type would you use to store a person's age in years? A) String B) Float C) Integer D) Boolean",
    "summary": "Today we learned about Python's four fundamental data types: integers for whole numbers, floats for decimals, strings for text, and booleans for true/false values. We also saw how to convert between these types.",
    "cta": "In the next lesson, we'll explore control flow - how to make decisions in your code using if statements and loops. See you there!"
}


# Mock reading with sections and references
MOCK_READING = {
    "introduction": "Control flow structures allow programs to make decisions and repeat operations. This reading explores Python's if statements, for loops, and while loops.",
    "sections": [
        {
            "heading": "Conditional Statements",
            "content": "Python's if statement executes code blocks based on boolean conditions. The basic syntax uses if, elif, and else keywords. Indentation defines code blocks."
        },
        {
            "heading": "For Loops",
            "content": "For loops iterate over sequences like lists, strings, or ranges. The range() function generates numeric sequences. Loop variables take each value in turn."
        },
        {
            "heading": "While Loops",
            "content": "While loops repeat as long as a condition remains true. They're useful when the number of iterations isn't known in advance. Be careful to avoid infinite loops."
        }
    ],
    "conclusion": "Mastering control flow is essential for writing dynamic programs that respond to data and user input. Practice combining these structures to solve complex problems.",
    "references": [
        {
            "authors": ["Van Rossum, G.", "Drake, F. L."],
            "year": 2023,
            "title": "The Python Language Reference",
            "url": "https://docs.python.org/3/reference/"
        },
        {
            "authors": ["Lutz, M."],
            "year": 2022,
            "title": "Learning Python",
            "publisher": "O'Reilly Media"
        }
    ]
}


# Mock quiz with 3 questions and distractors
MOCK_QUIZ = {
    "questions": [
        {
            "question_text": "What is the correct syntax for an if statement in Python?",
            "bloom_level": "REMEMBER",
            "options": [
                {
                    "text": "if x > 5:",
                    "is_correct": True,
                    "feedback": "Correct! Python uses a colon after the condition and indentation for the code block."
                },
                {
                    "text": "if (x > 5) {",
                    "is_correct": False,
                    "feedback": "This is C/Java syntax. Python uses colons instead of curly braces."
                },
                {
                    "text": "if x > 5 then",
                    "is_correct": False,
                    "feedback": "Python doesn't use 'then'. Just use a colon after the condition."
                },
                {
                    "text": "if x > 5;",
                    "is_correct": False,
                    "feedback": "Semicolons aren't needed in Python. Use a colon instead."
                }
            ]
        },
        {
            "question_text": "Which loop is best for iterating over a list?",
            "bloom_level": "APPLY",
            "options": [
                {
                    "text": "for loop",
                    "is_correct": True,
                    "feedback": "Correct! For loops are designed for iterating over sequences."
                },
                {
                    "text": "while loop",
                    "is_correct": False,
                    "feedback": "While loops work but require manual index management. For loops are cleaner."
                },
                {
                    "text": "do-while loop",
                    "is_correct": False,
                    "feedback": "Python doesn't have do-while loops."
                }
            ]
        },
        {
            "question_text": "What happens if a while loop's condition never becomes False?",
            "bloom_level": "UNDERSTAND",
            "options": [
                {
                    "text": "The loop runs indefinitely (infinite loop)",
                    "is_correct": True,
                    "feedback": "Correct! This is called an infinite loop and will hang your program."
                },
                {
                    "text": "Python automatically stops it after 1000 iterations",
                    "is_correct": False,
                    "feedback": "Python doesn't have automatic loop limits."
                },
                {
                    "text": "The loop runs once and exits",
                    "is_correct": False,
                    "feedback": "The loop continues as long as the condition is True."
                }
            ]
        }
    ]
}


# Mock HOL (Hands-On Lab)
MOCK_HOL = {
    "objective": "Practice writing and calling Python functions",
    "parts": [
        {
            "title": "Foundation: Basic Functions",
            "instructions": "Write a function that takes two numbers and returns their sum.",
            "estimated_minutes": 10
        },
        {
            "title": "Development: Functions with Default Arguments",
            "instructions": "Create a function with optional parameters using default values.",
            "estimated_minutes": 15
        },
        {
            "title": "Integration: Combining Functions",
            "instructions": "Build a program that uses multiple functions working together.",
            "estimated_minutes": 20
        }
    ],
    "rubric": [
        {
            "criterion": "Function Definition",
            "advanced": "Functions use clear names and type hints",
            "intermediate": "Functions defined correctly with parameters",
            "beginner": "Basic function syntax attempted"
        }
    ]
}


# Mock coach responses
MOCK_COACH_GREETING = {
    "message": "Hello! I'm here to help you explore the topic of Python data types. What questions do you have about integers, floats, strings, or booleans?"
}

MOCK_COACH_RESPONSE = {
    "message": "That's a great question. Let me guide you through this. Can you tell me what you already know about how Python stores different types of data?"
}

MOCK_COACH_EVALUATION = {
    "rubric_scores": [
        {
            "criterion": "Understanding of Core Concepts",
            "score": "Advanced",
            "feedback": "Demonstrated strong grasp of fundamental data type concepts"
        },
        {
            "criterion": "Critical Thinking",
            "score": "Intermediate",
            "feedback": "Asked thoughtful questions and made connections between ideas"
        },
        {
            "criterion": "Engagement",
            "score": "Advanced",
            "feedback": "Actively participated throughout the session"
        }
    ],
    "overall_feedback": "Excellent session! You showed strong understanding of Python data types and asked insightful questions.",
    "transcript": [
        {"role": "coach", "message": "Hello! I'm here to help you explore the topic..."},
        {"role": "student", "message": "What is the main topic of this lesson?"},
        {"role": "coach", "message": "That's a great question. Let me guide you..."}
    ]
}


def route_handler(route):
    """Route Playwright requests to appropriate mock responses.

    Args:
        route: Playwright route object

    Returns:
        Dict with 'status', 'content_type', and 'body' for route.fulfill()
        or None to continue with real request
    """
    url = route.request.url
    method = route.request.method

    # Only handle POST requests to generate endpoints
    if method != "POST":
        return None

    # Blueprint generation
    if "/blueprint/generate" in url:
        return {
            "status": 200,
            "content_type": "application/json",
            "body": json.dumps(MOCK_BLUEPRINT)
        }

    # Coach interactions
    if "/coach/" in url:
        if "/start" in url:
            return {
                "status": 200,
                "content_type": "application/json",
                "body": json.dumps(MOCK_COACH_GREETING)
            }
        elif "/message" in url or "/chat" in url:
            return {
                "status": 200,
                "content_type": "application/json",
                "body": json.dumps(MOCK_COACH_RESPONSE)
            }
        elif "/evaluate" in url or "/end" in url:
            return {
                "status": 200,
                "content_type": "application/json",
                "body": json.dumps(MOCK_COACH_EVALUATION)
            }

    # Content generation - determine type from request body
    if "/generate" in url and "/activities/" in url:
        try:
            # Parse request to determine content type
            post_data = route.request.post_data
            if post_data:
                data = json.loads(post_data)
                content_type = data.get("content_type", "VIDEO")

                # Map content types to mock responses
                mock_map = {
                    "VIDEO": MOCK_VIDEO_SCRIPT,
                    "READING": MOCK_READING,
                    "QUIZ": MOCK_QUIZ,
                    "HOL": MOCK_HOL
                }

                mock_content = mock_map.get(content_type, MOCK_VIDEO_SCRIPT)

                return {
                    "status": 200,
                    "content_type": "application/json",
                    "body": json.dumps({
                        "content": mock_content,
                        "metadata": {
                            "word_count": 250,
                            "duration_minutes": 5
                        }
                    })
                }
        except (json.JSONDecodeError, KeyError):
            pass

    # Default: don't mock this request
    return None

"""Create sample courses for testing and demonstration."""

import json
import os
from datetime import datetime


def create_sample_courses():
    """Create 2 comprehensive sample courses."""

    # Sample Course 1: Python Fundamentals
    course1 = {
        "id": "course_python_fundamentals",
        "title": "Python Programming Fundamentals",
        "description": "Master the basics of Python programming with hands-on exercises and real-world projects. Perfect for beginners looking to start their coding journey.",
        "audience_level": "beginner",
        "target_duration_minutes": 120,
        "modality": "online",
        "prerequisites": "Basic computer skills",
        "tools": ["Python 3.x", "VS Code", "Terminal"],
        "grading_policy": "Pass/Fail based on quiz scores (70% threshold)",
        "modules": [
            {
                "id": "mod_py_intro",
                "title": "Getting Started with Python",
                "description": "Introduction to Python and setting up your development environment",
                "lessons": [
                    {
                        "id": "les_py_setup",
                        "title": "Setting Up Python",
                        "description": "Install Python and configure your IDE",
                        "activities": [
                            {
                                "id": "act_py_welcome",
                                "title": "Welcome to Python",
                                "content_type": "video",
                                "activity_type": "video_lecture",
                                "wwhaa_phase": "hook",
                                "content": json.dumps({
                                    "title": "Welcome to Python",
                                    "hook": {"phase": "hook", "title": "Why Python?", "script_text": "Python is the most popular programming language in the world. From web apps to AI, data science to automation, Python does it all. Today, over 8 million developers use Python daily.", "speaker_notes": "Show enthusiasm, use stats slide"},
                                    "objective": {"phase": "objective", "title": "What You Will Learn", "script_text": "By the end of this video, you will understand why Python is so powerful, where it is used in the real world, and be ready to write your first program.", "speaker_notes": "Clear delivery, eye contact"},
                                    "content": {"phase": "content", "title": "Python Overview", "script_text": "Python was created by Guido van Rossum in 1991. Its design philosophy emphasizes code readability with its notable use of significant whitespace. Python is dynamically typed and garbage-collected. It supports multiple programming paradigms, including structured, object-oriented, and functional programming. Companies like Google, Netflix, Spotify, and Instagram all use Python extensively.", "speaker_notes": "Use company logos on slides"},
                                    "ivq": {"phase": "ivq", "title": "Quick Check", "script_text": "Quick question: What year was Python created? Think about it for a moment. The answer is 1991, making Python over 30 years old!", "speaker_notes": "Pause 3 seconds after question"},
                                    "summary": {"phase": "summary", "title": "Recap", "script_text": "Python is versatile, readable, and beginner-friendly. It powers everything from simple scripts to complex AI systems. That is why it is your best choice for learning programming.", "speaker_notes": "Summarize with hand gestures"},
                                    "cta": {"phase": "cta", "title": "Next Steps", "script_text": "Now let us install Python on your computer! Head to the next activity where we will walk through the installation process step by step.", "speaker_notes": "Point to next activity link"},
                                    "learning_objective": "Understand Python's history and use cases"
                                }),
                                "build_state": "generated",
                                "word_count": 245,
                                "estimated_duration_minutes": 1.6,
                                "bloom_level": "understand",
                                "order": 0,
                                "metadata": {"content_type": "video", "humanization_score": 85},
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            },
                            {
                                "id": "act_py_install",
                                "title": "Installing Python",
                                "content_type": "reading",
                                "activity_type": "reading_material",
                                "wwhaa_phase": "content",
                                "content": json.dumps({
                                    "title": "Installing Python on Your System",
                                    "introduction": "Follow these step-by-step instructions to install Python on Windows, Mac, or Linux. The process takes about 5 minutes.",
                                    "sections": [
                                        {"heading": "Windows Installation", "body": "1. Go to python.org/downloads\n2. Download the latest Python 3.x installer\n3. Run the installer\n4. IMPORTANT: Check 'Add Python to PATH'\n5. Click 'Install Now'\n6. Verify: Open Command Prompt and type: python --version"},
                                        {"heading": "Mac Installation", "body": "Option A - Homebrew (recommended):\n1. Install Homebrew: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"\n2. Run: brew install python3\n3. Verify: python3 --version\n\nOption B - Direct Download:\n1. Download from python.org\n2. Run the .pkg installer\n3. Follow the prompts"},
                                        {"heading": "Linux Installation", "body": "Most Linux distributions include Python. To update or install:\n\nUbuntu/Debian:\nsudo apt update\nsudo apt install python3 python3-pip\n\nFedora:\nsudo dnf install python3\n\nVerify: python3 --version"},
                                        {"heading": "Verify Your Installation", "body": "Open a terminal and run:\npython --version (or python3 --version)\n\nYou should see something like: Python 3.11.4\n\nIf you see an error, revisit the installation steps or check the troubleshooting section on python.org."}
                                    ],
                                    "conclusion": "Congratulations! With Python installed, you are ready to write your first program. In the next lesson, we will explore Python basics.",
                                    "references": [{"title": "Python Downloads", "url": "https://python.org/downloads"}]
                                }),
                                "build_state": "generated",
                                "word_count": 280,
                                "estimated_duration_minutes": 1.2,
                                "bloom_level": "apply",
                                "order": 1,
                                "metadata": {"content_type": "reading"},
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            },
                            {
                                "id": "act_py_quiz1",
                                "title": "Setup Knowledge Check",
                                "content_type": "quiz",
                                "activity_type": "practice_quiz",
                                "wwhaa_phase": "ivq",
                                "content": json.dumps({
                                    "title": "Python Setup Quiz",
                                    "questions": [
                                        {
                                            "question_text": "What command verifies that Python is correctly installed?",
                                            "options": [
                                                {"text": "python --version", "is_correct": True, "feedback": "Correct! This displays the installed Python version."},
                                                {"text": "python --check", "is_correct": False, "feedback": "This flag does not exist. Use --version instead."},
                                                {"text": "python --verify", "is_correct": False, "feedback": "Not a valid Python flag. Try --version."},
                                                {"text": "python --test", "is_correct": False, "feedback": "This runs the test suite, not version check."}
                                            ],
                                            "explanation": "The --version flag is standard across most command-line tools for checking installed versions."
                                        },
                                        {
                                            "question_text": "Why is it important to check 'Add Python to PATH' during Windows installation?",
                                            "options": [
                                                {"text": "It allows you to run Python from any terminal location", "is_correct": True, "feedback": "Correct! PATH tells Windows where to find the Python executable."},
                                                {"text": "It makes Python run faster", "is_correct": False, "feedback": "PATH configuration does not affect execution speed."},
                                                {"text": "It enables dark mode in Python", "is_correct": False, "feedback": "PATH has nothing to do with visual themes."},
                                                {"text": "It automatically updates Python", "is_correct": False, "feedback": "PATH does not handle updates."}
                                            ],
                                            "explanation": "Adding Python to PATH makes it accessible from any command prompt or terminal window."
                                        },
                                        {
                                            "question_text": "Which package manager can install Python on macOS?",
                                            "options": [
                                                {"text": "Homebrew", "is_correct": True, "feedback": "Correct! Homebrew is a popular package manager for macOS."},
                                                {"text": "apt", "is_correct": False, "feedback": "apt is for Debian/Ubuntu Linux, not macOS."},
                                                {"text": "npm", "is_correct": False, "feedback": "npm is for JavaScript packages, not Python."},
                                                {"text": "choco", "is_correct": False, "feedback": "Chocolatey is for Windows, not macOS."}
                                            ],
                                            "explanation": "Homebrew (brew) is the most popular package manager for macOS."
                                        }
                                    ],
                                    "passing_score": 70
                                }),
                                "build_state": "generated",
                                "word_count": 320,
                                "estimated_duration_minutes": 4.5,
                                "bloom_level": "remember",
                                "order": 2,
                                "metadata": {"content_type": "quiz", "num_questions": 3},
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            }
                        ],
                        "order": 0,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    },
                    {
                        "id": "les_py_basics",
                        "title": "Python Basics",
                        "description": "Variables, data types, and basic operations",
                        "activities": [
                            {
                                "id": "act_py_variables",
                                "title": "Variables and Data Types Demo",
                                "content_type": "screencast",
                                "activity_type": "screencast_simulation",
                                "wwhaa_phase": "content",
                                "content": "",
                                "build_state": "draft",
                                "word_count": 0,
                                "estimated_duration_minutes": 0.0,
                                "bloom_level": "apply",
                                "order": 0,
                                "metadata": {},
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            },
                            {
                                "id": "act_py_hol",
                                "title": "Hands-On: Your First Program",
                                "content_type": "hol",
                                "activity_type": "hands_on_lab",
                                "wwhaa_phase": "content",
                                "content": json.dumps({
                                    "title": "Your First Python Program",
                                    "overview": "Write and run your first Python program using variables and print statements.",
                                    "learning_objectives": ["Create variables of different types", "Use the print() function", "Run Python scripts from the terminal"],
                                    "prerequisites": ["Python installed", "Text editor or IDE ready"],
                                    "estimated_time_minutes": 15,
                                    "parts": [
                                        {"title": "Create a Script", "instructions": "Create a new file called hello.py and add the following code:", "code_snippet": "# hello.py\nname = \"Your Name\"\nage = 25\nprint(f\"Hello, {name}!\")\nprint(f\"You are {age} years old.\")"},
                                        {"title": "Run the Script", "instructions": "Open your terminal, navigate to the file location, and run: python hello.py", "expected_output": "Hello, Your Name!\nYou are 25 years old."},
                                        {"title": "Experiment and Extend", "instructions": "Modify the variables and add more print statements. Try adding a hobby variable.", "challenge": "Create a mini-profile that prints name, age, city, and favorite hobby."}
                                    ],
                                    "rubric_criteria": [
                                        {"criterion": "Script runs without syntax errors", "weight": 40},
                                        {"criterion": "Output matches expected format", "weight": 30},
                                        {"criterion": "Challenge completed with all 4 variables", "weight": 30}
                                    ]
                                }),
                                "build_state": "generated",
                                "word_count": 220,
                                "estimated_duration_minutes": 15.0,
                                "bloom_level": "apply",
                                "order": 1,
                                "metadata": {"content_type": "hol"},
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            }
                        ],
                        "order": 1,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                ],
                "order": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": "mod_py_control",
                "title": "Control Flow",
                "description": "Conditionals, loops, and program flow",
                "lessons": [
                    {
                        "id": "les_py_conditions",
                        "title": "Conditionals",
                        "description": "If, elif, else statements",
                        "activities": [
                            {
                                "id": "act_py_if",
                                "title": "If Statements Explained",
                                "content_type": "video",
                                "activity_type": "video_lecture",
                                "wwhaa_phase": "content",
                                "content": "",
                                "build_state": "draft",
                                "word_count": 0,
                                "estimated_duration_minutes": 0.0,
                                "bloom_level": "understand",
                                "order": 0,
                                "metadata": {},
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            },
                            {
                                "id": "act_py_coach",
                                "title": "Practice Conditionals with AI Coach",
                                "content_type": "coach",
                                "activity_type": "coach_dialogue",
                                "wwhaa_phase": "content",
                                "content": json.dumps({
                                    "title": "Conditional Logic Coach",
                                    "learning_objectives": ["Write if/elif/else statements", "Use comparison operators correctly", "Handle multiple conditions"],
                                    "scenario": "You are building a grade calculator that converts numeric scores to letter grades. The grading scale is: A (90-100), B (80-89), C (70-79), D (60-69), F (below 60).",
                                    "tasks": ["Check if score >= 90 for an A grade", "Use elif for B, C, D ranges", "Use else for F as the default"],
                                    "conversation_starters": [
                                        {"starter_text": "How would you check if a score qualifies for an A grade?", "purpose": "Test basic if understanding"},
                                        {"starter_text": "What happens if none of your conditions match?", "purpose": "Explore else clause usage"},
                                        {"starter_text": "Why do we use elif instead of multiple if statements?", "purpose": "Understand efficiency and logic flow"}
                                    ],
                                    "sample_responses": [
                                        {"response_text": "if score >= 90: return 'A'", "evaluation_level": "meets", "feedback": "Good basic structure! Consider using elif for subsequent grades."},
                                        {"response_text": "Use elif for B (80-89), C (70-79), D (60-69), else F", "evaluation_level": "exceeds", "feedback": "Excellent! You understand the complete branching pattern."},
                                        {"response_text": "Just check each grade with separate if statements", "evaluation_level": "needs_improvement", "feedback": "This would work but is inefficient. With separate ifs, all conditions are checked even after a match."}
                                    ],
                                    "evaluation_criteria": ["Uses correct Python syntax", "Handles all grade ranges", "Uses elif for efficiency", "Has a default else case"],
                                    "wrap_up": "Great work! You now understand how to use conditional branching to make decisions in your code. This pattern appears everywhere in programming.",
                                    "reflection_prompts": ["What other real-world scenarios need conditional logic?", "How would you handle invalid scores (negative or above 100)?"]
                                }),
                                "build_state": "generated",
                                "word_count": 340,
                                "estimated_duration_minutes": 10.0,
                                "bloom_level": "apply",
                                "order": 1,
                                "metadata": {"content_type": "coach"},
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            },
                            {
                                "id": "act_py_final_quiz",
                                "title": "Module Assessment",
                                "content_type": "quiz",
                                "activity_type": "graded_quiz",
                                "wwhaa_phase": "summary",
                                "content": "",
                                "build_state": "draft",
                                "word_count": 0,
                                "estimated_duration_minutes": 0.0,
                                "bloom_level": "analyze",
                                "order": 2,
                                "metadata": {},
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            }
                        ],
                        "order": 0,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                ],
                "order": 1,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ],
        "learning_outcomes": [
            {
                "id": "lo_py_1",
                "audience": "Beginners with no prior programming experience",
                "behavior": "write basic Python programs using variables, conditionals, and loops",
                "condition": "given a problem description and access to Python documentation",
                "degree": "with correct syntax and logical flow",
                "bloom_level": "apply",
                "mapped_activity_ids": ["act_py_hol", "act_py_coach"]
            },
            {
                "id": "lo_py_2",
                "audience": "New programmers",
                "behavior": "set up a complete Python development environment",
                "condition": "on Windows, Mac, or Linux",
                "degree": "independently without assistance",
                "bloom_level": "apply",
                "mapped_activity_ids": ["act_py_install", "act_py_quiz1"]
            }
        ],
        "textbook_chapters": [],
        "schema_version": 1,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    # Sample Course 2: Data Analysis with pandas
    course2 = {
        "id": "course_data_analysis",
        "title": "Data Analysis with Python and pandas",
        "description": "Learn to analyze, visualize, and interpret data using Python's powerful pandas library. Build real-world data analysis skills.",
        "audience_level": "intermediate",
        "target_duration_minutes": 180,
        "modality": "online",
        "prerequisites": "Python basics, familiarity with variables and functions",
        "tools": ["Python 3.x", "Jupyter Notebook", "pandas", "matplotlib"],
        "grading_policy": "Project-based assessment with rubric scoring",
        "modules": [
            {
                "id": "mod_da_intro",
                "title": "Introduction to Data Analysis",
                "description": "Overview of data analysis concepts and pandas basics",
                "lessons": [
                    {
                        "id": "les_da_overview",
                        "title": "What is Data Analysis?",
                        "description": "Understanding the data analysis workflow",
                        "activities": [
                            {
                                "id": "act_da_intro_video",
                                "title": "The Data Analysis Pipeline",
                                "content_type": "video",
                                "activity_type": "video_lecture",
                                "wwhaa_phase": "hook",
                                "content": json.dumps({
                                    "title": "The Data Analysis Pipeline",
                                    "hook": {"phase": "hook", "title": "Data is Everywhere", "script_text": "Every click, every purchase, every sensor reading generates data. Companies that can analyze this data effectively gain massive competitive advantages. Netflix saves 1 billion dollars per year through data-driven decisions.", "speaker_notes": "Show Netflix stats visual"},
                                    "objective": {"phase": "objective", "title": "Your Learning Goals", "script_text": "By the end of this module, you will understand the complete data analysis pipeline: collect, clean, analyze, visualize, and communicate insights.", "speaker_notes": "Show pipeline diagram"},
                                    "content": {"phase": "content", "title": "The 5-Step Pipeline", "script_text": "Step 1: Data Collection. Gathering data from databases, APIs, files, or web scraping. Step 2: Data Cleaning. Handling missing values, fixing formats, removing duplicates. This often takes 80% of your time! Step 3: Exploratory Analysis. Understanding patterns, distributions, and relationships. Step 4: Visualization. Creating charts that communicate findings clearly. Step 5: Communication. Presenting insights to stakeholders who make decisions.", "speaker_notes": "Walk through each step with examples"},
                                    "ivq": {"phase": "ivq", "title": "Quick Check", "script_text": "Which step typically takes the most time in data analysis? If you said data cleaning, you are correct! Real-world data is messy.", "speaker_notes": "Pause for answer"},
                                    "summary": {"phase": "summary", "title": "Key Takeaways", "script_text": "Data analysis follows a repeatable pipeline. Python and pandas make each step efficient. The goal is always actionable insights, not just charts.", "speaker_notes": "Emphasize insights over charts"},
                                    "cta": {"phase": "cta", "title": "Get Started", "script_text": "Let us install pandas and start analyzing some real data!", "speaker_notes": "Show install command"},
                                    "learning_objective": "Understand the data analysis workflow and pandas role"
                                }),
                                "build_state": "generated",
                                "word_count": 290,
                                "estimated_duration_minutes": 1.9,
                                "bloom_level": "understand",
                                "order": 0,
                                "metadata": {"content_type": "video"},
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            },
                            {
                                "id": "act_da_setup",
                                "title": "Setting Up Your Environment",
                                "content_type": "reading",
                                "activity_type": "reading_material",
                                "wwhaa_phase": "content",
                                "content": json.dumps({
                                    "title": "Setting Up pandas and Jupyter",
                                    "introduction": "Before analyzing data, you need the right tools. This guide walks you through installing pandas and Jupyter Notebook.",
                                    "sections": [
                                        {"heading": "Installing pandas", "body": "pip install pandas\n\nThis installs pandas and its dependencies (NumPy, etc.).\n\nVerify: python -c \"import pandas; print(pandas.__version__)\""},
                                        {"heading": "Installing Jupyter Notebook", "body": "pip install jupyter\n\nJupyter provides an interactive environment perfect for data exploration.\n\nLaunch: jupyter notebook"},
                                        {"heading": "Additional Libraries", "body": "pip install matplotlib seaborn\n\nThese visualization libraries work seamlessly with pandas."},
                                        {"heading": "Your First Notebook", "body": "1. Run: jupyter notebook\n2. Click 'New' > 'Python 3'\n3. In the first cell, type:\nimport pandas as pd\nprint('pandas ready!')\n4. Press Shift+Enter to run"}
                                    ],
                                    "conclusion": "Your data analysis environment is ready. In the next lesson, we will load and explore a real dataset.",
                                    "references": [{"title": "pandas documentation", "url": "https://pandas.pydata.org/docs/"}]
                                }),
                                "build_state": "generated",
                                "word_count": 180,
                                "estimated_duration_minutes": 0.8,
                                "bloom_level": "apply",
                                "order": 1,
                                "metadata": {"content_type": "reading"},
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            }
                        ],
                        "order": 0,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    },
                    {
                        "id": "les_da_dataframes",
                        "title": "Working with DataFrames",
                        "description": "Core pandas data structure and operations",
                        "activities": [
                            {
                                "id": "act_da_df_video",
                                "title": "DataFrame Fundamentals",
                                "content_type": "video",
                                "activity_type": "video_lecture",
                                "wwhaa_phase": "content",
                                "content": "",
                                "build_state": "draft",
                                "word_count": 0,
                                "estimated_duration_minutes": 0.0,
                                "bloom_level": "understand",
                                "order": 0,
                                "metadata": {},
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            },
                            {
                                "id": "act_da_df_lab",
                                "title": "Lab: Exploring DataFrames",
                                "content_type": "lab",
                                "activity_type": "ungraded_lab",
                                "wwhaa_phase": "content",
                                "content": json.dumps({
                                    "title": "Exploring DataFrames Lab",
                                    "overview": "Practice loading, inspecting, and manipulating DataFrames using a real dataset.",
                                    "learning_objectives": ["Load CSV data into a DataFrame", "Inspect data shape and types", "Select columns and filter rows"],
                                    "setup_steps": [
                                        {"step": 1, "instruction": "Download the sample dataset from the resources", "command": "wget https://example.com/sales_data.csv"},
                                        {"step": 2, "instruction": "Launch Jupyter Notebook", "command": "jupyter notebook"},
                                        {"step": 3, "instruction": "Create a new Python 3 notebook", "command": None}
                                    ],
                                    "exercises": [
                                        {"title": "Load Data", "instructions": "Use pd.read_csv() to load sales_data.csv", "starter_code": "import pandas as pd\n\n# Load the data\ndf = ", "solution": "df = pd.read_csv('sales_data.csv')"},
                                        {"title": "Inspect Data", "instructions": "Display first 5 rows and data types", "starter_code": "# Show first 5 rows\n\n# Show data types\n", "solution": "df.head()\ndf.dtypes"},
                                        {"title": "Filter Data", "instructions": "Find all sales over $1000", "starter_code": "# Filter for sales > 1000\nbig_sales = ", "solution": "big_sales = df[df['amount'] > 1000]"}
                                    ],
                                    "submission_requirements": "Export your notebook as HTML and submit.",
                                    "estimated_time_minutes": 30
                                }),
                                "build_state": "generated",
                                "word_count": 250,
                                "estimated_duration_minutes": 30.0,
                                "bloom_level": "apply",
                                "order": 1,
                                "metadata": {"content_type": "lab"},
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            },
                            {
                                "id": "act_da_discussion",
                                "title": "Discussion: Real-World Data Challenges",
                                "content_type": "discussion",
                                "activity_type": "discussion_prompt",
                                "wwhaa_phase": "content",
                                "content": json.dumps({
                                    "title": "Real-World Data Challenges",
                                    "prompt": "Think about a dataset you have encountered (at work, school, or in a personal project). What challenges did you face when trying to analyze it? How did you overcome them, or what would you do differently now?",
                                    "discussion_guidelines": ["Share specific examples", "Describe the data source", "Explain your approach", "Suggest alternatives"],
                                    "facilitation_questions": [
                                        "What was the messiest part of your data?",
                                        "How did missing values affect your analysis?",
                                        "What tools did you use to clean the data?"
                                    ],
                                    "minimum_posts": 1,
                                    "minimum_replies": 2,
                                    "grading_criteria": ["Substantive contribution", "Specific examples", "Engagement with peers"]
                                }),
                                "build_state": "generated",
                                "word_count": 130,
                                "estimated_duration_minutes": 20.0,
                                "bloom_level": "evaluate",
                                "order": 2,
                                "metadata": {"content_type": "discussion"},
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            }
                        ],
                        "order": 1,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                ],
                "order": 0,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            {
                "id": "mod_da_project",
                "title": "Capstone Project",
                "description": "Apply your skills to a real data analysis project",
                "lessons": [
                    {
                        "id": "les_da_capstone",
                        "title": "Sales Analysis Project",
                        "description": "Analyze sales data and present findings",
                        "activities": [
                            {
                                "id": "act_da_project",
                                "title": "Sales Analysis Capstone",
                                "content_type": "project",
                                "activity_type": "project_milestone",
                                "wwhaa_phase": "summary",
                                "content": json.dumps({
                                    "title": "Sales Data Analysis Capstone",
                                    "overview": "Analyze a year of sales data to identify trends, top products, and seasonal patterns.",
                                    "learning_objectives": ["Apply the full data analysis pipeline", "Create meaningful visualizations", "Present data-driven recommendations"],
                                    "milestones": [
                                        {"title": "Data Loading & Cleaning", "description": "Load the dataset and handle missing values", "deliverable": "Cleaned DataFrame with documentation of cleaning steps", "points": 20},
                                        {"title": "Exploratory Analysis", "description": "Calculate summary statistics and identify patterns", "deliverable": "Jupyter notebook with analysis", "points": 30},
                                        {"title": "Visualization", "description": "Create at least 3 visualizations that tell a story", "deliverable": "Charts with clear labels and titles", "points": 25},
                                        {"title": "Recommendations", "description": "Write 3-5 actionable recommendations based on your findings", "deliverable": "Summary report", "points": 25}
                                    ],
                                    "resources": ["sales_data_2024.csv", "Product category reference"],
                                    "submission_format": "Jupyter notebook + PDF report",
                                    "due_date_offset_days": 14
                                }),
                                "build_state": "generated",
                                "word_count": 180,
                                "estimated_duration_minutes": 120.0,
                                "bloom_level": "create",
                                "order": 0,
                                "metadata": {"content_type": "project"},
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            },
                            {
                                "id": "act_da_rubric",
                                "title": "Project Rubric",
                                "content_type": "rubric",
                                "activity_type": "peer_review",
                                "wwhaa_phase": "summary",
                                "content": json.dumps({
                                    "title": "Sales Analysis Project Rubric",
                                    "criteria": [
                                        {"name": "Data Cleaning", "description": "Quality of data preprocessing", "below_expectations": "Missing values not addressed; data types incorrect", "meets_expectations": "Missing values handled; data types appropriate", "exceeds_expectations": "Thorough cleaning with documented decisions; edge cases handled", "weight_percentage": 25},
                                        {"name": "Analysis Depth", "description": "Quality and depth of analysis", "below_expectations": "Only basic statistics; no pattern identification", "meets_expectations": "Summary statistics with some pattern analysis", "exceeds_expectations": "Deep analysis with correlations, segmentation, and insights", "weight_percentage": 30},
                                        {"name": "Visualizations", "description": "Clarity and effectiveness of charts", "below_expectations": "Charts unclear or poorly labeled", "meets_expectations": "Clear charts with proper labels and titles", "exceeds_expectations": "Publication-quality visualizations that tell a compelling story", "weight_percentage": 25},
                                        {"name": "Recommendations", "description": "Quality of business recommendations", "below_expectations": "Vague or unsupported recommendations", "meets_expectations": "Clear recommendations tied to data", "exceeds_expectations": "Actionable, specific, and prioritized recommendations", "weight_percentage": 20}
                                    ],
                                    "total_points": 100,
                                    "learning_objective": "Demonstrate mastery of the complete data analysis pipeline"
                                }),
                                "build_state": "generated",
                                "word_count": 200,
                                "estimated_duration_minutes": 5.0,
                                "bloom_level": "evaluate",
                                "order": 1,
                                "metadata": {"content_type": "rubric"},
                                "created_at": datetime.now().isoformat(),
                                "updated_at": datetime.now().isoformat()
                            }
                        ],
                        "order": 0,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                ],
                "order": 1,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        ],
        "learning_outcomes": [
            {
                "id": "lo_da_1",
                "audience": "Intermediate Python programmers",
                "behavior": "perform end-to-end data analysis using pandas",
                "condition": "given a raw CSV dataset",
                "degree": "producing cleaned data, visualizations, and actionable insights",
                "bloom_level": "create",
                "mapped_activity_ids": ["act_da_df_lab", "act_da_project"]
            },
            {
                "id": "lo_da_2",
                "audience": "Data analysis students",
                "behavior": "create effective data visualizations",
                "condition": "using matplotlib and pandas",
                "degree": "that clearly communicate patterns and trends",
                "bloom_level": "create",
                "mapped_activity_ids": ["act_da_project"]
            }
        ],
        "textbook_chapters": [],
        "schema_version": 1,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    # Create directories and save courses
    os.makedirs("projects/1/course_python_fundamentals", exist_ok=True)
    os.makedirs("projects/1/course_data_analysis", exist_ok=True)

    with open("projects/1/course_python_fundamentals/course_data.json", "w") as f:
        json.dump(course1, f, indent=2)

    with open("projects/1/course_data_analysis/course_data.json", "w") as f:
        json.dump(course2, f, indent=2)

    print("Created 2 sample courses:")
    print()
    print("1. Python Programming Fundamentals")
    print("   - 2 modules, 3 lessons, 8 activities")
    print("   - Content types: video, reading, quiz, screencast, hol, coach")
    print("   - 2 learning outcomes")
    print()
    print("2. Data Analysis with Python and pandas")
    print("   - 2 modules, 3 lessons, 7 activities")
    print("   - Content types: video, reading, lab, discussion, project, rubric")
    print("   - 2 learning outcomes")


if __name__ == "__main__":
    create_sample_courses()

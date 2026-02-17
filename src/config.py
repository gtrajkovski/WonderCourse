import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    # API
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    MODEL = os.getenv("MODEL", "claude-sonnet-4-20250514")
    MAX_TOKENS = 4096

    # Paths
    PROJECTS_DIR = Path("projects")
    DATABASE = Path("instance/users.db")

    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

    # Course defaults
    COURSE_MIN_DURATION_MINUTES = 30
    COURSE_MAX_DURATION_MINUTES = 180
    WORDS_PER_MINUTE = 150
    MAX_READING_WORDS = 1200
    MAX_TEXTBOOK_WORDS_PER_OUTCOME = 3000

    # Flask
    PORT = int(os.getenv("PORT", "5003"))
    DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    # Email configuration
    MAIL_SERVER = os.getenv("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.getenv("MAIL_PORT", "25"))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "noreply@coursebuilder.local")
    PASSWORD_RESET_TOKEN_MAX_AGE = int(os.getenv("PASSWORD_RESET_TOKEN_MAX_AGE", "3600"))
    APP_URL = os.getenv("APP_URL", "http://localhost:5003")

    @classmethod
    def ensure_dirs(cls):
        cls.PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        return cls.PROJECTS_DIR

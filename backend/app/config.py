from dotenv import load_dotenv
import os

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Fitness Agent")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fitness_agent.db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Agent SDK runtime configuration
ORCHESTRATOR_MODEL = os.getenv("ORCHESTRATOR_MODEL", "gpt-4.1-mini")
MOOD_AGENT_MODEL = os.getenv("MOOD_AGENT_MODEL", "gpt-4.1-mini")
ACTIVITY_AGENT_MODEL = os.getenv("ACTIVITY_AGENT_MODEL", "gpt-4.1-mini")
SUGGESTION_AGENT_MODEL = os.getenv("SUGGESTION_AGENT_MODEL", "gpt-4.1-mini")
CHALLENGE_AGENT_MODEL = os.getenv("CHALLENGE_AGENT_MODEL", SUGGESTION_AGENT_MODEL)


ORCHESTRATOR_TEMPERATURE = float(os.getenv("ORCHESTRATOR_TEMPERATURE", "0.2"))
MOOD_AGENT_TEMPERATURE = float(os.getenv("MOOD_AGENT_TEMPERATURE", "0.1"))
ACTIVITY_AGENT_TEMPERATURE = float(os.getenv("ACTIVITY_AGENT_TEMPERATURE", "0.1"))
SUGGESTION_AGENT_TEMPERATURE = float(os.getenv("SUGGESTION_AGENT_TEMPERATURE", "0.5"))
CHALLENGE_AGENT_TEMPERATURE = float(os.getenv("CHALLENGE_AGENT_TEMPERATURE", SUGGESTION_AGENT_TEMPERATURE))


ORCHESTRATOR_MAX_TOKENS = int(os.getenv("ORCHESTRATOR_MAX_TOKENS", "500"))
MOOD_AGENT_MAX_TOKENS = int(os.getenv("MOOD_AGENT_MAX_TOKENS", "250"))
ACTIVITY_AGENT_MAX_TOKENS = int(os.getenv("ACTIVITY_AGENT_MAX_TOKENS", "250"))
SUGGESTION_AGENT_MAX_TOKENS = int(os.getenv("SUGGESTION_AGENT_MAX_TOKENS", "350"))
CHALLENGE_AGENT_MAX_TOKENS = int(os.getenv("CHALLENGE_AGENT_MAX_TOKENS", SUGGESTION_AGENT_MAX_TOKENS))

# Mood logging behavior
# If True, only explicit requests like "log my mood" will trigger logging
# If False, any mood expression like "I am sad" will trigger logging
MOOD_REQUIRE_EXPLICIT_INTENT = os.getenv("MOOD_REQUIRE_EXPLICIT_INTENT", "False").lower() == "true"


# Langfuse settings
LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "true").lower() == "true"
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_HOST = os.getenv("LANGFUSE_BASE_URL", os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"))


"""Crayon runtime config. Everything comes from environment variables."""
import os


def env(key, default=""):
    return os.environ.get(key, default)


TELEGRAM_TOKEN = env("TELEGRAM_BOT_TOKEN")
GEMINI_KEY = env("GEMINI_API_KEY")
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_FALLBACKS = [m.strip() for m in env("GEMINI_FALLBACK_MODELS", "gemini-3.1-flash-lite,gemini-3-flash-preview").split(",") if m.strip()]
DATABASE_URL = env("DATABASE_URL")
ADMIN_TOKEN = env("CRAYON_ADMIN_TOKEN")  # guards /selftest, /tick
DEFAULT_TZ = env("CRAYON_TZ", "Asia/Kolkata")
MODE = env("CRAYON_MODE", "polling")  # polling | webhook
PUBLIC_URL = env("CRAYON_PUBLIC_URL", "https://crayon-v1.onrender.com")
HISTORY_TURNS = int(env("CRAYON_HISTORY_TURNS", "14"))
DAILY_MESSAGE_CAP = int(env("CRAYON_DAILY_CAP", "80"))
VERSION = "2.33.1"

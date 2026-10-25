"""Loads prompt files and fills in their {placeholders}."""

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load(name):
    """Read a prompt file, for example load("blog_v1.txt")."""
    return (PROMPTS_DIR / name).read_text(encoding="utf-8")


def fill(template, values):
    """Swap {placeholders} for values. Placeholders not in values stay as they are."""
    text = template
    for key, value in values.items():
        if isinstance(value, list):
            value = "\n".join(f"- {item}" for item in value)
        text = text.replace("{" + key + "}", str(value))
    return text


def brief_values(brief):
    """The placeholder values a brief provides."""
    return {
        "topic": brief["topic"],
        "audience": brief["audience"],
        "offer": brief["offer"],
        "facts": brief["facts"],
        "notes": brief.get("notes") or "none",
    }
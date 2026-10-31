from pathlib import Path

from veil.engine import Settings

DOC = Path(__file__).resolve().parents[3] / "docs" / "settings.md"


def test_the_settings_doc_names_every_setting():
    text = DOC.read_text()

    missing = [name for name in Settings.model_fields if f"`{name}`" not in text]

    assert missing == [], f"Add these settings to docs/settings.md: {missing}"

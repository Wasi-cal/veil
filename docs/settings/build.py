"""Write docs/settings-catalog.md from the declaration of the settings. Run: python docs/settings/build.py"""

from pathlib import Path

from veil.engine import render_settings_catalog

TARGET = Path(__file__).resolve().parents[1] / "settings-catalog.md"

if __name__ == "__main__":
    TARGET.write_text(render_settings_catalog())
    print(f"Wrote {TARGET}")

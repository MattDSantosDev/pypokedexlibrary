from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).parents[1] / "PokePyDex" / "streamlit_app.py"


def test_streamlit_app_starts_without_errors() -> None:
    app = AppTest.from_file(str(APP_PATH), default_timeout=30)
    app.run()

    assert not app.exception
    assert app.title[0].value == "🎮 PokePyDex"
    button_labels = {button.label for button in app.button}
    assert {"🔍 Search", "🔄 Reset"} <= button_labels

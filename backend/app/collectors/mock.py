import json
from pathlib import Path

def collect_mock() -> list[dict]:
    path = Path(__file__).resolve().parents[2] / "data" / "mock_hazards.json"
    return json.loads(path.read_text(encoding="utf-8"))

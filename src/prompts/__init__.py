import json
from pathlib import Path

_DIR = Path(__file__).resolve().parent


def _load_prompt(filename: str) -> str:
    path = _DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["system_prompt"]


SYSTEM_PROMPT_ANSWER = _load_prompt("answer_prompt.json")
SYSTEM_PROMPT_EVAL = _load_prompt("eval_prompt.json")

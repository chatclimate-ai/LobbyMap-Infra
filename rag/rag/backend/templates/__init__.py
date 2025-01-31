from pathlib import Path
import json

TEMPLATE_DIR = Path(__file__).parent


def read_prompt_template(name: str) -> str:
    """Read a template"""

    path = TEMPLATE_DIR / f"{name}.jinja"

    if not path.exists():
        raise ValueError(f"{name} is not a valid template.")

    return path.read_text()


def read_tool(name: str) -> dict:
    """Read a tool"""

    path = TEMPLATE_DIR / f"{name}.json"

    if not path.exists():
        raise ValueError(f"{name} is not a valid tool.")

    with open(path) as f:
        stance_schema = json.load(f)
    
    return stance_schema

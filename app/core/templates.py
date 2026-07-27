from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)


def render_template(name: str, context: dict | None = None) -> str:
    template = _env.get_template(name)
    return template.render(**(context or {}))

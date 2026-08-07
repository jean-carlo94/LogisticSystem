from pathlib import Path

from jinja2 import Environment, FileSystemLoader, SandboxedEnvironment, TemplateSyntaxError

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
_sandbox = SandboxedEnvironment(autoescape=True)


def render_template(name: str, context: dict | None = None) -> str:
    template = _env.get_template(name)
    return template.render(**(context or {}))


def render_template_string(source: str, context: dict | None = None) -> str:
    return _sandbox.from_string(source).render(**(context or {}))


def validate_template_syntax(source: str) -> None:
    try:
        _sandbox.from_string(source)
    except TemplateSyntaxError as e:
        from app.core.exceptions import ValidationException
        raise ValidationException(f"Error de sintaxis en plantilla: {e}")

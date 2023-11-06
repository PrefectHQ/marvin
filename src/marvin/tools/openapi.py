from typing import Optional

import httpx
import yaml
from jinja2 import Template, select_autoescape

from marvin.utilities.strings import jinja_env

jinja_env.autoescape = select_autoescape()

default_template = jinja_env.from_string("""
{%- for path, path_item in openapi_spec["paths"].items() %}
PATH: {{ path }}
{%- for method, operation in path_item.items() %}
  \n- {{ method.upper() }}:
    {%- if operation.get("summary") %}\n Summary: {{ operation["summary"] }}\n{% endif %}
    {%- set required_params = operation.get("parameters") | selectattr("required", "equalto", true) | list %}
    {%- if required_params %}
    Required Parameters:
    {%- for parameter in required_params %}
      \n\t\t- {{ parameter.get("name") }}
    {%- endfor %}
    {% endif %}
{% endfor %}
\n
{% endfor %}
\n
""".strip())  # noqa: E501


async def parse_spec_to_human_readable(
    url: str, template: Optional[Template] = None
) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "yaml" in content_type:
            spec = yaml.safe_load(response.text)
        elif "json" in content_type:
            spec = response.json()
        else:
            raise ValueError("Unsupported specification format (must be YAML or JSON)")

    if template is None:
        template = default_template

    return template.render(openapi_spec=spec)

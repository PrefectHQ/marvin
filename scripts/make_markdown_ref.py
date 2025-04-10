"""
API Documentation Generator using Griffe

Extracts Python module structures and generates well-formatted Markdown documentation.
"""

import json
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, cast

import commentjson
import griffe
from griffe import (
    Class,
    Function,
    Module,
    ObjectKind,
    Parameter,
    ParameterKind,
)


def trim_docstring(docstring: str | None) -> str:
    if not docstring or not docstring.strip():
        return ""

    lines = docstring.expandtabs().splitlines()
    stripped_lines = [line for line in lines if line.strip()]

    if not stripped_lines:
        return ""

    indent = min((len(line) - len(line.lstrip()) for line in stripped_lines), default=0)
    trimmed = [lines[0].lstrip()] + [line[indent:].rstrip() for line in lines[1:]]

    return "\n".join(trimmed).strip()


def format_signature(obj: Function | Class) -> str:
    kind = "class" if isinstance(obj, Class) else "def"
    name = obj.name
    param_strs: list[str] = []

    parameters: list[Parameter] = []
    if isinstance(obj, Function):
        parameters = obj.parameters  # type: ignore
    elif isinstance(obj, Class):  # type: ignore
        init_method = obj.members.get("__init__")
        if init_method and isinstance(init_method, Function):
            parameters = init_method.parameters  # type: ignore

    skip_init_self = isinstance(obj, Class)

    for i, param in enumerate(parameters):
        if skip_init_self and i == 0:
            continue

        param_str = param.name

        if param.annotation:
            annotation_str = (
                str(param.annotation).replace("<", "&lt;").replace(">", "&gt;")
            )
            param_str += f": {annotation_str}"

        if param.default:
            param_str += f" = {param.default}"

        if param.kind == ParameterKind.var_positional:
            param_str = f"*{param_str}"
        elif param.kind == ParameterKind.var_keyword:
            param_str = f"**{param_str}"

        param_strs.append(param_str)

    return_annotation = ""
    if isinstance(obj, Function) and obj.returns:
        ret_ann_str = str(obj.returns).replace("<", "&lt;").replace(">", "&gt;")
        if ret_ann_str != "None":
            return_annotation = f" -> {ret_ann_str}"

    return f"{kind} {name}({', '.join(param_strs)}){return_annotation}"


def generate_module_docs(module: Module, output_dir: Path) -> str | None:
    module_name = module.canonical_path

    # Skip modules that are private or the top-level package itself
    if module.name.startswith("_") or (module.is_package and module.name == "marvin"):
        return None

    print(f"Processing module: {module_name}")

    # Create filename from module path
    relative_path_parts = module_name.split(".")
    md_filename = "-".join(relative_path_parts) + ".mdx"
    md_path = output_dir / md_filename
    md_path.parent.mkdir(parents=True, exist_ok=True)

    # Determine page title from the last part of the module name
    page_title = module_name.split(".")[-1]

    # Prepare frontmatter (ensure correct YAML format)
    frontmatter = f"---\ntitle: {page_title}\n---"

    content = [frontmatter, f"\n# `{module_name}`"]

    module_doc = trim_docstring(module.docstring.value if module.docstring else None)
    if module_doc:
        content.append(module_doc)

    classes: list[Class] = []
    functions: list[Function] = []

    for name, member in module.members.items():
        if name.startswith("_") and name != "__init__":
            continue
        if member.is_alias:
            continue

        if member.kind == ObjectKind.CLASS:
            classes.append(cast(Class, member))
        elif member.kind == ObjectKind.FUNCTION:
            functions.append(cast(Function, member))

    if classes:
        content.append("\n## Classes")
        for cls in sorted(classes, key=lambda c: c.name):
            content.append(f"\n### `{cls.name}`")
            content.append(f"```python\n{format_signature(cls)}\n```")

            class_doc = trim_docstring(cls.docstring.value if cls.docstring else None)
            if class_doc:
                content.append(class_doc)

            methods = [
                m
                for name, m in cls.members.items()
                if not name.startswith("_") and isinstance(m, Function)
            ]

            if methods:
                content.append("\n**Methods:**\n")
                for method in sorted(methods, key=lambda m: m.name):
                    content.append(f"- **`{method.name}`**")
                    content.append(f"  ```python\n  {format_signature(method)}\n  ```")

                    method_doc = trim_docstring(
                        method.docstring.value if method.docstring else None
                    )
                    if method_doc:
                        indented_doc = "\n".join(
                            f"  {line}" for line in method_doc.splitlines()
                        )
                        content.append(indented_doc)

    if functions:
        content.append("\n## Functions")
        for func in sorted(functions, key=lambda f: f.name):
            content.append(f"\n### `{func.name}`")
            content.append(f"```python\n{format_signature(func)}\n```")

            func_doc = trim_docstring(func.docstring.value if func.docstring else None)
            if func_doc:
                content.append(func_doc)

    # Check if any actual content was generated besides the title
    has_public_content = bool(classes or functions or module_doc)

    if not has_public_content:
        content.append(
            "\n*No public API documentation found for this module. Please consider contributing documentation or [opening an issue](https://github.com/prefectHQ/marvin/issues/new).*"
        )

    # Always write the file now (unless skipped earlier)
    md_path.write_text("\n".join(content) + "\n", encoding="utf-8")
    return md_path.relative_to(output_dir.parent).as_posix()


def group_markdown_files(md_files: list[str]) -> list[dict[str, Any]]:
    # Group pages by their dotted module path, maintaining the original schema
    # Desired output structure: [{'group': 'marvin.agents', 'pages': ['api-reference/marvin-agents']}]
    grouped_pages: defaultdict[str, list[str]] = defaultdict(list)

    for file_path in sorted(md_files):
        path_obj = Path(file_path)
        stem = path_obj.stem

        dotted_path_group = stem.replace("-", ".")

        # Use the original page reference format (path without extension)
        page_ref = path_obj.with_suffix("").as_posix()
        grouped_pages[dotted_path_group].append(page_ref)

    return [
        {"group": group, "pages": sorted(pages)}
        for group, pages in sorted(grouped_pages.items())
    ]


def update_navigation(docs_json_path: Path, md_files: list[str]) -> bool:
    if not md_files:
        print("No markdown files generated.")
        return False

    try:
        with open(docs_json_path, "r", encoding="utf-8") as f:
            docs_config = cast(dict[str, Any], commentjson.load(f))  # type: ignore

        navigation_groups = group_markdown_files(md_files)

        found_anchor = False
        if "navigation" in docs_config and "anchors" in docs_config["navigation"]:
            for anchor in docs_config["navigation"]["anchors"]:
                if not isinstance(anchor, dict):
                    continue

                if anchor["anchor"] == "API Reference":
                    found_anchor = True
                    anchor.pop("openapi", None)  # type: ignore
                    anchor.pop("pages", None)  # type: ignore
                    anchor["groups"] = navigation_groups
                    print(f"Updated API Reference anchor in {docs_json_path}")
                    break

        if not found_anchor:
            print(f"API Reference anchor not found in {docs_json_path}")
            return False

        with open(docs_json_path, "w", encoding="utf-8") as f:
            json.dump(docs_config, f, indent=4, ensure_ascii=False)
            f.write("\n")

        print(f"Updated {docs_json_path}")
        return True

    except Exception as e:
        print(f"Error updating {docs_json_path}: {e}")
        return False


def main() -> None:
    docs_dir = Path("docs")
    api_ref_dir = docs_dir / "api-reference"
    docs_json_file = docs_dir / "docs.json"
    package_name = "marvin"

    print(f"Generating API docs for '{package_name}' in {api_ref_dir}")
    api_ref_dir.mkdir(parents=True, exist_ok=True)

    try:
        package_data = griffe.load(package_name)
    except ImportError as e:
        print(f"Error loading '{package_name}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    generated_files: list[str] = []

    with ThreadPoolExecutor() as executor:
        futures_map = {
            executor.submit(generate_module_docs, module, api_ref_dir): module_path
            for module_path, module in package_data.modules.items()
        }

        for future in as_completed(futures_map):
            module_path = futures_map[future]
            try:
                if result := future.result():
                    generated_files.append(result)
            except Exception as e:
                print(f"Error processing {module_path}: {e}")

    if generated_files:
        update_navigation(docs_json_file, generated_files)
        print(f"Generated {len(generated_files)} documentation files")
    else:
        print("No documentation files generated")


if __name__ == "__main__":
    main()

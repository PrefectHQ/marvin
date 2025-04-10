"""
Complete API Documentation Generator using Griffe

Extracts Python module structures and generates well-formatted Markdown documentation
for all modules, submodules, and individual Python files.
"""

import argparse
import importlib
import json
import pkgutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

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
    elif hasattr(obj, "members"):
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


def get_module_file_type(module_path: str) -> str:
    parts = module_path.split(".")
    if parts[-1] == "__init__":
        return "package"
    return "file"


def get_parent_module(module_path: str) -> str:
    parts = module_path.split(".")
    if len(parts) <= 1:
        return ""
    if parts[-1] == "__init__":
        return ".".join(parts[:-2]) if len(parts) > 2 else ""
    return ".".join(parts[:-1])


def find_all_modules(package_name: str) -> list[str]:
    """
    Find all modules in the package including both submodules and direct files.
    Uses pkgutil.walk_packages to discover all submodules recursively.
    Also explicitly checks for standalone .py files in the top-level package directory.
    """
    try:
        package = importlib.import_module(package_name)
        modules: list[str] = []

        # Get the package path
        if hasattr(package, "__path__"):
            package_path = package.__path__
        else:
            return []

        # Find all modules recursively using pkgutil
        for _, module_name, _ in pkgutil.walk_packages(
            package_path, package_name + "."
        ):
            if "._" in module_name or module_name.startswith("_"):
                continue

            modules.append(module_name)

        # Always include the base package itself
        if package_name not in modules:
            modules.append(package_name)

        return sorted(modules)
    except Exception as e:
        print(f"Error finding modules: {e}")
        return []


def get_module_title(module_path: str, default_package_name: str) -> str:
    parts = module_path.split(".")

    if parts[-1] == "__init__":
        return parts[-2] if len(parts) > 1 else default_package_name

    return parts[-1]


def module_path_to_file_path(module_path: str) -> str:
    """Convert a module path to a documentation file path."""
    if module_path.endswith(".__init__"):
        module_path = module_path[:-9]

    return module_path.replace(".", "-") + ".mdx"


def create_link(module_path: str) -> str:
    """Create a link to a module's documentation."""
    if module_path.endswith(".__init__"):
        module_path = module_path[:-9]

    return module_path.replace(".", "-")


def generate_module_docs(
    module: Module,
    output_dir: Path,
    all_module_paths: list[str],
    default_package_name: str,
) -> str | None:
    """Generate documentation for a single module."""
    module_path = module.canonical_path

    if "._" in module_path:
        return None

    md_filename = module_path_to_file_path(module_path)
    md_path = output_dir / md_filename
    md_path.parent.mkdir(parents=True, exist_ok=True)

    page_title = get_module_title(module_path, default_package_name)
    page_description = ""

    module_doc = trim_docstring(module.docstring.value if module.docstring else None)
    if module_doc:
        first_line = module_doc.split("\n")[0].strip()
        if first_line:
            page_description = first_line.replace('"', "'")

    content_sections: list[str] = []
    if module_doc:
        content_sections.append(module_doc)

    # Find direct submodules (not just immediate children)
    submodules: list[str] = []
    base_prefix = module_path + "."
    for m in all_module_paths:
        if m != module_path and m.startswith(base_prefix) and "._" not in m:
            # Get the next segment after the module_path
            remainder = m[len(base_prefix) :].split(".", 1)[0]
            submodule = f"{module_path}.{remainder}"
            if submodule not in submodules:
                submodules.append(submodule)

    submodules.sort()

    if submodules:
        content_sections.append("\n## Submodules")
        submodule_links: list[str] = []
        for submodule_path in submodules:
            submodule_name = submodule_path.split(".")[-1]
            submodule_link = create_link(submodule_path)
            submodule_links.append(f"- [`{submodule_name}`]({submodule_link})")
        content_sections.append("\n".join(submodule_links))

    classes: list[Class] = []
    functions: list[Function] = []
    constants: list[tuple[str, Any, Any]] = []  # (name, value, member) tuples

    for name, member in module.members.items():
        if name.startswith("_") and name != "__init__":
            continue
        if member.is_alias:
            continue

        if member.kind == ObjectKind.CLASS:
            classes.append(cast(Class, member))
        elif member.kind == ObjectKind.FUNCTION:
            functions.append(cast(Function, member))
        # Check for constants (uppercase variables)
        elif name.isupper():
            # Try to get the value directly
            try:
                value = getattr(member, "value", None)
                constants.append((name, value, member))
            except Exception:
                # If that fails, just add the name
                constants.append((name, None, member))

    # Add constants section
    if constants:
        content_sections.append("\n## Constants")
        for name, value, member_obj in sorted(constants):
            content_sections.append(f"\n### `{name}`")
            # Format the value as code
            try:
                # Try to format the value neatly
                if isinstance(value, str):
                    value_str = f'"{value}"'
                elif value is not None:
                    value_str = str(value)
                else:
                    value_str = "None"
                content_sections.append(f"```python\n{name} = {value_str}\n```")
            except Exception:
                # Fallback if we can't format the value
                content_sections.append(f"```python\n{name}\n```")

            # Try to add docstring if available
            try:
                if hasattr(member_obj, "docstring") and member_obj.docstring:
                    docstring_value = getattr(member_obj.docstring, "value", None)
                    if docstring_value:
                        const_doc = trim_docstring(docstring_value)
                        if const_doc:
                            content_sections.append(const_doc)
            except Exception:
                # Skip docstring if we can't get it
                pass

    if classes:
        content_sections.append("\n## Classes")
        for cls in sorted(classes, key=lambda c: c.name):
            content_sections.append(f"\n### `{cls.name}`")
            content_sections.append(f"```python\n{format_signature(cls)}\n```")

            class_doc = trim_docstring(cls.docstring.value if cls.docstring else None)
            if class_doc:
                content_sections.append(class_doc)

            methods = [
                m
                for name, m in cls.members.items()
                if not name.startswith("_") and isinstance(m, Function)
            ]

            if methods:
                content_sections.append("\n**Methods:**\n")
                for method in sorted(methods, key=lambda m: m.name):
                    content_sections.append(f"- **`{method.name}`**")
                    content_sections.append(
                        f"  ```python\n  {format_signature(method)}\n  ```"
                    )

                    method_doc = trim_docstring(
                        method.docstring.value if method.docstring else None
                    )
                    if method_doc:
                        indented_doc = "\n".join(
                            f"  {line}" for line in method_doc.splitlines()
                        )
                        content_sections.append(indented_doc)

    if functions:
        content_sections.append("\n## Functions")
        for func in sorted(functions, key=lambda f: f.name):
            content_sections.append(f"\n### `{func.name}`")
            content_sections.append(f"```python\n{format_signature(func)}\n```")

            func_doc = trim_docstring(func.docstring.value if func.docstring else None)
            if func_doc:
                content_sections.append(func_doc)

    if not (module_doc or classes or functions or submodules or constants):
        content_sections.append(
            "\n*No public API documentation found for this module.*"
        )

    parent_module = get_parent_module(module_path)
    if parent_module:
        parent_link = create_link(parent_module)
        parent_name = parent_module.split(".")[-1]
        content_sections.append(
            f"\n---\n\n**Parent Module:** [`{parent_name}`]({parent_link})"
        )

    frontmatter = f"""---
title: {page_title}
"""
    if page_description:
        frontmatter += f'description: "{page_description}"\n'
    frontmatter += "---"

    display_module_path = module_path
    if display_module_path.endswith(".__init__"):
        display_module_path = display_module_path[:-9]

    final_content = [frontmatter, f"\n# `{display_module_path}`"] + content_sections

    md_path.write_text("\n".join(final_content) + "\n", encoding="utf-8")
    return md_path.relative_to(output_dir.parent).as_posix()


def organize_navigation(
    generated_files: list[str], package_name: str
) -> list[dict[str, Any]]:
    """
    Organize files into navigation groups by their top-level module.
    Each top-level module gets its own group with all its submodules.
    """
    path_to_module: dict[str, str] = {}

    for file_path in sorted(generated_files):
        path_obj = Path(file_path)
        module_path = path_obj.stem.replace("-", ".")
        path_to_module[file_path] = module_path

    top_level_groups: dict[str, list[str]] = defaultdict(list)

    for file_path, module_path in path_to_module.items():
        parts = module_path.split(".")

        if len(parts) > 1:
            # For marvin.X.Y.Z, the group is X
            group_name = parts[1]
            # Convert to file path without extension
            page_path = file_path.replace(".mdx", "")
            top_level_groups[group_name].append(page_path)
        elif len(parts) == 1 and parts[0] == package_name:
            # The main module goes to "top level"
            top_level_groups["top level"].append(file_path.replace(".mdx", ""))

    # Clean up the navigation structure to avoid duplicates
    result: list[dict[str, Any]] = []

    # First add the "top level" group if it exists
    if "top level" in top_level_groups:
        filtered_pages: list[str] = []
        for page in sorted(top_level_groups["top level"]):
            page_module = Path(page).stem.replace("-", ".")
            parts = page_module.split(".")

            # Skip if this page is the parent module itself (shouldn't happen for top level)
            if len(parts) == 2 and parts[1] == "top level":
                continue

            filtered_pages.append(page)

        result.append({"group": "top level", "pages": filtered_pages})

        # Remove the top level group so it's not added again
        top_level_groups.pop("top level")

    # Then add all other groups in alphabetical order
    for group_name, pages in sorted(top_level_groups.items()):
        filtered_pages: list[str] = []
        for page in sorted(pages):
            page_module = Path(page).stem.replace("-", ".")
            parts = page_module.split(".")

            # Skip if this page is the parent module itself
            if len(parts) == 2 and parts[1] == group_name:
                continue

            filtered_pages.append(page)

        result.append({"group": group_name, "pages": filtered_pages})

    return result


def update_navigation(
    docs_json_path: Path, generated_files: list[str], package_name: str
) -> bool:
    """Update the navigation structure in docs.json."""
    if not generated_files:
        print("No markdown files generated.")
        return False

    try:
        try:
            import commentjson

            with open(docs_json_path, "r", encoding="utf-8") as f:
                docs_config = commentjson.load(f)  # type: ignore
        except ImportError:
            with open(docs_json_path, "r", encoding="utf-8") as f:
                docs_config = json.load(f)
                print("Warning: Using standard JSON parser - comments may be lost.")

        navigation_groups = organize_navigation(generated_files, package_name)

        found_anchor = False
        if "navigation" in docs_config and "anchors" in docs_config["navigation"]:
            for anchor in docs_config["navigation"]["anchors"]:
                if not isinstance(anchor, dict):
                    continue

                if TYPE_CHECKING:
                    anchor = cast(dict[str, Any], anchor)

                if anchor.get("anchor") == "API Reference":
                    found_anchor = True
                    if "openapi" in anchor:
                        anchor.pop("openapi")
                    if "pages" in anchor:
                        anchor.pop("pages")
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
    parser = argparse.ArgumentParser(
        description="Generate API documentation for a package"
    )
    parser.add_argument("--package", default="marvin", type=str, help="Package name")
    parser.add_argument(
        "--default-package-name",
        default="marvin",
        type=str,
        help="Default package name",
    )
    parser.add_argument("--docs-dir", type=Path, default="docs", help="Docs directory")
    parser.add_argument("--src-dir", type=Path, default="src", help="Src directory")
    parser.add_argument(
        "--docs-json-file", type=Path, default="docs/docs.json", help="Docs JSON file"
    )
    parser.add_argument(
        "--api-ref-dir",
        type=Path,
        default="docs/api-reference",
        help="API Reference directory",
    )

    args = parser.parse_args()
    package_name = args.package
    src_dir = args.src_dir
    api_ref_dir = args.api_ref_dir
    docs_json_file = args.docs_json_file
    default_package_name = args.default_package_name

    print(f"Generating API documentation for '{package_name}' in {api_ref_dir}")
    api_ref_dir.mkdir(parents=True, exist_ok=True)

    if src_dir.exists() and (src_dir / package_name).is_dir():
        print(f"Using src layout for {package_name}")
        sys.path.insert(0, str(src_dir.absolute()))

    try:
        all_module_paths = find_all_modules(package_name)
        print(f"Found {len(all_module_paths)} modules")

        modules_data: dict[str, Module] = {}

        for module_path in all_module_paths:
            try:
                module_obj = griffe.load(module_path)
                if hasattr(module_obj, "kind") and module_obj.kind == ObjectKind.MODULE:
                    modules_data[module_path] = cast(Module, module_obj)
            except Exception:
                init_path = f"{module_path}.__init__"
                try:
                    init_module = griffe.load(init_path)
                    if (
                        hasattr(init_module, "kind")
                        and init_module.kind == ObjectKind.MODULE
                    ):
                        modules_data[init_path] = cast(Module, init_module)
                except Exception:
                    print(f"Failed to load {init_path}")
                    pass

        print(f"Loaded {len(modules_data)} modules")

    except ImportError as e:
        print(f"Error loading '{package_name}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print("Generating documentation...")
    generated_files: list[str] = []

    for module_path, module_obj in modules_data.items():
        if module_path.endswith(".__init__"):
            continue

        if result := generate_module_docs(
            module_obj,
            api_ref_dir,
            all_module_paths,
            default_package_name,
        ):
            generated_files.append(result)

    for module_path, module_obj in modules_data.items():
        if not module_path.endswith(".__init__"):
            continue

        package_path = module_path[:-9]
        if package_path not in modules_data:
            if result := generate_module_docs(
                module_obj,
                api_ref_dir,
                all_module_paths,
                default_package_name,
            ):
                generated_files.append(result)

    if generated_files:
        update_navigation(docs_json_file, generated_files, package_name)
        print(f"Generated {len(generated_files)} documentation files")
    else:
        print("No documentation files generated")


if __name__ == "__main__":
    main()

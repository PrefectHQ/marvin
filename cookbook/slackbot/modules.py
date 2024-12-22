import importlib
import inspect
import pkgutil
from types import ModuleType
from typing import Any


class ModuleTreeExplorer:
    def __init__(self, root_module_path: str, max_depth: int = 2):
        """
        Initialize the module tree explorer with a root module path.

        Args:
            root_module_path: String representing the root module (e.g., 'prefect.runtime')
            max_depth: Maximum depth to explore in the module tree (default: 2)
        """
        self.root_module_path = root_module_path
        self.max_depth = max_depth
        self.tree = {}

    def _import_module(self, module_path: str) -> ModuleType | None:
        """Safely import a module.

        Args:
            module_path: String representing the module path (e.g., 'prefect.runtime')
        """
        try:
            return importlib.import_module(module_path)
        except (ImportError, TypeError) as e:
            print(f"Warning: Could not import {module_path}: {e}")
            return None

    def _is_defined_in_module(self, item: Any, current_module: str) -> bool:
        """Check if an item is defined in the current module.

        Args:
            item: The item to check
            current_module: The current module path
        """
        try:
            if inspect.ismodule(item):
                return False

            # Get the module where this item is defined
            if hasattr(item, "__module__"):
                return item.__module__ == current_module

            return False
        except Exception:
            return False

    def _get_module_public_api(
        self, module: ModuleType, module_path: str | None = None
    ) -> dict[str, list[str]]:
        """Get the public API of a module.

        Args:
            module: The module to get the public API of
            module_path: The path of the module (e.g., 'prefect.runtime')
        """
        api = {"all": [], "classes": [], "functions": [], "constants": []}

        try:
            if hasattr(module, "__all__"):
                api["all"] = list(module.__all__)
                items = {
                    name: getattr(module, name, None)
                    for name in module.__all__
                    if hasattr(module, name)
                }
            else:
                # Get non-underscore attributes
                items = {
                    name: getattr(module, name, None)
                    for name in dir(module)
                    if not name.startswith("_")
                }

            # Categorize items that we can safely inspect and are defined in our module
            module_name = module_path or module.__name__
            for name, item in items.items():
                try:
                    if item is not None and self._is_defined_in_module(
                        item, module_name
                    ):
                        if inspect.isclass(item):
                            api["classes"].append(name)
                        elif inspect.isfunction(item):
                            api["functions"].append(name)
                        elif not inspect.ismodule(item):
                            api["constants"].append(name)
                except (TypeError, ValueError):
                    # Skip items we can't properly inspect
                    continue

        except Exception as e:
            print(f"Warning: Error inspecting module {module.__name__}: {e}")

        return api

    def _explore_submodules(
        self, module: ModuleType, current_depth: int = 0
    ) -> dict[str, Any]:
        """Recursively explore submodules and their APIs.

        Args:
            module: The module to explore
            current_depth: The current depth of the exploration
        """
        result = {
            "api": self._get_module_public_api(module, module.__name__),
            "submodules": {},
        }

        if current_depth < self.max_depth:
            try:
                if hasattr(module, "__path__"):
                    for _, name, _ in pkgutil.iter_modules(module.__path__):
                        try:
                            full_name = f"{module.__name__}.{name}"
                            submodule = self._import_module(full_name)
                            if submodule:
                                result["submodules"][name] = self._explore_submodules(
                                    submodule, current_depth + 1
                                )
                        except Exception as e:
                            print(f"Warning: Error exploring submodule {name}: {e}")
                            continue
            except Exception as e:
                print(
                    f"Warning: Error accessing module path for {module.__name__}: {e}"
                )

        return result

    def explore(self) -> dict[str, Any]:
        """Explore the module tree starting from the root module.

        Returns:
            dict[str, Any]: The explored module tree
        """
        root_module = self._import_module(self.root_module_path)
        if root_module:
            self.tree = self._explore_submodules(root_module)
        return self.tree

    def get_tree_string(
        self, tree: dict[str, Any] | None = None, prefix: str = "", is_last: bool = True
    ) -> str:
        """Generate the module tree as a string in a hierarchical format.

        Args:
            tree: The module tree to generate a string for
            prefix: The prefix to use for the tree
            is_last: Whether the current module is the last in its parent
        """
        lines = []
        if tree is None:
            tree = self.tree
            lines.append(f"📦 {self.root_module_path}")

        api = tree.get("api", {})
        indent = "    " if is_last else "│   "

        # Add public API categories
        if api.get("all"):
            lines.append(
                f"{prefix}{'└── ' if is_last else '├── '}📜 __all__: {', '.join(api['all'])}"
            )

        for category, items in api.items():
            if category != "all" and items:
                lines.append(
                    f"{prefix}{'└── ' if is_last and not tree['submodules'] else '├── '}"
                    f"{'🔷' if category == 'classes' else '⚡' if category == 'functions' else '📌'} "
                    f"{category}: {', '.join(sorted(items))}"
                )

        # Add submodules
        submodules = tree.get("submodules", {})
        for idx, (name, subtree) in enumerate(submodules.items()):
            is_last_module = idx == len(submodules) - 1
            lines.append(f"{prefix}{'└── ' if is_last_module else '├── '}📦 {name}")
            lines.extend(
                self.get_tree_string(
                    subtree, prefix + indent, is_last_module
                ).splitlines()
            )

        return "\n".join(lines)

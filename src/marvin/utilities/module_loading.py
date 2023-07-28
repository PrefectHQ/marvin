import sys
from importlib import import_module


def cached_import(module_path, class_name):
    """
    This function checks if the module is already imported and if it is,
    it returns the class. Otherwise, it imports the module and returns the class.
    """

    # Check if the module is already imported
    module = sys.modules.get(module_path, None)
    module_already_loaded = (
        module
        and getattr(sys.modules[module_path], "__spec__", False)
        and getattr(sys.modules[module_path].__spec__, "_initializing", False) is False
    )
    if not module_already_loaded:
        module = import_module(module_path)
    else:
        return getattr(sys.modules[module], class_name)


def import_string(path: str):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import failed.
    """
    try:
        path_, class_ = path.rsplit(".", 1)
    except ValueError as err:
        raise ImportError("%s doesn't look like a module path" % path) from err
    try:
        return cached_import(path_, class_)
    except AttributeError as err:
        raise ImportError(f"Module '{path_}' isn't a '{class_}' attr/class") from err

import sys

if sys.platform == "win32" and sys.version_info > (3, 10):
    import collections.abc

    # Create a new module to replace the collections module
    class ShimModule:
        def __init__(self, original_module):
            self.__original_module = original_module

        def __getattr__(self, name):
            if name == "Callable":
                return collections.abc.Callable
            return getattr(self.__original_module, name)

    # Replace the collections module in sys.modules with the shim
    sys.modules["collections"] = ShimModule(sys.modules["collections"])

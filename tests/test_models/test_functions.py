class TestFunctions:
    def test_signature(self):
        import inspect

        from marvin.functions import Function

        def fn(x: int, y: int = 10) -> int:
            return x + y

        f = Function(fn=fn)
        assert f.signature == inspect.signature(fn)

    def test_name(self):
        from marvin.functions import Function

        def fn(x: int, y: int = 10) -> int:
            return x + y

        f = Function(fn=fn)
        assert f.name == fn.__name__

    def test_name_custom(self):
        from marvin.functions import Function

        def fn(x: int, y: int = 10) -> int:
            return x + y

        f = Function(fn=fn, name="custom")
        assert f.name == "custom"

    def test_description(self):
        from marvin.functions import Function

        def fn(x: int, y: int = 10) -> int:
            """This is a description"""
            return x + y

        f = Function(fn=fn)
        assert f.description == fn.__doc__

    def test_description_custom(self):
        from marvin.functions import Function

        def fn(x: int, y: int = 10) -> int:
            """This is a description"""
            return x + y

        f = Function(fn=fn, description="custom")
        assert f.description == "custom"

    def test_source_code(self):
        import inspect

        from marvin.functions import Function

        def fn(x: int, y: int = 10) -> int:
            return x + y

        f = Function(fn=fn)
        assert f.source_code == inspect.cleandoc(inspect.getsource(fn))

    def test_return_annotation_native(self):
        import inspect

        from marvin.functions import Function

        def fn(x: int, y: int = 10) -> int:
            return x + y

        f = Function(fn=fn)
        assert f.return_annotation == inspect.signature(fn).return_annotation

    def test_return_annotation_pydantic(self):
        from marvin.functions import Function
        from pydantic import BaseModel

        class Foo(BaseModel):
            foo: int
            bar: int

        def fn(x: int, y: int = 10) -> Foo:
            return Foo(foo=x, bar=y)

        f = Function(fn=fn)
        assert f.return_annotation == Foo

    def test_arguments(self):
        from marvin.functions import Function

        def fn(x: int, y: int = 10) -> int:
            return x + y

        f = Function(fn=fn)
        assert f.arguments(1) == {"x": 1, "y": 10}

    def test_schema(self):
        from marvin.functions import Function

        def fn(x: int, y: int = 10) -> int:
            return x + y

        f = Function(fn=fn)
        assert f.schema() == {
            "name": "fn",
            "description": fn.__doc__,
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "title": "X"},
                    "y": {"type": "integer", "title": "Y", "default": 10},
                },
                "required": ["x"],
            },
        }

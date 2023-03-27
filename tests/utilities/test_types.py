import marvin
import pytest
from marvin.models.documents import Document
from marvin.utilities.strings import hash_text
from marvin.utilities.types import MarvinBaseModel


class TestHashing:
    @pytest.fixture
    def document(self):
        return Document(text="Hello World", metadata={"foo": "bar"})

    def test_hashing_is_deterministic(self, document):
        assert hash_text(document.text) == hash_text(document.text)


class TestDiscriminatedUnions:
    def test_discriminated_unions_are_deserialized_correctly(self):
        class Parent(marvin.utilities.types.DiscriminatedUnionType):
            a: int

        class Child1(Parent):
            pass

        class Child2(Parent):
            pass

        class Child3(Child2):
            pass

        class MyObject(MarvinBaseModel):
            val: Parent
            list_val: list[Parent]
            nested_list_val: list[list[Parent]]
            dict_val: dict[str, Parent]
            list_dict_val: list[dict[str, Parent]]
            dict_list_val: dict[str, list[Parent]]

        obj = MyObject(
            val=Child1(a=1),
            list_val=[Parent(a=0), Child1(a=1), Child2(a=2)],
            nested_list_val=[[Child1(a=1), Child2(a=2)], [Child3(a=3)]],
            dict_val={"a": Child1(a=1), "b": Child2(a=2)},
            list_dict_val=[{"a": Child1(a=1), "b": Child2(a=2)}],
            dict_list_val={"a": [Child1(a=1), Child2(a=2)], "b": [Child3(a=3)]},
        )

        obj_dict = obj.dict()

        deserialized = MyObject(**obj_dict)

        # all objects were properly deserialized
        assert deserialized.val == obj.val
        assert deserialized.list_val == obj.list_val
        assert deserialized.nested_list_val == obj.nested_list_val
        assert deserialized.dict_val == obj.dict_val
        assert deserialized.list_dict_val == obj.list_dict_val
        assert deserialized.dict_list_val == obj.dict_list_val

    def test_du_members_can_be_generated_after_a_class_that_references_parent(
        self,
    ):
        class Parent(marvin.utilities.types.DiscriminatedUnionType):
            a: int

        class MyObject(MarvinBaseModel):
            list_val: list[Parent]

        class Child1(Parent):
            pass

        class Child2(Parent):
            pass

        obj = MyObject(
            list_val=[Parent(a=0), Child1(a=1), Child2(a=2)],
        )

        obj_dict = obj.dict()

        deserialized = MyObject(**obj_dict)

        # all objects were properly deserialized
        assert deserialized.list_val == obj.list_val

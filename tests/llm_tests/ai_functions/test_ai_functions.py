from typing import Optional

import marvin
import pydantic
import pytest
from marvin import ai_fn
from marvin.ai_functions import AIFunction
from marvin.utilities.tests import assert_llm


class TestAIFunctions:
    def test_rng(self):
        @ai_fn
        def rng() -> float:
            """generate a random number between 0 and 1"""

        x = rng()
        assert isinstance(x, float)
        assert 0 <= x <= 1

    def test_rng_with_limits(self):
        @ai_fn
        def rng(min: float, max: float) -> float:
            """generate a random number between min and max"""

        x = rng(20, 21)
        assert 20 <= x <= 21

    @pytest.mark.xfail(reason="GPT-3.5 fails on this sometimes")
    def test_spellcheck(self):
        @ai_fn
        def spellcheck(word: str) -> str:
            """spellcheck a word and return the correct spelling"""

        assert spellcheck("speling") == "spelling"
        assert spellcheck("spelling") == "spelling"
        assert spellcheck("spellling") == "spelling"

    def test_list_of_fruits(self):
        @ai_fn
        def list_fruits(n: int) -> list[str]:
            """generate a list of n fruits"""

        x = list_fruits(3)
        assert isinstance(x, list)
        assert len(x) == 3
        assert all(isinstance(fruit, str) for fruit in x)
        assert_llm(x, "a list of fruits")

    def test_list_of_fruits_calling_ai_fn_with_no_args(self):
        @ai_fn()
        def list_fruits(n: int) -> list[str]:
            """generate a list of n fruits"""

        x = list_fruits(3)
        assert isinstance(x, list)
        assert len(x) == 3
        assert all(isinstance(fruit, str) for fruit in x)
        assert_llm(x, "a list of fruits")

    def test_generate_fake_people_data(self):
        @ai_fn
        def fake_people(n: int) -> list[dict]:
            """
            Generates n examples of fake data representing people,
            each with a name and an age.
            """

        x = fake_people(3)
        assert isinstance(x, list)
        assert len(x) == 3
        assert all(isinstance(person, dict) for person in x)
        assert all("name" in person for person in x)
        assert all("age" in person for person in x)
        assert_llm(x, "a list of people data including name and age")

    def test_generate_rhyming_words(self, gpt_4):
        @ai_fn
        def rhymes(word: str) -> str:
            """generate a word that rhymes with the given word"""

        x = rhymes("blue")
        assert isinstance(x, str)
        assert x != "blue"
        assert_llm(x, 'rhymes with "blue"')

    def test_generate_rhyming_words_with_n(self, gpt_4):
        @ai_fn
        def rhymes(word: str, n: int) -> list[str]:
            """generate a word that rhymes with the given word"""

        x = rhymes("blue", 3)
        assert isinstance(x, list)
        assert len(x) == 3
        assert all(isinstance(word, str) for word in x)
        assert all(word != "blue" for word in x)
        assert_llm(
            x,
            "the output is a list of words, each one rhyming with 'blue'.",
        )


class TestBool:
    def test_bool_response(self):
        @ai_fn
        def is_blue(word: str) -> bool:
            """returns True if the word is blue"""

        x = is_blue("blue")
        assert isinstance(x, bool)
        assert x is True

        y = is_blue("green")
        assert isinstance(y, bool)
        assert y is False

    def test_bool_response_issue_55(self):
        # hinting `True` or `False` in a nested bool broke JSON parsing that
        # expected lowercase
        @ai_fn
        def classify_sentiment(messages: list[str]) -> list[bool]:
            """
            Given a list of messages, classifies each one as
            positive (True) or negative (False) and returns
            a corresponding list
            """

        result = classify_sentiment(["i love pizza", "i hate pizza"])
        assert result == [True, False]

    def test_extract_sentences_with_question_mark(self):
        @ai_fn
        def list_questions(email_body: str) -> list[str]:
            """
            Returns a list of any questions in the email body.
            """

        email_body = "Hi Taylor, It is nice outside today. What is your favorite color?"
        x = list_questions(email_body)
        assert x == ["What is your favorite color?"]

    def test_json_return_with_str_annotation_is_str(self):
        @ai_fn
        def build_json() -> str:
            """
            Always returns JSON: `{"a": 1}`
            """

        x = build_json()
        assert x == '{"a": 1}'

    def test_functions_are_not_run(self):
        @ai_fn
        def number_one() -> int:
            """
            Always returns 1
            """
            raise ValueError("This will not be raised")

        result = number_one()
        assert result == 1

    def test_generators_are_run(self):
        @ai_fn
        def number_one() -> int:
            """
            Always returns 1
            """
            raise ValueError("This will be raised")
            yield

        with pytest.raises(ValueError, match="(This will be raised)"):
            number_one()

    async def test_async_generators_are_run(self):
        @ai_fn
        async def number_one() -> int:
            """
            Always returns 1
            """
            raise ValueError("This will be raised")
            yield

        with pytest.raises(ValueError, match="(This will be raised)"):
            number_one()

    def test_yield_from_function(self):
        # assign p outside the function source code
        p = 99

        @ai_fn
        def yielding_fn() -> int:
            """
            Returns -1 * a number generated at runtime.
            """
            yield p

        result = yielding_fn()
        assert result == -1 * p


class TestContainers:
    """tests untyped containers"""

    def test_dict(self):
        @ai_fn
        def dict_response() -> dict:
            """
            Returns a dictionary that contains
                - name: str
                - age: int
            """

        response = dict_response()
        assert isinstance(response, dict)
        assert isinstance(response["name"], str)
        assert isinstance(response["age"], int)

    def test_list(self):
        @ai_fn
        def list_response() -> list:
            """
            Returns a list that contains two numbers
            """

        response = list_response()
        assert isinstance(response, list)
        assert len(response) == 2
        assert isinstance(response[0], (int, float))
        assert isinstance(response[1], (int, float))

    def test_set_gpt4(self, gpt_4):
        @ai_fn
        def set_response() -> set[int]:
            """
            Returns a set that contains two numbers, such as {3, 5}
            """

        response = set_response()
        assert isinstance(response, set)
        assert len(response) == 2
        assert isinstance(response.pop(), (int, float))
        assert isinstance(response.pop(), (int, float))

    def test_set_gpt35(self):
        assert marvin.settings.openai_model_name.startswith("gpt-3.5")

        @ai_fn
        def set_response() -> set:
            """
            Returns a set that contains two numbers, such as {3, 5}
            """

        # warn when running an ai function with a set under 3.5
        with pytest.warns(UserWarning):
            set_response()

    def test_tuple_gpt4(self, gpt_4):
        @ai_fn
        def tuple_response() -> tuple:
            """
            Returns a tuple that contains two numbers
            """

        response = tuple_response()
        assert isinstance(response, tuple)
        assert len(response) == 2
        assert isinstance(response[0], (int, float))
        assert isinstance(response[1], (int, float))

    def test_tuple_gpt35(self):
        assert marvin.settings.openai_model_name.startswith("gpt-3.5")

        @ai_fn
        def tuple_response() -> tuple:
            """
            Returns a tuple that contains two numbers
            """

        # warn when running an ai function with a tuple under 3.5
        with pytest.warns(UserWarning):
            tuple_response()

    def test_list_of_dicts(self):
        @ai_fn
        def list_of_dicts_response() -> list[dict]:
            """
            Returns a list of 2 dictionaries that each contain
                - name: str
                - age: int
            """

        response = list_of_dicts_response()
        assert isinstance(response, list)
        assert len(response) == 2
        for i in [0, 1]:
            assert isinstance(response[i], dict)
            assert isinstance(response[i]["name"], str)
            assert isinstance(response[i]["age"], int)


class TestSet:
    @pytest.mark.xfail(reason="GPT-3.5 fails to parse sometimes")
    def test_set_response(self):
        # https://github.com/PrefectHQ/marvin/issues/54
        @ai_fn
        def extract_colors(words: list[str]) -> set[str]:
            """returns a set of colors"""

        x = extract_colors(["red", "blue", "cat", "red", "dog"])
        assert isinstance(x, set)
        assert x == {"red", "blue"}


class TestNone:
    def test_none_response_gpt35(self):
        @ai_fn
        def filter_with_none(words: list[str]) -> list[Optional[str]]:
            """
            takes a list of words and returns a list of equal length that
            replaces any word except "blue" with None

            For example, ["red", "blue", "dog"] -> [None, "blue", None]
            """

        x = filter_with_none(["green", "cat", "blue"])

        # gpt_35 sometimes returns strings instead of actual nulls
        assert x in (
            ["null", "null", "blue"],
            ["None", "None", "blue"],
            [None, None, "blue"],
        )

    def test_none_response(self, gpt_4):
        @ai_fn
        def filter_with_none(words: list[str]) -> list[Optional[str]]:
            """
            takes a list of words and returns a list of equal length that
            replaces any word except "blue" with None

            For example, ["red", "blue", "dog"] -> [None, "blue", None]
            """

        x = filter_with_none(["green", "cat", "blue"])
        assert x == [None, None, "blue"]


class TestPydantic:
    def test_pydantic_model(self):
        class ReturnModel(pydantic.BaseModel):
            name: str
            age: int

        @ai_fn
        def get_person() -> ReturnModel:
            """returns a person"""

        x = get_person()
        assert isinstance(x, ReturnModel)

    def test_list_of_pydantic_models(self):
        class ReturnModel(pydantic.BaseModel):
            name: str
            age: int

        @ai_fn
        def get_people(n: int) -> list[ReturnModel]:
            """returns a list of n people"""

        x = get_people(3)
        assert isinstance(x, list)
        assert len(x) == 3
        assert all(isinstance(person, ReturnModel) for person in x)

    def test_nested_pydantic_models(self):
        class Person(pydantic.BaseModel):
            name: str
            age: int

        class ReturnModel(pydantic.BaseModel):
            people: list[Person]

        @ai_fn
        def fn() -> ReturnModel:
            """returns 2 people"""

        x = fn()
        assert isinstance(x, ReturnModel)
        assert len(x.people) == 2


class TestAIFunctionClass:
    def test_decorated_function_is_class(self):
        @ai_fn
        def my_fn() -> int:
            """returns 1"""

        assert isinstance(my_fn, AIFunction)

    def test_repr(self):
        @ai_fn
        def my_fn() -> int:
            """returns 1"""

        assert repr(my_fn) == "<AIFunction my_fn>"

    def test_name(self):
        fn = AIFunction(name="my_fn", fn=lambda: 1, description="returns 1")
        assert fn.name == "my_fn"
        assert fn.description == "returns 1"

    def test_name_from_fn(self):
        @ai_fn
        def my_fn() -> int:
            """returns 1"""

        assert my_fn.name == "my_fn"
        assert my_fn.description == "returns 1"

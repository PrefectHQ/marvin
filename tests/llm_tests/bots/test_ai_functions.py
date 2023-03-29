from typing import Optional

import pydantic
from marvin import ai_fn
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

    def test_generate_rhyming_words(self):
        @ai_fn
        def rhymes(word: str) -> str:
            """generate a word that rhymes with the given word"""

        x = rhymes("blue")
        assert isinstance(x, str)
        assert x != "blue"
        assert_llm(x, "the output is any word that rhymes with blue")

    def test_generate_rhyming_words_with_n(self):
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
            (
                "the output is a list of words, each one rhyming with 'blue'. For"
                " example ['clue', 'dew', 'flew']"
            ),
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


class TestSet:
    def test_set_response(self):
        # https://github.com/PrefectHQ/marvin/issues/54
        @ai_fn
        def extract_colors(words: list[str]) -> set[str]:
            """returns a set of colors"""

        x = extract_colors(["red", "blue", "cat", "red", "dog"])
        assert isinstance(x, set)
        assert x == {"red", "blue"}


class TestNone:
    def test_none_response(self):
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

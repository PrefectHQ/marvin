from marvin import towel
from marvin.utilities.tests import assert_llm


class TestTowel:
    def test_rng(self):
        @towel
        def rng() -> float:
            """generate a random number between 0 and 1"""

        x = rng()
        assert isinstance(x, float)
        assert 0 <= x <= 1

    def test_rng_with_limits(self):
        @towel
        def rng(min: float, max: float) -> float:
            """generate a random number between min and max"""

        x = rng(20, 21)
        assert 20 <= x <= 21

    def test_list_of_fruit(self):
        @towel
        def list_fruit(n: int) -> list[str]:
            """generate a list of n fruits"""

        x = list_fruit(3)
        assert isinstance(x, list)
        assert len(x) == 3
        assert all(isinstance(fruit, str) for fruit in x)
        assert_llm(x, "a list of fruit")

    def test_list_of_fruit_calling_towel_with_no_args(self):
        @towel()
        def list_fruit(n: int) -> list[str]:
            """generate a list of n fruits"""

        x = list_fruit(3)
        assert isinstance(x, list)
        assert len(x) == 3
        assert all(isinstance(fruit, str) for fruit in x)
        assert_llm(x, "a list of fruit")

    def test_generate_fake_people_data(self):
        @towel
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
        assert_llm(x, "a list of fake people")

    def test_generate_rhyming_words(self):
        @towel
        def rhymes(word: str) -> str:
            """generate a word that rhymes with the given word"""

        x = rhymes("blue")
        assert isinstance(x, str)
        assert x != "blue"
        assert_llm(x, "a word that rhymes with blue")

    def test_generate_rhyming_words_with_n(self):
        @towel
        def rhymes(word: str, n: int) -> list[str]:
            """generate a word that rhymes with the given word"""

        x = rhymes("blue", 3)
        assert isinstance(x, list)
        assert len(x) == 3
        assert all(isinstance(word, str) for word in x)
        assert all(word != "blue" for word in x)
        assert_llm(x, "a list of words that rhyme with blue")

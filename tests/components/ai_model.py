from typing import List, Literal, Optional

import pytest
from marvin import ai_model
from marvin.utilities.messages import Message, Role
from pydantic import BaseModel, Field

from tests.utils.mark import pytest_mark_class


@pytest_mark_class("llm")
class TestAIModels:
    def test_arithmetic(self):
        @ai_model
        class Arithmetic(BaseModel):
            sum: float = Field(
                ..., description="The resolved sum of provided arguments"
            )
            is_odd: bool

        x = Arithmetic("One plus six")
        assert x.sum == 7
        assert x.is_odd

    def test_geospatial(self):
        @ai_model
        class Location(BaseModel):
            latitude: float
            longitude: float
            city: str
            state: str
            country: str

        x = Location("The capital city of the Cornhusker State.")
        assert x.city == "Lincoln"
        assert x.state == "Nebraska"
        assert "United" in x.country
        assert "States" in x.country
        assert x.latitude // 1 == 40
        assert x.longitude // 1 == -97

    def test_depth(self):
        from typing import List

        class Country(BaseModel):
            name: str

        class City(BaseModel):
            name: str
            country: Country

        class Neighborhood(BaseModel):
            name: str
            city: City

        @ai_model
        class RentalHistory(BaseModel):
            neighborhood: List[Neighborhood]

        assert RentalHistory("""\
            I lived in Palms, then Mar Vista, then Pico Robertson.
        """)

    def test_resume(self):
        class Experience(BaseModel):
            technology: str
            years_of_experience: int
            supporting_phrase: Optional[str]

        @ai_model
        class Resume(BaseModel):
            """Details about a person's work experience."""

            greater_than_three_years_management_experience: bool
            greater_than_ten_years_management_experience: bool
            technologies: List[Experience]

        x = Resume("""\
            Data Engineering Manager, 2017-2022
            • Managed team of three engineers and data scientists
            • Deployed and maintained internal Apache Kafka pipeline
            • Built tree-based classifier to predict customer churn (xgboost)\
        """)

        assert x.greater_than_three_years_management_experience
        assert not x.greater_than_ten_years_management_experience
        assert len(x.technologies) == 2

    @pytest.mark.flaky(reruns=2)
    def test_literal(self):
        class CertainPerson(BaseModel):
            name: Literal["Adam", "Nate", "Jeremiah"]

        @ai_model
        class LLMConference(BaseModel):
            speakers: List[CertainPerson]

        x = LLMConference("""
            The conference for best LLM framework will feature talks by
            Adam, Nate, Jeremiah, Marvin, and Billy Bob Thornton.
        """)
        assert len(set([speaker.name for speaker in x.speakers])) == 3
        assert set([speaker.name for speaker in x.speakers]) == set(
            ["Adam", "Nate", "Jeremiah"]
        )

    @pytest.mark.xfail(reason="regression in OpenAI function-using models")
    def test_history(self):
        from typing import List

        class Location(BaseModel):
            city: str
            state: str

        class Candidate(BaseModel):
            name: str
            political_party: str
            campaign_slogan: str
            birthplace: Location

        @ai_model
        class Election(BaseModel):
            candidates: List[Candidate]
            winner: Candidate

        x = Election("The United States Election of 1800")

        assert x.winner in x.candidates
        assert x.winner.name == "Thomas Jefferson"
        assert x.winner.political_party == "Democratic-Republican"
        assert x.winner.birthplace.city == "Shadwell"
        assert x.winner.birthplace.state == "Virginia"
        assert set([candidate.name for candidate in x.candidates]).issubset(
            set(
                [
                    "Thomas Jefferson",
                    "John Adams",
                    "Aaron Burr",
                    "Charles C. Pinckney",
                    "Charles Pinckney",
                    "Charles Cotesworth Pinckney",
                ]
            )
        )

    def test_correct_class_is_returned(self):
        @ai_model
        class Fruit(BaseModel):
            color: str
            name: str

        fruit = Fruit("loved by monkeys")

        assert isinstance(fruit, Fruit)

    async def test_correct_class_is_returned_via_acall(self):
        @ai_model
        class Fruit(BaseModel):
            color: str
            name: str

        fruit = await Fruit.acall("loved by monkeys")

        assert isinstance(fruit, Fruit)


@pytest_mark_class("llm")
class TestAIModelsMessage:
    @pytest.mark.skip(reason="old behavior, may revisit")
    def test_arithmetic_message(self):
        @ai_model
        class Arithmetic(BaseModel):
            sum: float = Field(
                ..., description="The resolved sum of provided arguments"
            )

        x = Arithmetic("One plus six")
        assert x.sum == 7
        assert isinstance(x._message, Message)
        assert x._message.role == Role.FUNCTION_RESPONSE


@pytest_mark_class("llm")
class TestInstructions:
    @pytest.mark.skip(reason="old behavior, may revisit")
    def test_instructions_error(self):
        @ai_model
        class Test(BaseModel):
            text: str

        with pytest.raises(
            ValueError, match="(Received `instructions` but this model)"
        ):
            Test("Hello!", instructions="Translate to French")
        with pytest.raises(ValueError, match="(Received `model` but this model)"):
            Test("Hello!", model=None)

    def test_instructions(self):
        @ai_model
        class Text(BaseModel):
            text: str

        t1 = Text("Hello")
        assert t1.text == "Hello"

        # this model is identical except it has an instruction
        @ai_model(instructions="first translate the text to French")
        class Text(BaseModel):
            text: str

        t2 = Text("Hello")
        assert t2.text == "Bonjour"

    def test_follow_instance_instructions(self):
        @ai_model
        class Test(BaseModel):
            text: str

        t1 = Test("Hello")
        assert t1.text == "Hello"

        # this model is identical except it has an instruction
        @ai_model
        class Test(BaseModel):
            text: str

        t2 = Test("Hello", instructions_="first translate the text to French")
        assert t2.text == "Bonjour"

    def test_follow_global_and_instance_instructions(self):
        @ai_model(instructions="Always set color_1 to 'red'")
        class Test(BaseModel):
            color_1: str
            color_2: str

        t1 = Test("Hello", instructions_="Always set color_2 to 'blue'")
        assert t1 == Test(color_1="red", color_2="blue")

    def test_follow_docstring_and_global_and_instance_instructions(self):
        @ai_model(instructions="Always set color_1 to 'red'")
        class Test(BaseModel):
            """Always set color_3 to 'orange'"""

            color_1: str
            color_2: str
            color_3: str

        t1 = Test("Hello", instructions_="Always set color_2 to 'blue'")
        assert t1 == Test(color_1="red", color_2="blue", color_3="orange")

    def test_follow_multiple_instructions(self):
        # ensure that instructions don't bleed to other invocations
        @ai_model
        class Translation(BaseModel):
            """Translates from one language to another language"""

            original_text: str
            translated_text: str

        t1 = Translation("Hello, world!", instructions_="Translate to French")
        t2 = Translation("Hello, world!", instructions_="Translate to German")

        assert t1 == Translation(
            original_text="Hello, world!", translated_text="Bonjour, monde!"
        )
        assert t2 == Translation(
            original_text="Hello, world!", translated_text="Hallo, Welt!"
        )


@pytest_mark_class("llm")
class TestAIModelMapping:
    def test_arithmetic(self):
        @ai_model
        class Arithmetic(BaseModel):
            sum: float

        x = Arithmetic.map(["One plus six", "Two plus 100 minus one"])
        assert len(x) == 2
        assert x[0].sum == 7
        assert x[1].sum == 101

    def test_location(self):
        @ai_model
        class City(BaseModel):
            name: str = Field(description="The correct city name, e.g. Omaha")  # noqa

        results = City.map(
            [
                "the windy city",
                "chicago IL",
                "Chicago",
                "Chcago",
                "chicago, Illinois, USA",
                "chi-town",
            ]
        )
        assert len(results) == 6
        for result in results:
            assert result.name == "Chicago"

    def test_instructions(self):
        @ai_model
        class Translate(BaseModel):
            text: str

        result = Translate.map(["Hello", "Goodbye"], instructions="Translate to French")
        assert len(result) == 2
        assert result[0].text == "Bonjour"
        assert result[1].text == "Au revoir"

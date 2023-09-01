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
            sum: float
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
        assert 2 > abs(x.latitude - 41)  # Lincoln is at 40.8 N
        assert 2 > abs(x.longitude + 97)  # Lincoln is at 96.7 W

    def test_depth(self):
        class Neighborhood(BaseModel):
            name: str
            city: str

        @ai_model
        class RentalHistory(BaseModel):
            neighborhoods: list[Neighborhood]

        assert (
            RentalHistory("""\
            I lived in Queens for a bit, then to Logan Square in chitown, now French Quarter in NOLA.
        """)  # noqa
            == RentalHistory(
                neighborhoods=[
                    Neighborhood(name="Queens", city="New York"),
                    Neighborhood(name="Logan Square", city="Chicago"),
                    Neighborhood(name="French Quarter", city="New Orleans"),
                ]
            )
        )

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


@pytest_mark_class("llm")
class TestAIModelsMessage:
    def test_arithmetic_message(self):
        @ai_model
        class Arithmetic(BaseModel):
            sum: float

        x = Arithmetic("One plus six")
        assert x.sum == 7
        assert isinstance(x._message, Message)
        assert x._message.role == Role.FUNCTION_RESPONSE


@pytest_mark_class("llm")
class TestInstructions:
    def test_instructions(self):
        @ai_model
        class Test(BaseModel):
            text: str

        t1 = Test("Hello")
        assert t1.text == "Hello"

        # this model is identical except it has an instruction
        @ai_model(instructions="Translate the text to French")
        class Test(BaseModel):
            text: str

        t2 = Test("Hello")
        assert t2.text == "Bonjour"

    def test_follow_instance_instructions(self):
        @ai_model
        class Test(BaseModel):
            text: str

        t1 = Test("Hello")
        assert t1.text == "Hello"

        # this model is identical except it has an instruction
        @ai_model(instructions_="Translate the text to French")
        class Test(BaseModel):
            text: str

        t2 = Test("Hello")
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
        @ai_model(instructions="Translate to French")
        class Translation(BaseModel):
            """Translates from one language to another language"""

            original_text: str
            translated_text: str

        t1 = Translation("Hello, world!")

        @ai_model(instructions="Translate to German")
        class Translation(BaseModel):
            """Translates from one language to another language"""

            original_text: str
            translated_text: str

        t2 = Translation("Hello, world!")

        assert t1.original_text == "Hello, world!"
        assert t1.translated_text in [
            "Bonjour, le monde!",
            "Bonjour, monde!",
            "Bonjour, tout le monde!",
        ]
        assert t2.original_text == "Hello, world!"
        assert t2.translated_text in ["Hallo Welt!", "Hallo, Welt!", "Hallo, die Welt!"]


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
            name: str = Field("The proper name of the city")

        result = City.map(
            [
                "the windy city",
                "chicago IL",
                "Chicago",
                "Chcago",
                "chicago, Illinois, USA",
                "chi-town",
            ]
        )
        assert len(result) == 6
        expected = City(name="Chicago")
        assert all(r == expected for r in result)

    def test_instructions(self):
        @ai_model(instructions="Translate to French")
        class Translate(BaseModel):
            text: str

        result = Translate.map(["Hello", "Goodbye"])
        assert len(result) == 2
        assert result[0].text == "Bonjour"
        assert result[1].text == "Au revoir"

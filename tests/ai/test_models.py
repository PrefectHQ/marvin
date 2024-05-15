from typing import List, Literal, Optional

import marvin
import pytest
from pydantic import BaseModel, Field


class TestModels:
    def test_arithmetic(self):
        @marvin.model
        class Arithmetic(BaseModel):
            sum: float = Field(
                ..., description="The resolved sum of provided arguments"
            )
            is_odd: bool

        x = Arithmetic("One plus six")
        assert x.sum == 7
        assert x.is_odd

    def test_geospatial(self):
        @marvin.model
        class Location(BaseModel):
            latitude: float
            longitude: float
            city: str
            state: str
            country: str = Field(..., description="The abbreviated country name")

        x = Location("The capital city of the Cornhusker State.")
        assert x.city == "Lincoln"
        assert x.state == "Nebraska"
        assert x.country in {"US", "USA", "U.S.", "U.S.A.", "United States"}
        assert x.latitude // 1 == 40
        assert x.longitude // 1 == -97

    @pytest.mark.xfail(reason="TODO: flaky on 3.5")
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

        @marvin.model
        class RentalHistory(BaseModel):
            neighborhood: List[Neighborhood]

        assert RentalHistory(
            """\
            I lived in Palms, then Mar Vista, then Pico Robertson.
        """
        )

    @pytest.mark.flaky(max_runs=3)
    def test_resume(self):
        class Experience(BaseModel):
            technology: str
            years_of_experience: int
            supporting_phrase: Optional[str]

        @marvin.model
        class Resume(BaseModel):
            """Details about a person's work experience."""

            greater_than_three_years_management_experience: bool
            greater_than_ten_years_management_experience: bool
            technologies: List[Experience]

        x = Resume(
            """\
            Data Engineering Manager, 2017-2022
            • Managed team of three engineers and data scientists
            • Deployed and maintained internal Apache Kafka pipeline
            • Built tree-based classifier to predict customer churn (xgboost)\
        """
        )

        assert x.greater_than_three_years_management_experience
        assert not x.greater_than_ten_years_management_experience
        assert len(x.technologies) == 2

    def test_literal(self):
        @marvin.model
        class LLMConference(BaseModel):
            speakers: list[
                Literal["Adam", "Nate", "Jeremiah", "Marvin", "Billy Bob Thornton"]
            ]

        x = LLMConference(
            """
            The conference for best LLM framework will feature talks by
            Adam, Nate, Jeremiah, Marvin, and Billy Bob Thornton.
        """
        )
        assert len(set(x.speakers)) == 5
        assert set(x.speakers) == set(
            ["Adam", "Nate", "Jeremiah", "Marvin", "Billy Bob Thornton"]
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

        @marvin.model
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

    @pytest.mark.skip(reason="old behavior, may revisit")
    def test_correct_class_is_returned(self):
        @marvin.model
        class Fruit(BaseModel):
            color: str
            name: str

        fruit = Fruit("loved by monkeys")

        assert isinstance(fruit, Fruit)


class TestInstructions:
    def test_instructions(self):
        @marvin.model
        class Text(BaseModel):
            text: str

        t1 = Text("Hello")
        assert t1.text == "Hello"

        # this model is identical except it has an instruction
        @marvin.model(instructions="first translate the text to French")
        class Text(BaseModel):
            text: str

        t2 = Text("Hello")
        assert t2.text == "Bonjour"


class TestAsync:
    async def test_basic_async(self):
        from marvin.ai.text import Model

        class Location(Model):
            city: str
            state: str

        location = await Location.from_text_async("biggest midwestern city")

        assert location == Location(city="Chicago", state="Illinois")

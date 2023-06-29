from typing import List, Literal, Optional

import pytest
from marvin import ai_model
from pydantic import BaseModel


class TestAIModels:
    @pytest.mark.llm
    def test_arithmetic(self):
        @ai_model
        class Arithmetic(BaseModel):
            sum: float
            is_odd: bool

        x = Arithmetic("One plus six")
        assert x.sum == 7
        assert x.is_odd

    @pytest.mark.llm
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

    @pytest.mark.llm
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

    @pytest.mark.llm
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

    @pytest.mark.llm
    def test_literal(self):
        class Person(BaseModel):
            name: Literal["Adam", "Nate", "Jeremiah"]

        @ai_model
        class Conversation(BaseModel):
            speakers: List[Person]

        x = Conversation("""\
            The conference for best LLM framework will feature talks by\
            Adam, Nate, Jeremiah, and Marvin.\
        """)
        assert len(set([speaker.name for speaker in x.speakers])) == 3
        assert set([speaker.name for speaker in x.speakers]) == set(
            ["Adam", "Nate", "Jeremiah"]
        )

    @pytest.mark.llm
    @pytest.mark.xfail(reason="flaky test")
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


class TestInstructions:
    def test_follow_instructions(self):
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

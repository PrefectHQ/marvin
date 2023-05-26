from typing import List, Literal, Optional

import pydantic
from marvin import ai_model


class TestAIModels:
    def test_arithmetic(self):
        @ai_model
        class Arithmetic(pydantic.BaseModel):
            value: float
            is_odd: bool

        x = Arithmetic("One plus six")
        assert x.value == 7
        assert x.is_odd

    def test_geospatial(self):
        @ai_model
        class Location(pydantic.BaseModel):
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

        class Country(pydantic.BaseModel):
            name: str

        class City(pydantic.BaseModel):
            name: str
            country: Country

        class Neighborhood(pydantic.BaseModel):
            name: str
            city: City

        @ai_model
        class RentalHistory(pydantic.BaseModel):
            neighborhood: List[Neighborhood]

        assert RentalHistory("""\
            I lived in Palms, then Mar Vista, then Pico Robertson.
        """)

    def test_resume(self):
        class Experience(pydantic.BaseModel):
            technology: str
            years_of_experience: int
            supporting_phrase: Optional[str]

        @ai_model
        class Resume(pydantic.BaseModel):
            has_three_years_management_experience: bool
            has_ten_years_management_experience: bool
            technologies: List[Experience]

        x = Resume("""\
            Data Engineering Manager, 2017-2022
            • Managed team of three engineers and data scientists
            • Deployed and maintained internal Apache Kafka pipeline
            • Built tree-based classifier to predict customer churn (xgboost)\
        """)

        assert x.has_three_years_management_experience
        assert not x.has_ten_years_management_experience
        assert len(x.technologies) == 2

    def test_literal(self):
        class Person(pydantic.BaseModel):
            name: Literal["Adam", "Nate", "Jeremiah"]

        @ai_model
        class Conversation(pydantic.BaseModel):
            speakers: List[Person]

        x = Conversation("""\
            The conference for best LLM framework will feature talks by\
            Adam, Nate, Jeremiah, and Marvin.\
        """)
        assert len(set([speaker.name for speaker in x.speakers])) == 3
        assert set([speaker.name for speaker in x.speakers]) == set(
            ["Adam", "Nate", "Jeremiah"]
        )

    def test_history(self):
        from typing import List

        class Location(pydantic.BaseModel):
            city: str
            state: str

        class Candidate(pydantic.BaseModel):
            name: str
            political_party: str
            campaign_slogan: str
            birthplace: Location

        @ai_model
        class Election(pydantic.BaseModel):
            winner: Candidate
            candidates: List[Candidate]

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


class TestAIModelsMapping:
    def test_mapping_sync(self, prefect_db):
        @ai_model
        class CardinalDirection(pydantic.BaseModel):
            """use a single capital letter for each cardinal direction."""

            direction: str

        assert CardinalDirection.map(["sunrise", "sunset"]) == [
            CardinalDirection(direction="E"),
            CardinalDirection(direction="W"),
        ]

    async def test_mapping_async(self, prefect_db):
        @ai_model
        class CardinalDirection(pydantic.BaseModel):
            """use a single capital letter for each cardinal direction."""

            direction: str

        assert await CardinalDirection.map(["sunrise", "sunset"]) == [
            CardinalDirection(direction="E"),
            CardinalDirection(direction="W"),
        ]

from marvin.ai_functions import entities as entities_fns
from marvin.utilities.types import MarvinBaseModel


class TestKeywordExtraction:
    def test_keyword_extraction(self):
        text = (
            'The United States passed a law that requires all cars to have a "black'
            ' box" that records data about the car and its driver. The law is sponsored'
            " by John Smith. It goes into effect in 2025."
        )
        result = entities_fns.extract_keywords(text)
        assert result == [
            "United States",
            "law",
            "cars",
            "black box",
            "records",
            "data",
            "driver",
            "John Smith",
            "2025",
        ]


class TestNamedEntityExtraction:
    def test_named_entity_extraction(self):
        text = (
            'The United States passed a law that requires all cars to have a "black'
            ' box" that records data about the car and its driver. The law is sponsored'
            " by John Smith. It goes into effect in 2025."
        )
        result = entities_fns.extract_named_entities(text)
        assert result == [
            entities_fns.NamedEntity(entity="United States", type="GPE"),
            entities_fns.NamedEntity(entity="John Smith", type="PERSON"),
            entities_fns.NamedEntity(entity="2025", type="DATE"),
        ]


class TestExtractTypes:
    class Country(MarvinBaseModel):
        name: str

    class Money(MarvinBaseModel):
        amount: float
        currency: str

    def test_extract_types(self, gpt_4):
        text = "The United States EV tax credit is $7,500 for cars worth up to $50k."
        result = entities_fns.extract_types(text, types=[self.Country, self.Money])

        assert result == [
            self.Country(name="United States"),
            self.Money(amount=7500, currency="USD"),
            self.Money(amount=50000, currency="USD"),
        ]

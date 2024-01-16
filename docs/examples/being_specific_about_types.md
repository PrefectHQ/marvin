# Fully leveraging `pydantic`

## `Annotated` and `Field`

!!! example "Numbers in a valid range"

    Pydantic's `Field` lets us be very specific about what we want from the LLM.
    
    ```python
    from typing import Annotated
    import marvin
    from pydantic import Field
    from typing_extensions import TypedDict

    ActivationField = Field(
        description=(
            "A score between -1 (not descriptive) and 1"
            " (very descriptive) for the given emotion"
        ),
        ge=-1,
        le=1
    )

    SentimentActivation = Annotated[float, ActivationField]

    class DetailedSentiment(TypedDict):
        happy: SentimentActivation
        sad: SentimentActivation
        angry: SentimentActivation
        surprised: SentimentActivation
        amused: SentimentActivation
        scared: SentimentActivation

    @marvin.fn
    def sentiment_analysis(text: str) -> DetailedSentiment:
        """Analyze the sentiment of a given text"""

    sentiment_analysis(
        "dude i cannot believe how hard that"
        " kangaroo just punched that guy 🤣"
        " - he really had it coming, but glad he's ok"
    )
    ```
    
    !!! success "Result"
        ```python
        {
            'happy': 0.8,
            'sad': -0.1,
            'angry': -0.2,
            'surprised': 0.7,
            'amused': 1.0,
            'scared': -0.1
        }
        ```

## Complex types

!!! example "Using `BaseModel` and `Field`"

    To parse and validate complex nested types, use `BaseModel` and `Field`:
    
    
    ```python
    import marvin
    from pydantic import BaseModel, Field

    class Location(BaseModel):
        city: str
        state: str | None = Field(description="Two-letter state code")
        country: str
        latitute: float | None = Field(
            description="Latitude in degrees",
            ge=-90,
            le=90
        )
        longitude: float | None = Field(
            description="Longitude in degrees",
            ge=-180,
            le=180
        )
    
    class Traveler(BaseModel):
        name: str
        age: int | None = Field(description="Age in years")
    
    class Trip(BaseModel):
        travelers: list[Traveler]
        origin: Location
        destination: Location
    
    trip = marvin.model(Trip)(
        "Marvin and Ford are heading from Chi to SF for their 30th birthdays"
    )
    ```
    
    !!! success "Result"
        ```python
        Trip(
            travelers=[
                Traveler(name='Marvin', age=30),
                Traveler(name='Ford', age=30)
            ],
            origin=Location(
                city='Chicago',
                state='IL',
                country='USA',
                latitute=41.8781,
                longitude=-87.6298
            ),
            destination=Location(
                city='San Francisco',
                state='CA',
                country='USA',
                latitute=37.7749,
                longitude=-122.4194
            )
        )
        ```
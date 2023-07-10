# Hello Marvin 👋

A few quick examples to get you started with Marvin:

---

### natural language >> `pydantic` models

```python
from pydantic import BaseModel
from marvin import ai_model

@ai_model
class WorldCity(BaseModel):
    name: str
    country: str
    lat: float
    lon: float

    @property
    def map_url(self) -> str:
        return (
            "https://findlatitudeandlongitude.com/"
            f"?lat={self.lat}&lon={self.lon}"
        )

city = WorldCity("city that never sleeps")

print(city.map_url)

# https://findlatitudeandlongitude.com/?lat=40.7128&lon=-74.006
```

---

### classify anything
```python
from enum import Enum
from marvin import ai_choice

@ai_choice
class ZodiacSign(Enum):
    ARIES = "Aries"
    TAURUS = "Taurus"
    GEMINI = "Gemini"
    CANCER = "Cancer"
    LEO = "Leo"
    VIRGO = "Virgo"
    LIBRA = "Libra"
    SCORPIO = "Scorpio"
    SAGITTARIUS = "Sagittarius"
    CAPRICORN = "Capricorn"
    AQUARIUS = "Aquarius"
    PISCES = "Pisces"    

ZodiacSign(
    "creative, compassionate, always listening to Marvin's room by Drake"
)

# <ZodiacSign.PISCES: 'Pisces'>
```

---

### functional prompts with type-safe results
```python
from typing import Optional
from pydantic import BaseModel
from marvin import ai_fn

class Person(BaseModel):
    name: str
    year_of_death: Optional[int] = None

@ai_fn
def list_people(context: str) -> list[Person]:
    """ List people given a context """

list_people(
    "was mentored by the great educator in"
    " youth before hosting his own show Cosmos"
)

# [
#   Person(name='Neil deGrasse Tyson', year_of_death=None),
#   Person(name='Carl Sagan', year_of_death=1996)
# ]
```
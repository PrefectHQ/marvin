AI Models are a high-level component, or building block, of Marvin. Like all Marvin components, they are completely standalone: you're free to use them with or without the rest of Marvin.

!!! abstract "What it does"
    A decorator that lets you extract structured data from unstructured text, documents, or instructions.


!!! example "Example"
    ```python
    from marvin import ai_model
    from pydantic import BaseModel, Field


    @ai_model
    class Location(BaseModel):
        city: str
        state: str = Field(..., description="The two-letter state abbreviation")

    # We can now put pass unstructured context to this model.
    Location("The Big Apple")
    ```
    
    ???+ Returns
        ```python
        Location(city='New York', state='NY')
        ```

!!! info "How it works"
    AI Models use an LLM to extract, infer, or deduce data from the provided text. The data is parsed with Pydantic into the provided schema.

!!! tip "When to use"
    - Best for extractive tasks: structuing of text or data models.
    - Best for writing NLP pipelines that would otherwise be impossible to create.
    - Good for model generation, though, see AI Function.

## Creating an AI Model

AI Models are identical to Pydantic `BaseModels`, except that they can attempt to parse natural language to populate their fields. To build an effective AI Model, be as specific as possible with your field names, field descriptions, docstring, and instructions.

To build a minimal AI model, decorate any standard Pydantic model, like this:

!!! example "Example"
    ```python
    from marvin import ai_model
    from pydantic import BaseModel, Field


    @ai_model
    class Location(BaseModel):
        """A representation of a US city and state"""

        city: str = Field(description="The city's proper name")
        state: str = Field(description="The state's two-letter abbreviation (e.g. NY)")

    # We can now put pass unstructured context to this model.
    Location("The Big Apple")
    ```
    
    ???+ Returns
        ```python
        Location(city='New York', state='NY')
        ```

## Configuring an AI Model

In addition to how you define the AI model itself, there are two ways to control its behavior at runtime: `instructions` and `model`.

### Providing instructions
When parsing text, AI Models can take up to three different forms of instruction:
- the AI Model's docstring (set at the class level)
- instructions passed to the `@ai_model` decorator (set at the class level)
- instructions passed to the AI Model when instantiated (set at the instance / call level)

The AI Model's docstring and the `@ai_model` instructions are roughly equivalent: they are both provided when the class is defined, not when it is instantiated, and are therefore applied to every instance of the class. Users can choose to put information in either location. If you only want to use one, our recommendation is to use the docstring for clarity. Alternatively, you may prefer to put the model's documentation in the docstring (as you would for a normal Pydantic model) and put parsing instructions in the `@ai_model` decorator, since those are unique to the LLM. This is entirely a matter of preference and users should opt for whichever is more clear; both the docstring and the `@ai_model` instructions are provided to the LLM in the same way.

Here is an example of an AI model with a documentation docstring and parsing instructions provided to the decorator:


```python
@ai_model(instructions="Translate to French")
class Translation(BaseModel):
    """A record of original text and translated text"""

    original_text: str
    translated_text: str


Translation("Hello, world!")
```




    Translation(original_text='Hello, world!', translated_text='Bonjour le monde!')



In the above case, we could have also put "translate to French" in the docstring (and perhaps renamed the object `FrenchTranslation`, since that's the only language it can represent).

The third opportunity to provide instructions is when the model is actually instantiated. These instructions are **combined** with any other instructions to guide the model behavior. Here's how we could use the same `Translation` object to handle multiple languages:


```python
@ai_model
class Translation(BaseModel):
    """A record of original text and translated text"""

    original_text: str
    translated_text: str


print(Translation("Hello, world!", instructions_="Translate to French"))
print(Translation("Hello, world!", instructions_="Translate to German"))
```

    original_text='Hello, world!' translated_text='Bonjour, le monde!'
    original_text='Hello, world!' translated_text='Hallo, Welt!'



Note that the kwarg is `instructions_` with a trailing underscore; this is to avoid conflicts with models that may have a real `instructions` field. If you accidentally pass "instructions" to a model without an "instructions" field, a helpful error will identify your mistake.

Putting this all together, here is a model whose behavior is informed by a docstring on the class itself, an instruction provided to the decorator, and an instruction provided to the instance.


```python
@ai_model(instructions="Always set color_2 to 'red'")
class Test(BaseModel):
    """Always set color_1 to 'orange'"""

    color_1: str
    color_2: str
    color_3: str


t1 = Test("Hello", instructions_="Always set color_3 to 'blue'")
assert t1 == Test(color_1="orange", color_2="red", color_3="blue")
```

### Configuring the LLM
By default, `@ai_model` uses the global LLM settings. To specify a particular LLM, pass it as an argument to the decorator or at instantiation. If you provide it to the decorator, it becomes the default for all uses of that model. If you provide it at instantiation, it is only used for that specific model. 

Note that the kwarg is `model_` with a trailing underscore; this is to avoid conflicts with models that may have a real `model` field. If you accidentally pass a "model" kwarg and there is no "model" field, a helpful error will identify your mistake.


```python
from marvin.engine.language_models import chat_llm


@ai_model(model=chat_llm(model="openai/gpt-3.5-turbo", temperature=0))
class Location(BaseModel):
    city: str
    state: str


print(Location("The Big Apple"))
print(
    Location(
        "The Big Apple",
        model_=chat_llm(model="openai/gpt-3.5-turbo", temperature=1),
    )
)
```

    city='New York' state='New York'
    city='New York' state='New York'


## Features

#### ⚙️ Type Safe
`ai_model` is fully type-safe. It works out of the box with Pydantic models.

#### 🧠 Powered by deduction
`ai_model` gives your data model access to the knowledge and deductive power 
of a Large Language Model. This means that your data model can infer answers
to previous impossible tasks.


```python
@ai_model
class Location(BaseModel):
    city: str
    state: str
    country: str
    latitude: float
    longitude: float


Location("He says he's from the windy city")

# Location(
#   city='Chicago',
#   state='Illinois',
#   country='United States',
#   latitude=41.8781,
#   longitude=-87.6298
# )
```



## Examples 
### Resumes


```python
from typing import Optional
from pydantic import BaseModel
from marvin import ai_model


@ai_model
class Resume(BaseModel):
    first_name: str
    last_name: str
    phone_number: Optional[str]
    email: str


Resume("Ford Prefect • (555) 5124-5242 • ford@prefect.io").json(indent=2)

# {
# first_name: 'Ford',
# last_name: 'Prefect',
# email: 'ford@prefect.io',
# phone: '(555) 5124-5242',
# }
```

### Customer Service


```python
import datetime
from typing import Optional, List
from pydantic import BaseModel
from marvin import ai_model


class Destination(pydantic.BaseModel):
    start: datetime.date
    end: datetime.date
    city: Optional[str]
    country: str
    suggested_attractions: list[str]


@ai_model
class Trip(pydantic.BaseModel):
    trip_start: datetime.date
    trip_end: datetime.date
    trip_preferences: list[str]
    destinations: List[Destination]


Trip("""\
    I've got all of June off, so hoping to spend the first\
    half of June in London and the second half in Rabat. I love \
    good food and going to museums.
""").json(indent=2)

# {
#   "trip_start": "2023-06-01",
#   "trip_end": "2023-06-30",
#   "trip_preferences": [
#     "good food",
#     "museums"
#   ],
#   "destinations": [
#     {
#       "start": "2023-06-01",
#       "end": "2023-06-15",
#       "city": "London",
#       "country": "United Kingdom",
#       "suggested_attractions": [
#         "British Museum",
#         "Tower of London",
#         "Borough Market"
#       ]
#     },
#     {
#       "start": "2023-06-16",
#       "end": "2023-06-30",
#       "city": "Rabat",
#       "country": "Morocco",
#       "suggested_attractions": [
#         "Kasbah des Oudaias",
#         "Hassan Tower",
#         "Rabat Archaeological Museum"
#       ]
#     }
#   ]
# }
```

### Electronic Health Records


```python
from datetime import date
from typing import Optional, List
from pydantic import BaseModel


class Patient(BaseModel):
    name: str
    age: int
    is_smoker: bool


class Diagnosis(BaseModel):
    condition: str
    diagnosis_date: date
    stage: Optional[str] = None
    type: Optional[str] = None
    histology: Optional[str] = None
    complications: Optional[str] = None


class Treatment(BaseModel):
    name: str
    start_date: date
    end_date: Optional[date] = None


class Medication(Treatment):
    dose: Optional[str] = None


class BloodTest(BaseModel):
    name: str
    result: str
    test_date: date


@ai_model
class PatientData(BaseModel):
    patient: Patient
    diagnoses: List[Diagnosis]
    treatments: List[Treatment]
    blood_tests: List[BloodTest]


PatientData("""\
Ms. Lee, a 45-year-old patient, was diagnosed with type 2 diabetes mellitus on 06-01-2018.
Unfortunately, Ms. Lee's diabetes has progressed and she developed diabetic retinopathy on 09-01-2019.
Ms. Lee was diagnosed with type 2 diabetes mellitus on 06-01-2018.
Ms. Lee was initially diagnosed with stage I hypertension on 06-01-2018.
Ms. Lee's blood work revealed hyperlipidemia with elevated LDL levels on 06-01-2018.
Ms. Lee was prescribed metformin 1000 mg daily for her diabetes on 06-01-2018.
Ms. Lee's most recent A1C level was 8.5% on 06-15-2020.
Ms. Lee was diagnosed with type 2 diabetes mellitus, with microvascular complications, including diabetic retinopathy, on 09-01-2019.
Ms. Lee's blood pressure remains elevated and she was prescribed lisinopril 10 mg daily on 09-01-2019.
Ms. Lee's most recent lipid panel showed elevated LDL levels, and she was prescribed atorvastatin 40 mg daily on 09-01-2019.\
""").json(indent=2)

# {
#   "patient": {
#     "name": "Ms. Lee",
#     "age": 45,
#     "is_smoker": false
#   },
#   "diagnoses": [
#     {
#       "condition": "Type 2 diabetes mellitus",
#       "diagnosis_date": "2018-06-01",
#       "stage": "I",
#       "type": null,
#       "histology": null,
#       "complications": null
#     },
#     {
#       "condition": "Diabetic retinopathy",
#       "diagnosis_date": "2019-09-01",
#       "stage": null,
#       "type": null,
#       "histology": null,
#       "complications": null
#     }
#   ],
#   "treatments": [
#     {
#       "name": "Metformin",
#       "start_date": "2018-06-01",
#       "end_date": null
#     },
#     {
#       "name": "Lisinopril",
#       "start_date": "2019-09-01",
#       "end_date": null
#     },
#     {
#       "name": "Atorvastatin",
#       "start_date": "2019-09-01",
#       "end_date": null
#     }
#   ],
#   "blood_tests": [
#     {
#       "name": "A1C",
#       "result": "8.5%",
#       "test_date": "2020-06-15"
#     },
#     {
#       "name": "LDL",
#       "result": "Elevated",
#       "test_date": "2018-06-01"
#     },
#     {
#       "name": "LDL",
#       "result": "Elevated",
#       "test_date": "2019-09-01"
#     }
#   ]
# }
```

### Text to SQL


```python
from datetime import date
from typing import Optional
from pydantic import BaseModel
from django.db.models import Q


class DjangoLookup(BaseModel):
    field: Literal[*django_fields]
    lookup: Literal[*django_lookups] = pydantic.Field(description="e.g. __iregex")
    value: Any


@ai_model
class DjangoQuery(BaseModel):
    """A model representing a Django ORM query"""

    lookups: List[DjangoLookup]

    def to_q(self) -> Q:
        q = Q()
        for lookup in self.lookups:
            q &= Q(**{f"{lookup.field}__{lookup.lookup}": lookup.value})
        return q


DjangoQuery("""\
    All users who joined more than two months ago but\
    haven't made a purchase in the last 30 days""").to_q()

# <Q: (AND:
#     ('date_joined__lte', '2023-03-11'),
#     ('last_purchase_date__isnull', False),
#     ('last_purchase_date__lte', '2023-04-11'))>
```

### Financial Reports


```python
from datetime import date
from typing import Optional
from pydantic import BaseModel


@ai_model
class CapTable(BaseModel):
    total_authorized_shares: int
    total_common_share: int
    total_common_shares_outstanding: Optional[int]
    total_preferred_shares: int
    conversion_price_multiple: int = 1


CapTable("""\
    In the cap table for Charter, the total authorized shares amount to 13,250,000. 
    The total number of common shares stands at 10,000,000 as specified in Article Fourth, 
    clause (i) and Section 2.2(a)(i). The exact count of common shares outstanding is not 
    available at the moment. Furthermore, there are a total of 3,250,000 preferred shares mentioned 
    in Article Fourth, clause (ii) and Section 2.2(a)(ii). The dividend percentage for Charter is 
    set at 8.00%. Additionally, the mandatory conversion price multiple is 3x, which is 
    derived from the Term Sheet.\
""").json(indent=2)

# {
#   "total_authorized_shares": 13250000,
#   "total_common_share": 10000000,
#   "total_common_shares_outstanding": null,
#   "total_preferred_shares": 3250000,
#   "conversion_price_multiple": 3
# }
```

### Meeting Notes


```python
import datetime
from typing import List
from pydantic import BaseModel
from typing_extensions import Literal
from marvin import ai_model


class ActionItem(BaseModel):
    responsible: str
    description: str
    deadline: Optional[datetime.datetime]
    time_sensitivity: Literal["low", "medium", "high"]


@ai_model
class Conversation(BaseModel):
    """A class representing a team conversation"""

    participants: List[str]
    action_items: List[ActionItem]


Conversation("""
    Adam: Hey Jeremiah can you approve my PR? I requested you to review it.
    Jeremiah: Yeah sure, when do you need it done by?
    Adam: By this Friday at the latest, we need to ship it by end of week.
    Jeremiah: Oh shoot, I need to make sure that Nate and I have a chance to chat first.
    Nate: Jeremiah we can meet today to chat.
    Jeremiah: Okay, I'll book something for today.
""").json(indent=2)

# {
#   "participants": [
#     "Adam",
#     "Jeremiah",
#     "Nate"
#   ],
#   "action_items": [
#     {
#       "responsible": "Jeremiah",
#       "description": "Approve Adam's PR",
#       "deadline": "2023-05-12T23:59:59",
#       "time_sensitivity": "high"
#     },
#     {
#       "responsible": "Jeremiah",
#       "description": "Book a meeting with Nate",
#       "deadline": "2023-05-11T23:59:59",
#       "time_sensitivity": "high"
#     }
#   ]
# }
```

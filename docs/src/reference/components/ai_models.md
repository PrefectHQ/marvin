# AI Model

## Use Large Language Models to *structure data*.

`ai_model` is a decorator that uses Large Language Models to extract structured data 
from unstructured text.

```python
@ai_model
class CompanyProfile(BaseModel):
    name: str
    address: str
    ceo: str
    industry: str
    founded: str

CompanyProfile(company.html) # Structures html page into name, address, etc.

```
## Use Large Language Models to ***infer*** *missing data*.

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

## Use Large Language Models *without prompts*.
`ai_model` is especially useful for data extraction and normalization tasks that are impossible to code. It lets you 
bring your company's data model to your data, extract and infer data that would be difficult to extract.

### No Prompting Required.
- If you can write Pydantic, you can use `ai_model`. No prompts required.
- We use your model's json schema to craft a templated prompt.
- We send that prompt to a Large Languagel Model to extract data.

### No code Required.
- `ai_model` is especially useful for extractive tasks that would be difficult, time-consuming, or impossible to code. They are particularly powerful for parsing and processing strings, but can be used with almost any data structure. 
- `ai_model` satisfies strong-typesafety guarantees so it works with your data.
- `ai_model` works with native python types and Pydantic.

## Examples

```python hl_lines="5"
from typing import Optional
from pydantic import BaseModel
from marvin import ai_model

@ai_model
class Resume(BaseModel):
	first_name: str
	last_name: str
	phone_number: Optional[str]
	email: str

Resume('Ford Prefect • (555) 5124-5242 • ford@prefect.io').json(indent = 2)

#{
# first_name: 'Ford',
# last_name: 'Prefect',
# email: 'ford@prefect.io',
# phone: '(555) 5124-5242',
# }
```


### Structure conversational user input

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

Trip('''\
    I've got all of June off, so hoping to spend the first\
    half of June in London and the second half in Rabat. I love \
    good food and going to museums.
''').json(indent = 2)

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

### Format electronic health records data declaratively

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


PatientData('''\
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
''').json(indent = 2)

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
    lookup: Literal[*django_lookups] = pydantic.Field(description = 'e.g. __iregex')
    value: Any

@ai_model
class DjangoQuery(BaseModel):
    ''' A model representing a Django ORM query'''

    lookups: List[DjangoLookup]

    def to_q(self) -> Q:
        q = Q()
        for lookup in self.lookups:
            q &= Q(**{f"{lookup.field}__{lookup.lookup}": lookup.value})
        return q

DjangoQuery('''\
    All users who joined more than two months ago but\
    haven't made a purchase in the last 30 days'''
).to_q()

# <Q: (AND: 
#     ('date_joined__lte', '2023-03-11'), 
#     ('last_purchase_date__isnull', False), 
#     ('last_purchase_date__lte', '2023-04-11'))>
```

### Extract financial information from messy CSV data

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

CapTable('''\
    In the cap table for Charter, the total authorized shares amount to 13,250,000. 
    The total number of common shares stands at 10,000,000 as specified in Article Fourth, 
    clause (i) and Section 2.2(a)(i). The exact count of common shares outstanding is not 
    available at the moment. Furthermore, there are a total of 3,250,000 preferred shares mentioned 
    in Article Fourth, clause (ii) and Section 2.2(a)(ii). The dividend percentage for Charter is 
    set at 8.00%. Additionally, the mandatory conversion price multiple is 3x, which is 
    derived from the Term Sheet.\
''').json(indent = 2)

# {
#   "total_authorized_shares": 13250000,
#   "total_common_share": 10000000,
#   "total_common_shares_outstanding": null,
#   "total_preferred_shares": 3250000,
#   "conversion_price_multiple": 3
# }

```

### Extract action items from meeting transcripts
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
    time_sensitivity: Literal['low', 'medium', 'high']

@ai_model
class Conversation(BaseModel):
    '''A class representing a team conversation'''

    participants: List[str]
    action_items: List[ActionItem]


Conversation('''
    Adam: Hey Jeremiah can you approve my PR? I requested you to review it.
    Jeremiah: Yeah sure, when do you need it done by?
    Adam: By this Friday at the latest, we need to ship it by end of week.
    Jeremiah: Oh shoot, I need to make sure that Nate and I have a chance to chat first.
    Nate: Jeremiah we can meet today to chat.
    Jeremiah: Okay, I'll book something for today.
''').json(indent = 2)

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

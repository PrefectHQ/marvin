# 🪄 AI Functions

![](../../img/heroes/ai_model_windy_city_hero.png)

!!! tip "Features"

    🎉 Create AI models with a single @ai_model decorator

    🧱 Define Pydantic models that work with both structured data and unstructured text

    🔗 Use AI models to transform raw text into type-safe outputs

    🧙 Enhance your data schema with AI capabilities that would be difficult or impossible to implement manually


AI models are Pydantic models that are defined locally but use AI to process their inputs. Like normal Pydantic models, AI models define a schema that data must comply with. Unlike normal Pydantic models, they can handle unstructured text and automatically convert it into structured, type-safe outputs without requiring any additional source code!

With Marvin, you employ Pydantic to shape your data model as per usual and enhance your model with @ai_model. This imparts an extraordinary capability to your Pydantic model: the capacity to manage unstructured text.

```python hl_lines="5"
from marvin import ai_model
import pydantic
from typing import Optional

@ai_model
class Resume(pydantic.BaseModel):
    first_name: str
    last_name: str
    phone_number: Optional[str]
    email: str

Resume('Ford Prefect • (555) 5124-5242 • ford@prefect.io').json(indent = 2)

#{
#     first_name: 'Ford',
#     last_name: 'Prefect',
#     email: 'ford@prefect.io',
#     phone: '(555) 5124-5242',
# }
```
!!! tip
    AI models work best with GPT-4, but results are still very good with GPT-3.5.

## When to use AI Models

Because AI models integrate seamlessly with the Pydantic framework, they are the most straightforward method to infuse AI capabilities into your data processing pipeline. Just define the Pydantic model with the fields you want to extract from the unstructured text and use it anywhere! However, even though they can feel like magic, it's crucial to understand that there are situations where you might prefer not to use AI models.

Modern LLMs are extraordinarily potent, particularly when dealing with natural language and concepts that are simple to express but challenging to encode algorithmically. However, since they don't actually execute code, computing incredibly precise results can be unexpectedly tricky. Asking an AI to understand intricate legal language is akin to asking a human to do the same -- it's feasible they'll comprehend the right context, but you'll probably want to double-check with a legal expert. On the other hand, you wouldn't ask the legal expert to summarize a complex research paper, which is a perfectly natural thing to ask an AI. 

Therefore, while there are many suitable times to use AI models, it's important to note that they complement traditional data processing models remarkably well and to know when to use one or the other. AI models tend to excel at exactly the things that are very hard to codify algorithmically. If you're performing simple data validation, use a normal Pydantic model. If you're extracting context from unstructured text, use an AI model.

## Basic usage

The `ai_model` decorator can be applied to any Pydantic model. For optimal results, the model should have a descriptive name, annotated fields, and a class docstring. The model does not need to have any pre-processing or post-processing methods written, but advanced users can add these methods to influence the output in two different ways (Note that the data is sent to the LLM as the first root_validator). 

When an `ai_model`-decorated model is instantiated with unstructured text, all available information is sent to the AI, which generates a predicted output. This output is parsed according to the model's schema and returned as the model's instance.

```python hl_lines="5"
from marvin import ai_model
import pydantic
from typing import Optional

@ai_model
class Resume(pydantic.BaseModel):
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


## Advanced usage

Under the hood, AI Models use AI Functions to extract data before it's passed to Pydantic's
validation rules. Unsurprisingly then, AI Models expose the same advanced customizations that AI Functions do. 

```python
@ai_model(llm_model_name='gpt-3.5-turbo', llm_model_temperature=0.2)
class MyFirstModel(pydantic.BaseModel):
    ...
```

You can customize the LLM's temperature, or give your AI Model access to Wikipedia, 
internal documentation, or a sanitized executable environment by using Marvin's [plugins](plugins.md). AI models have no plugins available by default in order to minimize the possibility of confusing behavior. See [AI function docs](ai_functions.md). 

## Examples

### Structing conversational user input

```python
from marvin import ai_model
from typing import Optional, List
import datetime
import pydantic

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

### Text to ORM
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
    ''' A model represneting a Django ORM query'''
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

### Extracting financials from terrible CSV data

```python
from datetime import date
from typing import Optional
from pydantic import BaseModel

@ai_model
class CapTable(pydantic.BaseModel):
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
from marvin import ai_model
import datetime
from typing import Literal, List
import pydantic

class ActionItem(pydantic.BaseModel):
    responsible: str
    description: str
    deadline: Optional[datetime.datetime]
    time_sensitivity: Literal['low', 'medium', 'high']

@ai_model
class Conversation(pydantic.BaseModel):
    '''A class representing a team converastion'''
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

### Schema normalization for data warehousing

```python
from marvin import ai_model
import datetime
from typing import Literal, List
import pydantic
        
class YourSchema(pydantic.BaseModel):
    '''A profile representing a user'''
    first_name: str
    last_name: str
    phone_number: str
    email: str
    date_joined: datetime.datetime
        
@ai_model
class MySchema(pydantic.BaseModel):
    '''A profile representing a user'''
    given_name: str
    family_name: str
    contact_number: str
    email_address: str
    datetime_created: datetime.datetime

# I want the data in my schema.
MySchema(
    # But I only have data from your schema.
    YourSchema(
        first_name = 'Ford',
        last_name = 'Prefect',
        phone_number = '555-555-5555',
        email = 'ford@prefect.io',
        date_joined ='2022-05-11T23:59:59'
    ).json()
).json(indent = 2)

# {
#   "given_name": "Ford",
#   "family_name": "Prefect",
#   "contact_number": "555-555-5555",
#   "email_address": "ford@prefect.io",
#   "datetime_created": "2022-05-11T23:59:59"
# }
```

### Structing data from scraping web pages

```python
from marvin import ai_model
import pydantic
import requests
from bs4 import BeautifulSoup as soup

@ai_model
class Company(pydantic.BaseModel):
    name: str
    industries: List[str]
    description_short: str
    description_long: str
    products: List[str]

response = requests.get('https://www.apple.com')
text = soup(response.content).get_text(separator = ' ', strip = True)
Company(text).json(indent = 2)

# {
#   "name": "Apple",
#   "industries": [
#     "Technology",
#     "Consumer electronics"
#   ],
#   "description_short": "Apple is a multinational technology company that designs, develops, and sells consumer electronics, computer software, and online services.",
#   "description_long": "Apple Inc. is an American multinational technology company that designs, develops, and sells consumer electronics, computer software, and online services. The company's hardware products include the iPhone smartphone, the iPad tablet computer, the Mac personal computer, the iPod portable media player, the Apple Watch smartwatch, the Apple TV digital media player, and the HomePod smart speaker. Apple's software includes the macOS, iOS, iPadOS, watchOS, and tvOS operating systems, the iTunes media player, the Safari web browser, and the iLife and iWork creativity and productivity suites. The online services include the iTunes Store, the iOS App Store, and Mac App Store, Apple Music, and iCloud. The company was founded on April 1, 1976, and incorporated on January 3, 1977, by Steve Jobs, Steve Wozniak, and Ronald Wayne.",
#   "products": [
#     "iPhone",
#     "iPad",
#     "Mac",
#     "iPod",
#     "Apple Watch",
#     "Apple TV",
#     "HomePod",
#     "macOS",
#     "iOS",
#     "iPadOS",
#     "watchOS",
#     "tvOS",
#     "iTunes",
#     "Safari",
#     "iLife",
#     "iWork",
#     "iTunes Store",
#     "iOS App Store",
#     "Mac App Store",
#     "Apple Music",
#     "iCloud"
#   ]
# }

```


### Smart routing in application development
```python
from marvin import ai_model
import datetime
from typing import Literal, List
import pydantic


@ai_model
class Router(pydantic.BaseModel):
    '''A class representing an AI-based router'''
    request: str = pydantic.Field(description = 'Raw user query')
    page: Literal['/profile', '/billing', '/metrics', '/refunds']
        
Router('''I want to update my address''')

# {
#   "request": "I want to update my address",
#   "page": "/profile"
# }

```
# AI Functions

![](../img/heroes/ai_model_windy_city_hero.png)

AI models, grounded in Pydantic, offer a transformative approach to data processing by converting unstructured contexts into type-safe outputs that align with your model schema. This empowers you to interrogate your data through your schema, by combining the potent reasoning capabilities of AI with the type boundaries set by Pydantic.

The challenge of transforming unstructured text data into a structured format is a familiar adversary to engineers, analysts, and data scientists. Traditionally, dealing with unstructured data has been the exclusive domain of specialists, requiring the creation of custom models for each data feature. Overlooked a feature? Time to reset the clock for the next quarter. However, with AI models, adjusting your schema suffices, and Marvin handles the rest.

AI Models make inference declarative - they offer a method to generate synthetic and hyper-realistic training data for custom tools.

Let's illustrate with a practical example. Suppose we aim to devise a system to parse resumes in an applicant tracking system. Resumes are diverse in shape, size, and format. In the past, data scientists would craft an array of regular expressions and custom Natural Language Processing (NLP) models to extract entities such as companies or universities and link them to specific dates. The introduction of each new feature would trigger a fresh development cycle.

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

This is a rather idealized scenario, so let's delve into a more realistic use case. Imagine a real-world situation where resumes are not as neat and predictable. They may include varied sections like work history, education, skills, and they might even contain unconventional structures or typos. Let's enrich our model to handle this complexity:

```python
import datetime
from typing import List, Literal, Optional, Union
import pydantic
from marvin import ai_model

class Institution(pydantic.BaseModel):
    name: str
    start_date: Optional[datetime.date]
    end_date: Union[datetime.date, Literal['Present']]

@ai_model
class Resume(pydantic.BaseModel):
    first_name: str
    last_name: str
    phone_number: Optional[str]
    email: str
    education: List[Institution]
    work_experience: List[Institution]

Resume("""
Ford Prefect
Contact: (555) 5124-5242, ford@prefect.io

Education:
- University of Betelgeuse, 1965 - 1969
- School of Galactic Travel, 1961 - 1965

Work Experience:
- The Hitchhiker's Guide to the Galaxy, Researcher, 1979 - Present
- Galactic Freelancer, 1969 - 1979\
""").json(indent = 2)

# {
#   "first_name": "Ford",
#   "last_name": "Prefect",
#   "phone_number": "(555) 5124-5242",
#   "email": "ford@prefect.io",
#   "education": [
#     {
#       "name": "University of Betelgeuse",
#       "start_date": "1965-01-01",
#       "end_date": "1969-01-01"
#     },
#     {
#       "name": "School of Galactic Travel",
#       "start_date": "1961-01-01",
#       "end_date": "1965-01-01"
#     }
#   ],
#   "work_experience": [
#     {
#       "name": "The Hitchhiker's Guide to the Galaxy",
#       "start_date": "1979-01-01",
#       "end_date": "Present"
#     },
#     {
#       "name": "Galactic Freelancer",
#       "start_date": "1969-01-01",
#       "end_date": "1979-01-01"
#     }
#   ]
# }
```

The magic here is not just that Marvin can parse this structure, but that it can also evolve with the schema. If we decide tomorrow that we want to parse out a new section, or get more granular with the dates, we just change our Pydantic schema, and Marvin takes care of the rest.

One of the most powerful features of AI Models is that it can infer and/or derive information. 
Let's revist the previous example, but let's say we want our Experience model to infer *derived* information.

```python
from marvin import ai_model
import pydantic
from typing import List, Literal, Optional

class Institution(pydantic.BaseModel):
    name: str
    start_date: Optional[datetime.date]
    end_date: Union[datetime.date, Literal['Present']]
        
class Technology(pydantic.BaseModel):
    technology: str = pydantic.Field(description = 'e.g. SQL, Python')
    years_of_experience: int

@ai_model
class Resume(pydantic.BaseModel):
    first_name: str
    last_name: str
    phone_number: Optional[str]
    email: str
    education: List[Institution]
    work_experience: List[Institution]
        
    years_of_experience: int
    technologies: List[Technology]

Resume("""\
Ford Prefect
Contact: (555) 5124-5242, ford@prefect.io

Education:
- University of Betelgeuse, 1965 - 1969
- School of Galactic Travel, 1961 - 1965

Work Experience:
- The Hitchhiker's Guide to the Galaxy, Researcher, 1979 - Present
    • Proficient in data analysis and database management, utilizing tools such as Excel and SQL to maintain a comprehensive interstellar knowledge base.
    • Skilled in interstellar travel logistics, including navigation, transportation, and accommodation arrangements, ensuring smooth and efficient interstellar expeditions.
    • Experienced in multimedia production, utilizing software such as Adobe Creative Suite to create engaging and informative content for various mediums, including video, audio, and graphic design.
- Galactic Freelancer, 1969 - 1979\
""")

# {
#   "first_name": "Ford",
#   "last_name": "Prefect",
#   "phone_number": "(555) 5124-5242",
#   "email": "ford@prefect.io",
#   "education": [
#     {
#       "name": "University of Betelgeuse",
#       "start_date": "1965-01-01",
#       "end_date": "1969-01-01"
#     },
#     {
#       "name": "School of Galactic Travel",
#       "start_date": "1961-01-01",
#       "end_date": "1965-01-01"
#     }
#   ],
#   "work_experience": [
#     {
#       "name": "The Hitchhiker's Guide to the Galaxy",
#       "start_date": "1979-01-01",
#       "end_date": "Present"
#     },
#     {
#       "name": "Galactic Freelancer",
#       "start_date": "1969-01-01",
#       "end_date": "1979-01-01"
#     }
#   ],
#   "years_of_experience": 54,
#   "technologies": [
#     {
#       "technology": "Excel",
#       "years_of_experience": 42
#     },
#     {
#       "technology": "SQL",
#       "years_of_experience": 42
#     },
#     {
#       "technology": "Adobe Creative Suite",
#       "years_of_experience": 42
#     }
#   ]
# }
```

AI Models are not just a tool; they're a revolution in how we handle unstructured data, making our lives easier and our data richer. They open up new avenues for creativity and productivity, effectively blurring the lines between AI and conventional software systems. With AI Models, we are truly pushing the boundaries of what's possible.

For more information about AI Models, including examples, see the [AI Models docs](ai_models.md).
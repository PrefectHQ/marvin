# Classification

Marvin can classify text as one of a number of labels, using a logit bias technique to be faster and less error-prone than "traditional" LLM approaches. This approach can be used to assign a category to text, route an input to one of many outputs, or any other one-of-many objective.
  
The required arguments to `classify` are the text to classify and the classification labels. Users can optionally provide additional instructions to guide the process or provide parameters to the underlying LLM.

!!! example
    
    ```python
    import marvin


    marvin.classify("I love this feature", ["positive", "negative"])
    ```

    !!! success "Result"
        ```python
        "positive"
        ```



<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    Marvin enumerates your options, and uses a <a href="https://twitter.com/AAAzzam/status/1669753721574633473">clever logit bias trick</a> to force an LLM to deductively choose the index of the best option given your provided input. It then returns the choice associated with that index.
  </p>
</div>


## Lables

You can provide labels to `classify` in a variety of ways: as an `Enum`, as a `Literal` type, or as a list of options.

The flexibility in providing labels to `classify` allows you to choose the method that best suits your needs. If you want to use the same set of labels throughout your application, you can define them as an `Enum`. This has the added benefit of making your code easier to understand and maintain, and can also be used for automatic documentation. On the other hand, if your labels are dynamic and change based on the context, you can provide them as a list. This gives you the flexibility to define your labels on the fly. Providing labels as a `Literal` is useful for inferring labels from function signatures and other type hints.

Here are examples of the three approaches, starting with a list:

```python
classify("go to bed", ["house", "office", "store"]) # "house"
```

a literal:

```python
classify("go to bed", Literal["house", "office", "store"]) # "house"
```

and an enum:

```python
class Place(Enum):
    house = 'house'
    office = 'office'
    store = 'store'

classify("go to bed", Place) # Place.house
```

## Instructions

By default, `classify` does its best to match the text to the provided labels. For more control, you can supply additional `instructions`. Instructions are expressed in natural language and can be gentle hints or completely change the behavior. Instructions can also be used to provide examples or context.

Here, the instructions are used to 
```python
# Define personas through examples
personas = {
    "Tech Enthusiast": [
        "I'm always excited about the latest tech gadgets.", 
        "I spend my weekends coding and trying out new software."
        ],
    "Fitness Fanatic": [
        "I never miss a day at the gym.", 
        "My ideal vacation involves a hiking or biking adventure."
        ],
    "Foodie": [
        "I love trying new restaurants and experimenting with recipes.", 
        "My Instagram is full of pictures of my culinary creations."
        ]
}

# Statement to classify
statement = "This weekend I'm planning to check out the new health-focused cafe in town."

# Classify the statement into one of the personas
persona = marvin.classify(
    statement, 
    labels=list(personas.keys()), 
    instructions="Match the statement to the persona based on the given examples."
)
# "Fitness Fanatic"
```

## Enums as classifiers

In addition to providing enums as labels to `classify`, Marvin supports turning enums *into* classifiers with the `@classifier` decorator. Classifier enums work exactly like regular enums, except that they can be instantiated with natural language. For most use cases, we recommend using the `classify` function because it is more flexible (and can be provided any enum as labels).

Here is an example of using the `classifier` decorator:
```python
import marvin
from enum import Enum


@marvin.classifier
class Sentiment(Enum)
    positive = "positive"
    negative = "negative"


Sentiment("I love this feature")
# Sentiment.positive
```

And here is an equivalent outcome from providing an enum to the `classify` function:
```python
import marvin
from enum import Enum


class Sentiment(Enum)
    positive = "positive"
    negative = "negative"


marvin.classify("I love this feature", Sentiment)
# Sentiment.positive
```


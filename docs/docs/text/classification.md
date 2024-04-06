# Classifying text

Marvin has a powerful classification tool that can be used to categorize text into predefined labels. It uses a logit bias technique that is faster and more accurate than traditional LLM approaches. This capability is essential across a range of applications, from categorizing user feedback and tagging issues to managing inputs in natural language interfaces.

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    The <code>classify</code> function categorizes text from a set of provided labels. <code>@classifier</code> is a class decorator that allows you to instantiate Enums with natural language.
  </p>
</div>


!!! example "Example: categorize user feedback"
    Categorize user feedback into labels such as "bug", "feature request", or "inquiry":
    
    ```python
    import marvin

    category = marvin.classify(
        "The app crashes when I try to upload a file.", 
        labels=["bug", "feature request", "inquiry"]
    )
    ```

    !!! success "Result"
        Marvin correctly identifies the statement as a bug report.
        ```python
        assert category == "bug"
        ```


<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    Marvin enumerates your options, and uses a <a href="https://twitter.com/AAAzzam/status/1669753721574633473">clever logit bias trick</a> to force the LLM to deductively choose the index of the best option given your provided input. It then returns the choice associated with that index.
  </p>
</div>


## Providing labels

Marvin's classification tool is designed to accommodate a variety of label formats, each suited to different use cases.

### Lists

When quick, ad-hoc categorization is required, a simple list of strings is the most straightforward approach. For example:

!!! example "Example: sentiment analysis"
    
    ```python
    import marvin

    sentiment = marvin.classify(
        "Marvin is so easy to use!", 
        labels=["positive", "negative", "meh"]
    )
    ```

    !!! success "Result"
        ```python
        assert sentiment == "positive"
        ```


### Enums

For applications where classification labels are more structured and recurring, Enums provide an organized and maintainable solution:

```python
from enum import Enum
import marvin

class RequestType(Enum):
    SUPPORT = "support request"
    ACCOUNT = "account issue"
    INQUIRY = "general inquiry"

request = marvin.classify("Reset my password", RequestType)
assert request == RequestType.ACCOUNT
```

This approach not only enhances code readability but also ensures consistency across different parts of an application.

### Booleans

For cases where the classification is binary, Booleans are a simple and effective solution. As a simple example, you could map natural-language responses to a yes/no question to a Boolean label:

```python
import marvin

response = marvin.classify('no way', bool)
assert response is False

```

### Literals

In scenarios where labels are part of the function signatures or need to be inferred from type hints, `Literal` types are highly effective. This approach is particularly useful in ensuring type safety and clarity in the codebase:

```python
from typing import Literal
import marvin

RequestType = Literal["support request", "account issue", "general inquiry"]

request = marvin.classify("Reset my password", RequestType)
assert request == "account issue"
```


## Providing instructions

The `instructions` parameter in `classify()` offers an additional layer of control, enabling more nuanced classification, especially in ambiguous or complex scenarios.

### Gentle guidance

For cases where the classification needs a slight nudge for accuracy, gentle instructions can be very effective:

```python
comment = "The interface is confusing."
category = marvin.classify(
    comment,
    ["usability feedback", "technical issue", "feature request"],
    instructions="Consider it as feedback if it's about user experience."
)
assert category == "usability feedback"
```

### Adding detailed instructions

In more complex cases, where the context and specifics are crucial for accurate classification, detailed instructions play a critical role:

```python
# Classifying a customer review as positive, negative, or neutral
review_sentiments = [
    "Positive",
    "Negative",
    "Neutral"
]

review = "The product worked well, but the delivery took longer than expected."

# Without instructions
predicted_sentiment = marvin.classify(
    review,
    labels=review_sentiments
)
assert predicted_sentiment == "Negative"

# With instructions
predicted_sentiment = marvin.classify(
    review,
    labels=review_sentiments,
    instructions="Focus on the sentiment towards the product itself, rather than the delivery experience."
)
assert predicted_sentiment == "Positive"
```

## Enums as classifiers

While the primary focus is on the `classify` function, Marvin also includes the `classifier` decorator. Applied to Enums, it enables them to be used as classifiers that can be instantiated with natural language. This interface is particularly handy when dealing with a fixed set of labels commonly reused in your application.


```python
@marvin.classifier
class IssueType(Enum):
    BUG = "bug"
    IMPROVEMENT = "improvement"
    FEATURE = "feature"

issue = IssueType("There's a problem with the login feature")
assert issue == IssueType.BUG
```

While convenient for certain scenarios, it's recommended to use the `classify` function for its greater flexibility and broader application range.

## Model parameters
You can pass parameters to the underlying API via the `model_kwargs` argument of `classify` or `@classifier`. These parameters are passed directly to the API, so you can use any supported parameter.

## Best practices

1. **Choosing the right labels**: Opt for labels that are mutually exclusive and collectively exhaustive for your classification context. This ensures clarity and prevents overlaps in categorization.
2. **Effective use of instructions**: Provide clear, concise, and contextually relevant instructions. This enhances the accuracy of the classification, especially in ambiguous or complex cases.
3. **Iterative testing and refinement**: Continuously test and refine your classification criteria and instructions based on real-world feedback. This iterative process helps in fine-tuning the classification logic for better results.
4. **Prefer `classify()` over `@classifier`**: `classify()` is more versatile and adaptable for a wide range of scenarios. It should be the primary tool for classification tasks in Marvin.

## Async support

If you are using Marvin in an async environment, you can use `classify_async`:

```python
result = await marvin.classify_async(
    "The app crashes when I try to upload a file.", 
    labels=["bug", "feature request", "inquiry"]
) 

assert result == "bug"
```

## Mapping

To classify a list of inputs at once, use `.map`:

```python
inputs = [
    "The app crashes when I try to upload a file.",
    "How do change my password?"
]
result = marvin.classify.map(inputs, ["bug", "feature request", "inquiry"])
assert result == ["bug", "inquiry"]
```

(`marvin.classify_async.map` is also available for async environments.)

Mapping automatically issues parallel requests to the API, making it a highly efficient way to classify multiple inputs at once. The result is a list of classifications in the same order as the inputs.

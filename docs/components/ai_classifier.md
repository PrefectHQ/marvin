# AI Classifier

AI Classifiers are a high-level component, or building block, of Marvin. Like all Marvin components, they are completely standalone: you're free to use them with or without the rest of Marvin.

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    <code>@ai_classifier</code> is a decorator that lets you use LLMs to choose options, tools, or classify input. 
  </p>
</div>

!!! example 
    ```python
    from marvin import ai_classifier
    from enum import Enum

    class CustomerIntent(Enum):
        """Classifies the incoming users intent"""

        SALES = 'SALES'
        TECHNICAL_SUPPORT = 'TECHNICAL_SUPPORT'
        BILLING_ACCOUNTS = 'BILLING_ACCOUNTS'
        PRODUCT_INFORMATION = 'PRODUCT_INFORMATION'
        RETURNS_REFUNDS = 'RETURNS_REFUNDS'
        ORDER_STATUS = 'ORDER_STATUS'
        ACCOUNT_CANCELLATION = 'ACCOUNT_CANCELLATION'
        OPERATOR_CUSTOMER_SERVICE = 'OPERATOR_CUSTOMER_SERVICE'

    @ai_classifier
    def classify_intent(text: str) -> CustomerIntent:
        '''Classifies the most likely intent from user input'''

    classify_intent("I got double charged, can you help me out?")
    ```
    !!! success "Result"
        ```python 
        <CustomerIntent.RETURNS_REFUNDS: 'RETURNS_REFUNDS'>
        ```



<div class="admonition info">
  <p class="admonition-title">How it works</p>
  <p>
    Marvin enumerates your options, and uses a <a href="https://twitter.com/AAAzzam/status/1669753721574633473">clever logit bias trick</a> to force an LLM to deductively choose the index of the best option given your provided input. It then returns the choice associated with that index.
  </p>
</div>

<div class="admonition tip">
  <p class="admonition-title">When to use</p>
  <p>
    <ol>
    <li> Best for classification tasks when no training data is available. 
    <li> Best for writing classifiers that need deduction or inference.
    </ol>
  </p>
</div>


<div class="admonition warning">
  <p class="admonition-title">OpenAI compatibility</p>
  <p> The technique that AI Classifiers use for speed and correctness is only available through the OpenAI API at this time. Therefore, AI Classifiers can only be used with OpenAI-compatible LLMs, including the Azure OpenAI service.
  </p>
</div>


## Features
#### 🚅 Bulletproof

`ai_classifier` will always output one of the options you've given it


```python
from marvin import ai_classifier
from enum import Enum


@ai_classifier
class AppRoute(Enum):
    """Represents distinct routes command bar for a different application"""

    USER_PROFILE = "/user-profile"
    SEARCH = "/search"
    NOTIFICATIONS = "/notifications"
    SETTINGS = "/settings"
    HELP = "/help"
    CHAT = "/chat"
    DOCS = "/docs"
    PROJECTS = "/projects"
    WORKSPACES = "/workspaces"


AppRoute("update my name")
```




    <AppRoute.USER_PROFILE: '/user-profile'>



#### 🏃 Fast

`ai_classifier` only asks your LLM to output one token, so it's blazing fast - on the order of ~200ms in testing.

#### 🫡 Deterministic

`ai_classifier` will be deterministic so long as the underlying model and options does not change.

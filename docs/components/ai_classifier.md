# AI Classifier

AI Classifiers are a high-level component, or building block, of Marvin. Like all Marvin components, they are completely standalone: you're free to use them with or without the rest of Marvin.

<div class="admonition abstract">
  <p class="admonition-title">What it does</p>
  <p>
    <code>@ai_classifier</code> is a decorator that lets you use LLMs to choose options, tools, or classify input. 
  </p>
</div>


```python
from marvin import ai_classifier
from enum import Enum


@ai_classifier
class CustomerIntent(Enum):
    """Classifies the incoming users intent"""

    SALES = 1
    TECHNICAL_SUPPORT = 2
    BILLING_ACCOUNTS = 3
    PRODUCT_INFORMATION = 4
    RETURNS_REFUNDS = 5
    ORDER_STATUS = 6
    ACCOUNT_CANCELLATION = 7
    OPERATOR_CUSTOMER_SERVICE = 0


CustomerIntent("I got double charged, can you help me out?")
```




    <CustomerIntent.BILLING_ACCOUNTS: 3>



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

## Creating an AI Classifier

AI Classifiers are Python `Enums`, or classes that can represent one of many possible options. To build an effective AI Classifier, be as specific as possible with your class name, docstring, option names, and option values.

To build a minimal AI Classifier, decorate any standard enum, like this:


```python
from marvin import ai_classifier
from enum import Enum


@ai_classifier
class Sentiment(Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"


Sentiment("That looks great!")
```




    <Sentiment.POSITIVE: 'POSITIVE'>



Because AI Classifiers are enums, you can use any enum construction you want, including the all-caps string approach above, integer values, `enum.auto()`, or complex values. The only thing to remember is that the class you build *is* essentially the instruction that gets sent to the LLM, so the more information you provide, the better your classifier will behave.

For example, you may want to have a classifier that has a Python object (like an AI Model!) as its value, but still need to provide instruction hints to the LLM. One way to achieve that is to add descriptions to your classifier's values that will become visible to the LLM:



```python
# dummy objects that stand in for complex tools
WebSearch = lambda: print("Searching!")
Calculator = lambda: print("Calculating!")
Translator = lambda: print("Translating!")


@ai_classifier
class Router(Enum):
    translate = dict(tool=Translator, description="A translator tool")
    web_search = dict(tool=WebSearch, description="A web search tool")
    calculator = dict(tool=Calculator, description="A calculator tool")


result = Router("Whats 2+2?")
result.value["tool"]()
```

    Calculating!


## Configuring an AI Classifier

In addition to how you define the AI classifier itself, there are two ways to control its behavior at runtime: `instructions` and `model`.

### Providing instructions
You can control an AI classifier's behavior by providing instructions. This can either be provided globally as the classifier's docstring or on a per-call basis when you instantiate it.


```python
@ai_classifier
class Sentiment(Enum):
    """
    Score the sentiment of provided text.
    """

    POSITIVE = 1
    NEGATIVE = -1


Sentiment("Everything is awesome!")
```




    <Sentiment.POSITIVE: 1>




```python
@ai_classifier
class Sentiment(Enum):
    """
    How would a very very sad person rate the text?
    """

    POSITIVE = 1
    NEGATIVE = -1


Sentiment("Everything is awesome!")
```




    <Sentiment.NEGATIVE: -1>



Instructions can also be provided for each call:


```python
@ai_classifier
class Sentiment(Enum):
    POSITIVE = 1
    NEGATIVE = -1


Sentiment("Everything is awesome!", instructions="It's opposite day!")
```




    <Sentiment.NEGATIVE: -1>



### Configuring the LLM
By default, `@ai_classifier` uses the global LLM settings. To specify a particular LLM, pass it as an argument to the decorator. 


```python
from marvin.engine.language_models import chat_llm


@ai_classifier(model=chat_llm("openai/gpt-3.5-turbo-0613"))
class Sentiment(Enum):
    POSITIVE = 1
    NEGATIVE = -1


Sentiment("Everything is awesome!")
```




    <Sentiment.POSITIVE: 1>



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

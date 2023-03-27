# AI Functions


Marvin's `ai_fn` decorator is the simplest way to add AI to your code. It can take any function definition and "magically" return the result of calling that function. Under the hood, `ai_fn` uses [bots](bots.md) to analyze, predict, and parse the output.

Note: `ai_fn` works best with GPT-4.

```python hl_lines="3"
from marvin import ai_fn

@ai_fn
def list_fruit(n: int) -> list[str]:
    """Generate a list of n fruit"""


list_fruit(3) # ["apple", "banana", "orange"]
```


## Usage

The `ai_fn` decorator can be applied to any function. For best results, the function should have an informative name, annotated input types, a return type, and a docstring. The function does *not* need to have any source code written, but advanced users can add source code to influence the output in two different ways (see "writing source code")

When a `ai_fn`-decorated function is called, all available information is sent to the AI, which generates a predicted output. This output is parsed and returned as the function result.

### Basic usage
Here is an overview of basic decorator use. First, you create a function definition and decorate it with `@ai_fn`. You don't need to add any source code. Then you call the function on some inputs!

```python
from marvin import ai_fn

@ai_fn
def my_function(input: Type) -> ReturnType:
    """ 
    A docstring that describes the function's purpose and behavior.
    """

# call the function
my_function(input="my input")
```

Note the following:

1. Apply the decorator to the function. It does not need to be called (though it can take optional arguments)
2. The function should have a descriptive name
3. The function's inputs should have type annotations
4. The function's return type should be annotated
5. The function has a descriptive docstring
6. The function does not need any source code!

### Advanced usage

#### Calling the function
By default, the `ai_fn` decorator will call your function and supply the return value to the AI. For functions without source code, this obviously has no consequence. However, you can take advantage of this fact to influence the AI result by returning helpful or preprocessed outputs. Since the AI sees the source code as well as the return value, you can also influence it through comments. 

You can see this strategy used in the example that [summarizes text from Wikipedia](#summarize-text-from-wikipedia). In the example, the function takes in a page's title and uses it to load the page's content. The content is returned and used by the AI for summarization.

To disable this behavior entirely, call the decorator as `@ai_fn(call_function=False)`.

#### Async functions
The `ai_fn` decorator works with async functions.

```python
from marvin import ai_fn

@ai_fn
async def f(x: int) -> int:
    """Add 100 to x"""

await f(5)
```

#### Complex annotations
Annotations don't have to be types; they can be complex objects or even string descriptions. For inputs, the annotation is transmitted to the AI as-is. Return annotations are processed through Marvin's `ResponseFormatter` mechanism, which puts extra emphasis on compliance. This means you can supply complex instructions in your return annotation. However, note that you must include the word `json` in order for Marvin to automatically parse the result into native objects!

Therefore, consider these two approaches to defining an output:
```python
from marvin import ai_fn

@ai_fn
def fn_with_docstring(n: int) -> list[dict]:
    """
    Generate a list of n people with names and ages
    """



@ai_fn
def fn_with_string_annotation(n: int) -> 'a json list of dicts that have keys for name and age':
    """
    Generate a list of n people
    """



class Person(pydantic.BaseModel):
    name: str
    age: int

@ai_fn
def fn_with_structured_annotation(n: int) -> list[Person]:
    """
    Generate a list of n people
    """
```
All three of these functions will give similar output (though the last one, `fn_with_structured_annotation`, will return Pydantic models instead of dicts). However, they are increasingly specific in their instructions to the AI. While you should always try to make your intent as clear as possible to the AI, you should also choose an approach that will make sense to other people reading your code. This would lead us to probably prefer the first or third functions over the second, which doesn't look like a typical Python function.



## Examples

### Generate a list of fruit
```python
from marvin import ai_fn

@ai_fn
def list_fruit(n: int) -> list[str]:
    """Generate a list of n fruit"""


list_fruit(3) # ["apple", "banana", "orange"]
```

### Generate fake data according to a schema
```python
from marvin import ai_fn

@ai_fn
def fake_people(n: int) -> list[dict]:
    """
    Generates n examples of fake data representing people, 
    each with a name and an age.
    """


fake_people(3)
# [{'name': 'John Doe', 'age': 29},
#  {'name': 'Jane Smith', 'age': 34},
#  {'name': 'Alice Johnson', 'age': 42}]
```

### Correct spelling and grammar

```python
from marvin import ai_fn

@ai_fn
def fix_sentence(sentence: str) -> str:
    """
    Fix all grammatical and spelling errors in a sentence
    """

fix_sentence("he go to mcdonald and buy burg") # "He goes to McDonald's and buys a burger."
```

### Summarize text

This function takes any text and summarizes it. See the next example for a
function that can also access Wikipedia automatically.

```python
from marvin import ai_fn

@ai_fn
def summarize(text: str) -> str:
    """
    Summarize the provided text
    """

import wikipedia
page = wikipedia.page('large language model')
summarize(text=page.content)
# Large language models (LLMs) are neural networks with billions of parameters
# trained on massive amounts of unlabelled text. They excel at various tasks and
# can capture much of human language's syntax and semantics. LLMs use the
# transformer architecture and are trained using unsupervised learning. Their
# applications include fine-tuning and prompting for specific natural language
# processing tasks.
```

### Summarize text after loading a Wikipedia page

This example demonstrates how `ai_fn` can call a function to get additional information that can be used in producing a result. Here, the function downloads content from Wikipedia given a title.

```python
from marvin import ai_fn

@ai_fn
def summarize_from_wikipedia(title: str) -> str:
    """
    Loads the wikipedia page corresponding to the provided 
    title and returns a summary of the content.
    """
    import wikipedia
    page = wikipedia.page(title)

    # the content to summarize
    return page.content


summarize_from_wikipedia(title='large language model')
# A large language model (LLM) is a language model consisting of a neural
# network with many parameters (typically billions of weights or more), trained
# on large quantities of unlabelled text using self-supervised learning. LLMs
# emerged around 2018 and perform well at a wide variety of tasks. This has
# shifted the focus of natural language processing research away from the
# previous paradigm of training specialized supervised models for specific
# tasks.
```

### Suggest a title after loading a URL

This example demonstrates how `ai_fn` can call a function to get additional information that can be used in producing a result. Here, the function loads an article and then suggests a title for it.

```python
from marvin import ai_fn

@ai_fn
def suggest_title(url: str) -> str:
    """
    Suggests a title for the article found at the provided URL
    """

    import httpx

    # load the url
    response = httpx.get(url)

    # return the url contents 
    return marvin.utilities.strings.html_to_content(response.content)


suggest_title(url="https://techcrunch.com/2023/03/14/openai-releases-gpt-4-ai-that-it-claims-is-state-of-the-art/")
# OpenAI Releases GPT-4: State-of-the-Art AI Model with Improved Image and Text Understanding
```

### Generate rhymes

```python
from marvin import ai_fn

@ai_fn
def rhyme(word: str) -> str:
    """
    Generate a word that rhymes with the supplied `word`
    """

rhyme("blue") # glue
```

### Find words meeting specific criteria

```python
from marvin import ai_fn

@ai_fn
def find_words(text: str, criteria: str) -> list[str]:
    """
    Given text and some criteria, returns a list of 
    every word meeting that criteria.
    """

text = "The quick brown fox jumps over the lazy dog."
find_words(text, criteria="adjectives") # ["quick", "brown", "lazy"]
find_words(text, criteria="colors") # ["brown"]
find_words(text, criteria="animals that aren't dogs") # ["fox"]
```



### Suggest emojis

```python
from marvin import ai_fn

@ai_fn
def get_emoji(text: str) -> str:
    """
    Returns an emoji that describes the provided text.
    """

get_emoji("incredible snack") # '🍿'
```


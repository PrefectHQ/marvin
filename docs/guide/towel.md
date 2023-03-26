# Towel


Marvin's `towel` decorator is the simplest way to add AI to your code. It can take any function definition and "magically" return the result of calling that function. Under the hood, it uses Marvin `Bots` to analyze, predict, and parse the output.

Note: `towel` works best with GPT-4.

```python hl_lines="3"
from marvin import towel

@towel()
def list_fruit(n: int) -> list[str]:
    """Generate a list of n fruit"""


list_fruit(3) # ["apple", "banana", "orange"]
```


## Usage

The `towel` decorator can be applied to any function. For best results, the function should have an informative name, annotated input types, a return type, and a docstring. The function does *not* need to have any source code written, but advanced users can add source code to influence the output in two different ways (see "writing source code")

When a `towel`-decorated function is called, all available information is sent to the AI, which generates a predicted output. This output is parsed and returned as the function result.

### Basic usage
Here is an overview of basic decorator use:

```python
from marvin import towel

@towel()
def your_function(input: Type) -> ReturnType:
    """ 
    A docstring that describes the function's purpose and behavior.
    """
```

Note the following:

1. The decorator must be called when it is applied to the function. This is because it takes (optional) arguments.
2. The function should have a descriptive name
3. The function's inputs should have type annotations
4. The function's return type should be annotated
5. The function has a descriptive docstring
6. The function does not need any source code!

### Advanced usage

#### Calling the function
By default, the `towel` decorator will call your function and supply the return value to the AI. For functions without source code, this obviously has no consequence. However, you can take advantage of this fact to influence the AI result by returning helpful or preprocessed outputs. Since the AI sees the source code as well as the return value, you can also influence it through comments. 

You can see this strategy used in the example that [summarizes text from Wikipedia](#summarize-text-from-wikipedia). In the example, the function takes in a page's title and uses it to load the page's content. The content is returned and used by the AI for summarization.

To disable this behavior entirely, call the decorator as `@towel(call_function=False)`.

#### Async functions
The towel decorator works with async functions.

```python
@towel()
async def f(x: int) -> int:
    """Add 100 to x"""

await f(5)
```

#### Complex annotations
Annotations don't have to be types; they can be complex objects or even string descriptions. For inputs, the annotation is transmitted to the AI as-is. Return annotations are processed through Marvin's `ResponseFormatter` mechanism, which puts extra emphasis on compliance. This means you can supply complex instructions in your return annotation. However, note that you must include the word `json` in order for Marvin to automatically parse the result into native objects!

Therefore, consider these two approaches to defining an output:
```python
@towel()
def fn_with_docstring(n: int) -> list[dict]:
    """
    Generate a list of n people with names and ages
    """



@towel()
def fn_with_string_annotation(n: int) -> 'a json list of dicts that have keys for name and age':
    """
    Generate a list of n people
    """



class Person(pydantic.BaseModel):
    name: str
    age: int

@towel()
def fn_with_structured_annotation(n: int) -> list[Person]:
    """
    Generate a list of n people
    """
```
All three of these functions will give similar output (though the last one, `fn_with_structured_annotation`, will return Pydantic models instead of dicts). However, they are increasingly specific in their instructions to the AI. While you should always try to make your intent as clear as possible to the AI, you should also choose an approach that will make sense to other people reading your code. This would lead us to probably prefer the first or third functions over the second, which doesn't look like a typical Python function.



## Examples

### Generate a list of fruit
```python
@towel()
def list_fruit(n: int) -> list[str]:
    """Generate a list of n fruit"""


list_fruit(3) # ["apple", "banana", "orange"]
```

### Generate fake data according to a schema
```python
@towel()
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
@towel()
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
@towel()
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

### Summarize text from Wikipedia

This example demonstrates how `towel` can call a function to get additional information that can be used in producing a result. Here, the function downloads content from Wikipedia given a title.

```python
@towel()
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

### Generate rhymes

```python
@towel()
def rhyme(word: str) -> str:
    """
    Generate a word that rhymes with the supplied `word`
    """

rhyme("blue") # glue
```

### Find words meeting specific criteria

```python
@towel()
def find_words(text: str, criteria: str) -> list[str]:
    """
    Given text and some criteria, returns a list of every word meeting that criteria.
    """

find_words("The quick brown fox jumps over the lazy dog.", criteria="adjectives") # ["quick", "brown", "lazy"]
find_words("The quick brown fox jumps over the lazy dog.", criteria="colors") # ["brown"]
find_words("The quick brown fox jumps over the lazy dog.", criteria="animals that aren't dogs") # ["fox"]
```


## Why is this called "towel"?
> A towel is just about the most massively useful thing an interstellar hitchhiker can carry. Partly because it has great practical value. You can wrap it around you for warmth as you bound across the cold moons of Jaglan Beta; you can lie on it on the brilliant marble-sanded beaches of Santraginus V, inhaling the heady sea vapours; you can sleep under it beneath the stars which shine so redly on the desert world of Kakrafoon; use it to sail a miniraft down the slow heavy River Moth; wet it for use in hand-to-hand combat; wrap it around your head to ward off noxious fumes or avoid the gaze of the Ravenous Bugblatter Beast of Traal (a mind-bogglingly stupid animal, it assumes that if you can't see it, it can't see you — daft as a brush, but very very ravenous); you can wave your towel in emergencies as a distress signal, and of course you can dry yourself off with it if it still seems to be clean enough.
>
> More importantly, a towel has immense psychological value. For some reason, if a strag discovers that a hitchhiker has his towel with him, he will automatically assume that he is also in possession of a toothbrush, washcloth, soap, tin of biscuits, flask, compass, map, ball of string, gnat spray, wet-weather gear, space suit etc., etc. Furthermore, the strag will then happily lend the hitchhiker any of these or a dozen other items that the hitchhiker might accidentally have "lost." What the strag will think is that any man who can hitch the length and breadth of the Galaxy, rough it, slum it, struggle against terrible odds, win through and still knows where his towel is, is clearly a man to be reckoned with.
>
> -- The Hitchhiker's Guide to the Galaxy
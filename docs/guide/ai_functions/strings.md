# AI Functions for strings

## Actual title case

Return a title case string that you would want to use in a title.

The Python string method [`.title()`](https://docs.python.org/3/library/stdtypes.html#str.title) makes the first letter of every word uppercase and the remaing letters lowercase. This result isn't what you want to use for the title of a piece of writing, generally. `title_case` takes a string and returns a string you can use in a title.

```python

from marvin.ai_functions.strings import title_case

title_case("the european went over to canada, eh?")
# The European Went Over to Canada, Eh?
```


# AI Functions for strings

## Fix capitalization
Given a string that may not have correct capitalization, fix its capitalization but make no other changes.

```python
from marvin.ai_functions.strings import fix_capitalization

fix_capitalization("the european went over to canada, eh?")
# The European went over to Canada, eh?
```

## APA title case

Return a title case string that you would want to use in a title.

The Python string method [`.title()`](https://docs.python.org/3/library/stdtypes.html#str.title) makes the first letter of every word uppercase and the remaing letters lowercase. This result isn't what you want to use for the title of a piece of writing, generally. `title_case` takes a string and returns a string you can use in a title.

```python
from marvin.ai_functions.strings import title_case

title_case("the european went over to canada, eh?")
# The European Went Over to Canada, Eh?
```

## RRules

Generate RRules (structured objects that represent possibly recurring calendar events) from natural language.

```python
from marvin.ai_functions.strings import rrule

rrule("9am on the first business day of the quarter")
# "RRULE:FREQ=MONTHLY;BYSETPOS=1;BYDAY=MO,TU,WE,TH,FR;BYMONTH=1,4,7,10;BYHOUR=9;BYMINUTE=0;BYSECOND=0;BYWEEKNO=1,14,27,40"
```
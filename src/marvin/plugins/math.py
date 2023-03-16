import math
import operator
import random

from simpleeval import simple_eval

from marvin.plugins import Plugin

math_functions = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "sqrt": math.sqrt,
    "ln": math.log,
    "log": math.log10,
    "abs": operator.abs,
    "^": operator.pow,
    "e": math.e,
    "pi": math.pi,
    "π": math.pi,
}


class Calculator(Plugin):
    name: str = "calculator"
    description: str = (
        "Compute arithmetic expressions. Expressions can ONLY include operators,"
        f" numbers, and the functions {', '.join(math_functions)}; not strings or"
        " units."
    )

    async def run(self, expression: str) -> str:
        return simple_eval(expression, functions=math_functions)


class RandomNumber(Plugin):
    name: str = "rng"

    description: str = "Use this plugin to generate a random number between `a` and `b`"

    def run(self, a: float, b: float) -> float:
        return a + (b - a) * random.random()

import ast
import math
import operator
import random

from simpleeval import SimpleEval, safe_power

from marvin.plugins import Plugin

math_functions = {
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "sqrt": math.sqrt,
    "ln": math.log,
    "log": math.log10,
    "abs": operator.abs,
    "e": math.e,
    "pi": math.pi,
    "π": math.pi,
    "random": lambda a=0, b=1: a + (b - a) * random.random(),
    "randint": random.randint,
}


_calculator = SimpleEval(functions=math_functions)
_calculator.operators[ast.BitXor] = safe_power


class Calculator(Plugin):
    name: str = "calculator"
    description: str = (
        "Compute an arithmetic expression. The Expression can ONLY include operators,"
        f" numbers, and the functions {', '.join(math_functions)}; not strings or"
        " units. One expression at a time."
    )

    async def run(self, expression: str) -> str:
        return _calculator.eval(expression)


class RandomNumber(Plugin):
    name: str = "rng"
    description: str = (
        "Use this plugin to generate a random number between `min` and `max`"
    )

    def run(self, min: float, max: float) -> float:
        return min + (max - min) * random.random()

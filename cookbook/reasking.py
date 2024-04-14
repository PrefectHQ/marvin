from typing import Annotated

import marvin
from marvin.beta.retries import retry_on_validation_error
from pydantic import AfterValidator


def verify_random_number(number: int) -> int:
    if number != 37:
        raise ValueError("Everyone knows the most random number is 37!")
    return number


RandomNumber = Annotated[int, AfterValidator(verify_random_number)]


@retry_on_validation_error  # shows the validation error message in subsequent retries
@marvin.fn
def get_random_number() -> RandomNumber:
    """returns a random number"""


if __name__ == "__main__":
    print(get_random_number())

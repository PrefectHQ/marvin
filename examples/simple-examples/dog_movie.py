from marvin import ai_fn


@ai_fn()
def make_script(dog1: str, dog2: str) -> list[str]:
    """returns a 50 to 100 word plot of a movie about dogs named {dog1} and {dog2}"""


print(make_script("Mila", "Ralphie"))

# ['Mila and Ralphie are two dogs who find themselves lost in the big city. Together, they must navigate the streets, avoid danger, and ultimately find their way back home. Along the way, they meet a cast of colorful characters who help them on their journey. This heartwarming adventure will leave you cheering for these two brave pups.']

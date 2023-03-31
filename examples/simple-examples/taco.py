from marvin import ai_fn


@ai_fn
def taco_of_the_day(ingredient: list[str]) -> list[str]:
    """Generates a taco recipe and list of instructions to cook,
    that includes the listed ingredients as well as additional toppings that are not listed
    """  # noqa: E501


ingredients = ["chorizo", "goat cheese"]
t = taco_of_the_day(ingredients)
print(t)

# ["Start by heating up the chorizo in a pan over medium-high heat.
# Once it's browned and crispy, remove it from the pan and set it aside.
# Next, start building your taco. Grab a tortilla and spread a bit of goat cheese on it, then top it with the chorizo. # noqa: E501
# Add some shredded lettuce and diced tomatoes, then drizzle with your favorite hot sauce. # noqa: E501
# Enjoy your delicious chorizo and goat cheese tacos!"]

import marvin
from rich import print
from rich.prompt import Prompt
from rich.table import Table
from pydantic import BaseModel, Field

class ShoppingItem(BaseModel):
    item: str
    retrieved: bool = False

class ShoppingListState(BaseModel):
    items: list[ShoppingItem] = Field(default_factory=list)


def create_shopping_list() -> ShoppingListState:

    items = []

    while True:
        item = Prompt.ask("Enter an item to add to your shopping list (or press Enter to finish)")
        if not item:
            break
        
        items.append(ShoppingItem(item=item))

    display_shopping_list(state := ShoppingListState(items=items))

    return state

def display_shopping_list(state) -> None:
    table = Table(title="Shopping List")
    table.add_column("Item", style="cyan")
    table.add_column("Retrieved", style="magenta")

    for item in state.items:
        table.add_row(item.item, "Yes" if item.retrieved else "No")

    print(table)

def check_shopping_list(app: marvin.beta.applications.Application, image_url: str) -> list[str]:
    """returns any missing items that are on the list but not in the image"""
    missing_items = marvin.beta.cast(
        marvin.beta.Image(image_url),
        instructions=f"Did I forget anything on my list: {[item.item for item in app.state.value.items]}?",
    )
    return missing_items


def play_game() -> None:

    shopping_list = create_shopping_list()

    with marvin.beta.Application(
        name="Grocery Shopping Assistant",
        instructions=(
            "Your job is to help grocery shoppers remember what they need to buy."
            " You'll be shown an image of groceries retrieved so far, and you'll need to check if anything is missing."
            " Do not worry about any items that are not on the list, regardless of whether they are in the image."
            " If an item is on the list and found in an image, update your state to mark it as retrieved."
        ),
        state=shopping_list,
        tools=[check_shopping_list]
    ) as app:
        while True:
            image_url = Prompt.ask("Enter the URL of the image showing your cart (or press Enter to finish)")
            if not image_url:
                break

            app.say(f"Assistant, please check if I forgot anything on my shopping list based on this image: {image_url}")
            display_shopping_list(app.state.value)

        print("Thanks for playing! Here's your final shopping list:")
        display_shopping_list(app.state.value)

if __name__ == "__main__":
    play_game()
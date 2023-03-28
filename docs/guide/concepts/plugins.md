# Plugins

![](plugin_rng.png)

!!! tip "Features"
    🦸 Give bots the ability to access new information and abilities
    
    🦾 Turn any function into a bot plugin

Plugins extend a bot's functionality by letting it call a function and see the returned value. Plugins must be provided to a bot when it is instantiated, and the bot will decide whether to use a plugin based on its description. Users can influence that choice through instruction (e.g. telling the bot to use a specific plugin). 

## Writing plugins

The simplest way to write a plugin is using the `@plugin` decorator. Note that plugin functions must have a docstring, as this is displayed to the bot so it can decide if it should use a plugin or not.

```python
from marvin import Bot, plugin
import random

@plugin
def random_number(min:float, max:float) -> float:
    """Use this plugin to generate a random number between min and max"""
    return min + (max - min) * random.random()

bot = Bot(plugins=[random_number])

await bot.say('Use the plugin to pick a random number between 41 and 43')
```

For more complex plugins, you can inherit from the `marvin.Plugin` base class and implement a `run()` method. Class-based plugins must also have a `description` attribute. This is the equivalent of the function-based plugin above:

```python
from marvin import Bot, Plugin
import random

class RandomNumber(Plugin):
    description: str = "Use this plugin to generate a random number between min and max"

    def run(self, min:float, max:float) -> float:
        return min + (max - min) * random.random()

bot = Bot(plugins=[RandomNumber()])

await bot.say('Use the plugin to pick a random number between 41 and 43')
```



## Technical note: plugin registration

Plugins that inherit from `marvin.Plugin` automatically register themselves for deserialization based on their class name. Bots are serialized with a reference to the plugin name and load the appropriate plugin upon deserialization. In a situation where you want to avoid conflict, you can manually set the deserialization key:

```python
class MyPlugin(marvin.Plugin):
    _discriminator = 'my-key'
```

In order for a bot to use a plugin, the plugin must be available *and imported* prior to the plugin being deserialized. Otherwise it will not be properly registered when the bot is loaded. 
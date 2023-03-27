# Plugins

Plugins extend a bot's functionality by letting it call a function and see the returned value. Plugins must be provided to a bot when it is instantiated, and the bot will decide whether to use a plugin based on its description. Users can influence that choice through instruction (e.g. telling the bot to use a specific plugin). 

## Writing plugins



## Technical note: plugin registration

Plugins that inherit from `marvin.Plugin` automatically register themselves for deserialization based on their class name. Bots are serialized with a reference to the plugin name and load the appropriate plugin upon deserialization. In a situation where you want to avoid conflict, you can manually set the deserialization key:

```python
class MyPlugin(marvin.Plugin):
    _discriminator = 'my-key'
```

In order for a bot to use a plugin, the plugin must be available *and imported* prior to the plugin being deserialized. Otherwise it will not be properly registered when the bot is loaded. 
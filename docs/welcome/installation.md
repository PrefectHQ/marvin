# Installing Marvin

Install Marvin with `pip`:

```shell
pip install marvin
```

To verify your installation, run `marvin version` in your terminal.

Upgrade to the latest released version at any time:

```shell
pip install marvin -U
```

Next, check out the [tutorial](tutorial.md) to get started with Marvin.

## Requirements

Marvin requires Python 3.9 or greater, and is tested on all major Python versions and operating systems.

## Optional dependencies

Marvin has a few features that have additional dependencies that are not installed by default. If you want to use these features, you can install the optional dependencies with the following commands:

### Audio features

Marvin can transcribe and generate speech out-of-the box by working with audio files, but in order to record and play sound, you'll need additional dependencies. See the [documentation](/docs/audio/recording) for more details.

Please follow the instructions to set up PyAudio and PyDub, then run:

```shell
pip install marvin[audio]
```

#### Set up PyAudio
Marvin's audio features depend on PyAudio, which may have additional platform-dependent instructions. Please review the PyAudio installation instructions [here](https://people.csail.mit.edu/hubert/pyaudio/) for the latest information. 

On macOS, PyAudio depends on PortAudio, which can be installed with [Homebrew](https://brew.sh/):
```shell
brew install portaudio
```


#### Set up PyDub
Marvin's audio features also depend on PyDub, which may have additional platform-dependent instructions. Please review the PyDub installation instructions [here](https://github.com/jiaaro/pydub#dependencies).

Generally, you'll need to install ffmpeg.

On macOS, use [Homebrew](https://brew.sh/):
```shell
brew install ffmpeg
```

On Linux, use your package manager:
```shell
apt-get install ffmpeg libavcodec-extra
```

On Windows, see the PyDub instructions.

### Video features

Marvin has utilities for recording video that make it easy to apply vision AI models to video streams. See the [documentation](docs/video/recording) for more details.

```shell
pip install marvin[video]
```

### Development

Generally, to install Marvin for development, you'll need to use the `dev` extra. However, in practice you'll want to create an editable install from your local source code:

```shell
pip install -e "path/to/marvin[dev]"
```

To build the documentation, you may also have to install certain imaging dependencies of MkDocs Material, which you can learn more about [here](https://squidfunk.github.io/mkdocs-material/plugins/requirements/image-processing/#dependencies).


See the [contributing docs](../../community/development_guide) for further instructions.

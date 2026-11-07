"""Check generated signatures against Python's constructor binding rules."""

import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType

import griffe
import pytest

from marvin.agents.agent import Agent
from marvin.agents.team import RandomTeam, RoundRobinTeam, Swarm, Team
from marvin.memory.memory import Memory


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def generator() -> ModuleType:
    return load_module(
        Path(__file__).parents[2] / "scripts/create_mintlify_api_ref.py",
        "api_reference_generator",
    )


@pytest.fixture
def signature_module(tmp_path: Path) -> tuple[ModuleType, griffe.Module]:
    source = tmp_path / "signature_examples.py"
    source.write_text(
        """
from dataclasses import dataclass, field as dataclass_field

@dataclass(kw_only=True)
class Base:
    option: int = 3
    value: str = dataclass_field(kw_only=False, default="base")
    forced: int = dataclass_field(kw_only=True, default=4)

@dataclass(kw_only=True)
class Child(Base):
    value: str = dataclass_field(kw_only=True, default="child")
    extra: int = dataclass_field(kw_only=False, default=5)

@dataclass(kw_only=True)
class Inherited(Base):
    another: int = 6

@dataclass(kw_only=True)
class Manual:
    value: int = dataclass_field(kw_only=False, default=0)

    def __init__(self, *, custom: str = "manual"):
        self.value = len(custom)

def ordinary(value: int, /, other: str = "default", *, flag: bool = False) -> str:
    return other
"""
    )
    return (
        load_module(source, "signature_examples"),
        griffe.load("signature_examples", search_paths=[tmp_path]),
    )


@pytest.mark.parametrize("name", ["Base", "Child", "Inherited", "Manual", "ordinary"])
def test_generated_signature_matches_python(
    generator: ModuleType,
    signature_module: tuple[ModuleType, griffe.Module],
    name: str,
) -> None:
    runtime, static = signature_module
    rendered = generator.format_signature(static.members[name])
    # Compile the actual generated parameter list, then use Python's independent
    # signature implementation to compare order, kinds, annotations and defaults.
    namespace = dict(vars(runtime))
    exec(rendered.replace("class ", "def ", 1) + ": pass", namespace)
    generated = inspect.signature(namespace[name])
    expected = inspect.signature(getattr(runtime, name))
    assert generated.parameters == expected.parameters


@pytest.mark.parametrize(
    ("runtime_class", "module_name", "field"),
    [
        (Agent, "marvin.agents.agent", "name"),
        (Memory, "marvin.memory.memory", "key"),
        (Team, "marvin.agents.team", "members"),
        (Swarm, "marvin.agents.team", "members"),
        (RoundRobinTeam, "marvin.agents.team", "members"),
        (RandomTeam, "marvin.agents.team", "members"),
    ],
)
def test_public_constructor_positional_field(
    generator: ModuleType, runtime_class: type, module_name: str, field: str
) -> None:
    constructor = inspect.signature(runtime_class)
    assert next(iter(constructor.parameters)) == field
    constructor.bind(object())
    with pytest.raises(TypeError):
        constructor.bind(object(), object())
    module = griffe.load(module_name, search_paths=[Path("src")])
    rendered = generator.format_signature(module.members[runtime_class.__name__])
    assert rendered.startswith(f"class {runtime_class.__name__}({field}:")
    assert ", *, " in rendered

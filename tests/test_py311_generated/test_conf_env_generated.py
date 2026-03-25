"""Tests for tyro.conf.Env() — environment variable fallback for CLI arguments."""

import dataclasses
import enum
import pathlib
from typing import Annotated, List, Literal, Optional, Tuple

import pytest
from helptext_utils import get_helptext_with_checks

import tyro


@dataclasses.dataclass
class SimpleConfig:
    name: Annotated[str, tyro.conf.Env("MY_NAME")] = "default"


@dataclasses.dataclass
class RequiredEnvConfig:
    token: Annotated[str, tyro.conf.Env("AUTH_TOKEN")]


class Color(enum.Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


def test_cli_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI value takes precedence over environment variable."""
    monkeypatch.setenv("MY_NAME", "from-env")
    result = tyro.cli(SimpleConfig, args=["--name", "from-cli"])
    assert result.name == "from-cli"


def test_env_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment variable takes precedence over field default."""
    monkeypatch.setenv("MY_NAME", "from-env")
    result = tyro.cli(SimpleConfig, args=[])
    assert result.name == "from-env"


def test_default_used_when_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Field default is used when env var is not set."""
    monkeypatch.delenv("MY_NAME", raising=False)
    result = tyro.cli(SimpleConfig, args=[])
    assert result.name == "default"


def test_required_field_with_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Required field satisfied by env var — no CLI argument needed."""
    monkeypatch.setenv("AUTH_TOKEN", "secret123")
    result = tyro.cli(RequiredEnvConfig, args=[])
    assert result.token == "secret123"


def test_required_field_no_env_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Required field with no env var and no CLI argument should error."""
    monkeypatch.delenv("AUTH_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        tyro.cli(RequiredEnvConfig, args=[])


def test_required_field_cli_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI overrides env even for required fields."""
    monkeypatch.setenv("AUTH_TOKEN", "env-token")
    result = tyro.cli(RequiredEnvConfig, args=["--token", "cli-token"])
    assert result.token == "cli-token"


def test_env_int(monkeypatch: pytest.MonkeyPatch) -> None:
    @dataclasses.dataclass
    class Config:
        count: Annotated[int, tyro.conf.Env("MY_COUNT")] = 0

    monkeypatch.setenv("MY_COUNT", "42")
    result = tyro.cli(Config, args=[])
    assert result.count == 42


def test_env_float(monkeypatch: pytest.MonkeyPatch) -> None:
    @dataclasses.dataclass
    class Config:
        rate: Annotated[float, tyro.conf.Env("MY_RATE")] = 0.0

    monkeypatch.setenv("MY_RATE", "3.14")
    result = tyro.cli(Config, args=[])
    assert result.rate == pytest.approx(3.14)


def test_env_path(monkeypatch: pytest.MonkeyPatch) -> None:
    @dataclasses.dataclass
    class Config:
        output_path: Annotated[pathlib.Path, tyro.conf.Env("OUTPUT_PATH")] = (
            pathlib.Path(".")
        )

    monkeypatch.setenv("OUTPUT_PATH", "/tmp/output")
    result = tyro.cli(Config, args=[])
    assert result.output_path == pathlib.Path("/tmp/output")


def test_env_enum(monkeypatch: pytest.MonkeyPatch) -> None:
    @dataclasses.dataclass
    class Config:
        color: Annotated[Color, tyro.conf.Env("MY_COLOR")] = Color.RED

    monkeypatch.setenv("MY_COLOR", "GREEN")
    result = tyro.cli(Config, args=[])
    assert result.color == Color.GREEN


def test_env_literal(monkeypatch: pytest.MonkeyPatch) -> None:
    @dataclasses.dataclass
    class Config:
        mode: Annotated[Literal["train", "eval"], tyro.conf.Env("MODE")] = "train"

    monkeypatch.setenv("MODE", "eval")
    result = tyro.cli(Config, args=[])
    assert result.mode == "eval"


@dataclasses.dataclass
class _BoolConfig:
    verbose: Annotated[bool, tyro.conf.Env("VERBOSE")] = False


@pytest.mark.parametrize(
    "env_str, expected",
    [
        ("true", True),
        ("True", True),
        ("yes", True),
        ("on", True),
        ("1", True),
        ("false", False),
        ("False", False),
        ("no", False),
        ("off", False),
        ("0", False),
    ],
)
def test_env_bool_flag(
    monkeypatch: pytest.MonkeyPatch, env_str: str, expected: bool
) -> None:
    monkeypatch.setenv("VERBOSE", env_str)
    result = tyro.cli(_BoolConfig, args=[])
    assert result.verbose is expected


def test_env_bool_cli_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERBOSE", "true")
    result = tyro.cli(_BoolConfig, args=["--no-verbose"])
    assert result.verbose is False


def test_env_bool_flag_conversion_off(monkeypatch: pytest.MonkeyPatch) -> None:
    @dataclasses.dataclass
    class Config:
        flag: Annotated[tyro.conf.FlagConversionOff[bool], tyro.conf.Env("MY_FLAG")] = (
            False
        )

    monkeypatch.setenv("MY_FLAG", "True")
    result = tyro.cli(Config, args=[])
    assert result.flag is True


def test_env_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    @dataclasses.dataclass
    class Config:
        verbosity: Annotated[
            tyro.conf.UseCounterAction[int], tyro.conf.Env("VERBOSITY")
        ] = 0

    monkeypatch.setenv("VERBOSITY", "3")
    result = tyro.cli(Config, args=[])
    assert result.verbosity == 3


def test_env_counter_cli_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    @dataclasses.dataclass
    class Config:
        verbosity: Annotated[
            tyro.conf.UseCounterAction[int], tyro.conf.Env("VERBOSITY")
        ] = 0

    monkeypatch.setenv("VERBOSITY", "3")
    result = tyro.cli(Config, args=["--verbosity", "--verbosity"])
    assert result.verbosity == 2


def test_multiple_env_args(monkeypatch: pytest.MonkeyPatch) -> None:
    @dataclasses.dataclass
    class Config:
        host: Annotated[str, tyro.conf.Env("HOST")] = "localhost"
        port: Annotated[int, tyro.conf.Env("PORT")] = 8080

    monkeypatch.setenv("HOST", "0.0.0.0")
    monkeypatch.setenv("PORT", "9090")
    result = tyro.cli(Config, args=[])
    assert result.host == "0.0.0.0"
    assert result.port == 9090


def test_env_with_arg_config(monkeypatch: pytest.MonkeyPatch) -> None:
    @dataclasses.dataclass
    class Config:
        token: Annotated[
            str,
            tyro.conf.Env("TOKEN"),
            tyro.conf.arg(aliases=["-t"], help="Auth token."),
        ] = ""

    monkeypatch.setenv("TOKEN", "env-token")
    result = tyro.cli(Config, args=[])
    assert result.token == "env-token"


def test_helptext_shows_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MY_NAME", raising=False)
    helptext = get_helptext_with_checks(SimpleConfig, default=SimpleConfig())
    assert "[env: MY_NAME]" in helptext


def test_helptext_shows_env_value_when_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MY_NAME", "hello")
    helptext = get_helptext_with_checks(SimpleConfig, default=SimpleConfig())
    assert "[env: MY_NAME=hello]" in helptext


def test_helptext_required_with_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Required field with env shows env info instead of just '(required)'."""
    monkeypatch.delenv("AUTH_TOKEN", raising=False)
    helptext = get_helptext_with_checks(RequiredEnvConfig)
    assert "[env: AUTH_TOKEN]" in helptext
    assert "(required)" in helptext


def test_helptext_required_field_satisfied_by_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Required field with env var set shows 'from env' instead of 'required'."""
    monkeypatch.setenv("AUTH_TOKEN", "secret")
    helptext = get_helptext_with_checks(RequiredEnvConfig)
    assert "(required)" not in helptext
    assert "(from env)" in helptext
    assert "[env: AUTH_TOKEN=secret]" in helptext


def test_env_auto_derive_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env() with no argument derives env var name from field name."""

    @dataclasses.dataclass
    class Config:
        secret: Annotated[str, tyro.conf.Env()] = "default"

    monkeypatch.setenv("SECRET", "from-env")
    result = tyro.cli(Config, args=[])
    assert result.secret == "from-env"


def test_env_auto_derive_name_underscore(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env() derives UPPER_SNAKE_CASE from snake_case field names."""

    @dataclasses.dataclass
    class Config:
        database_url: Annotated[str, tyro.conf.Env()] = ""

    monkeypatch.setenv("DATABASE_URL", "postgres://localhost/db")
    result = tyro.cli(Config, args=[])
    assert result.database_url == "postgres://localhost/db"


def test_env_auto_derive_cli_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI still overrides an auto-derived env var."""

    @dataclasses.dataclass
    class Config:
        secret: Annotated[str, tyro.conf.Env()] = "default"

    monkeypatch.setenv("SECRET", "from-env")
    result = tyro.cli(Config, args=["--secret", "from-cli"])
    assert result.secret == "from-cli"


def test_env_auto_derive_helptext(monkeypatch: pytest.MonkeyPatch) -> None:
    """Help text shows the derived env var name."""

    @dataclasses.dataclass
    class Config:
        secret: Annotated[str, tyro.conf.Env()] = "default"

    monkeypatch.delenv("SECRET", raising=False)
    helptext = get_helptext_with_checks(Config, default=Config())
    assert "[env: SECRET]" in helptext


def test_env_auto_derive_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """Auto-derived env var satisfies a required field."""

    @dataclasses.dataclass
    class Config:
        api_key: Annotated[str, tyro.conf.Env()]

    monkeypatch.setenv("API_KEY", "key123")
    result = tyro.cli(Config, args=[])
    assert result.api_key == "key123"


def test_env_nested_struct_field_name_not_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Env() in a nested struct derives from the field name, not the full path.

    Field `inner.token` with Env() maps to TOKEN, not INNER_TOKEN.
    """

    @dataclasses.dataclass
    class Inner:
        token: Annotated[str, tyro.conf.Env()] = ""

    @dataclasses.dataclass
    class Outer:
        inner: Inner = dataclasses.field(default_factory=Inner)

    monkeypatch.setenv("TOKEN", "nested-value")
    result = tyro.cli(Outer, args=[])
    assert result.inner.token == "nested-value"


def test_env_nested_helptext_shows_derived_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Help text in nested struct shows the derived env var (field name only)."""

    @dataclasses.dataclass
    class Inner:
        token: Annotated[str, tyro.conf.Env()] = ""

    @dataclasses.dataclass
    class Outer:
        inner: Inner = dataclasses.field(default_factory=Inner)

    monkeypatch.delenv("TOKEN", raising=False)
    helptext = get_helptext_with_checks(Outer, default=Outer())
    assert "[env: TOKEN]" in helptext


def test_env_optional_type(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env provides a value for an Optional field that defaults to None."""

    @dataclasses.dataclass
    class Config:
        token: Annotated[Optional[str], tyro.conf.Env("OPT_TOKEN")] = None

    monkeypatch.setenv("OPT_TOKEN", "hello")
    result = tyro.cli(Config, args=[])
    assert result.token == "hello"


def test_env_optional_not_set_stays_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Optional field stays None when env var is absent."""

    @dataclasses.dataclass
    class Config:
        token: Annotated[Optional[str], tyro.conf.Env("OPT_TOKEN")] = None

    monkeypatch.delenv("OPT_TOKEN", raising=False)
    result = tyro.cli(Config, args=[])
    assert result.token is None


@dataclasses.dataclass
class _ListConfig:
    tags: Annotated[List[str], tyro.conf.Env("TAGS")] = dataclasses.field(
        default_factory=list
    )


@pytest.mark.parametrize(
    "env_str, expected",
    [
        ("a b c", ["a", "b", "c"]),
        ("foo 'bar baz' qux", ["foo", "bar baz", "qux"]),
        ("single", ["single"]),
    ],
)
def test_env_list_shlex(
    monkeypatch: pytest.MonkeyPatch, env_str: str, expected: List[str]
) -> None:
    monkeypatch.setenv("TAGS", env_str)
    result = tyro.cli(_ListConfig, args=[])
    assert result.tags == expected


def test_env_list_cli_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI values override the env var for list types."""
    monkeypatch.setenv("TAGS", "from-env")
    result = tyro.cli(_ListConfig, args=["--tags", "from-cli"])
    assert result.tags == ["from-cli"]


def test_env_tuple_shlex_split(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env provides a space-separated variable-length tuple."""

    @dataclasses.dataclass
    class Config:
        names: Annotated[Tuple[str, ...], tyro.conf.Env("NAMES")] = ()

    monkeypatch.setenv("NAMES", "alice bob carol")
    result = tyro.cli(Config, args=[])
    assert result.names == ("alice", "bob", "carol")


def test_env_with_aliases(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env composes with arg(aliases=...) — env fallback still works."""

    @dataclasses.dataclass
    class Config:
        token: Annotated[
            str,
            tyro.conf.Env("MY_TOKEN"),
            tyro.conf.arg(aliases=["-t"]),
        ] = ""

    monkeypatch.setenv("MY_TOKEN", "env-value")
    # No CLI flag provided — env should fill in.
    result = tyro.cli(Config, args=[])
    assert result.token == "env-value"
    # Short alias overrides env.
    result = tyro.cli(Config, args=["-t", "cli-value"])
    assert result.token == "cli-value"


def test_env_with_omit_arg_prefixes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Env works when OmitArgPrefixes removes the nested struct prefix."""

    @dataclasses.dataclass
    class Inner:
        host: Annotated[str, tyro.conf.Env("HOST")] = "localhost"

    @dataclasses.dataclass
    class Outer:
        server: Inner = dataclasses.field(default_factory=Inner)

    monkeypatch.setenv("HOST", "0.0.0.0")
    result = tyro.cli(tyro.conf.OmitArgPrefixes[Outer], args=[])
    assert result.server.host == "0.0.0.0"

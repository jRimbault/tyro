"""Environment Variable Fallback

The :func:`tyro.conf.Env` annotation reads a CLI argument's value from an
environment variable when no explicit CLI flag is provided. Precedence is:
CLI argument > environment variable > default value.

When called with no argument, ``Env()`` derives the environment variable
name from the field name (``secret`` becomes ``SECRET``).

Usage:

    python ./17_env.py --help
    python ./17_env.py --secret s3cret --host 127.0.0.1
    SECRET=s3cret HOST=0.0.0.0 APP_PORT=9090 python ./17_env.py
"""

import dataclasses

from typing_extensions import Annotated

import tyro


@dataclasses.dataclass
class ServerConfig:
    # Required on CLI unless SECRET env var is set.
    # Env var name derived automatically from field name.
    secret: Annotated[str, tyro.conf.Env()]

    # Falls back to HOST env var if --host is not passed.
    host: Annotated[str, tyro.conf.Env()] = "localhost"

    # Falls back to APP_PORT env var if --port is not passed.
    # Explicit env var name overrides derivation.
    port: Annotated[int, tyro.conf.Env("APP_PORT")] = 8080


if __name__ == "__main__":
    config = tyro.cli(ServerConfig)
    print(f"host={config.host} port={config.port} secret={config.secret}")

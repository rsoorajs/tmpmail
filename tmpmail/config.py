from __future__ import annotations

import os
import typing as t
from dataclasses import dataclass

import trafaret as tr


@dataclass
class Config:
    # domain for which we accept email (IE the RCPT TO
    # addresses on incoming mail must match `*@{mail_domain}`
    mail_domain: str = "localhost"
    # port to bind the LMTP server to
    lmtp_port: int = 2525


def acquire_config(*, environ: t.Mapping[str, str] = os.environ) -> Config:
    """Attempt to resolve a complete Config instance from the environment.

    Args:
        environ: if specified a mapping to use rather than `os.environ` to
            locate environment variables for configuration values.

    Returns:
        A complete instance of the `Config`

    Raises:
        trafaret.DataError if any required value is missing, or any specified
            value for configuration is malformed.
    """
    env_converter = tr.Dict(
        {
            tr.Key(
                "TMPMAIL_MAIL_DOMAIN", optional=True, to_name="mail_domain",
            ): tr.String,
            tr.Key("TMPMAIL_LMTP_PORT", optional=True, to_name="lmtp_port"): tr.ToInt(
                gt=0, lt=(2 ** 16)
            ),
        },
        ignore_extra="*",
    )
    return Config(**env_converter(environ))

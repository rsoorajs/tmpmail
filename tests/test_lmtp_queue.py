import asyncio
from smtplib import SMTP

import pytest

from tmpmail import lmtp
from tmpmail.config import Config


@pytest.fixture
def config():
    yield Config()


@pytest.fixture
async def mail_q(config):
    async with lmtp.server(config=config) as q:
        yield q


@pytest.fixture
def smtp_client(config, mail_q):
    yield SMTP(config.mail_domain, config.lmtp_port)


@pytest.mark.asyncio
async def test_mail_is_queued(config, smtp_client, mail_q):
    """Ensure mail sent to the LMTP instance is enqueued."""
    assert mail_q.async_q.empty() is True
    smtp_client.sendmail(
        f"foo@{config.mail_domain}",
        [f"bar@{config.mail_domain}"],
        f"""\
From: Foo Foo <foo@{config.mail_domain}>
To: Bar bar <bar@{config.mail_domain}>
Subject: Test Mail
Message-ID: 1

Message Content""",
    )

    await asyncio.wait_for(mail_q.async_q.get(), timeout=1.0)

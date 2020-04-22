from __future__ import annotations

import contextlib
import logging
import typing as t
from email.message import Message

from aiosmtpd.controller import Controller
from aiosmtpd.handlers import AsyncMessage
from aiosmtpd.smtp import SMTP, Envelope, Session
from janus import Queue

from tmpmail.config import Config

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def server(config: Config) -> t.AsyncIterator[Queue[Message]]:
    """Manage the LMTP server's lifetime, returning a queue of messages received."""
    msg_queue: Queue[Message] = Queue()
    controller = Controller(
        handler=LmtpHandler(config=config, queue=msg_queue),
        hostname=config.mail_domain,
        port=config.lmtp_port,
    )
    controller.start()
    logger.info(f"listening on {config.mail_domain}:{config.lmtp_port}")
    yield msg_queue
    controller.stop()


class LmtpHandler(AsyncMessage):
    """Queues incoming mail for the websocket server to deliver."""

    config: Config
    queue: Queue[Message]

    def __init__(self, config: Config, queue: Queue[Message], *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.config = config
        self.queue = queue

    async def handle_RCPT(
        self,
        server: SMTP,
        session: Session,
        envelope: Envelope,
        address: str,
        rcpt_options: t.List[str],
    ) -> str:
        """Reject mail in need of relay."""
        if not address.endswith(f"@{self.config.mail_domain}"):
            return "550 not relaying to that domain"
        else:
            envelope.rcpt_tos.append(address)
            return "250 OK"

    async def handle_message(self, message: Message) -> None:
        """Enqueue new message."""
        self.queue.async_q.put_nowait(message)

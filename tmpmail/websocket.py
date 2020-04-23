from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import random
import string
import typing as t
import weakref
from email.message import Message
from pathlib import Path

import aiohttp_jinja2
import jinja2
from aiohttp import WSCloseCode, web
from janus import Queue

from tmpmail.config import Config

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def server(*, config: Config, msg_q: Queue[Message]) -> t.AsyncIterator[None]:
    """Manage the Websocket server's lifetime.

    Args:
        config: application configuration.
        msg_q: queue of incoming mail.

    Yields:
        None
    """
    app = web.Application()
    app["config"] = config
    app["inboxes"] = weakref.WeakValueDictionary()
    app.on_shutdown.append(on_shutdown)
    app.add_routes([web.get("/", index)])
    app.add_routes([web.get("/inbox", inbox)])

    aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader("tmpmail", "web_static"))
    if config.http_host_static:
        this_dir = Path(os.path.dirname(os.path.realpath(__file__)))
        static_dir = this_dir.joinpath("web_static")
        app.router.add_static("/static/", static_dir)
        logger.info(f"hosting static assets from {static_dir}")

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner=runner, host=config.http_host, port=config.http_port)
    await site.start()
    logger.info(f"listening on http://{config.http_host}:{config.http_port}")

    drain_q_task = asyncio.create_task(drain_q(msg_q, app["inboxes"]))

    try:
        yield
    finally:
        drain_q_task.cancel()
        await runner.shutdown()
        await runner.cleanup()


async def on_shutdown(app: web.Application) -> None:
    """Send a going-away signal to all still-open websockets on shutdown."""
    keys = set(app["inboxes"].keys())
    for addr in keys:
        await app["inboxes"][addr].close(
            code=WSCloseCode.GOING_AWAY, message="server shutdown"
        )


@aiohttp_jinja2.template("index.html")
async def index(request: web.Request) -> dict:
    """SPA route."""
    return {}


async def inbox(request: web.Request) -> web.WebSocketResponse:
    """Primary websocket interface for the frontend."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    addr = get_new_addr(
        domain=request.app["config"].mail_domain,
        addresses=set(request.app["inboxes"].keys()),
    )
    request.app["inboxes"][addr] = ws
    try:
        await ws.receive()
        await ws.send_json({"type": "addr", "addr": addr})
        while True:
            # ping every 10s and discard pongs
            await asyncio.sleep(10.0)
            ws.send_json({"type": "ping"})
            msg = await ws.receive_json()
    finally:
        del request.app["inboxes"][addr]
        await ws.close()

    return ws


async def drain_q(
    msg_q: Queue[Message],
    inboxes: weakref.WeakValueDictionary[str, web.WebSocketResponse],
) -> None:
    """Deliver each incoming message to the correct recipient/s, if any."""
    while True:
        msg = await msg_q.async_q.get()
        tos = msg['X-RcptTo'].split(', ')
        froms = msg.get_all("From")
        subject = msg.get("Subject")
        payload = msg.get_payload()
        for to in tos:
            if to in inboxes:
                await inboxes[to].send_json(
                    {
                        "type": "message",
                        "tos": tos,
                        "froms": froms,
                        "subject": subject,
                        "payload": payload,
                    }
                )


def get_new_addr(*, domain: str, addresses: t.Set[str], length: int = 6) -> str:
    """Get a new address which isn't yet reserved.

    Args:
        domain: domain part of the address to create.
        addresses: iterable of existing addresses.
        length: the length of the mailbox part of the address.

    Returns:
        An unreserved address.
    """

    def random_addr() -> str:
        mailbox = "".join(random.choice(string.ascii_lowercase) for _ in range(6))
        return f"{mailbox}@{domain}"

    addr = random_addr()
    while addr in addresses:
        addr = random_addr()

    return addr

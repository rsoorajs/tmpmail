from __future__ import annotations

import asyncio
import contextlib
import functools
import logging
import signal
import sys
import traceback
import typing as t

import trafaret as tr

from tmpmail import lmtp
from tmpmail.config import Config, acquire_config

logger = logging.getLogger(__name__)


def main() -> None:
    try:
        config = acquire_config()
        logging.basicConfig(
            level=logging.INFO, format="%(levelname)-7s %(name)-32s %(message)s"
        )
        asyncio.run(async_main(config))
    except tr.DataError as e:
        logger.error(f"configuration is invalid: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"unexpected error: {e}")
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


async def async_main(config: Config) -> None:
    """Run the lmtp and websocket servers until signalled."""
    async with contextlib.AsyncExitStack() as stack:
        caught_sig = stack.enter_context(catch_signals())
        _ = await stack.enter_async_context(lmtp.server(config))

        await caught_sig


@contextlib.contextmanager
def catch_signals() -> t.Generator[asyncio.Future[int], None, None]:
    """Get a future which resolves with the first terminal signal caught."""
    loop = asyncio.get_event_loop()
    caught_sig: asyncio.Future[int] = asyncio.Future()
    catch_sigs = [signal.SIGINT, signal.SIGTERM]

    def on_catch(signalnum: signal.Signals) -> None:
        """On catching a signal complete the `caught_sig` future."""
        if not caught_sig.done():
            logger.info(f"caught signal {signalnum}; shutting down")
            caught_sig.set_result(signalnum)

    for sig in catch_sigs:
        handler = functools.partial(on_catch, signalnum=sig)
        loop.add_signal_handler(sig, handler)

    try:
        yield caught_sig
    finally:
        for sig in catch_sigs:
            loop.remove_signal_handler(sig)

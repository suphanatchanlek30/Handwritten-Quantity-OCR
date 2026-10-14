"""Network helpers used before the first model download.

On the development machine IPv6 routes time out (``curl -6`` hangs) while IPv4
works, so model downloads from Hugging Face stall indefinitely. ``force_ipv4``
filters DNS results to IPv4 for the whole process.
"""

from __future__ import annotations

import logging
import os
import socket

logger = logging.getLogger(__name__)

_PATCHED = False


def force_ipv4(default_timeout_s: float | None = 60.0) -> None:
    """Restrict ``socket.getaddrinfo`` to ``AF_INET`` results (idempotent)."""
    global _PATCHED
    if _PATCHED:
        return
    original = socket.getaddrinfo

    def _ipv4_only(*args, **kwargs):  # type: ignore[no-untyped-def]
        return [r for r in original(*args, **kwargs) if r[0] == socket.AF_INET]

    socket.getaddrinfo = _ipv4_only  # type: ignore[assignment]
    if default_timeout_s is not None and socket.getdefaulttimeout() is None:
        socket.setdefaulttimeout(default_timeout_s)
    _PATCHED = True
    logger.info("Network: forced IPv4-only DNS resolution")


def disable_model_source_check() -> None:
    """Skip PaddleX's connectivity probe of model hosters at predictor init."""
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

from __future__ import annotations
from typing import Any

from hashlib import md5


def chksum(x: Any) -> str:
    """
    Get the md5 checksum for any input
    """
    chksum = md5()
    chksum.update(bytes(str(x).strip().upper().encode("ascii")))
    return chksum.hexdigest()

"""
Load proxies from a static text file.
File format: one proxy per line, format: host:port or host:port:user:pass
"""

import logging
from pathlib import Path

from proxy.manager import proxy_manager

logger = logging.getLogger(__name__)


def load_from_file(file_path: str) -> int:
    path = Path(file_path)
    if not path.exists():
        logger.warning(f"Proxy file not found: {file_path}")
        return 0

    count = 0
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(":")
        try:
            if len(parts) == 2:
                host, port = parts
                proxy_manager.add_proxy(host, int(port))
            elif len(parts) == 4:
                host, port, user, password = parts
                proxy_manager.add_proxy(host, int(port), user, password)
            else:
                logger.warning(f"Unrecognized proxy format: {line}")
                continue
            count += 1
        except Exception as e:
            logger.warning(f"Failed to parse proxy line '{line}': {e}")

    logger.info(f"Loaded {count} proxies from {file_path}")
    return count

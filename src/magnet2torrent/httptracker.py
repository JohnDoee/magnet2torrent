import asyncio
import struct
import time
from ipaddress import IPv4Address
from urllib.parse import quote

import aiohttp
from yarl import URL

from . import settings
from .bencode import bdecode


async def retrieve_peers_http_tracker(task_registry, tracker, infohash, logger):
    url = f"{tracker}?info_hash={quote(infohash)}" \
          f"&peer_id={quote(settings.PEER_ID)}" \
          f"&port={settings.BITTORRENT_PORT}" \
          f"&uploaded=0&downloaded=0&left=16384&compact=1&event=started" \
          f"&no_peer_id=1&numwant=200"
    failed = False
    i = 5
    err = None
    while i > 0:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=7)) as session:
                try:
                    async with session.get(URL(url, encoded=True)) as response:
                        task = asyncio.ensure_future(response.read())
                        task_registry.add(task)
                        result = await task
                        if response.status != 200:
                            failed = True
                        task_registry.remove(task)
                except (
                    aiohttp.client_exceptions.ClientConnectorError,
                    asyncio.TimeoutError,
                    asyncio.CancelledError,
                ):
                    failed = True

            if failed:
                return tracker, {"seeders": 0, "leechers": 0, "peers": []}
            result = bdecode(result)
            break
        except Exception as e:
            i -= 1
            time.sleep(5)
            logger.error(f'Error {repr(e)}')
            err = e
    else:
        logger.error(f'All tries failed. Error {repr(err)}')
        return tracker, {"seeders": 0, "leechers": 0, "peers": []}

    if b"failure reason" in result:
        return tracker, {"seeders": 0, "leechers": 0, "peers": []}

    peer_data = result[b"peers"]
    peers = []
    while len(peer_data) >= 6:
        peer_ip, peer_port = struct.unpack("!IH", peer_data[:6])
        peers.append((IPv4Address(peer_ip), peer_port))
        peer_data = peer_data[6:]

    return (
        tracker,
        {
            "seeders": result[b"complete"],
            "leechers": result[b"incomplete"],
            "peers": peers,
        },
    )

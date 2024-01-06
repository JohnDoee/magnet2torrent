import asyncio
import struct
from ipaddress import IPv4Address
from urllib.parse import quote

import aiohttp
from yarl import URL

from . import settings
from .bencode import bdecode, BTFailure


async def retrieve_peers_http_tracker(task_registry, tracker, infohash):
    url = f"{tracker}?info_hash={quote(infohash)}&peer_id={quote(settings.PEER_ID)}&port={settings.BITTORRENT_PORT}&uploaded=0&downloaded=0&left=16384&compact=1&event=started&no_peer_id=1&numwant=200"
    failed = False
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

    try:
        result = bdecode(result)
    except BTFailure:
        failed = True

    if failed or b"failure reason" in result:
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

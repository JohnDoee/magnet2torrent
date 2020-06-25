import asyncio
import logging
import random
import socket
import struct
from ipaddress import IPv4Address

from . import settings

logger = logging.getLogger(__name__)


class TrackerUDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, cb, infohash):
        self.state = "connect"
        self.transport = None
        self.last_transaction_id = None
        self.cb = cb
        self.infohash = infohash

    def get_transaction_id(self):
        self.last_transaction_id = random.randint(0, 2 ** 32 - 1)
        return self.last_transaction_id

    def connection_made(self, transport):
        self.transport = transport
        self.send_connect()

    def send_connect(self):
        data = struct.pack("!qiI", 0x41727101980, 0, self.get_transaction_id())
        self.transport.sendto(data)

    def send_announce(self):
        data = struct.pack(
            "!qiI20s20sqqqiiiiH",
            self.connection_id,
            1,
            self.get_transaction_id(),
            self.infohash,
            settings.PEER_ID,
            0,
            0,
            0,
            0,
            0,
            0,  # Key, not sure
            100,
            0,
        )
        self.transport.sendto(data)

    def datagram_received(self, data, addr):
        logger.debug(f"received datagram from {addr}")
        asyncio.ensure_future(self._handle_response(data, addr))

    async def _handle_response(self, data, addr):
        if self.state == "connect":
            fmt_header = "!iIq"
            if len(data) != struct.calcsize(fmt_header):
                logger.warning("Wrong stuff returned on connect")
                return
            action, transaction_id, connection_id = struct.unpack(fmt_header, data)
            self.connection_id = connection_id
            self.state = "announce"
            self.send_announce()
        elif self.state == "announce":
            fmt_header = "!iIiii"
            header_size = struct.calcsize(fmt_header)
            if len(data) < header_size:
                logger.warning("Wrong stuff returned on announce")
                return
            action, transaction_id, interval, leechers, seeders = struct.unpack(
                fmt_header, data[:header_size]
            )
            peer_data = data[header_size:]
            peers = []
            fmt_peer = "!IH"
            peer_size = struct.calcsize(fmt_peer)
            while len(peer_data) >= peer_size:
                peer_ip, peer_port = struct.unpack(fmt_peer, peer_data[:peer_size])
                peers.append((IPv4Address(peer_ip), peer_port))
                peer_data = peer_data[peer_size:]

            if not self.cb.done():
                self.cb.set_result(
                    {"seeders": seeders, "leechers": leechers, "peers": peers}
                )


async def retrieve_peers_udp_tracker(task_registry, host, port, tracker, infohash):
    loop = asyncio.get_running_loop()
    cb = loop.create_future()
    try:
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: TrackerUDPProtocol(cb, infohash), remote_addr=(host, port)
        )
    except socket.gaierror:
        return tracker, {"seeders": 0, "leechers": 0, "peers": []}
    try:
        task = asyncio.ensure_future(cb)
        task_registry.add(task)
        result = await asyncio.wait_for(task, timeout=12)
        task_registry.remove(task)
    except asyncio.TimeoutError:
        return tracker, {"seeders": 0, "leechers": 0, "peers": []}
    except asyncio.CancelledError:
        transport.close()
    else:
        return tracker, result

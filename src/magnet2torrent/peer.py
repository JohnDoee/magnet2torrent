import asyncio
import binascii
import hashlib
import logging
import struct

from . import settings
from .bencode import bdecode, bencode

logger = logging.getLogger(__name__)


BITTORRENT_HANDSHAKE = b"\x13BitTorrent protocol"
RESERVED_BYTES = 0
RESERVED_BYTES |= settings.METADATA_EXCHANGE
RESERVED_BYTES = struct.pack("!Q", RESERVED_BYTES)


class BittorrentTCPProtocol(asyncio.Transport):
    def __init__(self, cb, infohash, addr):
        self.state = "connect"
        self.transport = None
        self.cb = cb
        self.infohash = infohash
        self.buffer = b""
        self.state = "handshake"
        self.addr = addr
        self.extended_config = {}
        self.expected_torrent_size = None
        self.torrent_data = {}

    def eof_received(self):
        return None

    def connection_made(self, transport):
        logger.debug(f"{self.addr} | Connected, sending handshake")
        self.transport = transport
        self.send_handshake()

    def connection_lost(self, exc):
        logger.debug(f"{self.addr} | Lost connection {exc!r}")
        if not self.cb.done():
            self.cb.set_result(None)

    def data_received(self, data):
        logger.debug(f"{self.addr} | Data received: {data!r}")
        self.buffer += data
        handled_message = True
        while handled_message:
            handled_message = False
            if self.state == "handshake":
                handshake_length = 20 + 8 + 20 + 20
                if len(self.buffer) >= handshake_length:
                    handshake_data = self.buffer[:handshake_length]
                    self.buffer = self.buffer[handshake_length:]

                    (
                        bittorrent_handshake,
                        supported_extensions,
                        infohash,
                        peer_id,
                    ) = struct.unpack("!20sQ20s20s", handshake_data)

                    if supported_extensions & settings.METADATA_EXCHANGE == 0:
                        self.kill("Peer does not support extended metadata")
                        return

                    if bittorrent_handshake != BITTORRENT_HANDSHAKE:
                        self.kill("Invalid handshake")
                        return

                    if infohash != self.infohash:
                        self.kill("Invalid infohash")
                        return

                    handled_message = True
                    self.state = "normal"
                    self.handshake_complete()

            if self.state == "normal" and len(self.buffer) >= 5:
                length, action = struct.unpack("!IB", self.buffer[:5])

                if length > settings.MAX_PACKET_SIZE:
                    self.kill("Packet size too big")

                if len(self.buffer) < length + 4:
                    return

                payload = self.buffer[5 : length + 4]
                self.buffer = self.buffer[length + 4 :]

                self.handle_action(action, payload)
                handled_message = True

    def send_handshake(self):
        self.transport.write(
            BITTORRENT_HANDSHAKE + RESERVED_BYTES + self.infohash + settings.PEER_ID
        )

    def send_message(self, action, payload):
        data = struct.pack("!IB", len(payload) + 1, action) + payload
        logger.debug(f"{self.addr} | Sending data: {data!r}")
        self.transport.write(data)

    def send_extended_message(self, action, payload):
        return self.send_message(20, bytes([action]) + payload)

    def handshake_complete(self):
        logger.debug(f"{self.addr} | Sending extension data")
        self.send_message(
            20,
            b"\x00" + bencode({b"m": {b"ut_metadata": settings.EXTENDED_ID_METADATA,}}),
        )

    def request_metadata_piece(self, piece):
        self.send_extended_message(
            self.ut_metadata, bencode({b"msg_type": 0, b"piece": piece,})
        )

    def handle_extended_action(self, action, payload):
        if action == 0:
            self.extended_config = bdecode(payload)
            if b"ut_metadata" not in self.extended_config.get(b"m", {}):
                self.kill("Does not support actual torrent exchange")
                return

            self.expected_torrent_size = self.extended_config.get(b"metadata_size")
            self.ut_metadata = self.extended_config[b"m"][b"ut_metadata"]

            logger.debug(
                f"{self.addr} | We got torrent size {self.expected_torrent_size}"
            )
            self.request_metadata_piece(0)

        elif action == settings.EXTENDED_ID_METADATA:
            payload_index = payload.index(b"ee") + 2
            payload_msg = payload[:payload_index]
            payload_data = payload[payload_index:]
            payload_msg = bdecode(payload_msg)
            if payload_msg[b"msg_type"] == 2:
                self.kill("Our request for data was denied, bailing")
                return
            elif payload_msg[b"msg_type"] == 1:
                self.torrent_data[payload_msg[b"piece"]] = payload_data
                if (
                    sum(len(v) for v in self.torrent_data.values())
                    < self.expected_torrent_size
                ):
                    self.request_metadata_piece(payload_msg[b"piece"] + 1)
                else:
                    self.verify_and_set_result()
                    self.kill("Finished")
                    return

    def handle_action(self, action, payload):
        logger.debug(f"{self.addr} | Handling {action!r} with payload {payload!r}")
        if action == 20:
            extended_id = payload[0]
            payload = payload[1:]
            self.handle_extended_action(extended_id, payload)

    def verify_and_set_result(self):
        if self.cb.done():
            return
        torrent_data = b""
        for v in self.torrent_data.values():
            torrent_data += v
        infohash = hashlib.sha1(torrent_data).digest()
        if infohash == self.infohash:
            self.cb.set_result(torrent_data)
        else:
            logger.warning(
                f"Got wrong infohash, got {binascii.hexlify(infohash)} expected {binascii.hexlify(self.infohash)}"
            )

    def kill(self, reason):
        logger.debug(f"{self.addr} | Killing connection because of {reason}")
        self.transport.close()
        if not self.cb.done():
            self.cb.set_result(None)


async def fetch_from_peer(task_registry, ip, port, infohash):
    loop = asyncio.get_event_loop()
    cb = loop.create_future()
    addr = (ip, port)
    try:
        task = asyncio.ensure_future(
            loop.create_connection(
                lambda: BittorrentTCPProtocol(cb, infohash, addr), str(ip), port
            )
        )
        task_registry.add(task)
        transport, protocol = await asyncio.wait_for(task, timeout=7,)
        task_registry.remove(task)
    except (OSError, asyncio.TimeoutError) as e:
        logger.debug(f"{addr} | Failed to connect to peer: {e!r}")
        return
    except asyncio.CancelledError:
        return

    try:
        task = asyncio.ensure_future(cb)
        task_registry.add(task)
        result = await asyncio.wait_for(task, timeout=30)
        task_registry.remove(task)
        return result
    except asyncio.TimeoutError:
        protocol.kill("Timeout")
    except asyncio.CancelledError:
        protocol.kill("Cancelled")

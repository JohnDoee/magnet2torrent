import asyncio
import base64
import binascii
import logging
from urllib.parse import parse_qs, urlparse

from . import settings
from .bencode import bencode, bdecode
from .exceptions import FailedToFetchException
from .httptracker import retrieve_peers_http_tracker
from .peer import fetch_from_peer
from .udptracker import retrieve_peers_udp_tracker

logger = logging.getLogger(__name__)


class Magnet2Torrent:
    def __init__(
        self,
        magnet_link,
        use_trackers=True,
        use_additional_trackers=False,
        use_dht=False,
    ):
        self.magnet_link = magnet_link
        self.use_trackers = use_trackers
        self.use_additional_trackers = use_additional_trackers
        self.use_dht = use_dht

    def _parse_url(self):
        url = urlparse(self.magnet_link)
        url_query = parse_qs(url.query)
        infohash = url_query["xt"][0].split(":")[2]
        if len(infohash) == 40:
            infohash = binascii.unhexlify(infohash)
        elif len(infohash) == 32:
            infohash = base64.b32decode(infohash)
        else:
            raise Exception("Unable to parse infohash")

        trackers = url_query.get("tr", [])
        name = url_query.get("dn")
        if name:
            name = name[0]
        else:
            name = binascii.hexlify(infohash)
        return infohash, trackers, name

    @property
    def infohash(self):
        return self._parse_url()[0]

    @property
    def trackers(self):
        return self._parse_url()[1]

    @property
    def name(self):  # TODO: better stripping
        return (
            self._parse_url()[2]
            .strip(".")
            .replace("/", "")
            .replace("\\", "")
            .replace(":", "")
        )

    def create_torrent(self, torrent_data):
        torrent = {b"info": bdecode(torrent_data)}
        trackers = None
        if self.use_trackers:
            trackers = self.trackers
            if self.use_additional_trackers:
                trackers += settings.DEFAULT_TRACKERS

            torrent[b"announce-list"] = [
                [tracker.encode("utf-8")] for tracker in trackers
            ]
            torrent[b"announce"] = torrent[b"announce-list"][0][0]

        return f"{self.name}.torrent", bencode(torrent)

    async def retrieve_torrent(self):
        task_registry = set()
        infohash = self.infohash
        tasks = []
        if self.use_trackers:
            trackers = self.trackers
            if self.use_additional_trackers:
                trackers += settings.DEFAULT_TRACKERS

            for tracker in trackers:
                logger.debug(f"Trying to fetch peers from {tracker}")
                tracker_url = urlparse(tracker)
                if tracker_url.scheme in ["http", "https"]:
                    task = retrieve_peers_http_tracker(task_registry, tracker, infohash)
                elif tracker_url.scheme in ["udp"]:
                    host, port = tracker_url.netloc.split(":")
                    task = retrieve_peers_udp_tracker(
                        task_registry, host, port, tracker, infohash
                    )
                else:
                    print(f"Unknown scheme, {tracker_url.scheme}")
                    continue

                task = asyncio.ensure_future(task)
                task.task_type = "tracker"
                tasks.append(task)

        handled_peers = set()
        while tasks:
            done, tasks = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                result = task.result()
                if task.task_type == "tracker":
                    for peer in result[1]["peers"]:
                        if peer in handled_peers:
                            continue
                        handled_peers.add(peer)
                        peer_ip, peer_port = peer
                        logger.debug(f"Connecting to {peer_ip}:{peer_port}")
                        peer_task = asyncio.ensure_future(
                            fetch_from_peer(task_registry, peer_ip, peer_port, infohash)
                        )
                        peer_task.task_type = "peer"
                        tasks.add(peer_task)
                elif task.task_type == "peer":
                    if result:
                        for task in task_registry:
                            if not task.done():
                                task.cancel()
                        return self.create_torrent(result)

        raise FailedToFetchException()

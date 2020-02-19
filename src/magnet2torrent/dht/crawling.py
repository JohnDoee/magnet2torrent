from collections import Counter
import logging
import struct

from ipaddress import IPv4Address

from .node import Node, NodeHeap
from .utils import gather_dict


log = logging.getLogger(__name__)  # pylint: disable=invalid-name


# pylint: disable=too-few-public-methods
class SpiderCrawl:
    """
    Crawl the network and look for given 160-bit keys.
    """
    def __init__(self, protocol, node, peers, ksize, alpha):
        """
        Create a new C{SpiderCrawl}er.

        Args:
            protocol: A :class:`~magnet2torrent.dht.protocol.KRPCProtocol` instance.
            node: A :class:`~magnet2torrent.dht.node.Node` representing the key we're
                  looking for
            peers: A list of :class:`~magnet2torrent.dht.node.Node` instances that
                   provide the entry point for the network
            ksize: The value for k based on the paper
            alpha: The value for alpha based on the paper
        """
        self.protocol = protocol
        self.ksize = ksize
        self.alpha = alpha
        self.node = node
        self.nearest = NodeHeap(self.node, self.ksize)
        self.last_ids_crawled = []
        log.info("creating spider with peers: %s", peers)
        self.nearest.push(peers)

    async def _find(self, rpcmethod):
        """
        Get either a value or list of nodes.

        Args:
            rpcmethod: The protocol's callfindValue or call_find_node.

        The process:
          1. calls find_* to current ALPHA nearest not already queried nodes,
             adding results to current nearest list of k nodes.
          2. current nearest list needs to keep track of who has been queried
             already sort by nearest, keep KSIZE
          3. if list is same as last time, next call should be to everyone not
             yet queried
          4. repeat, unless nearest list has all been queried, then ur done
        """
        log.info("crawling network with nearest: %s", str(tuple(self.nearest)))
        count = self.alpha
        if self.nearest.get_ids() == self.last_ids_crawled:
            count = len(self.nearest)
        self.last_ids_crawled = self.nearest.get_ids()

        dicts = {}
        for peer in self.nearest.get_uncontacted()[:count]:
            dicts[peer.id] = rpcmethod(peer, self.node)
            self.nearest.mark_contacted(peer)
        found = await gather_dict(dicts)
        return await self._nodes_found(found)

    async def _nodes_found(self, responses):
        raise NotImplementedError


class PeerSpiderCrawl(SpiderCrawl):
    def __init__(self, protocol, node, peers, ksize, alpha, queue):
        SpiderCrawl.__init__(self, protocol, node, peers, ksize, alpha)
        self.crawl_finished = False
        self.cancel_crawl = False
        self._queue = queue

    async def find(self):
        """
        Find either the closest nodes or the value requested.
        """
        return await self._find(self.protocol.call_get_peers)

    async def _nodes_found(self, responses):
        """
        Handle the result of an iteration in _find.
        """
        if self.cancel_crawl:
            return

        toremove = []
        for peerid, response in responses.items():
            response = RPCFindResponse(response)
            if not response.happened():
                toremove.append(peerid)
            elif response.has_value():
                await self._queue.put(response.get_values())
            else:
                self.nearest.push(response.get_node_list())
        self.nearest.remove(toremove)

        if self.nearest.have_contacted_all():
            self.crawl_finished = True
            await self._queue.put([])
            return
        return await self.find()


class NodeSpiderCrawl(SpiderCrawl):
    async def find(self):
        """
        Find the closest nodes.
        """
        return await self._find(self.protocol.call_find_node)

    async def _nodes_found(self, responses):
        """
        Handle the result of an iteration in _find.
        """
        toremove = []
        for peerid, response in responses.items():
            response = RPCFindResponse(response)
            if not response.happened():
                toremove.append(peerid)
            else:
                self.nearest.push(response.get_node_list())
        self.nearest.remove(toremove)

        if self.nearest.have_contacted_all():
            return list(self.nearest)
        return await self.find()


class RPCFindResponse:
    def __init__(self, response):
        """
        A wrapper for the result of a RPC find.
        """
        self.response = response

    def happened(self):
        """
        Did the other host actually respond?
        """
        return self.response[0]

    def has_value(self):
        return b"values" in self.response[1]

    def get_values(self):
        peers = []
        for value in self.response[1].get(b"values", []):
            peer_ip, peer_port = struct.unpack("!IH", value)
            peers.append((IPv4Address(peer_ip), peer_port))
        return peers

    def get_node_list(self):
        """
        Get the node list in the response.  If there's no value, this should
        be set.
        """
        response = self.response[1].get(b"nodes")
        nodelist = []
        while response and len(response) >= 26:
            peer_id = response[:20]
            peer_ip, peer_port = struct.unpack("!IH", response[20:26])
            node = Node(peer_id, str(IPv4Address(peer_ip)), peer_port)
            nodelist.append(node)
            response = response[26:]
        return nodelist

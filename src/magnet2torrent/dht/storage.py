import time
import random
from itertools import takewhile
import operator
from collections import OrderedDict, defaultdict
from abc import abstractmethod, ABC


class IStorage(ABC):
    """
    Local storage for this node.
    IStorage implementations of get must return the same type as put in by set
    """

    @abstractmethod
    def __setitem__(self, key, value):
        """
        Set a key to the given value.
        """

    @abstractmethod
    def __getitem__(self, key):
        """
        Get the given key.  If item doesn't exist, raises C{KeyError}
        """

    @abstractmethod
    def get(self, key, default=None):
        """
        Get given key.  If not found, return default.
        """

    @abstractmethod
    def iter_older_than(self, seconds_old):
        """
        Return the an iterator over (key, value) tuples for items older
        than the given secondsOld.
        """

    @abstractmethod
    def __iter__(self):
        """
        Get the iterator for this storage, should yield tuple of (key, value)
        """


class ForgetfulStorage(IStorage):
    def __init__(self, ttl=60 * 60 * 2):
        """
        By default, max age is two hours.
        """
        self.data = OrderedDict()
        self.ttl = ttl

    def __setitem__(self, key, value):
        if key in self.data:
            del self.data[key]
        self.data[key] = (time.monotonic(), value)
        self.cull()

    def cull(self):
        for _ in self.iter_older_than(self.ttl):
            self.data.popitem(last=False)

    def get(self, key, default=None):
        self.cull()
        if key in self.data:
            return self[key]
        return default

    def __getitem__(self, key):
        self.cull()
        return self.data[key][1]

    def __repr__(self):
        self.cull()
        return repr(self.data)

    def iter_older_than(self, seconds_old):
        min_birthday = time.monotonic() - seconds_old
        zipped = self._triple_iter()
        matches = takewhile(lambda r: min_birthday >= r[1], zipped)
        return list(map(operator.itemgetter(0, 2), matches))

    def _triple_iter(self):
        ikeys = self.data.keys()
        ibirthday = map(operator.itemgetter(0), self.data.values())
        ivalues = map(operator.itemgetter(1), self.data.values())
        return zip(ikeys, ibirthday, ivalues)

    def __iter__(self):
        self.cull()
        ikeys = self.data.keys()
        ivalues = map(operator.itemgetter(1), self.data.values())
        return zip(ikeys, ivalues)


class ForgetfulTokenStorage(ForgetfulStorage):
    def __init__(self, ttl=600):
        super().__init__(ttl=ttl)

    def get_token(self, sender, id, info_hash):
        token = bytes([random.randint(0, 255) for _ in range(16)])
        self.data[token] = (sender[0], id, info_hash)
        return token

    def verify_token(self, sender, id, info_hash, token):
        self.cull()
        if self.get(token) == (sender[0], id, info_hash):
            del self.data[token]
            return True
        return False


class ForgetfulPeerStorage:
    def __init__(self, ttl=60 * 60):
        self.ttl = ttl
        self.data = defaultdict(dict)

    def insert_peer(self, info_hash, peer):
        self.data[info_hash][peer] = time.monotonic()

    def get_peers(self, info_hash):
        self.cull()
        return self.data[info_hash].keys()

    def cull(self):
        delete_info_hashes = []
        for info_hash, peers in self.data.items():
            delete_keys = []
            for sender, birthday in peers.items():
                if time.monotonic() - birthday >= self.ttl:
                    delete_keys.append(sender)
            for key in delete_keys:
                del peers[key]

            if not peers:
                delete_info_hashes.append(info_hash)

        for info_hash in delete_info_hashes:
            del self.data[info_hash]

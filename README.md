# Magnet2Torrent

Pure python project to turn a magnet link into a .torrent file.
The goal is to do it as fast as possible.

## Getting Started

### Installing

```bash
pip install magnet2torrent
```

### Usage

Download an ubuntu iso torrent.

```bash
magnet2torrent fetch "magnet:?xt=urn:btih:e2467cbf021192c241367b892230dc1e05c0580e&dn=ubuntu-19.10-desktop-amd64.iso&tr=https%3A%2F%2Ftorrent.ubuntu.com%2Fannounce&tr=https%3A%2F%2Fipv6.torrent.ubuntu.com%2Fannounce"
```

Run it as an HTTP server.


```bash
magnet2torrent serve
```

Run it as an HTTP server with lots of features enabled.

```bash
magnet2torrent --use-dht --dht-state-file dht.state --torrent-cache-folder torcache serve --apikey secretkey
```

Use from python

```python
import asyncio

from magnet2torrent import Magnet2Torrent, FailedToFetchException

async def fetch_that_torrent():
    m2t = Magnet2Torrent("magnet:?xt=urn:btih:e2467cbf021192c241367b892230dc1e05c0580e&dn=ubuntu-19.10-desktop-amd64.iso&tr=https%3A%2F%2Ftorrent.ubuntu.com%2Fannounce&tr=https%3A%2F%2Fipv6.torrent.ubuntu.com%2Fannounce")
    try:
        filename, torrent_data = await m2t.retrieve_torrent()
    except FailedToFetchException:
        print("Failed")

asyncio.run(fetch_that_torrent())
```

If you want to use DHT to retrieve, you will have to bootstrap and run it.

```python

import asyncio
import os

from magnet2torrent import Magnet2Torrent, FailedToFetchException, settings


DHT_STATE_FILE = "/tmp/dht.state"

async def start_dht():
    if os.path.exists(DHT_STATE_FILE):
        dht_server = DHTServer.load_state(DHT_STATE_FILE)
        await dht_server.listen(settings.DHT_PORT)
    else:
        dht_server = DHTServer()
        await dht_server.listen(settings.DHT_PORT)
        await dht_server.bootstrap(settings.DHT_BOOTSTRAP_NODES)
    return dht_server

async def fetch_that_torrent(dht_server):
    m2t = Magnet2Torrent("magnet:?xt=urn:btih:e2467cbf021192c241367b892230dc1e05c0580e&dn=ubuntu-19.10-desktop-amd64.iso", dht_server=dht_server)
    try:
        filename, torrent_data = await m2t.retrieve_torrent()
    except FailedToFetchException:
        print("Failed")

dht_server = asyncio.run(start_dht())
asyncio.run(fetch_that_torrent(dht_server))
dht_server.save_state(DHT_STATE_FILE)
```

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

The DHT part is forked from [bmueller/kademlia](https://github.com/bmuller/kademlia/) - its license can be
found in the dht folder or in the original project.


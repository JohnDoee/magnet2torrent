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

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details


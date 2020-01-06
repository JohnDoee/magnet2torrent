import argparse
import asyncio
import ipaddress
import logging

from aiohttp import web

from . import settings
from .exceptions import FailedToFetchException
from .magnet2torrent import Magnet2Torrent
from .server import routes


def main():
    parser = argparse.ArgumentParser(description="Turn a magnet link to torrent.")
    parser.add_argument("--debug", help="Enable debug", action="store_true")
    subparsers = parser.add_subparsers(help="sub-command help", dest="command")

    serve_subparser = subparsers.add_parser(
        "serve", help="Run an HTTP server that serves torrents via an API or directly"
    )
    serve_subparser.add_argument(
        "--ip",
        type=ipaddress.ip_address,
        default=ipaddress.IPv4Address("0.0.0.0"),
        help="Port to listen on",
    )
    serve_subparser.add_argument(
        "--port", type=int, default=18667, help="Host to listen on"
    )
    serve_subparser.add_argument(
        "--apikey",
        type=str,
        default=None,
        help="Protect the endpoint with a simple apikey, add apikey=<apikey> to the url to access",
    )

    fetch_subparser = subparsers.add_parser(
        "fetch", help="Fetch a torrent and save it locally"
    )
    fetch_subparser.add_argument("magnet", help="Magnet link")

    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)-15s:%(levelname)s:%(name)s:%(lineno)d:%(message)s",
        )

    if args.command == "serve":
        if not args.debug:
            stdio_handler = logging.StreamHandler()
            stdio_handler.setLevel(logging.INFO)
            logger = logging.getLogger("aiohttp.access")
            logger.setLevel(logging.INFO)
            logger.addHandler(stdio_handler)

        settings.SERVE_APIKEY = args.apikey
        app = web.Application()
        app.add_routes(routes)
        web.run_app(app, host=str(args.ip), port=args.port)
    elif args.command == "fetch":
        loop = asyncio.get_event_loop()
        m2t = Magnet2Torrent(args.magnet)
        try:
            filename, torrent_data = loop.run_until_complete(m2t.retrieve_torrent())
        except FailedToFetchException:
            print("Unable to fetch magnet link")
            quit(1)
        else:
            with open(filename, "wb") as f:
                f.write(torrent_data)

            print(f"Downloaded magnet link into file: {filename}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

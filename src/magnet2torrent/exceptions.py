class FailedToFetchException(Exception):
    """Unable to fetch torrent exception"""


class MalformedMessage(Exception):
    """
    Message does not contain what is expected.
    """

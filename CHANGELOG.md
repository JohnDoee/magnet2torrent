# Changelog

## [1.2.1] - 2024-01-11

### Bugfix
- Fixed bug related to UDP trackers missing port

## [1.2.0] - 2024-01-06

### Changed
- Removed PY2 support and Six
- Changed aiohttp version dependency to be more free

### Bugfix
- Fixed bug related to bencode / http tracker and how it handles invalid bencoded string

## [1.1.1] - 2020-06-25

### Bugfix
- Fixed bug related to short UDP messages in response from UDP tracker #4 - Thanks to hph86

## [1.1.0] - 2020-05-07

### Added
- DHT support
- Optional torrent metadata storage cache

### Changed
- Fixed bug when torrent had no name.

## [1.0.4] - 2020-02-19

### Changed
- Debug code removed

## [1.0.3] - 2020-01-24

### Changed
- Fixed bug related to HTTP annnounce not always being accepted
- Fixed bug related to unresolable UDP trackers

## [1.0.2] - 2020-01-05

### Changed
- Fixed asyncio Python 3.6 errors, fixing #1
- Added six as dependency, fixing #1

## [1.0.1] - 2020-01-05

### Added
- Changelog

### Changed
- Reading readme for pypi

## [1.0.0] - 2020-01-05

Initial release

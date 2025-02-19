# Changelog

## [4.0.0] - 2025-02-19

### Changed

- __Breaking__: Do not autoconnect on `SerialHandler` zero-arg instantiation ([`2ae3f09`](https://github.com/fossasia/pslab-python/commit/2ae3f0968fbaac9b99d7fc037fd82f16660cd6e1)) (Alexander Bessman)
- __Breaking__: Deprecate `serial_handler` in favor of `connection` ([`0605386`](https://github.com/fossasia/pslab-python/commit/0605386f74f5929008dd7b8396e6bfe9933c6e92)) (Alexander Bessman)
- __Breaking__: Move `SerialHandler` to `connection` ([`2ae3f09`](https://github.com/fossasia/pslab-python/commit/2ae3f0968fbaac9b99d7fc037fd82f16660cd6e1)) (Alexander Bessman)
- __Breaking__: Move `detect` to `connection` ([`2ae3f09`](https://github.com/fossasia/pslab-python/commit/2ae3f0968fbaac9b99d7fc037fd82f16660cd6e1)) (Alexander Bessman)
- __Breaking__: Make `check_serial_access_permission` private ([`2ae3f09`](https://github.com/fossasia/pslab-python/commit/2ae3f0968fbaac9b99d7fc037fd82f16660cd6e1)) (Alexander Bessman)
- __Breaking__: Move `ADCBufferMixin` to `instrument.buffer` ([`2ae3f09`](https://github.com/fossasia/pslab-python/commit/2ae3f0968fbaac9b99d7fc037fd82f16660cd6e1)) (Alexander Bessman)

### Added

- Add common `connection` module for different control interfaces ([`2ae3f09`](https://github.com/fossasia/pslab-python/commit/2ae3f0968fbaac9b99d7fc037fd82f16660cd6e1)) (Alexander Bessman)
- Add `WLANHandler` class for controlling the PSLab over WLAN ([`f595d01`](https://github.com/fossasia/pslab-python/commit/f595d01b51b8d3d2e7c6b8c8c1e4a051fcb793df)) (Alexander Bessman)
- Add `ConnectionHandler` base class for `SerialHandler` and `WLANHandler` ([`2ae3f09`](https://github.com/fossasia/pslab-python/commit/2ae3f0968fbaac9b99d7fc037fd82f16660cd6e1)) (Alexander Bessman)
- Add `connection.autoconnect` function ([`2ae3f09`](https://github.com/fossasia/pslab-python/commit/2ae3f0968fbaac9b99d7fc037fd82f16660cd6e1)) (Alexander Bessman)
- Add `instrument.buffer` module ([`2ae3f09`](https://github.com/fossasia/pslab-python/commit/2ae3f0968fbaac9b99d7fc037fd82f16660cd6e1)) (Alexander Bessman)

### Removed

- __Breaking__: Remove `SerialHandler.wait_for_data` ([`2ae3f09`](https://github.com/fossasia/pslab-python/commit/2ae3f0968fbaac9b99d7fc037fd82f16660cd6e1)) (Alexander Bessman)

### Fixed

- Fix SPI configuration sending one byte too few ([`bd11b73`](https://github.com/fossasia/pslab-python/commit/bd11b7319af7768a6929ba35d0b5e81b43ee5033)) (Alexander Bessman)

## [3.1.1] - 2025-01-05

### Changed

- Raise `RuntimeError` if `_I2CPrimitive._start` is called on an already active peripheral ([`d86fbfa`](https://github.com/fossasia/pslab-python/commit/d86fbfa324b6671926a8548340221b40228c782c)) (Alexander Bessman)

### Fixed

- Fix I2C bus becomes unusable after device scan ([`05c135d`](https://github.com/fossasia/pslab-python/commit/05c135d8c59b5075a1d36e3af256022f5759a3a5)) (Alexander Bessman)

## [3.1.0] - 2024-12-28

_Changelog added in following release._

[4.0.0]: https://github.com/fossasia/pslab-python/releases/tag/4.0.0
[3.1.1]: https://github.com/fossasia/pslab-python/releases/tag/3.1.1
[3.1.0]: https://github.com/fossasia/pslab-python/releases/tag/3.1.0

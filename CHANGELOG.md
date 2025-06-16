# Changelog

## [4.0.1] - 2025-06-16

### Fixed

- Fix UART passthrough ([`1346356`](https://github.com/fossasia/pslab-python/commit/1346356d3cf95691ea0e3e87be335659d5513ec8)) (Anashuman Singh)

## [4.0.0] - 2025-02-19

### Changed

- __Breaking__: Do not autoconnect on `SerialHandler` zero-arg instantiation ([`e70d01d`](https://github.com/fossasia/pslab-python/commit/e70d01d8761b7c0d8446994447849561450d5200)) (Alexander Bessman)
- __Breaking__: Deprecate `serial_handler` in favor of `connection` ([`bc53dd3`](https://github.com/fossasia/pslab-python/commit/bc53dd38830f3d70e908e2c4f1ae797a809231a6)) (Alexander Bessman)
- __Breaking__: Move `SerialHandler` to `connection` ([`e70d01d`](https://github.com/fossasia/pslab-python/commit/e70d01d8761b7c0d8446994447849561450d5200)) (Alexander Bessman)
- __Breaking__: Move `detect` to `connection` ([`e70d01d`](https://github.com/fossasia/pslab-python/commit/e70d01d8761b7c0d8446994447849561450d5200)) (Alexander Bessman)
- __Breaking__: Make `check_serial_access_permission` private ([`e70d01d`](https://github.com/fossasia/pslab-python/commit/e70d01d8761b7c0d8446994447849561450d5200)) (Alexander Bessman)
- __Breaking__: Move `ADCBufferMixin` to `instrument.buffer` ([`e70d01d`](https://github.com/fossasia/pslab-python/commit/e70d01d8761b7c0d8446994447849561450d5200)) (Alexander Bessman)

### Added

- Add common `connection` module for different control interfaces ([`e70d01d`](https://github.com/fossasia/pslab-python/commit/e70d01d8761b7c0d8446994447849561450d5200)) (Alexander Bessman)
- Add `WLANHandler` class for controlling the PSLab over WLAN ([`1316df4`](https://github.com/fossasia/pslab-python/commit/1316df452bff97106dc9313fe9458c93d7f954ab)) (Alexander Bessman)
- Add `ConnectionHandler` base class for `SerialHandler` and `WLANHandler` ([`e70d01d`](https://github.com/fossasia/pslab-python/commit/e70d01d8761b7c0d8446994447849561450d5200)) (Alexander Bessman)
- Add `connection.autoconnect` function ([`e70d01d`](https://github.com/fossasia/pslab-python/commit/e70d01d8761b7c0d8446994447849561450d5200)) (Alexander Bessman)
- Add `instrument.buffer` module ([`e70d01d`](https://github.com/fossasia/pslab-python/commit/e70d01d8761b7c0d8446994447849561450d5200)) (Alexander Bessman)

### Removed

- __Breaking__: Remove `SerialHandler.wait_for_data` ([`e70d01d`](https://github.com/fossasia/pslab-python/commit/e70d01d8761b7c0d8446994447849561450d5200)) (Alexander Bessman)

### Fixed

- Fix SPI configuration sending one byte too few ([`a3d88bb`](https://github.com/fossasia/pslab-python/commit/a3d88bbfeee8cdb012d033c6c80f40b971802851)) (Alexander Bessman)

## [3.1.1] - 2025-01-05

### Changed

- Raise `RuntimeError` if `_I2CPrimitive._start` is called on an already active peripheral ([`d86fbfa`](https://github.com/fossasia/pslab-python/commit/d86fbfa324b6671926a8548340221b40228c782c)) (Alexander Bessman)

### Fixed

- Fix I2C bus becomes unusable after device scan ([`05c135d`](https://github.com/fossasia/pslab-python/commit/05c135d8c59b5075a1d36e3af256022f5759a3a5)) (Alexander Bessman)

## [3.1.0] - 2024-12-28

_Changelog added in following release._

[4.0.1]: https://github.com/fossasia/pslab-python/releases/tag/4.0.1
[4.0.0]: https://github.com/fossasia/pslab-python/releases/tag/4.0.0
[3.1.1]: https://github.com/fossasia/pslab-python/releases/tag/3.1.1
[3.1.0]: https://github.com/fossasia/pslab-python/releases/tag/3.1.0

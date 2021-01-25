# PSLab Python Library

The Python library for the [Pocket Science Lab](https://pslab.io) from FOSSASIA.

[![Build Status](https://travis-ci.org/fossasia/pslab-python.svg?branch=development)](https://travis-ci.org/fossasia/pslab-python)
[![Gitter](https://badges.gitter.im/fossasia/pslab.svg)](https://gitter.im/fossasia/pslab?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/ce4af216571846308f66da4b7f26efc7)](https://www.codacy.com/app/mb/pslab-python?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=fossasia/pslab&amp;utm_campaign=Badge_Grade)
[![Mailing List](https://img.shields.io/badge/Mailing%20List-FOSSASIA-blue.svg)](https://groups.google.com/forum/#!forum/pslab-fossasia)
[![Twitter Follow](https://img.shields.io/twitter/follow/pslabio.svg?style=social&label=Follow&maxAge=2592000?style=flat-square)](https://twitter.com/pslabio)

This repository hosts the Python library for communicating with the Pocket Science Lab open hardware platform (PSLab). Using this library you can communicate with the PSLab using simple Python code. The Python library is also used by the PSLab GUI as a backend component.

The goal of PSLab is to create an Open Source hardware device (open on all layers) and software applications that can be used for experiments by teachers, students and scientists. Our tiny pocket lab provides an array of instruments for doing science and engineering experiments. It provides functions of numerous measurement tools including an oscilloscope, a waveform generator, a logic analyzer, a programmable voltage and current source, and even a component to control robots with up to four servos.

For more information see [https://pslab.io](https://pslab.io).

## Buy

* You can get a Pocket Science Lab device from the [FOSSASIA Shop](https://fossasia.com).
* More resellers are listed on the [PSLab website](https://pslab.io/shop/).

## Installation

pslab-python can be installed from PyPI:

	$ pip install pslab

**Note**: Linux users must additionally install a udev rules file for pslab-python to be able to communicate with the PSLab device. The file [99-pslab.rules](https://github.com/fossasia/pslab-python/blob/development/99-pslab.rules) should be copied to /etc/udev/rules.d/.

**Note**: If you are only interested in using PSLab as an acquisition device without a display/GUI, only pslab-python needs to be installed. If you would like a GUI, install the [pslab-desktop app](https://github.com/fossasia/pslab-desktop) and follow the instructions of the Readme in that repo.


## Validate installation

1. Plug in the PSLab device and check that both the LEDs light up.
2. The following piece of code should run without errors:
```
from PSL import sciencelab
I = sciencelab.connect()
capacitance = I.multimeter.measure_capacitance()
print(capacitance)
```

## Communication

* If you encounter any bugs, please file them in our [issue tracker](https://github.com/fossasia/pslab-python/issues).
* You can chat with the PSLab developers on [Gitter](https://gitter.im/fossasia/pslab).
* There is also a [mailing list](https://groups.google.com/forum/#!forum/pslab-fossasia).

Wherever we interact, we strive to follow the [FOSSASIA Code of Conduct](https://fossasia.org/coc/).

## Contributing

See [CONTRIBUTING.md](https://github.com/fossasia/pslab-python/blob/development/CONTRIBUTING.md) to get started.

## License

This library is free and open source software licensed under the [GPL v3](https://github.com/fossasia/pslab-python/blob/development/README.md). The copyright is owned by FOSSASIA.

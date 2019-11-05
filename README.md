# PSLab Python Library

The Python library for the [Pocket Science Lab](https://pslab.io) from FOSSASIA.

[![Build Status](https://travis-ci.org/fossasia/pslab-python.svg?branch=development)](https://travis-ci.org/fossasia/pslab-python)
[![Gitter](https://badges.gitter.im/fossasia/pslab.svg)](https://gitter.im/fossasia/pslab?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/ce4af216571846308f66da4b7f26efc7)](https://www.codacy.com/app/mb/pslab-python?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=fossasia/pslab&amp;utm_campaign=Badge_Grade)
[![Mailing List](https://img.shields.io/badge/Mailing%20List-FOSSASIA-blue.svg)](https://groups.google.com/forum/#!forum/pslab-fossasia)
[![Twitter Follow](https://img.shields.io/twitter/follow/pslabio.svg?style=social&label=Follow&maxAge=2592000?style=flat-square)](https://twitter.com/pslabio)

This repository hosts the python library for communicating with the Pocket Science Lab open hardware platform (PSLab). This can be installed on a Linux or Windows system. Using this library you can communicate with the PSLab using simple Python code. The Python library is also used in the PSLab desktop application as a backend component. The goal of PSLab is to create an Open Source hardware device (open on all layers) and software applications that can be used for experiments by teachers, students and scientists. Our tiny pocket lab provides an array of instruments for doing science and engineering experiments. It provides functions of numerous measurement tools including an oscilloscope, a waveform generator, a frequency counter, a programmable voltage, current source and even a component to control robots with up to four servos. The website is at: https://pslab.io

## Buy

* You can get a Pocket Science Lab device from the [FOSSASIA Shop](https://fossasia.com).
* More resellers are listed on the [PSLab website](https://pslab.io/shop/).

## Communication

* The PSLab [chat channel is on Gitter](https://gitter.im/fossasia/pslab).
* Please also join us on the [PSLab Mailing List](https://groups.google.com/forum/#!forum/pslab-fossasia).

## Installation

To install PSLab on Debian based GNU/Linux system, the following dependencies must be installed.

### Dependencies

* Python 3.4 or higher [Link to Official download page](https://www.python.org/downloads/windows/)
* Pip &nbsp; **Support package installer**
* NumPy &nbsp; **For numerical calculations**
* PySerial &nbsp; **For device connection**
* iPython-qtconsole &nbsp; **_Optional_**

**Note**: If you are only interested in using PSLab as an acquisition device without a display/GUI, only one repository  [pslab-python](https://github.com/fossasia/pslab-python) needs to be installed. If you like a GUI, install the [pslab-desktop app](https://github.com/fossasia/pslab-desktop) and follow the instructions of the Readme in that repo.

### How To Install on Linux

cd into the directories

    $ cd <SOURCE_DIR>

and run the following

    $ sudo make clean
    $ sudo make
    $ sudo make install

Now you are ready with the PSLab software on your machine.

### How to Install on Windows

**Step 1**: Install the latest Python version on your computer and configure `PATH` variable to have both Python installation directory and the Scripts directory to access `pip` tools. In Windows, Python is installed in `C:` drive by default. We can set `$PATH` by opening the **Environment variables** dialog box by following the steps below;

1. [Right click on My Computer] 
2. Select "Properties"
3. Open "System Properties"
4. Click "Advanced" tab
5. Click "Environment Variables" button
6. Look for "**_PATH_**" in "System Variables" section and click on it and press "Edit" button
7. To the end of "Variable value" text box, append "`C:\Python34\;C:\Python34\Scripts\;`" (without quotes and `34` may differ depending on the python version installed. It could be 35, 37 ...)
8. Click "OK" twice to save and move out from path windows

**Step 2**: Open up command prompt and execute the following commands to install the required dependencies.

    $ pip install pyserial
    $ pip install numpy

#### Validate

1. Download the PSLab-Python library from this repository and extract it to a directory.
2. Browse in to that directory and create a new file named `test-pslab-libs.py`
3. Paste the following code into that file and save it.
```
from PSL import sciencelab
I = sciencelab.connect()
capacitance = I.get_capacitance()
print(capacitance)
```
4. Plug in the PSLab device and check if both the LEDs are turned on.
5. Now run this file by typing `python test-pslab-libs.py` on a command prompt and observe a numerical value printed on the screen along with PSLab device version and the port it is connected to.

### How to Setup the Development Environment

To set up the development environment, install the packages mentioned in dependencies. For building GUI's you can use Qt Designer or create a frontend using any other compatible technology. The PSLab desktop app is using Electron for example.

## How to Build the Documentation Website

First install sphinx by running following command

    sudo pip install -U Sphinx

Then go to pslab/docs and run the following command

    $ sudo make html

## License

The library is free and open source software licensed under the [GPL v3](LICENSE). The copyright is owned by FOSSASIA. 

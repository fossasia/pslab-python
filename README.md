# PSLab-python 

The Pocket Science Lab from FOSSASIA <https://pslab.io>

[![Build Status](https://travis-ci.org/fossasia/pslab-python.svg?branch=development)](https://travis-ci.org/fossasia/pslab-python)
[![Gitter](https://badges.gitter.im/fossasia/pslab.svg)](https://gitter.im/fossasia/pslab?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/ce4af216571846308f66da4b7f26efc7)](https://www.codacy.com/app/mb/pslab-python?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=fossasia/pslab&amp;utm_campaign=Badge_Grade)

This repository hosts the python library for communicating with PSLab. This can be installed on a linux pc/raspberry pi. With this, one can communicate with the hardware using simple python code. 

The goal of PSLab is to create an Open Source hardware device (open on all layers) that can be used for experiments by teachers, students and citizen scientists. Our tiny pocket lab provides an array of sensors for doing science and engineering experiments. It provides functions of numerous measurement devices including an oscilloscope, a waveform generator, a frequency counter, a programmable voltage, current source and as a data logger. Our website is at: https://pslab.io

### Communication

Please join us on the following channels:
* [Pocket Science Channel](https://gitter.im/fossasia/pslab)
* [Mailing List](https://groups.google.com/forum/#!forum/pslab-fossasia)

### Installation

To install PSLab on Debian based Gnu/Linux system, the following dependencies must be installed.

#### Dependencies

* PyQt 4.7+, PySide, or PyQt5
* python 2.6, 2.7, or 3.x
* NumPy, Scipy
* pyqt4-dev-tools         &nbsp;   **For pyuic4**
* Pyqtgraph               &nbsp;  **For Plotting library**
* pyopengl and qt-opengl  &nbsp;   **For 3D graphics**
* iPython-qtconsole       &nbsp;   **optional**


##### Now clone both the repositories [pslab-apps](https://github.com/fossasia/pslab-apps)  and [pslab](https://github.com/fossasia/pslab).


##### Libraries must be installed in any order

1. pslab-apps
2. pslab

**Note**
*If user is only interested in using PSLab as an acquisition device without a display/GUI, only one repository  [pslab](https://github.com/fossasia/pslab) needs to be installed*


##### To install, cd into the directories

    $ cd <SOURCE_DIR>

and run the following (for both the repos)

    $ sudo make clean

    $ sudo make

    $ sudo make install

Now you are ready with the PSLab software on your machine :)

For the main GUI (Control panel), you can run Experiments from the terminal.

    $ Experiments

-----------------------

#### Development Environment

To set up the development environment, install the packages mentioned in dependencies. For building GUI's Qt Designer is used.

## Steps to build documentation

First install sphinx by running following command

    pip install -U Sphinx

Then go to pslab/docs and run the following command

    $ make html

### Blog posts related to PSLab on FOSSASIA blog 
* [Installation of PSLab](http://blog.fossasia.org/pslab-code-repository-and-installation/)
* [Communicating with PSLab](http://blog.fossasia.org/communicating-with-pocket-science-lab-via-usb-and-capturing-and-plotting-sine-waves/)
* [Features and Controls of PSLab](http://blog.fossasia.org/features-and-controls-of-pocket-science-lab/)
* [Design your own Experiments](http://blog.fossasia.org/design-your-own-experiments-with-pslab/)
* [New Tools and Sensors for Fossasia PSLab and ExpEYES](http://blog.fossasia.org/new-tools-and-sensors-fossasia-pslab-and-expeyes/) 



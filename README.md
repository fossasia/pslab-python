# PSLab 

The Pocket Science Lab from FOSSASIA <http://pslab.fossasia.org>

This repository hosts the python library for communicating with PSLab. This can be installed on a linux pc/raspberry pi. With this, one can communicate with the hardware using simple python code. 


* The project is inspired from ExpEYES  http://expeyes.in
* FOSSASIA is supporting development and promotion of ExpEYES project since 2014 mainly through Google Summer of Code
* The current work is a part of my GSoC-16 project

Installation
------------

To install PSLab on Debian based Gnu/Linux system, the following dependencies must be installed.

####Dependencies

* PyQt 4.7+, PySide, or PyQt5
* python 2.6, 2.7, or 3.x
* NumPy, Scipy
* pyqt4-dev-tools         &nbsp;   #for pyuic4
* Pyqtgraph               &nbsp;  #Plotting library
* pyopengl and qt-opengl  &nbsp;   #for 3D graphics
* iPython-qtconsole       &nbsp;   #optional


#####Now clone both the repositories [pslab-apps](https://github.com/fossasia/pslab-apps)  and [pslab](https://github.com/fossasia/pslab).

#####Libraries must be installed in the following order

1. pslab-apps
2. pslab


To install, cd into the directories

`$ cd <SOURCE_DIR>`

and run the following (for both the repos)

`$ sudo make clean`

`$ sudo make` 

`$ sudo make install`

Now you are ready with the PSLab software on your machine :)

For the main GUI (Control panel), you can run Experiments from the terminal.

`$ Experiments`


####Development Environment
-----------------------
To set up the development environment, install the packages mentioned in dependencies. For building GUI's Qt Designer is used.

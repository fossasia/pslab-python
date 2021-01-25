Installation
============

``pslab-python`` can be installed from PyPI:
::

    $ pip install pslab

**Note:** Linux users must additionally install a udev rules file for
pslab-python to be able to communicate with the PSLab device. The file
[99-pslab.rules](https://github.com/fossasia/pslab-python/blob/development/99-pslab.rules)
should be copied to /etc/udev/rules.d/.

**Note**: pslab-python does not provide a graphical user interface. If you want
a GUI, install the [pslab-desktop app](https://github.com/fossasia/pslab-desktop).

Dependencies
------------

``pslab-python`` requires `Python <http://python.org/download/>`__ version
3.6 or later.
#!/usr/bin/env python
from __future__ import print_function

import os
import shutil
from distutils.util import execute
from subprocess import call

from setuptools import setup, find_packages
from setuptools.command.install import install


def udev_reload_rules():
    call(["udevadm", "control", "--reload-rules"])


def udev_trigger():
    call(["udevadm", "trigger", "--subsystem-match=usb", "--attr-match=idVendor=04d8", "--action=add"])


def install_udev_rules(raise_exception):
    if check_root():
        shutil.copy('99-pslab.rules', '/etc/udev/rules.d')
        execute(udev_reload_rules, [], "Reloading udev rules")
        execute(udev_trigger, [], "Triggering udev rules")
    else:
        msg = "You must have root privileges to install udev rules. Run 'sudo python setup.py install'"
        if raise_exception:
            raise OSError(msg)
        else:
            print(msg)


def check_root():
    return os.geteuid() == 0


class CustomInstall(install):
    def run(self):
        if not hasattr(self, "root"):
            install_udev_rules(True)
        elif self.root is not None:
            if 'debian' not in self.root:
                install_udev_rules(True)
        install.run(self)


setup(name='PSL',
      version='1.1.0',
      description='Pocket Science Lab by FOSSASIA',
      author='FOSSASIA PSLab Developers',
      author_email='pslab-fossasia@googlegroups.com',
      url='https://pslab.io/',
      install_requires=['numpy>=1.16.3.', 'pyqtgraph>=0.9.10'],
      packages=find_packages(),
      package_data={'': ['*.css', '*.png', '*.gif', '*.html', '*.css', '*.js', '*.png', '*.jpg', '*.jpeg', '*.htm',
                         '99-pslab.rules']},
      cmdclass={'install': CustomInstall})

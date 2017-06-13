#!/usr/bin/env python


from __future__ import print_function
#from distutils.core import setup
from setuptools import setup, find_packages
from setuptools.command.install import install
import os,shutil
from distutils.util import execute
from distutils.cmd import Command
from subprocess import call

def udev_reload_rules():
    call(["udevadm", "control", "--reload-rules"])

def udev_trigger():
    call(["udevadm", "trigger", "--subsystem-match=usb","--attr-match=idVendor=04d8", "--action=add"])

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
        if not hasattr(self,"root"):
            install_udev_rules(True)
        elif self.root is not None:
            if 'debian' not in self.root:
                install_udev_rules(True)
        install.run(self)

setup(name='PSL',
    version='1.0.0',
    description='Pocket Science Lab from FOSSASIA - inspired by ExpEYES http://expeyes.in',
    author='Praveen Patil and Jithin B.P.',
    author_email='praveenkumar103@gmail.com',
    url='http://fossasia.github.io/pslab.fossasia.org/',
    install_requires = ['numpy>=1.8.1','pyqtgraph>=0.9.10'],
    packages=find_packages(),
    #scripts=["PSL/bin/"+a for a in os.listdir("PSL/bin/")],
    package_data={'': ['*.css','*.png','*.gif','*.html','*.css','*.js','*.png','*.jpg','*.jpeg','*.htm','99-pslab.rules']},
    cmdclass={'install': CustomInstall},
)


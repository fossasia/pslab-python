from distutils.cmd import Command
from distutils.util import execute
import os
import platform
import shutil
from subprocess import call
import warnings

from setuptools import setup, find_packages
from setuptools.command.develop import develop
from setuptools.command.install import install


def udev_reload_rules():
    call(["udevadm", "control", "--reload-rules"])


def udev_trigger():
    call(  # nosec
        [
            "udevadm",
            "trigger",
            "--subsystem-match=usb",
            "--attr-match=idVendor=04d8",
            "--action=add",
        ]
    )


def install_udev_rules():
    shutil.copy("99-pslab.rules", "/lib/udev/rules.d")
    execute(udev_reload_rules, [], "Reloading udev rules")
    execute(udev_trigger, [], "Triggering udev rules")


def check_root():
    return os.geteuid() == 0


class CustomInstall(install):
    def run(self):
        install.run(self)
        self.run_command("udev")


class CustomDevelop(develop):
    def run(self):
        develop.run(self)
        try:
            self.run_command("udev")
        except OSError as e:
            warnings.warn(e)


class InstallUdevRules(Command):
    description = "install udev rules (requires root privileges)."
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        if platform.system() == "Linux":
            if check_root():
                install_udev_rules()
            else:
                msg = "You must have root privileges to install udev rules."
                raise OSError(msg)


setup(
    name="PSL",
    version="1.1.0",
    description="Pocket Science Lab by FOSSASIA",
    author="FOSSASIA PSLab Developers",
    author_email="pslab-fossasia@googlegroups.com",
    url="https://pslab.io/",
    install_requires=["numpy>=1.16.3."],
    packages=find_packages(),
    package_data={
        "": [
            "*.css",
            "*.png",
            "*.gif",
            "*.html",
            "*.css",
            "*.js",
            "*.png",
            "*.jpg",
            "*.jpeg",
            "*.htm",
            "99-pslab.rules",
        ]
    },
    cmdclass={
        "develop": CustomDevelop,
        "install": CustomInstall,
        "udev": InstallUdevRules,
    },
)

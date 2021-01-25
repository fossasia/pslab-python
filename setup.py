import setuptools


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pslab",
    version="2.0.0.rc1",
    description="Pocket Science Lab by FOSSASIA",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="FOSSASIA PSLab Developers",
    author_email="pslab-fossasia@googlegroups.com",
    url="https://pslab.io/",
    install_requires=["numpy>=1.16.3", "pyserial>=3.4", "scipy>=1.3.0"],
    python_requires=">=3.6",
    packages=setuptools.find_packages(exclude=("tests",)),
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
    entry_points = {
        'console_scripts': ['pslab=PSL.cli:cmdline'],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
    ],
)

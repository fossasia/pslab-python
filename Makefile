DESTDIR =

# Find library installation path
INSTALL_PATH = $(patsubst Location:,,$(shell python3 -m pip show PSL | grep Location))
INSTALL_PATH_LEN = $(shell echo $(INSTALL_PATH) | wc -c)

all:
        python3 setup.py build

fullcleanup: verifyFiles
        # Removes every PSL instance in system. Be careful and check if the following list got all files inside a python folder or related to PSLab
        find /usr/* -name "PSL*" -type d | xargs rm -rf
        find /usr/* -name "pslab*" -type d | xargs rm -rf
        find /opt/* -name "pslab-*" -type d | xargs rm -rf
        find /usr/* -name "Experiments" -type f | xargs rm -rf
        @echo "All selected files are deleted.."

verifyFiles:
        @find /usr/* -name "PSL*" -type d
        @find /usr/* -name "pslab*" -type d
        @find /opt/* -name "pslab-*" -type d
        @find /usr/* -name "Experiments" -type f
        @echo -n "Confirm if you want to remove all these files.. [Y/N] " && read ans && [ $${ans:-N} = Y ]

clean:
        # Remove build files
        @rm -rf docs/_*
        @rm -rf PSL.egg-info build
        @find . -name "*~" -o -name "*.pyc" -o -name "__pycache__" | xargs rm -rf
        if [ ${INSTALL_PATH_LEN} -gt 2 ]; then sudo rm -rf $(INSTALL_PATH)/PSL $(INSTALL_PATH)/PSL-1* ; fi

install:
        python3 setup.py install
        mkdir -p $(DESTDIR)/lib/udev/rules.d
        install -m 644 99-pslab.rules $(DESTDIR)/lib/udev/rules.d/99-pslab

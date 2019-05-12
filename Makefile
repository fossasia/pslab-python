DESTDIR =

# Find library installation path
INSTALL_PATH = $(patsubst Location:,,$(shell pip show PSL | grep Location))
INSTALL_PATH_LEN = $(shell echo $(INSTALL_PATH) | wc -c)

all:
	python3 setup.py build

clean:
	# Remove build files
	@rm -rf docs/_*
	@rm -rf PSL.egg-info build
	@find . -name "*~" -o -name "*.pyc" -o -name "__pycache__" | xargs rm -rf
	# Remove previously installed library files if there is any
	if [ ${INSTALL_PATH_LEN} -gt 2 ]; then sudo rm -rf $(INSTALL_PATH)/PSL $(INSTALL_PATH)/PSL-1* ; fi

install:
	python3 setup.py install
	# rules for udev
	mkdir -p $(DESTDIR)/lib/udev/rules.d
	install -m 644 99-pslab.rules $(DESTDIR)/lib/udev/rules.d/99-pslab

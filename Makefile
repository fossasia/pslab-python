DESTDIR =

all:
	python setup.py build

clean:
	@rm -rf docs/_*
	@rm -rf PSL.egg-info build
	@find . -name "*~" -o -name "*.pyc" -o -name "__pycache__" | xargs rm -rf

install:
	python setup.py install
	# rules for udev
	mkdir -p $(DESTDIR)/lib/udev/rules.d
	install -m 644 99-pslab.rules $(DESTDIR)/lib/udev/rules.d/99-pslab

DESTDIR =

all:
	[ ! -d PSLab-apps-master ] || make -C PSLab-apps-master $@ DESTDIR=$(DESTDIR)
	python3 setup.py build

clean:
	rm -rf docs/_*
	[ ! -d PSLab-apps-master ] || make -C PSLab-apps-master $@ DESTDIR=$(DESTDIR)
	rm -rf PSL.egg-info build
	find . -name "*~" -o -name "*.pyc" -o -name "__pycache__" | xargs rm -rf

install:
	# make in subdirectory PSLab-apps-master if it is there
	[ ! -d PSLab-apps-master ] || make -C PSLab-apps-master $@ DESTDIR=$(DESTDIR)
	# install documents
	install -d $(DESTDIR)/usr/share/doc/pslab
	python3 setup.py install --install-layout=deb --root=$(DESTDIR)/ --prefix=/usr
	# rules for udev
	mkdir -p $(DESTDIR)/lib/udev/rules.d
	install -m 644 99-pslab.rules $(DESTDIR)/lib/udev/rules.d/99-pslab

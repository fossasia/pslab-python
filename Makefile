DESTDIR =
all:
	#make -C docs html
	#make -C docs/misc all
	# make in subdirectory PSLab-apps-master if it is there
	[ ! -d PSLab-apps-master ] || make -C PSLab-apps-master $@ DESTDIR=$(DESTDIR)
	python setup.py build

clean:
	rm -rf docs/_*
	# make in subdirectory PSLab-apps-master if it is there
	[ ! -d PSLab-apps-master ] || make -C PSLab-apps-master $@ DESTDIR=$(DESTDIR)
	rm -rf PSL.egg-info build
	find . -name "*~" -o -name "*.pyc" -o -name "__pycache__" | xargs rm -rf

IMAGEDIR=$(DESTDIR)/usr/share/doc/pslab-common/images

install:
	# make in subdirectory PSLab-apps-master if it is there
	[ ! -d PSLab-apps-master ] || make -C PSLab-apps-master $@ DESTDIR=$(DESTDIR)
	# install documents
	install -d $(DESTDIR)/usr/share/doc/pslab
	#cp -a docs/_build/html $(DESTDIR)/usr/share/doc/pslab
	#cp docs/misc/build/*.html $(DESTDIR)/usr/share/doc/pslab/html
	python setup.py install --install-layout=deb \
	         --root=$(DESTDIR)/ --prefix=/usr
	# rules for udev
	mkdir -p $(DESTDIR)/lib/udev/rules.d
	install -m 644 99-pslab.rules $(DESTDIR)/lib/udev/rules.d/99-pslab
	# fix a few permissions
	#find $(DESTDIR)/usr/share/pslab/psl_res -name auto.sh -exec chmod -x {} \;

OUTPUTS = autotab.plugin  autotab.py
DESTDIR = ~/.local/share/gedit/plugins

install: autotab.plugin  autotab.py
	@ [ `whoami` != "root" ] || ( echo 'Run make install as yourself, not as root.' ; exit 1 )
	mkdir -p $(DESTDIR)
	cp $(OUTPUTS) $(DESTDIR)

uninstall:
	rm -f $(foreach o, $(OUTPUTS), $(DESTDIR)/$o)


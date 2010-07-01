OUTPUTS = autotab.gedit-plugin  autotab.py

install: autotab.gedit-plugin  autotab.py
	@ [ `whoami` != "root" ] || ( echo 'Run make install as yourself, not as root.' ; exit 1 )
	mkdir -p ~/.gnome2/gedit/plugins
	cp $(OUTPUTS) ~/.gnome2/gedit/plugins

uninstall:
	rm -f $(foreach o, $(OUTPUTS), ~/.gnome2/gedit/plugins/$o)


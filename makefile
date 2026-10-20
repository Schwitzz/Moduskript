UI := $(wildcard moduskript/ui/*.ui) $(wildcard moduskript/ui/*/*.ui) $(wildcard moduskript/ui/*/*/*.ui) $(wildcard moduskript/ui/*.qrc) 
UIs= $(UI:.ui=.py) $(UI:.qrc=_rc.py)
TS := $(wildcard i18n/*.ts)
QMs= $(TS:.ts=.qm)

ui: $(UIs)

run: $(UIs)
# 	python3 manuskript/main.py
	bin/moduskript

debug: $(UIs)
	gdb --args python3 bin/moduskript

lineprof:
	kernprof -l -v bin/moduskript

profile:
	python3 -m cProfile -s 'cumtime' bin/moduskript | more

compile:
	cd moduskript && python3 setup.py build_ext --inplace

callgraph:
	cd moduskript; pycallgraph myoutput -- main.py

translation:
	pylupdate5 -noobsolete i18n/moduskript.pro

linguist:
	linguist i18n/moduskript_fr.ts
	lrelease i18n/moduskript_fr.ts

i18n: $(QMs)

pyinstaller:
	python3 /usr/local/bin/pyinstaller moduskript.spec

snappkg:
	snapcraft snap

stats:
	python3 libs/gh-release-stats.py olivierkes manuskript -d

%_rc.py : %.qrc
	pyrcc5 "$<" -o "$@"

%.py : %.ui
# 	pyuic4  "$<" > "$@"
	pyuic5  "$<" > "$@"

%.qm:  %.ts
	lrelease "$<"


py_files := $(wildcard *.py)

mkwg: $(py_files)
	python -m zipapp -p '/usr/bin/env python3' -o $@ $<
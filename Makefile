py_files := $(wildcard *.py)

mkwg: $(py_files)
	tmpdir="$$(mktemp -d)" && cp $^ "$$tmpdir" && python -m zipapp -p '/usr/bin/env python3' -o $@ "$$tmpdir"

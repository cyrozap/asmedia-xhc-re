# SPDX-License-Identifier: GPL-3.0-or-later

# Copyright (C) 2020-2021  Forest Crossman <cyrozap@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


KAITAI_STRUCT_COMPILER ?= kaitai-struct-compiler

DOC_SOURCES := $(wildcard data/regs-*.yaml)
DOC_TARGETS := $(DOC_SOURCES:data/%.yaml=doc/out/%.xhtml)
DOC_TARGETS += doc/out/pm/index.html

TOOL_TARGETS := tools/asm_fw.py


all: $(TOOL_TARGETS)

tools/%.py: tools/%.ksy
	$(KAITAI_STRUCT_COMPILER) --target=python --outdir=$(@D) $<

doc/out/%.xhtml: data/%.yaml tools/generate_docs.py
	python3 tools/generate_docs.py -o $@ $<

doc/out/pm/index.html: doc/src/index.adoc $(wildcard doc/src/*.adoc)
	asciidoctor --out-file $@ $<

doc: $(DOC_TARGETS)

clean:
	rm -f $(TOOL_TARGETS) $(DOC_TARGETS)


.PHONY: clean doc

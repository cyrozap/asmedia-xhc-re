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

DOC_SOURCES := $(wildcard data/regs-*.yaml)
DOC_TARGETS := $(DOC_SOURCES:data/%.yaml=doc/out/%.xhtml)


all: asm_fw.py

%.py: %.ksy
	kaitai-struct-compiler -t python $<

doc/out/%.xhtml: data/%.yaml generate_docs.py
	python3 generate_docs.py -o $@ $<

doc: $(DOC_TARGETS)

clean:
	rm -f asm_fw.py $(DOC_TARGETS)


.PHONY: clean doc

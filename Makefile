DOC_SOURCES := $(wildcard data/regs-*.yaml)
DOC_TARGETS := $(DOC_SOURCES:data/%.yaml=doc/out/%.xhtml)
DOC_TARGETS += doc/out/pm/index.html


all: asm_fw.py

%.py: %.ksy
	kaitai-struct-compiler -t python $<

doc/out/%.xhtml: data/%.yaml generate_docs.py
	python3 generate_docs.py -o $@ $<

doc/out/pm/index.html: doc/src/index.adoc $(wildcard doc/src/*.adoc)
	asciidoctor --out-file $@ $<

doc: $(DOC_TARGETS)

clean:
	rm -f asm_fw.py $(DOC_TARGETS)


.PHONY: clean doc

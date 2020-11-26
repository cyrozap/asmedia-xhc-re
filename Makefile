all: asm_fw.py

%.py: %.ksy
	kaitai-struct-compiler -t python $<

doc/%.xhtml: data/%.yaml generate_docs.py
	python3 generate_docs.py -o $@ $<

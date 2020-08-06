all: asm_fw.py

%.py: %.ksy
	kaitai-struct-compiler -t python $<

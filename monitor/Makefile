AS := sdas8051
ASFLAGS := -l -o -s
CC := sdcc
CFLAGS := -mmcs51 --std-sdcc11 --model-small --stack-auto
OBJCOPY := sdobjcopy

TARGET ?= ASM1142
FLASH_SIZE ?= 64K

all: monitor.img monitor.bin

%.rel: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

%.rel: %.S
	$(AS) $(ASFLAGS) $<

build_info.c: build_info.inc.c
	sed s/BUILD_VERSION/$(shell printf "r%s.g%s" "$(shell git rev-list --count HEAD)" "$(shell git rev-parse --short HEAD)")/g $< | \
		sed s/BUILD_TIME/$(shell date -u '+%FT%H:%M:%SZ')/g > $@

sfr.c: sfr.inc.c gen_sfr_c.py
	./gen_sfr_c.py -o $@ $<

monitor.ihx: main.rel sfr.rel vectors.rel build_info.rel
	$(CC) $(CFLAGS) -o $@ $^

%.bin: %.ihx
	$(OBJCOPY) -I ihex -O binary $< $@

%.img: %.bin
	./make_image.py -c $(TARGET) -o $@ $<
	truncate -s $(FLASH_SIZE) $@

flash: monitor.img
	flashrom -p ch341a_spi -w $<

clean:
	rm -f *.asm *.bin *.ihx *.img *.lk *.lst *.map *.mem *.rel *.rst *.sym build_info.c sfr.c

.PHONY: all clean flash build_info.c

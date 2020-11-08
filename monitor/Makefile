AS := sdas8051
ASFLAGS := -l -o -s
CC := sdcc
CFLAGS := -mmcs51 --std-sdcc11 --model-small --stack-auto
OBJCOPY := sdobjcopy

all: monitor.img monitor.bin

%.rel: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

%.rel: %.S
	$(AS) $(ASFLAGS) $<

build_info.c: build_info.inc.c
	sed s/BUILD_VERSION/$(shell printf "r%s.g%s" "$(shell git rev-list --count HEAD)" "$(shell git rev-parse --short HEAD)")/g $< | \
		sed s/BUILD_TIME/$(shell date -u '+%FT%H:%M:%SZ')/g > $@

monitor.ihx: main.rel vectors.rel build_info.rel
	$(CC) $(CFLAGS) -o $@ $^

%.bin: %.ihx
	$(OBJCOPY) -I ihex -O binary $< $@

%.img: %.bin
	./make_image.py -o $@ $<

flash: monitor.img
	flashrom -p ch341a_spi -w $<

clean:
	rm -f *.asm *.bin *.ihx *.img *.lk *.lst *.map *.mem *.rel *.rst *.sym build_info.c

.PHONY: all clean flash build_info.c

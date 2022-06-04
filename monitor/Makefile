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


AS := sdas8051
ASFLAGS := -l -o -s
CC := sdcc
CFLAGS := -mmcs51 --std-sdcc11 --model-small --stack-auto
OBJCOPY := sdobjcopy

CHIPS := ASM1042 ASM1042A ASM1142 ASM2142 ASM3242
CHIPS_LOWER := $(shell echo $(CHIPS) | tr A-Z a-z)
BINARIES := $(CHIPS_LOWER:%=monitor-%.bin)
IMAGES := $(BINARIES:%.bin=%.img)

TARGET ?= ASM1142
TARGET_LOWER = $(shell echo $(TARGET) | tr A-Z a-z)
FLASH_SIZE ?= 64K

all: $(IMAGES) $(BINARIES)

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

$(BINARIES): monitor.bin
	./make_image.py -t bin -c $$(echo $@ | sed -e 's/monitor-\([0-9a-z]\+\)\.bin/\1/g' | tr a-z A-Z) -o $@ $<

%.img: %.bin
	./make_image.py -t image -c $$(echo $@ | sed -e 's/monitor-\([0-9a-z]\+\)\.img/\1/g' | tr a-z A-Z) -o $@ $<

%.flash: %.img
	cp $< $@
	truncate -c -s $(FLASH_SIZE) $@

flash: monitor-$(TARGET_LOWER).flash
	flashrom -p ch341a_spi -w $<

clean:
	rm -f *.asm *.bin *.flash *.ihx *.img *.lk *.lst *.map *.mem *.rel *.rst *.sym build_info.c sfr.c

.PHONY: all clean flash build_info.c

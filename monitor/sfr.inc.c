#include <mcs51/compiler.h>

#include "sfr.h"

${SFR_DEFS}

uint8_t get_sfr(uint8_t addr) {
	switch (addr) {
${GET_CASES}
	default:
		return 0;
	}
}

void set_sfr(uint8_t addr, uint8_t value) {
	switch (addr) {
${SET_CASES}
	default:
		break;
	}
}

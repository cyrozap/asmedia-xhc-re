#ifndef SFR_H
#define SFR_H

#include <stdint.h>

uint8_t get_sfr(uint8_t addr);
void set_sfr(uint8_t addr, uint8_t value);

#endif /* SFR_H */

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include <mcs51/8051.h>

#include "sfr.h"

static __sfr __at (0x93) DPX;

static char const __code __at (0x0087) fw_magic[8];

static uint32_t UART_BASE;
#define UART_RBR (UART_BASE + 0)
#define UART_THR (UART_BASE + 1)
#define UART_RFBR (UART_BASE + 5)
#define UART_TFBF (UART_BASE + 6)
#define UART_LCR (UART_BASE + 7)

static uint32_t CPU_CON_BASE;
#define CPU_MODE_NEXT (CPU_CON_BASE + 0)
#define CPU_MODE_CURRENT (CPU_CON_BASE + 1)
#define CPU_MODE_NEXT_CURRENT_CLOCK_DIV (1 << 1)
#define CPU_EXEC_CTRL (CPU_CON_BASE + 2)
#define CPU_EXEC_CTRL_RESET (1 << 0)
#define CPU_EXEC_CTRL_HALT (1 << 1)

static uint32_t CHIP_VERSION_ADDR;

#define MAX_CMD_LEN 80
#define MAX_ARGS 3

extern char const * const build_version;
extern char const * const build_time;

static char const * chip_name;

__bit volatile eint0_triggered = 0;
__bit volatile eint1_triggered = 0;


void isr_eint0 (void) __interrupt {
	EX0 = 0;
	eint0_triggered = 1;
}

void isr_eint1 (void) __interrupt {
	EX1 = 0;
	eint1_triggered = 1;
}

/*
 * Prefix the 16-bit address with one of the following bytes to access
 * the corresponding memory region:
 *   0x00: XRAM
 *   0x40: IRAM
 *   0x80: PMEM
 */

#define ADDR_MAX 0xFFFFFFUL

static uint8_t readb(uint32_t reg) {
	if (reg < 0xC00000UL) {
		uint8_t ret;
		uint8_t dpx = DPX;
		DPX = (reg >> 16) & 0x1f;
		ret = *(uint8_t *)(reg);
		DPX = dpx;
		return ret;
	} else
		return get_sfr(reg);
}

#if 0
static uint16_t readw(uint32_t reg) {
	if (reg < 0xC00000UL) {
		uint16_t ret;
		uint8_t dpx = DPX;
		DPX = (reg >> 16) & 0x1f;
		ret = *(uint16_t *)(reg);
		DPX = dpx;
		return ret;
	} else {
		uint32_t value;
		for (size_t i = 0; i < 2; i++) {
			((uint8_t *)&value)[i] = get_sfr(reg+i);
		}
		return value;
	}
}
#endif

static uint32_t readl(uint32_t reg) {
	if (reg < 0xC00000UL) {
		uint32_t ret;
		uint8_t dpx = DPX;
		DPX = (reg >> 16) & 0x1f;
		ret = *(uint32_t *)(reg);
		DPX = dpx;
		return ret;
	} else {
		uint32_t value;
		for (size_t i = 0; i < 4; i++) {
			((uint8_t *)&value)[i] = get_sfr(reg+i);
		}
		return value;
	}
}

static void writeb(uint32_t reg, uint8_t value) {
	if (reg < 0x800000UL) {
		uint8_t dpx = DPX;
		DPX = (reg >> 16) & 0x1f;
		*(uint8_t *)(reg) = value;
		DPX = dpx;
	} else if (reg < 0xC00000UL) {
		uint8_t dpx = DPX;
		DPX = (reg >> 16) & 0x1f;
		PCON |= (1 << 4);
		*(uint8_t *)(reg & 0xffff) = value;
		PCON &= ~(1 << 4);
		DPX = dpx;
	} else
		set_sfr(reg, value);
}

#if 0
static void writew(uint32_t reg, uint16_t value) {
	if (reg < 0x800000UL) {
		uint8_t dpx = DPX;
		DPX = (reg >> 16) & 0x1f;
		*(uint16_t *)(reg) = value;
		DPX = dpx;
	} else if (reg < 0xC00000UL) {
		uint8_t dpx = DPX;
		DPX = (reg >> 16) & 0x1f;
		PCON |= (1 << 4);
		*(uint16_t *)(reg & 0xffff) = value;
		PCON &= ~(1 << 4);
		DPX = dpx;
	} else {
		set_sfr(reg+0, value & 0xff);
		set_sfr(reg+1, (value >> 8) & 0xff);
	}
}
#endif

static void writel(uint32_t reg, uint32_t value) {
	if (reg < 0x800000UL) {
		uint8_t dpx = DPX;
		DPX = (reg >> 16) & 0x1f;
		*(uint32_t *)(reg) = value;
		DPX = dpx;
	} else if (reg < 0xC00000UL) {
		uint8_t dpx = DPX;
		DPX = (reg >> 16) & 0x1f;
		PCON |= (1 << 4);
		*(uint32_t *)(reg & 0xffff) = value;
		PCON &= ~(1 << 4);
		DPX = dpx;
	} else {
		set_sfr(reg+0, value & 0xff);
		set_sfr(reg+1, (value >> 8) & 0xff);
		set_sfr(reg+2, (value >> 16) & 0xff);
		set_sfr(reg+3, (value >> 24) & 0xff);
	}
}

static char getchar(void) {
	char ret;

	// Wait for at least one byte of data to appear in the UART RX
	// FIFO.
	while (readb(UART_RFBR) < 1);

	ret = readb(UART_RBR);

	return ret;
}

static void putchar(char c) {
	// Wait for space to free up in the UART TX FIFO.
	while (readb(UART_TFBF) < 8);

	if (c == '\n')
		putchar('\r');

	writeb(UART_THR, c);
}

static void putbyte(uint8_t b) {
	// Wait for space to free up in the UART TX FIFO.
	while (readb(UART_TFBF) < 8);

	writeb(UART_THR, b);
}

static void print(const char * buf) {
	for (size_t i = 0; ; i++) {
		if (buf[i] == 0)
			break;
		putchar(buf[i]);
	}
}

static void println(const char * buf) {
	print(buf);
	putchar('\n');
}

typedef enum {
	CHIP_ASM1042,
	CHIP_ASM1042A,
	CHIP_ASM1142,
	CHIP_ASM2142,
	CHIP_ASM3242,
	CHIP_UNKNOWN,
} chip_t;

typedef struct {
	chip_t chip;
	char const * base;
	char const * divided;
} chip_clocks_t;

#define CLK_062500MHZ "62.5 MHz"
#define CLK_125000MHZ "125 MHz"
#define CLK_078125MHZ "78.125 MHz"
#define CLK_156250MHZ "156.25 MHz"
#define CLK_UNKNOWNHZ "UNKNOWN MHz"

static chip_clocks_t const chip_clocks_map[] = {
	{CHIP_ASM1042A, CLK_125000MHZ, CLK_062500MHZ},
	{CHIP_ASM1142,  CLK_156250MHZ, CLK_078125MHZ},
	{CHIP_ASM2142,  CLK_156250MHZ, CLK_078125MHZ},
	{CHIP_ASM3242,  CLK_156250MHZ, CLK_078125MHZ},
	{CHIP_UNKNOWN,  CLK_UNKNOWNHZ, CLK_UNKNOWNHZ},
};

static char const * get_current_clock_speed(chip_t chip) {
	for (size_t i = 0; chip_clocks_map[i].chip != CHIP_UNKNOWN; i++) {
		if (chip == chip_clocks_map[i].chip) {
			if (readb(CPU_MODE_CURRENT) & CPU_MODE_NEXT_CURRENT_CLOCK_DIV)
				return chip_clocks_map[i].divided;
			else
				return chip_clocks_map[i].base;
		}
	}

	return CLK_UNKNOWNHZ;
}

typedef struct {
	char * fw_magic;
	chip_t chip;
} magic_chip_t;

static magic_chip_t const magic_chip_map[] = {
	{"U2104_FW", CHIP_ASM1042},
	{"2104B_FW", CHIP_ASM1042A},
	{"2114A_FW", CHIP_ASM1142},
	{"2214A_FW", CHIP_ASM2142},
	{"2324A_FW", CHIP_ASM3242},
	{NULL, CHIP_UNKNOWN},
};

static chip_t get_chip_type(void) {
	for (size_t i = 0; magic_chip_map[i].fw_magic != NULL; i++) {
		if (!strncmp(magic_chip_map[i].fw_magic, fw_magic, 8)) {
			return magic_chip_map[i].chip;
		}
	}

	return CHIP_UNKNOWN;
}

static void init(void) {
	chip_t chip = get_chip_type();
	switch(chip) {
	case CHIP_ASM1042:
		chip_name = "ASM1042";
		UART_BASE = 0xF100;
		CPU_CON_BASE = 0xF340;
		CHIP_VERSION_ADDR = 0xF38C;
		break;
	case CHIP_ASM1042A:
		chip_name = "ASM1042A";
		UART_BASE = 0xF100;
		CPU_CON_BASE = 0xF340;
		CHIP_VERSION_ADDR = 0xF38C;
		break;
	case CHIP_ASM1142:
		chip_name = "ASM1142";
		UART_BASE = 0xF100;
		CPU_CON_BASE = 0xF340;
		CHIP_VERSION_ADDR = 0xF38C;
		break;
	case CHIP_ASM2142:
		chip_name = "ASM2142";
		UART_BASE = 0x15100;
		CPU_CON_BASE = 0x15040;
		CHIP_VERSION_ADDR = 0x150B2;
		break;
	case CHIP_ASM3242:
		chip_name = "ASM3242";
		UART_BASE = 0x15100;
		CPU_CON_BASE = 0x15040;
		CHIP_VERSION_ADDR = 0x1508C;
		break;
	default:
		chip_name = "UNKNOWN";
		break;
	}

	/* Serial port setup */
	writeb(UART_LCR, 3);  /* 8N1 */
}

#if 0
static int parse_dec(uint32_t * value, const char * str) {
	size_t len = strlen(str);
	if (len > 10) {
		println("Error: Decimal string too long.");
		return -1;
	}

	*value = 0;
	uint32_t multiplier = 1;
	for (size_t i = 0; i < len; i++) {
		char c = str[len - i - 1];
		if ('0' <= c && c <= '9') {
			uint8_t digit = c - '0';
			*value += digit * multiplier;
			multiplier *= 10;
		} else {
			print("Error: Bad character in decimal string: ");
			putchar(c);
			putchar('\n');
			return -1;
		}
	}

	return 0;
}
#endif

static int parse_hex(uint32_t * value, const char * str) {
	size_t start = 0;
	if (str[0] == '0' && (str[1] == 'x' || str[1] == 'X')) {
		start = 2;
	}

	size_t len = strlen(&str[start]);
	if (len > 8) {
		println("Error: Hex string too long.");
		return -1;
	}

	*value = 0;
	for (size_t i = start; i < len + start; i++) {
		uint32_t nybble = 0;
		if ('a' <= str[i] && str[i] <= 'f') {
			nybble = str[i] - 'a' + 0xa;
		} else if ('A' <= str[i] && str[i] <= 'F') {
			nybble = str[i] - 'A' + 0xa;
		} else if ('0' <= str[i] && str[i] <= '9') {
			nybble = str[i] - '0';
		} else {
			print("Error: Bad character in hex string: ");
			putchar(str[i]);
			putchar('\n');
			return -1;
		}

		*value |= nybble << (4 * (len + start - i - 1));
	}

	return 0;
}

static void print_dec(uint32_t value, size_t min_digits) {
	size_t digits = 0;
	for (uint32_t remaining = value; remaining != 0; remaining /= 10) {
		digits++;
	}
	if (value == 0) {
		digits = 1;
	}
	if (min_digits > 0 && min_digits > digits) {
		digits = min_digits;
	}
	for (size_t i = 0; i < digits; i++) {
		uint32_t digit = value;
		for (size_t d = 1; d < digits - i; d++) {
			digit /= 10;
		}
		uint8_t chr = (digit % 10) + '0';
		putchar(chr);
	}
}

static void print_hex(uint32_t value, size_t min_digits) {
	size_t digits = 0;
	for (uint32_t remaining = value; remaining != 0; remaining >>= 4) {
		digits++;
	}
	if (value == 0) {
		digits = 1;
	}
	if (min_digits > 0 && min_digits > digits) {
		digits = min_digits;
	}

	putchar('0');
	putchar('x');
	for (size_t i = 0; i < digits; i++) {
		uint8_t nybble = (value >> (4 * (digits - i - 1))) & 0xf;
		uint8_t chr = 0;
		if (nybble <= 9) {
			chr = nybble + '0';
		} else if (0xa <= nybble && nybble <= 0xf) {
			chr = nybble - 0xa + 'a';
		} else {
			chr = '?';
		}
		putchar(chr);
	}
}

static char const * const get_region_name_for_addr(uint32_t addr) {
	if (addr < 0x400000UL) {
		return "XDATA";
	} else if (addr < 0x600000UL) {
		return "IDATA";
	} else if (addr < 0x800000UL) {
		return "PDATA";
	} else if (addr < 0xC00000UL) {
		return "CODE";
	} else {
		return "SFR";
	}
}

static void print_addr_with_region(uint32_t addr) {
	print(get_region_name_for_addr(addr));
	print(" ");
	print_hex(addr & 0x1fffff, 6);
}

static int mrb_handler(size_t argc, const char * argv[]) {
	if (argc < 2) {
		println("Error: Too few arguments.");
		println("Usage: mrb address");
		println("Examples:");
		println("    mrb 0x00000000");
		println("    mrb 0x8");
		println("    mrb 00000");
		println("    mrb c");
		println("    mrb 00201000");
		println("    mrb 201000");
		return -1;
	}

	uint32_t ptr = 0;
	int ret = parse_hex(&ptr, argv[1]);
	if (ret != 0) {
		println("Error: parse_hex() failed.");
		return -1;
	}
	if (ptr > ADDR_MAX) {
		println("Error: Address too large.");
		return -1;
	}
	print_addr_with_region(ptr);
	print(": ");

	uint32_t value = readb(ptr);
	print_hex(value, 2);
	putchar('\n');

	return 0;
}

static int mrw_handler(size_t argc, const char * argv[]) {
	if (argc < 2) {
		println("Error: Too few arguments.");
		println("Usage: mrw address");
		println("Examples:");
		println("    mrw 0x00000000");
		println("    mrw 0x8");
		println("    mrw 00000");
		println("    mrw c");
		println("    mrw 00201000");
		println("    mrw 201000");
		return -1;
	}

	uint32_t ptr = 0;
	int ret = parse_hex(&ptr, argv[1]);
	if (ret != 0) {
		println("Error: parse_hex() failed.");
		return -1;
	}
	if (ptr > ADDR_MAX) {
		println("Error: Address too large.");
		return -1;
	}
	print_addr_with_region(ptr);
	print(": ");

	uint32_t value = readl(ptr);
	print_hex(value, 8);
	putchar('\n');

	return 0;
}

static int mw_common(const char * addr_str, const char * value_str, uint8_t size) {
	int ret = 0;
	uint32_t tmp;

	uint32_t max_value = 0;
	switch (size) {
	case 1:
		max_value = 0xFF;
		break;
	case 4:
		break;
	default:
		print("Error: invalid size passed to mw_common: ");
		print_dec(size, 1);
		putchar('\n');
		return -1;
	}

	uint8_t digits = size * 2;

	uint32_t ptr = 0;
	ret = parse_hex(&ptr, addr_str);
	if (ret != 0) {
		println("Error: parse_hex(addr_str) failed.");
		return -1;
	}
	if (ptr > ADDR_MAX) {
		println("Error: Address too large.");
		return -1;
	}
	print_addr_with_region(ptr);
	print(": ");
	switch (size) {
	case 1:
		tmp = readb(ptr);
		break;
	case 4:
		tmp = readl(ptr);
		break;
	default:
		tmp = 0xdeaddeadUL;
		break;
	}
	print_hex(tmp, digits);
	putchar('\n');

	uint32_t value = 0;
	ret = parse_hex(&value, value_str);
	if (ret != 0) {
		println("Error: parse_hex(value_str) failed.");
		return -1;
	}
	if (max_value != 0 && value > max_value) {
		println("Error: Value too large.");
		return -1;
	}
	switch (size) {
	case 1:
		writeb(ptr, value);
		break;
	case 4:
		writel(ptr, value);
		break;
	default:
		break;
	}

	print_addr_with_region(ptr);
	print(": ");
	switch (size) {
	case 1:
		tmp = readb(ptr);
		break;
	case 4:
		tmp = readl(ptr);
		break;
	default:
		tmp = 0xdeaddeadUL;
		break;
	}
	print_hex(tmp, digits);
	putchar('\n');

	return ret;
}

static int mwb_handler(size_t argc, const char * argv[]) {
	if (argc < 3) {
		println("Error: Too few arguments.");
		println("Usage: mwb address value");
		println("Examples:");
		println("    mwb 0x00200000 0");
		println("    mwb 0x100008 c0");
		println("    mwb 100000 0x08");
		println("    mwb 20100c 0x1");
		println("    mwb 00201000 0");
		return -1;
	}

	return mw_common(argv[1], argv[2], 1);
}

static int mww_handler(size_t argc, const char * argv[]) {
	if (argc < 3) {
		println("Error: Too few arguments.");
		println("Usage: mww address value");
		println("Examples:");
		println("    mww 0x00200000 0");
		println("    mww 0x100008 1234");
		println("    mww 100000 0x008");
		println("    mww 20100c 0x1");
		println("    mww 00201000 0");
		return -1;
	}

	return mw_common(argv[1], argv[2], 4);
}

static int reset_handler(size_t argc, const char * argv[]) {
	bool reload = false;

	if (argc > 1) {
		reload = true;
	}

	print("Resetting chip");
	if (reload) {
		print(" to mask ROM");
	}
	println("...");

	// Wait for the UART to finish printing.
	while (readb(UART_TFBF) < 15);

	// Delay hack because for some reason waiting
	// while(UART_TFBF < 16) returns instantly and so nothing gets
	// printed.
	const uint8_t delay_count = 200;
	for (uint8_t i = 0; i < delay_count; i++);

	// Delay twice as long when the clock is twice as fast.
	if (!(readb(CPU_MODE_CURRENT) & CPU_MODE_NEXT_CURRENT_CLOCK_DIV))
		for (uint8_t i = 0; i < delay_count; i++);

	if (reload) {
		// Boot from the mask ROM so it can reload our code from
		// flash.
		writeb(CPU_MODE_NEXT, readb(CPU_MODE_NEXT) & 0xfe);
	}

	// Trigger the reset.
	writeb(CPU_EXEC_CTRL, readb(CPU_EXEC_CTRL) | CPU_EXEC_CTRL_RESET);

	// Loop until the chip resets.
	while (1);

	return 0;
}

typedef enum bmo_commands {
	EXIT = '\r',
	READ = 'R',
	WRITE = 'W',
	SETBAUD = 'S',
	MEM_READ = 'r',
	MEM_WRITE = 'w',
} bmo_command_t;

static int bmo_handler(size_t argc, const char * argv[]) {
	int ret = 0;
	int done = 0;

	println("OK");
	while (!done) {
		uint32_t addr = 0;
		uint32_t len = 0;
		bmo_command_t command = getchar();
		switch (command) {
		case EXIT:
			done = 1;
			break;
		case READ:
			for (int i = 0; i < 4; i++) {
				((uint8_t *)&addr)[i] = getchar();
			}
			for (uint32_t off = 0; off < 4; off++) {
				putbyte(readb(addr + off));
			}
			break;
		case WRITE:
			for (int i = 0; i < 4; i++) {
				((uint8_t *)&addr)[i] = getchar();
			}
			for (uint32_t off = 0; off < 4; off++) {
				writeb(addr + off, getchar());
			}
			break;
		case MEM_READ:
			for (int i = 0; i < 4; i++) {
				((uint8_t *)&addr)[i] = getchar();
			}
			for (int i = 0; i < 4; i++) {
				((uint8_t *)&len)[i] = getchar();
			}
			for (uint32_t off = 0; off < len; off++) {
				putbyte(readb(addr + off));
			}
			break;
		case MEM_WRITE:
			for (int i = 0; i < 4; i++) {
				((uint8_t *)&addr)[i] = getchar();
			}
			for (int i = 0; i < 4; i++) {
				((uint8_t *)&len)[i] = getchar();
			}
			for (uint32_t off = 0; off < len; off++) {
				writeb(addr + off, getchar());
			}
			break;
		default:
			break;
		}
	}
	return ret;
}

static int version_handler(size_t argc, const char * argv[]) {
	print("Build version: ");
	println(build_version);
	print("Build time: ");
	println(build_time);
	print("Chip: ");
	print(chip_name);
	print(", version ");
	print_hex(readb(CHIP_VERSION_ADDR), 2);
	println("");
	print("CPU frequency: ");
	println(get_current_clock_speed(get_chip_type()));
	return 0;
}

static int help_handler(size_t argc, const char * argv[]);

typedef struct {
	char * command;
	int (* handler)(size_t, const char **);
} command;

static const command cmd_table[] = {
	{ "help", help_handler },
	{ "version", version_handler },
	{ "mrb", mrb_handler },
	{ "mrw", mrw_handler },
	{ "mwb", mwb_handler },
	{ "mww", mww_handler },
	{ "reset", reset_handler },
	{ "bmo", bmo_handler },
	{ 0, 0 },
};

static int help_handler(size_t argc, const char * argv[]) {
	println("Commands available:");
	for (size_t i = 0; cmd_table[i].command != 0; i++) {
		print(" - ");
		println(cmd_table[i].command);
	}
	return 0;
}

static int handle_command(size_t argc, const char * argv[]) {
	if (argc > 0) {
		for (size_t i = 0; cmd_table[i].command != 0; i++) {
			if (!strncmp(argv[0], cmd_table[i].command, MAX_CMD_LEN)) {
				return cmd_table[i].handler(argc, argv);
			}
		}
		print("Error: Unknown command: ");
		println(argv[0]);
	}

	return -1;
}

static int parse_cmdline(char * buf) {
	size_t argc = 0;
	const char * argv[MAX_ARGS] = { 0 };

	for (size_t i = 0; i < MAX_CMD_LEN + 1 && argc != MAX_ARGS; i++) {
		switch (buf[i]) {
		case 0:
		case ' ':
		case '\t':
			if (argv[argc] != 0) {
				buf[i] = 0;
				argc++;
			}
			break;
		default:
			if (argv[argc] == 0) {
				argv[argc] = &buf[i];
			}
			break;
		}
	}

	return handle_command(argc, argv);
}

static void cmdloop(void) {
	while (1) {
		print("> ");
		char cmd_buf[MAX_CMD_LEN + 1] = { 0 };
		size_t cmd_len = 0;
		int cmd_entered = 0;
		while (!cmd_entered) {
			char c = getchar();
			switch (c) {
			case 0x1b:
				// Escape sequences.
				c = getchar();
				switch (c) {
				case '[':
					c = getchar();
					switch (c) {
					case 'A':
					case 'B':
					case 'C':
					case 'D':
						// Arrow keys.
						break;
					case '1':
					case '2':
					case '3':
					case '4':
					case '5':
					case '6':
						// Paging.
						getchar();
						break;
					default:
						print("^[[");
						putchar(c);
					}
					break;
				case 'O':
					c = getchar();
					switch (c) {
					case 'F':
						// End key.
						break;
					default:
						print("^[O");
						putchar(c);
					}
					break;
				default:
					print("^[");
					putchar(c);
				}
				break;
			case '\r':
				// Newline.
				cmd_buf[cmd_len] = 0;
				cmd_entered = 1;
				break;
			case '\b':
				// Backspace.
				if (cmd_len > 0) {
					print("\b \b");
					cmd_buf[--cmd_len] = 0;
				}
				break;
			case 0x03:
				// Control-C
				memset(cmd_buf, 0, MAX_CMD_LEN + 1);
				cmd_entered = 1;
				break;
			default:
				if (cmd_len < MAX_CMD_LEN) {
					putchar(c);
					cmd_buf[cmd_len++] = c;
				}
			}
		}
		putchar('\n');
		parse_cmdline(cmd_buf);
	}
}

int main(void) {
	init();
	println("\nHello from monitor!");
	print("monitor version ");
	print(build_version);
	print(" (built on ");
	print(build_time);
	println(")");
	cmdloop();
	return 0;
}

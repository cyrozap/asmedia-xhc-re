#include <stddef.h>
#include <stdint.h>
#include <string.h>

static uint8_t volatile __xdata * const mem = 0x0000;
#define ADDR_MAX 0xFFFFUL

static uint16_t UART_BASE;
#define UART_RBR (UART_BASE + 0)
#define UART_THR (UART_BASE + 1)
#define UART_RSR (UART_BASE + 5)
#define UART_TSR (UART_BASE + 6)

#define MAX_CMD_LEN 80
#define MAX_ARGS 3

extern char const * const build_version;
extern char const * const build_time;

#define CHIP_ID 0x1242

static char const * chip_name;

static uint8_t readb(uint16_t reg) {
	return *(uint8_t *)(mem + reg);
}

#if 0
static uint16_t readw(uint16_t reg) {
	return *(uint16_t *)(mem + reg);
}
#endif

static uint32_t readl(uint16_t reg) {
	return *(uint32_t *)(mem + reg);
}

static void writeb(uint16_t reg, uint8_t value) {
	*(uint8_t *)(mem + reg) = value;
}

#if 0
static void writew(uint16_t reg, uint16_t value) {
	*(uint16_t *)(mem + reg) = value;
}
#endif

static void writel(uint16_t reg, uint32_t value) {
	*(uint32_t *)(mem + reg) = value;
}

static char getchar(void) {
	char ret;

	// Wait for the UART to assert the "data ready" flag.
	while (readb(UART_RSR) < 1);

	ret = readb(UART_RBR);

	return ret;
}

static void putchar(char c) {
	// Wait for the UART to become ready.
	while (readb(UART_TSR) < 8);

	if (c == '\n')
		putchar('\r');

	writeb(UART_THR, c);
}

static void putbyte(uint8_t b) {
	// Wait for the UART to become ready.
	while (readb(UART_TSR) < 8);

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

static void init(void) {
	switch(CHIP_ID) {
#if 0
	case 0x1042:
		chip_name = "ASM1042";
		break;
	case 0x1142:
		chip_name = "ASM1042A";
		break;
#endif
	case 0x1242:
		chip_name = "ASM1142";
		UART_BASE = 0xF100;
		break;
#if 0
	case 0x2142:
		chip_name = "ASM2142";
		break;
	default:
		chip_name = "UNKNOWN";
		break;
#endif
	}
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

#if 0
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
#endif

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
	print_hex(ptr, 8);
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
	print_hex(ptr, 8);
	print(": ");

	uint32_t value = readl(ptr);
	print_hex(value, 8);
	putchar('\n');

	return 0;
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

	int ret = 0;

	uint32_t ptr = 0;
	ret = parse_hex(&ptr, argv[1]);
	if (ret != 0) {
		println("Error: parse_hex(argv[1]) failed.");
		return -1;
	}
	if (ptr > ADDR_MAX) {
		println("Error: Address too large.");
		return -1;
	}
	print_hex(ptr, 8);
	print(": ");
	print_hex(readb(ptr), 2);
	putchar('\n');

	uint32_t value = 0;
	ret = parse_hex(&value, argv[2]);
	if (ret != 0) {
		println("Error: parse_hex(argv[2]) failed.");
		return -1;
	}
	if (value > 0xFF) {
		println("Error: Value too large.");
		return -1;
	}
	writeb(ptr, value);

	print_hex(ptr, 8);
	print(": ");
	print_hex(readb(ptr), 2);
	putchar('\n');

	return ret;
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

	int ret = 0;

	uint32_t ptr = 0;
	ret = parse_hex(&ptr, argv[1]);
	if (ret != 0) {
		println("Error: parse_hex(argv[1]) failed.");
		return -1;
	}
	if (ptr > ADDR_MAX) {
		println("Error: Address too large.");
		return -1;
	}
	print_hex(ptr, 8);
	print(": ");
	print_hex(readl(ptr), 8);
	putchar('\n');

	uint32_t value = 0;
	ret = parse_hex(&value, argv[2]);
	if (ret != 0) {
		println("Error: parse_hex(argv[2]) failed.");
		return -1;
	}
	writel(ptr, value);

	print_hex(ptr, 8);
	print(": ");
	print_hex(readl(ptr), 8);
	putchar('\n');

	return ret;
}

static int reset_handler(size_t argc, const char * argv[]) {
	println("Resetting chip...");

	// Wait for the UART to finish printing.
	while (readb(UART_TSR) < 15);

	// Delay hack because for some reason waiting while(UART_TSR < 16)
	// returns instantly and so nothing gets printed.
	for (uint8_t i = 0; i < 200; i++);

	uint8_t tmp = readb(0xf342);
	writeb(0xf342, tmp | 1);

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
		uint32_t val = 0;
		uint32_t len = 0;
		bmo_command_t command = getchar();
		switch (command) {
		case EXIT:
			done = 1;
			break;
		case READ:
			for (int i = 0; i < 4; i++) {
				addr |= getchar() << (i * 8);
			}
			val = readl(addr);
			for (int i = 0; i < 4; i++) {
				putbyte((val >> (i * 8)) & 0xff);
			}
			break;
		case WRITE:
			for (int i = 0; i < 4; i++) {
				addr |= getchar() << (i * 8);
			}
			for (int i = 0; i < 4; i++) {
				val |= getchar() << (i * 8);
			}
			writel(addr, val);
			break;
		case MEM_READ:
			for (int i = 0; i < 4; i++) {
				addr |= getchar() << (i * 8);
			}
			for (int i = 0; i < 4; i++) {
				len |= getchar() << (i * 8);
			}
			for (uint32_t off = 0; off < len; off += 4) {
				val = readl(addr + off);
				for (int i = 0; i < 4; i++) {
					putbyte((val >> (i * 8)) & 0xff);
				}
			}
			break;
		case MEM_WRITE:
			for (int i = 0; i < 4; i++) {
				addr |= getchar() << (i * 8);
			}
			for (int i = 0; i < 4; i++) {
				len |= getchar() << (i * 8);
			}
			for (uint32_t off = 0; off < len; off += 4) {
				val = 0;
				for (int i = 0; i < 4; i++) {
					val |= getchar() << (i * 8);
				}
				writel(addr + off, val);
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
	print("Chip name: ");
	println(chip_name);
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

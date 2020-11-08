	.globl __sdcc_gsinit_startup

	.area VECTOR	(ABS,CODE)
	.org	0x0000
__interrupt_vect:
	ljmp	__sdcc_gsinit_startup
	.ds	0x8f
	sjmp	. - 3

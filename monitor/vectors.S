	.globl __sdcc_gsinit_startup
	.globl _isr_eint0
	.globl _isr_eint1

	.area VECTOR	(ABS,CODE)
	.org	0x0000
__interrupt_vect:
	ljmp	__sdcc_gsinit_startup
	ljmp	_isr_eint0
	.ds	0x13 - (0x3 + 3)
	ljmp	_isr_eint1
	.ds	0x8F - (0x13 + 3)
loop_forever:
	nop
	nop
	nop
	sjmp	loop_forever

; SPDX-License-Identifier: GPL-3.0-or-later

; Copyright (C) 2020  Forest Crossman <cyrozap@gmail.com>
;
; This program is free software: you can redistribute it and/or modify
; it under the terms of the GNU General Public License as published by
; the Free Software Foundation, either version 3 of the License, or
; (at your option) any later version.
;
; This program is distributed in the hope that it will be useful,
; but WITHOUT ANY WARRANTY; without even the implied warranty of
; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
; GNU General Public License for more details.
;
; You should have received a copy of the GNU General Public License
; along with this program.  If not, see <https://www.gnu.org/licenses/>.


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

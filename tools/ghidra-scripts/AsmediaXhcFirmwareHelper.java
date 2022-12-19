// Script that analyzes ASMedia xHC firmware.
// @author cyrozap
// @category ASMedia.xHC

// SPDX-License-Identifier: GPL-3.0-or-later

// Copyright (C) 2022  Forest Crossman <cyrozap@gmail.com>
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

import java.util.*;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.*;
import ghidra.program.model.lang.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.scalar.*;
import ghidra.program.model.symbol.*;
import ghidra.util.bytesearch.*;
import ghidra.util.exception.*;
import ghidra.util.task.*;

public class AsmediaXhcFirmwareHelper extends GhidraScript {
	private Register DPTR;
	private Register DPL;
	private Register DPH;
	private Register R1;
	private Register R2;
	private Register R3;
	private Register R4;
	private Register R5;
	private Register R6;
	private Register R7;
	private Address DPL_addr;
	private Address DPH_addr;
	private Address DPX_addr;

	private boolean isCfReferenceToInstruction(Reference instRef, Instruction inst) {
		return instRef.isPrimary() &&
			instRef.getToAddress() == inst.getAddress() &&
			(instRef.getReferenceType() == FlowType.UNCONDITIONAL_CALL ||
			 instRef.getReferenceType() == FlowType.UNCONDITIONAL_JUMP ||
			 instRef.getReferenceType() == FlowType.CONDITIONAL_JUMP);
	}

	private void createStringXrefsForPrintFunctionInner(Instruction startInstruction) {
		// Working backwards, find explicit assignments to the pointer variables.
		Instruction inst = startInstruction;
		Instruction prevInst = inst.getPrevious();
		boolean r2Found = false;
		boolean r3Found = false;
		Address r3Address = null;
		int newRefAddrInt = 0;

		for (int i = 0; i < 10 && !(r2Found && r3Found); i++) {
			// Check if this instruction is the target of a branch, then perform the analysis following the branch.
			Reference[] instRefs = getReferencesTo(inst.getAddress());
			for (Reference instRef : instRefs) {
				if (!isCfReferenceToInstruction(instRef, inst)) {
					continue;
				}

				Address refAddr = instRef.getFromAddress();
				Instruction branchInst = getInstructionAt(refAddr);

				//printf("Found branch to %s at %s, following...\n", inst.getAddress(), refAddr);
				createStringXrefsForPrintFunctionInner(branchInst);
			}

			inst = prevInst;
			prevInst = inst.getPrevious();

			String mnemonic = inst.getMnemonicString();
			if (mnemonic.equals("LCALL") ||
					mnemonic.startsWith("AJ") ||
					mnemonic.startsWith("CJ") ||
					mnemonic.startsWith("DJ") ||
					mnemonic.startsWith("J") ||
					mnemonic.startsWith("LJ") ||
					mnemonic.startsWith("SJ") ||
					mnemonic.startsWith("RET")) {
				break;
			}

			if (!mnemonic.equals("MOV")) {
				continue;
			}

			Object[] resultObjects = inst.getResultObjects();
			if (resultObjects.length < 1) {
				continue;
			}

			Object[] inputObjects = inst.getInputObjects();
			if (inputObjects.length < 1) {
				continue;
			}

			Object dst = resultObjects[0];
			Object src = inputObjects[0];
			if (!(dst instanceof Register && src instanceof Scalar)) {
				continue;
			}

			Register reg = (Register)dst;
			Scalar value = (Scalar)src;

			//printf("Register %s: 0x%02x\n", reg, value.getUnsignedValue());

			if (reg == R2) {
				newRefAddrInt |= value.getUnsignedValue() & 0xff;
				r2Found = true;
			}
			if (reg == R3) {
				newRefAddrInt |= (value.getUnsignedValue() & 0xff) << 8;
				r3Found = true;
				r3Address = inst.getAddress();
			}
		}

		if (!(r2Found && r3Found)) {
			return;
		}

		Address newRefAddr = toAddr(String.format("CODE:%04x", newRefAddrInt));

		currentProgram.getReferenceManager().addMemoryReference(r3Address, newRefAddr, RefType.DATA, SourceType.USER_DEFINED, 1);

		printf(getScriptName() + "> Added reference from %s to %s.\n", r3Address, newRefAddr);
	}

	private Address findAddressByBytesMaskAndOffset(byte[] bytes, byte[] mask, int offset) throws CancelledException {
		List<Address> results = new ArrayList<Address>();
		GenericMatchAction<Address> action = new GenericMatchAction<Address>(null) {
			@Override
			public void apply(Program prog, Address addr, Match match) {
				results.add(addr);
			}
		};
		GenericByteSequencePattern pattern = new GenericByteSequencePattern(bytes, mask, action);
		MemoryBytePatternSearcher searcher = new MemoryBytePatternSearcher("findAddressByBytesMaskAndOffset",
				new ArrayList<Pattern>(Arrays.asList(pattern)));
		searcher.setSearchExecutableOnly(true);
		searcher.search(currentProgram, currentProgram.getMemory(), new TaskDialog("findAddressByBytesMaskAndOffset", true, false, true));

		if (results.size() < 1) {
			return null;
		}

		return results.get(0).add(offset);
	}

	private void createStringXrefsForPrintFunction() throws CancelledException {
		// Get the function address.
		Address functionAddr = null;
		while (true) {
			Function function = getFunction("asm_print_log");
			if (function != null) {
				functionAddr = function.getEntryPoint();
				if (functionAddr != null) {
					printf(getScriptName() + "> Found print function by name: %s\n", functionAddr);
					break;
				}
			}

			functionAddr = findAddressByBytesMaskAndOffset(
				new byte[] { (byte)0xe5, (byte)0x18, (byte)0x54, (byte)0x04, (byte)0x70, (byte)0x21 },
				new byte[] { (byte)0xff, (byte)0xff, (byte)0xff, (byte)0xff, (byte)0xff, (byte)0xff },
				-13);
			if (functionAddr != null) {
				printf(getScriptName() + "> Found print function by bytes (64K): %s\n", functionAddr);
				break;
			}

			functionAddr = findAddressByBytesMaskAndOffset(
				new byte[] { (byte)0xea, (byte)0xfe, (byte)0xeb, (byte)0xff, (byte)0x80, (byte)0x0f },
				new byte[] { (byte)0xff, (byte)0xff, (byte)0xff, (byte)0xff, (byte)0xff, (byte)0xff },
				-5);
			if (functionAddr != null) {
				printf(getScriptName() + "> Found print function by bytes (128K): %s\n", functionAddr);
				break;
			}

			break;
		}

		if (functionAddr == null) {
			printf(getScriptName() + "> Failed to find \"asm_print_log\" function! Try defining it manually.\n");
			return;
		}

		// Loop over all the locations where the function is called.
		Reference[] calls = getReferencesTo(functionAddr);
		for (Reference call : calls) {
			Address callSite = call.getFromAddress();
			Instruction inst = getInstructionAt(callSite);

			createStringXrefsForPrintFunctionInner(inst);
		}
	}

	private void createDataXrefsForFunctionInner(String region, Instruction startInstruction) {
		// Working backwards, find explicit assignments to the pointer variables.
		Instruction inst = startInstruction;
		Instruction prevInst = inst.getPrevious();
		boolean dptrFound = false;
		Address dptrAddress = null;
		long newRefAddrInt = 0;

		for (int i = 0; i < 10 && !dptrFound; i++) {
			// Check if this instruction is the target of a branch, then perform the analysis following the branch.
			Reference[] instRefs = getReferencesTo(inst.getAddress());
			for (Reference instRef : instRefs) {
				if (!isCfReferenceToInstruction(instRef, inst)) {
					continue;
				}

				Address refAddr = instRef.getFromAddress();
				Instruction branchInst = getInstructionAt(refAddr);

				//printf("Found branch to %s at %s, following...\n", inst.getAddress(), refAddr);
				createDataXrefsForFunctionInner(region, branchInst);
			}

			inst = prevInst;
			prevInst = inst.getPrevious();

			String mnemonic = inst.getMnemonicString();
			if (mnemonic.equals("LCALL") ||
					mnemonic.startsWith("AJ") ||
					mnemonic.startsWith("CJ") ||
					mnemonic.startsWith("DJ") ||
					mnemonic.startsWith("J") ||
					mnemonic.startsWith("LJ") ||
					mnemonic.startsWith("SJ") ||
					mnemonic.startsWith("RET")) {
				break;
			}

			if (!mnemonic.equals("MOV")) {
				continue;
			}

			Object[] resultObjects = inst.getResultObjects();
			if (resultObjects.length < 1) {
				continue;
			}

			Object[] inputObjects = inst.getInputObjects();
			if (inputObjects.length < 1) {
				continue;
			}

			Object dst = resultObjects[0];
			Object src = inputObjects[0];

			if ((dst instanceof Address &&
					((Address)dst == DPL_addr || (Address)dst == DPH_addr)) ||
					dst instanceof Register &&
					((Register)dst == DPL || (Register)dst == DPH)) {
				break;
			}

			if (!(dst instanceof Register && src instanceof Scalar)) {
				continue;
			}

			Register reg = (Register)dst;
			Scalar value = (Scalar)src;

			//printf("Register %s: 0x%04x\n", reg, value.getUnsignedValue());

			if (reg == DPTR) {
				newRefAddrInt = value.getUnsignedValue() & 0xffff;
				dptrAddress = inst.getAddress();
				dptrFound = true;
			}
		}

		if (!dptrFound) {
			return;
		}

		Address newRefAddr = toAddr(String.format("%s:%04x", region, newRefAddrInt));

		currentProgram.getReferenceManager().addMemoryReference(dptrAddress, newRefAddr, RefType.DATA, SourceType.USER_DEFINED, 1);

		printf(getScriptName() + "> Added reference from %s to %s.\n", dptrAddress, newRefAddr);
	}

	private void createDataXrefsForFunction(String substring, String region) {
		// Search through the symbol table for functions containing the substring.
		for (Symbol sym : currentProgram.getSymbolTable().getSymbolIterator(substring, true)) {
			Address functionAddr = sym.getAddress();

			// Loop over all the locations where the function is called.
			Reference[] calls = getReferencesTo(functionAddr);
			for (Reference call : calls) {
				Address callSite = call.getFromAddress();
				Instruction inst = getInstructionAt(callSite);

				createDataXrefsForFunctionInner(region, inst);
			}
		}
	}

	public void run() throws Exception {
		// Get the registers we care about.
		DPTR = currentProgram.getRegister("DPTR");
		DPL = currentProgram.getRegister("DPL");
		DPH = currentProgram.getRegister("DPH");
		R1 = currentProgram.getRegister("R1");
		R2 = currentProgram.getRegister("R2");
		R3 = currentProgram.getRegister("R3");
		R4 = currentProgram.getRegister("R4");
		R5 = currentProgram.getRegister("R5");
		R6 = currentProgram.getRegister("R6");
		R7 = currentProgram.getRegister("R7");

		// Get the addresses of the SFRs.
		DPL_addr = toAddr("SFR:82");
		DPH_addr = toAddr("SFR:83");
		DPX_addr = toAddr("SFR:93");

		createStringXrefsForPrintFunction();

		createDataXrefsForFunction("*from_pmem*", "CODE");
		createDataXrefsForFunction("*with_pmem*", "CODE");
		createDataXrefsForFunction("*check_equal_u32_iram_pmem", "CODE");
		createDataXrefsForFunction("*from_xram*", "EXTMEM");
		createDataXrefsForFunction("*to_xram_from_iram*", "EXTMEM");
		createDataXrefsForFunction("*to_xram_with_iram*", "EXTMEM");
	}
}

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

# test_make_image.py - Tests for the firmware image generator.
# Copyright (C) 2026  Forest Crossman <cyrozap@gmail.com>
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

"""Characterization tests for tools/make_image.py.

The files in fixtures/ are the expected output of the generator for the
deterministic firmware payload defined by PAYLOAD. They pin the on-disk format
so that refactoring the generator cannot silently change the images.

To regenerate the fixtures after an intentional format change, run:

    REGEN_FIXTURES=1 python3 -m unittest discover -s tools/tests

The raw firmware image embeds the build timestamp at RAW_VERSION_OFFSET, so
that field is overwritten with FIXED_TIMESTAMP before comparing or storing a
fixture. Otherwise the fixtures would change on every run.
"""

import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from zlib import crc32


TOOLS_DIR = pathlib.Path(__file__).resolve().parents[1]
FIXTURES_DIR = pathlib.Path(__file__).resolve().parent / "fixtures"
SCRIPT = TOOLS_DIR / "make_image.py"

sys.path.insert(0, str(TOOLS_DIR))

try:
    import asm_fw
except ModuleNotFoundError:
    asm_fw = None


REGEN = "REGEN_FIXTURES" in os.environ

CHIPS = ("ASM1042", "ASM1042A", "ASM1142", "ASM2142", "ASM3242")

# Chip names are mapped to (header magic, body magic).
EXPECTED_MAGICS = {
    "ASM1042": ("U2104_RCFG", "U2104_FW"),
    "ASM1042A": ("2104B_RCFG", "2104B_FW"),
    "ASM1142": ("2114A_RCFG", "2114A_FW"),
    "ASM2142": ("2214A_RCFG", "2214A_FW"),
    "ASM3242": ("2324A_RCFG", "2324A_FW"),
}

PAYLOAD = bytes(range(256)) * 4

RAW_VERSION_OFFSET = 0x80
RAW_VERSION_LEN = 6
FIXED_TIMESTAMP = bytes.fromhex("260102030405")


def checksum8(data: bytes) -> int:
    return sum(data) & 0xff

def run_generator_process(data: bytes, args: list[str]) -> tuple[subprocess.CompletedProcess, bytes | None]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = pathlib.Path(tmp)
        input_path = tmp_dir / "input.bin"
        output_path = tmp_dir / "output.bin"

        input_path.write_bytes(data)
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), *args, "-o", str(output_path), str(input_path)],
            capture_output=True,
        )
        output = output_path.read_bytes() if proc.returncode == 0 else None

        return proc, output

def run_generator(data: bytes, args: list[str]) -> bytes:
    proc, output = run_generator_process(data, args)
    if proc.returncode != 0:
        raise RuntimeError("make_image.py failed: {}".format(proc.stderr.decode(errors="replace")))
    assert output is not None
    return output

def run_generator_error(data: bytes, args: list[str]) -> str:
    proc, _ = run_generator_process(data, args)
    if proc.returncode == 0:
        raise AssertionError("make_image.py unexpectedly succeeded")
    return proc.stderr.decode(errors="replace")

def normalize_timestamp(data: bytes) -> bytes:
    data = bytearray(data)
    data[RAW_VERSION_OFFSET:RAW_VERSION_OFFSET + RAW_VERSION_LEN] = FIXED_TIMESTAMP
    return bytes(data)

def generate_raw(chip: str) -> bytes:
    return normalize_timestamp(run_generator(PAYLOAD, ["-t", "bin", "-c", chip]))

def generate_image(chip: str, firmware: bytes, sig_bypass: bool = False) -> bytes:
    args = ["-t", "image", "-c", chip]
    if sig_bypass:
        args.append("-s")
    return run_generator(firmware, args)

def raw_fixture_name(chip: str) -> str:
    return "raw_{}.bin".format(chip.lower())

def image_fixture_name(chip: str, sig_bypass: bool = False) -> str:
    suffix = "_sigbypass" if sig_bypass else ""
    return "image_{}{}.img".format(chip.lower(), suffix)


class FixtureTest(unittest.TestCase):
    def check_fixture(self, name: str, actual: bytes) -> None:
        path = FIXTURES_DIR / name
        if REGEN:
            FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
            path.write_bytes(actual)
            return

        self.assertTrue(path.exists(), "Missing fixture: {} (run with REGEN_FIXTURES=1 to create it)".format(path))
        self.assertEqual(path.read_bytes(), actual, "Fixture is out of date: {} (run with REGEN_FIXTURES=1 to update it)".format(path))

    def test_raw_fixtures(self) -> None:
        for chip in CHIPS:
            with self.subTest(chip=chip):
                self.check_fixture(raw_fixture_name(chip), generate_raw(chip))

    def test_image_fixtures(self) -> None:
        for chip in CHIPS:
            with self.subTest(chip=chip):
                image = generate_image(chip, generate_raw(chip))
                self.check_fixture(image_fixture_name(chip), image)

    def test_sig_bypass_fixture(self) -> None:
        image = generate_image("ASM3242", generate_raw("ASM3242"), sig_bypass=True)
        self.check_fixture(image_fixture_name("ASM3242", sig_bypass=True), image)


@unittest.skipIf(asm_fw is None, "tools/asm_fw.py has not been generated (run \"make\" at the repository root)")
class GeneratedImageFormatTest(unittest.TestCase):
    def test_header_and_body(self) -> None:
        for chip in CHIPS:
            with self.subTest(chip=chip):
                firmware = generate_raw(chip)
                image = generate_image(chip, firmware)
                fw = asm_fw.AsmFw.from_bytes(image)

                header_magic, body_magic = EXPECTED_MAGICS[chip]
                self.assertEqual(fw.header.magic, header_magic)
                self.assertEqual(fw.body.magic, body_magic)

                header_bytes = image[:fw.header.len]
                self.assertEqual(checksum8(header_bytes), fw.header.checksum)
                self.assertEqual(crc32(header_bytes), fw.header.crc32)

                self.assertEqual(fw.body.firmware.code, firmware)
                self.assertEqual(checksum8(fw.body.firmware.code), fw.body.checksum)
                self.assertEqual(crc32(fw.body.firmware.code), fw.body.crc32)

    def test_sig_bypass_layout(self) -> None:
        firmware = generate_raw("ASM3242")
        image = generate_image("ASM3242", firmware, sig_bypass=True)
        fw = asm_fw.AsmFw.from_bytes(image)

        # The loader program pads the header out to a fixed size, and loads the
        # firmware from the flash address immediately following the header, its
        # checksum and crc32, and the body length field.
        self.assertEqual(fw.header.len, 0x400)
        expected_flash_addr = fw.header.len + 5 + 4

        writes = {
            config_word.info.addr: config_word.info.value
            for config_word in fw.header.data.config_words
            if config_word.type == 0xcc
        }
        flash_addr = writes[0x506b] | (writes[0x506d] << 16)
        self.assertEqual(flash_addr, expected_flash_addr)


class ValidationTest(unittest.TestCase):
    def assert_rejected(self, data: bytes, args: list[str], expected: str) -> None:
        stderr = run_generator_error(data, args)
        self.assertIn(expected, stderr)
        self.assertNotIn("Traceback", stderr)

    def test_empty_image(self) -> None:
        self.assert_rejected(b"", ["-t", "image", "-c", "ASM1142"], "is empty")

    def test_body_length_limit(self) -> None:
        max_len = (1 << 16) - 1
        for chip in ("ASM1042", "ASM1042A", "ASM1142"):
            with self.subTest(chip=chip):
                run_generator(bytes(max_len), ["-t", "image", "-c", chip])
                self.assert_rejected(bytes(max_len + 1), ["-t", "image", "-c", chip], "too large")

    def test_body_length_accepts_64k_with_u4(self) -> None:
        run_generator(bytes(1 << 16), ["-t", "image", "-c", "ASM2142"])

    def test_raw_minimum_length(self) -> None:
        required_len = 0x87 + 8
        run_generator(bytes(required_len), ["-t", "bin", "-c", "ASM1142"])
        self.assert_rejected(bytes(required_len - 1), ["-t", "bin", "-c", "ASM1142"], "too small")

    def test_sig_bypass_firmware_limit(self) -> None:
        args = ["-t", "image", "-c", "ASM3242", "-s"]
        run_generator(bytes(0x8000), args)
        self.assert_rejected(bytes(0x8001), args, "too large for the signature check bypass")


if __name__ == "__main__":
    unittest.main()

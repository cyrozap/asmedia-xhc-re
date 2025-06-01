#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

# extract_promontory_fw.py - A tool to extract Promontory firmware images from other files.
# Copyright (C) 2025  Forest Crossman <cyrozap@gmail.com>
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


import argparse
import struct
import sys


def checksum32(data: bytes) -> int:
    return sum(data) & 0xffffffff

def find_and_extract_embedded_files(data: bytes, input_file: str, ignore_checksum: bool) -> int:
    count: int = 0
    offset: int = 0
    while offset < len(data):
        pos: int = data.find(b"_PT_", offset)
        if pos == -1:
            break

        # Check if the full header (4B magic, 4B len, 4B checksum) can be read
        if pos + 12 > len(data):
            offset = pos + 1
            continue

        # Skip if the length is less than the minimum
        length_value: int = struct.unpack_from("<I", data, pos + 4)[0]
        if length_value < 12:
            offset = pos + 1
            continue

        # Skip if the file is larger than the available data
        if pos + length_value > len(data):
            offset = pos + 1
            continue

        fw_image: bytes = data[pos : pos + length_value]

        # Only extract if the checksum matches or we're ignoring the checksum
        valid: bool = ignore_checksum
        if not valid:
            stored_checksum: int = struct.unpack_from("<I", data, pos + 8)[0]
            calculated_checksum: int = checksum32(fw_image[12 : length_value & 0xFFFFFF00])
            valid = (calculated_checksum == stored_checksum)

        if valid:
            filename: str = f"{input_file}.{count}.bin"
            with open(filename, "wb") as f:
                f.write(fw_image)
            count += 1

        offset = pos + length_value

    return count

def main() -> int:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("-i", "--ignore-checksum", action="store_true",
                        help="Ignore the Promontory firmware image checksum, and extract it even if it doesn't match.")
    parser.add_argument("input_file", help="Input binary file to search for embedded files")
    args: argparse.Namespace = parser.parse_args()

    try:
        with open(args.input_file, "rb") as f:
            data: bytes = f.read()
    except FileNotFoundError:
        print(f"Error: Could not open input file '{args.input_file}'.", file=sys.stderr)
        return 1

    files_extracted: int = find_and_extract_embedded_files(data, args.input_file, args.ignore_checksum)

    if files_extracted > 0:
        images: str = "image" if files_extracted == 1 else "images"
        print(f"Successfully extracted {files_extracted} Promontory firmware {images} from '{args.input_file}'.")
        return 0
    else:
        print(f"No Promontory firmware images were found in '{args.input_file}'.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3

import argparse
import sys
import xml.etree.ElementTree as ET

import yaml


REGION_NAMES = {
    "pci": "PCI Configuration",
    "sfr": "SFR",
    "xdata": "XDATA",
}

def validate(doc):
    unknown_keys = set(doc.keys()).difference(set(['meta', 'xdata', 'registers']))
    if unknown_keys:
        print("Error: Invalid keys in document: {}".format(unknown_keys))
        return False

    xdata = doc.get('xdata', list())
    if type(xdata) is not list:
        print("Error: \"xdata\" is not a list.")
        return False

    for i, region in enumerate(xdata):
        unknown_keys = set(region.keys()).difference(set(['name', 'start', 'end', 'permissions', 'notes']))
        if unknown_keys:
            print("Error: Invalid keys in xdata[{}]: {}".format(i, unknown_keys))
            return False

    registers = doc.get('registers', dict())
    if type(registers) is not dict:
        print("Error: \"registers\" is not a dict.")
        return False

    for region in REGION_NAMES.keys():
        region_registers = registers.get(region, list())
        if type(region_registers) is not list:
            print("Error: Register region \"{}\" is not a list.".format(region))
            return False

        for i, register in enumerate(region_registers):
            unknown_keys = set(register.keys()).difference(set(['name', 'start', 'end', 'permissions', 'bits', 'notes']))
            if unknown_keys:
                print("Error: Invalid keys in registers.{}[{}]: {}".format(region, i, unknown_keys))
                return False

            bits = register.get('bits', list())
            if type(bits) is not list:
                print("Error: Register {}.{}.bits is not a list.".format(region, i))
                return False

            for b, bit_range in enumerate(bits):
                unknown_keys = set(bit_range.keys()).difference(set(['name', 'start', 'end', 'permissions', 'notes']))
                if unknown_keys:
                    print("Error: Invalid keys in registers.{}[{}].bits[{}]: {}".format(region, i, b, unknown_keys))
                    return False

    return True

def gen_css():
    style = '''
    span.monospace {
        font-family: monospace;
        background-color: #dedede;
        padding-left: 5px;
        padding-right: 5px;
        padding-top: 2px;
        padding-bottom: 2px;
        border-radius: 3px;
    }
    table, th, td {
        border: 1px solid black;
    }
    td.bitfield {
        text-align: center;
    }
    td.bitfield-unused {
        background-color: #c0c0c0;
    }
    '''
    return style

def markdown_lite(parent, tag, md):
    parts = " ".join(md.strip('\n').split('\n')).split('`')
    for i, part in enumerate(parts):
        if i % 2 == 1:
            span = ET.Element('span', {'class': 'monospace'})
            span.text = part
            parts[i] = ET.tostring(span, encoding='utf-8', xml_declaration=False).decode('utf-8')
    parent.append(ET.fromstring("<{}>{}</{}>".format(tag, "".join(parts), tag)))

def gen_xhtml(doc):
    html = ET.Element('html', {
        'xmlns': "http://www.w3.org/1999/xhtml",
        'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance",
        'xsi:schemaLocation': "http://www.w3.org/MarkUp/SCHEMA/xhtml11.xsd",
        'xml:lang': "en",
    })
    head = ET.SubElement(html, 'head')
    body = ET.SubElement(html, 'body')

    meta = doc.get('meta', dict())
    chip = meta.get('chip', "UNKNOWN")

    title = ET.SubElement(head, 'title')
    title.text = "{} Memory Map and Register Manual".format(chip)

    style = ET.SubElement(head, 'style')
    style.text = gen_css()

    heading = ET.SubElement(body, 'h1')
    heading.text = title.text

    ET.SubElement(body, 'h2').text = "XDATA Memory Map"
    xdata_memory_map = ET.SubElement(body, 'table')
    xdata_memory_map_header = ET.SubElement(xdata_memory_map, 'tr')
    for header in ["Start", "End", "Size", "Name", "Permissions", "Notes"]:
        ET.SubElement(xdata_memory_map_header, 'th').text = header

    xdata = doc.get('xdata', list())
    for region in xdata:
        tr = ET.SubElement(xdata_memory_map, 'tr')
        start = region.get('start')
        start_text = ""
        if start is not None:
            start_text = "0x{:04X}".format(start)
        ET.SubElement(tr, 'td').text = start_text
        end = region.get('end')
        end_text = ""
        if end is not None:
            end_text = "0x{:04X}".format(end)
        ET.SubElement(tr, 'td').text = end_text
        size_text = ""
        if start is not None and end is not None:
            size_text = "0x{:04X}".format(end + 1 - start)
        ET.SubElement(tr, 'td').text = size_text
        ET.SubElement(tr, 'td').text = region.get('name', "")
        ET.SubElement(tr, 'td').text = region.get('permissions', "")
        markdown_lite(tr, 'td', region.get('notes', ""))

    ET.SubElement(body, 'h2').text = "Register Map"
    register_regions = doc.get('registers', dict())
    for region_name, region_registers in register_regions.items():
        ET.SubElement(body, 'hr')
        ET.SubElement(body, 'h3').text = "{} Region Registers".format(REGION_NAMES[region_name])
        for register in region_registers:
            ET.SubElement(body, 'hr')
            reg_name = register.get('name', "")
            addr_format = "0x{:04X}"
            if region_name in ("pci", "sfr"):
                addr_format = "0x{:02X}"
            start = register.get('start')
            addr_string = ""
            if start is not None:
                addr_string = addr_format.format(start)
            ET.SubElement(body, 'h4').text = "{}: {}".format(addr_string, reg_name)
            end = register.get('end')
            size = 0
            if start is not None and end is not None:
                size = end + 1 - start
            max_bits = size * 8
            ET.SubElement(body, 'p').text = "Size: {} byte{}".format(size, "s" if size > 1 else "")
            markdown_lite(body, 'p', register.get('notes', ""))
            if max_bits > 64:
                continue
            bit_table = ET.SubElement(body, 'table')
            bits = register.get('bits')
            if bits is None:
                bits = [{
                    'name': reg_name,
                    'start': 0,
                    'end': max_bits - 1,
                    'permissions': register.get('permissions', ""),
                }]
            unused_bits = set(range(max_bits))
            bit_spans = dict()
            for bit_range in bits:
                bit_start = bit_range.get('start')
                bit_end = bit_range.get('end')
                if bit_start is None or bit_end is None:
                    continue
                unused_bits = unused_bits.difference(set(range(bit_start, bit_end + 1)))
                bit_len = bit_end + 1 - bit_start
                start_bit_block = bit_start // 16
                end_bit_block = bit_end // 16
                if end_bit_block > start_bit_block:
                    for block in range(start_bit_block, end_bit_block + 1):
                        if block == end_bit_block:
                            upper_len = bit_end + 1 - block*16
                            bit_spans[bit_end] = {
                                'name': bit_range.get('name', ""),
                                'permissions': bit_range.get('permissions', ""),
                                'span': upper_len,
                            }
                        elif block == start_bit_block:
                            lower_len = block*16+16 - bit_start
                            bit_spans[block*16+16-1] = {
                                'name': bit_range.get('name', ""),
                                'permissions': bit_range.get('permissions', ""),
                                'span': lower_len,
                            }
                        else:
                            bit_spans[block*16+16-1] = {
                                'name': bit_range.get('name', ""),
                                'permissions': bit_range.get('permissions', ""),
                                'span': 16,
                            }
                else:
                    bit_spans[bit_end] = {
                        'name': bit_range.get('name', ""),
                        'permissions': bit_range.get('permissions', ""),
                        'span': bit_len,
                    }
            if max_bits > 32:
                bit_table_upper_header = ET.SubElement(bit_table, 'tr')
                ET.SubElement(bit_table_upper_header, 'th').text = "Bit"
                for bit in range(48, 64)[::-1]:
                    ET.SubElement(bit_table_upper_header, 'th').text = str(bit)
                bit_table_upper_perms = ET.SubElement(bit_table, 'tr')
                ET.SubElement(bit_table_upper_perms, 'th').text = "Type"
                for bit in range(48, 64)[::-1]:
                    if bit in bit_spans.keys():
                        span = bit_spans[bit]
                        bit_element = ET.SubElement(bit_table_upper_perms, 'td', {'class': 'bitfield'})
                        bit_element.text = span['permissions']
                        colspan = span['span']
                        if colspan > 1:
                            bit_element.set('colspan', str(colspan))
                    elif bit in unused_bits:
                        ET.SubElement(bit_table_upper_perms, 'td', {'class': 'bitfield bitfield-unused'})
                bit_table_upper_data = ET.SubElement(bit_table, 'tr')
                ET.SubElement(bit_table_upper_data, 'th').text = "Name"
                for bit in range(48, 64)[::-1]:
                    if bit in bit_spans.keys():
                        span = bit_spans[bit]
                        bit_element = ET.SubElement(bit_table_upper_data, 'td', {'class': 'bitfield'})
                        bit_element.text = span['name']
                        colspan = span['span']
                        if colspan > 1:
                            bit_element.set('colspan', str(colspan))
                    elif bit in unused_bits:
                        ET.SubElement(bit_table_upper_data, 'td', {'class': 'bitfield bitfield-unused'})
                bit_table_lower_header = ET.SubElement(bit_table, 'tr')
                ET.SubElement(bit_table_lower_header, 'th').text = "Bit"
                for bit in range(32, 48)[::-1]:
                    ET.SubElement(bit_table_lower_header, 'th').text = str(bit)
                bit_table_lower_perms = ET.SubElement(bit_table, 'tr')
                ET.SubElement(bit_table_lower_perms, 'th').text = "Type"
                for bit in range(32, 48)[::-1]:
                    if bit in bit_spans.keys():
                        span = bit_spans[bit]
                        bit_element = ET.SubElement(bit_table_lower_perms, 'td', {'class': 'bitfield'})
                        bit_element.text = span['permissions']
                        colspan = span['span']
                        if colspan > 1:
                            bit_element.set('colspan', str(colspan))
                    elif bit in unused_bits:
                        ET.SubElement(bit_table_lower_perms, 'td', {'class': 'bitfield bitfield-unused'})
                bit_table_lower_data = ET.SubElement(bit_table, 'tr')
                ET.SubElement(bit_table_lower_data, 'th').text = "Name"
                for bit in range(32, 48)[::-1]:
                    if bit in bit_spans.keys():
                        span = bit_spans[bit]
                        bit_element = ET.SubElement(bit_table_lower_data, 'td', {'class': 'bitfield'})
                        bit_element.text = span['name']
                        colspan = span['span']
                        if colspan > 1:
                            bit_element.set('colspan', str(colspan))
                    elif bit in unused_bits:
                        ET.SubElement(bit_table_lower_data, 'td', {'class': 'bitfield bitfield-unused'})
            if max_bits > 16:
                bit_table_upper_header = ET.SubElement(bit_table, 'tr')
                ET.SubElement(bit_table_upper_header, 'th').text = "Bit"
                for bit in range(16, 32)[::-1]:
                    ET.SubElement(bit_table_upper_header, 'th').text = str(bit)
                bit_table_upper_perms = ET.SubElement(bit_table, 'tr')
                ET.SubElement(bit_table_upper_perms, 'th').text = "Type"
                for bit in range(16, 32)[::-1]:
                    if bit in bit_spans.keys():
                        span = bit_spans[bit]
                        bit_element = ET.SubElement(bit_table_upper_perms, 'td', {'class': 'bitfield'})
                        bit_element.text = span['permissions']
                        colspan = span['span']
                        if colspan > 1:
                            bit_element.set('colspan', str(colspan))
                    elif bit in unused_bits:
                        ET.SubElement(bit_table_upper_perms, 'td', {'class': 'bitfield bitfield-unused'})
                bit_table_upper_data = ET.SubElement(bit_table, 'tr')
                ET.SubElement(bit_table_upper_data, 'th').text = "Name"
                for bit in range(16, 32)[::-1]:
                    if bit in bit_spans.keys():
                        span = bit_spans[bit]
                        bit_element = ET.SubElement(bit_table_upper_data, 'td', {'class': 'bitfield'})
                        bit_element.text = span['name']
                        colspan = span['span']
                        if colspan > 1:
                            bit_element.set('colspan', str(colspan))
                    elif bit in unused_bits:
                        ET.SubElement(bit_table_upper_data, 'td', {'class': 'bitfield bitfield-unused'})
            bit_table_lower_header = ET.SubElement(bit_table, 'tr')
            ET.SubElement(bit_table_lower_header, 'th').text = "Bit"
            for bit in range(0, min(16, max_bits))[::-1]:
                ET.SubElement(bit_table_lower_header, 'th').text = str(bit)
            bit_table_lower_perms = ET.SubElement(bit_table, 'tr')
            ET.SubElement(bit_table_lower_perms, 'th').text = "Type"
            for bit in range(0, min(16, max_bits))[::-1]:
                if bit in bit_spans.keys():
                    span = bit_spans[bit]
                    bit_element = ET.SubElement(bit_table_lower_perms, 'td', {'class': 'bitfield'})
                    bit_element.text = span['permissions']
                    colspan = span['span']
                    if colspan > 1:
                        bit_element.set('colspan', str(colspan))
                elif bit in unused_bits:
                    ET.SubElement(bit_table_lower_perms, 'td', {'class': 'bitfield bitfield-unused'})
            bit_table_lower_data = ET.SubElement(bit_table, 'tr')
            ET.SubElement(bit_table_lower_data, 'th').text = "Name"
            for bit in range(0, min(16, max_bits))[::-1]:
                if bit in bit_spans.keys():
                    span = bit_spans[bit]
                    bit_element = ET.SubElement(bit_table_lower_data, 'td', {'class': 'bitfield'})
                    bit_element.text = span['name']
                    colspan = span['span']
                    if colspan > 1:
                        bit_element.set('colspan', str(colspan))
                elif bit in unused_bits:
                    ET.SubElement(bit_table_lower_data, 'td', {'class': 'bitfield bitfield-unused'})

            actual_bits = register.get('bits', list())
            for bit_range in actual_bits[::-1]:
                start_bit = bit_range.get('start')
                end_bit = bit_range.get('end')
                if start_bit is None or end_bit is None:
                    continue
                bit = "Bit [{}]".format(start_bit)
                if end_bit != start_bit:
                    bit = "Bits [{}:{}]".format(end_bit, start_bit)
                bit_notes = "{}, `{}`: {}".format(bit, bit_range.get('name', ""), bit_range.get('notes', ""))
                markdown_lite(body, 'p', bit_notes)

    return ET.tostring(html, encoding='utf-8', xml_declaration=False)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", type=str, default="regs.xhtml", help="The output file.")
    parser.add_argument("input", type=str, help="The input YAML register definition file.")
    args = parser.parse_args()

    doc = yaml.safe_load(open(args.input, 'r'))

    doc_valid = validate(doc)
    if not doc_valid:
        print("Error: Document \"{}\" invalid.".format(args.input))
        return 1

    xhtml = gen_xhtml(doc)
    output = open(args.output, 'wb')
    output.write(b"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
    output.write(b"<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.1//EN\" \"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd\">\n")
    output.write(xhtml)

    return 0


if __name__ == "__main__":
    sys.exit(main())

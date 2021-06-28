# ASMedia xHC RE


## Quick start

### Software dependencies

* Python 3
* Firmware image parser:
  * [Kaitai Struct Compiler][ksc]
  * [Kaitai Struct Python Runtime][kspr]
* Documentation generator:
  * [Python-Markdown][python-markdown]
  * [PyYAML][pyyaml]

### Procedure

1. Install dependencies.
2. Run `make` to generate the parser code used by `validate_fw.py`.
3. Obtain the firmware binaries you're interested in. You can download
   some installer executables from the links in [this file][urls].
   They're self-extracting archives, so you can use the `7z` utility to
   extract the executable inside. Use `wine` to run the extracted
   executable (no need to finish the install), then grab the files it
   extracts from the Wine user's TEMP folder.
4. Explore the firmware with [the Kaitai Web IDE][ide] and the
   [Kaitai Struct definition file][ksy], or run `./validate_fw.py` to
   check the integrity and version of the firmware.
5. Run `make doc` to generate XHTML documentation in [doc/out][doc].


## Reverse engineering notes

See [Notes.md](Notes.md).


[ksc]: https://github.com/kaitai-io/kaitai_struct_compiler
[kspr]: https://github.com/kaitai-io/kaitai_struct_python_runtime
[python-markdown]: https://python-markdown.github.io/
[pyyaml]: https://pyyaml.org/
[urls]: firmware-urls.txt
[ide]: https://ide.kaitai.io/
[ksy]: asm_fw.ksy
[doc]: doc/out

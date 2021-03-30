# monitor

This is a simple firmware that can be flashed to an ASMedia USB 3 host
controller card and interacted with over a serial interface.


#### Table of contents

1. [User interface](#user-interface)
    * [help](#help)
    * [version](#version)
    * [mrb](#mrb)
    * [mrw](#mrw)
    * [mwb](#mwb)
    * [mww](#mww)
    * [reset](#reset)
    * [bmo](#bmo)
2. [Build instructions](#build-instructions)
3. [Hardware modifications](#hardware-modifications)
    * [SPI flash socket](#spi-flash-socket)
        - [Necessary parts and equipment](#necessary-parts-and-equipment)
        - [Procedure](#procedure)
    * [UART header](#uart-header)
        - [Necessary parts and equipment](#necessary-parts-and-equipment-2)
        - [Procedure](#procedure-2)


## User interface

It's a simple command line with some useful commands.

```
Hello from monitor!
monitor version r117.g628dc28 (built on 20XX-01-01T00:00:00Z)
> help
Commands available:
 - help
 - version
 - mrb
 - mrh
 - mrw
 - mwb
 - mwh
 - mww
 - reset
 - bmo
>
```


### help

Display the list of commands.


### version

Print the monitor version, build date/time, and chip name.


### mrb

"Memory Read Byte": Read a single byte of memory.


### mrh

"Memory Read Half-word": Read a 2-byte little-endian half-word of
memory.

On an 8051, "words" are typically considered 16 bits (2 bytes), but I
originally wrote this code for ARM and didn't feel like changing the
names of the commands after porting it to the 8051.


### mrw

"Memory Read Word": Read a 4-byte little-endian word of memory.

On an 8051, "words" are typically considered 16 bits (2 bytes), but I
originally wrote this code for ARM and didn't feel like changing the
names of the commands after porting it to the 8051.


### mwb

"Memory Write Byte": Write a single byte of memory.


### mwh

"Memory Write Half-word": Write a 2-byte little-endian half-word of
memory.

On an 8051, "words" are typically considered 16 bits (2 bytes), but I
originally wrote this code for ARM and didn't feel like changing the
names of the commands after porting it to the 8051.


### mww

"Memory Write Word": Write a 4-byte little-endian word of memory.

On an 8051, "words" are typically considered 16 bits (2 bytes), but I
originally wrote this code for ARM and didn't feel like changing the
names of the commands after porting it to the 8051.


### reset

Perform a CPU soft reset.


### bmo

Switch the monitor into Binary MOde, for use with `bmo.py`. If you
accidentally run this command and enter binary mode, press "Enter" to
exit it and return to a prompt.


## Build instructions

1. Install [sdcc][sdcc].
2. Run `make`.
3. Connect your SPI flash programmer to the flash chip on the board,
   then run `make flash` to write `monitor.img` to the flash. If you
   aren't using a CH341A-based programmer, run the flashrom command
   appropriate for your device.


## Hardware modifications

If you don't already have a pin header soldered to the UART pins on the
chip (the specific pins and other UART information are listed in
[Notes.md][notes] in the parent directory), you'll need to do that
before you can use this. Please note that if you want to replace the SPI
flash chip with a SOIC socket, you'll probably want to do that _before_
adding the UART header, since it's easiest to remove the IC with a hot
air gun or a hot air rework tool, and using those kinds of tools will
put a lot of heat into the board, which would likely melt the hot glue
used to hold the header in place.


### SPI flash socket


#### Necessary parts and equipment

  - Safety glasses (to protect your eyes from splattering solder, sharp
    objects, and hot objects.
  - A decent microscope (all the better to see things with).
  - A soldering iron.
  - Soldering iron tips of various sizes.
    - A thin/sharp one for soldering to the signal pads.
    - A large one (preferably with a chisel tip) for soldering the
      ground pad.
  - A fume extractor (optional, but good so you don't breathe in any
    fumes).
  - Solder.
  - Flux.
  - A hot air rework tool or a hot air gun.
  - An SOIC (SOP8) socket matching the width of the flash chip.
    - Typically, for the boards these chips are used on, the width is
      150mil.
  - Precision tweezers.
  - Kapton (polyimide) tape.
  - PCB vise.
  - Paper towels (to apply and clean up the flux).


#### Procedure

TODO

Basically: Put on your safety glasses, fire up your hot air tool, and
heat the flash chip until you can remove it with tweezers. Then remove
the flash chip and wait for the board to cool down. Then put some flux
on the now-empty PCB pads, stick the socket on the pads, and hold it
down with polyimide tape. Then use the soldering iron with the
sharp/thin tip to solder all the signal pins first, then switch to the
large tip to solder power, then finally ground. Check conductivity with
a multimeter to ensure there are no shorts or broken connections, then
clean up the flux residue.


### UART header


#### Necessary parts and equipment

  - Safety glasses (to protect your eyes from splattering solder, sharp
    objects, and hot objects.
  - A decent microscope (all the better to see things with).
  - A soldering iron.
  - Soldering iron tips of various sizes.
    - A thin/sharp one for soldering to the TX/RX pads.
    - A large one (preferably with a chisel tip) for soldering to
      ground.
  - A fume extractor (optional, but good so you don't breathe in any
    fumes).
  - Solder.
  - 31 AWG armature wire/magnet wire/enamel-coated wire.
    - You don't need this exact gauge (I actually don't remember what
      gauge I used), but you want it to be very thin, very flexible, and
      coated in enamel.
  - Pin or socket header.
    - Doesn't matter which you use, but personally I find pins to be the
      most convenient and least expensive.
  - A hot glue gun.
  - Hot glue.
  - A hobby knife/precision knife.
  - Precision tweezers.
  - Kapton (polyimide) tape.
  - PCB vise.


#### Procedure

Find the correct pins on the IC, then trace the pins to the pull up/pull
down resistors they connect to on the PCB. Then, using a multimeter,
confirm the connection between the pins on the IC and the pads you just
found. These will be the TX and RX pads you'll solder to.

Using a multimeter, find a nice ground pad to solder to. Try to find one
somewhat close to the TX/RX pads, to help maintain the signal integrity.
If you can't find one, you can make one by scraping off the soldermask
on the copper ground fill. If the ground pad you're using is large, or
completely surrounded by copper (as is the case when you use the ground
fill as your connection to ground), you'll want to make sure to use the
large soldering iron tip when soldering to it.

With your TX, RX, and ground pads identified, it's time to prepare the
magnet wire. With the wire still on the spool, use your hobby knife to
scrape off a few millimeters of enamel from the tip. Make sure to scrape
it off the entire surface--not just on one side--and try to avoid
cutting through the wire while you do it. Then cut the wire to the
appropriate length--try to keep the it under 4 in. (10 cm) long. Repeat
this process two times, for the other two wires. Don't scrape the enamel
off the other end just yet--it's alright if you've already done so, but
it'll be easier if you wait to do that until after soldering the exposed
end of the wire to the header.

Now you should have three, short, enamel-coated wires, each with the
enamel entirely scraped off of one of the tips. Heat up your soldering
iron (thin/sharp tip), then use the solder to tin the enamel-free tips
of each of the wires. Then use a pair of sharp tweezers to twist one of
the tinned tips of the wires around one of the pins. Ideally, the wire
should now be able to stay there by friction. Now use the soldering iron
and solder to solder the wire to the pin. Repeat this process for the
other two wires and pins.

With the wires soldered to the pin header, repeat the enamel-removal
process on the free tips of each of the wires, and then tin them like
the other ends.

Now, place the pin header on the board in approximately the location you
would like it to stay in, and use the polyimide tape to keep it there.

With the soldering iron (sharp/thin tip), solder the TX and RX wires to
the pads you found earlier. Use polyimide tape to keep the solder from
bridging to any other pads, components, or wires, if necessary.

Wait for the iron to cool down, then change to the large tip. Then
re-heat the iron and use it to solder the final wire to the ground pad
you identified earlier, once again using polyimide tape as needed.

With the wires soldered in place, use the multimeter to check the
conductivity from each pin on the header to the corresponding TX and RX
pins on the IC, as well as ground. Make sure not only that each pin
connects to the appropriate signals, but also that there are no
short-circuits between any of the pins.

Now that you know that the circuits are electrically correct, remove any
unncessary polyimide tape that remains on the board. Use the hot glue
gun to bind the pin/socket header to the circuit board, as well as to
insulate the pins and provide strain relief for the wires. If you like,
you can also use the hot glue to protect the places where you soldered
the wires to the PCB pads, so that bending the wires won't accidentally
break the connections, as well as to provide strain relief and
electrical insulation.

The board modification is now complete, and you can use this header to
connect to the UART of the USB host controller.


[sdcc]: http://sdcc.sourceforge.net/
[notes]: ../Notes.md

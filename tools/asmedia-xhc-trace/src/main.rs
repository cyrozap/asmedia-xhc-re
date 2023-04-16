/* SPDX-License-Identifier: GPL-3.0-or-later */

/*
 * Copyright (C) 2020, 2023  Forest Crossman <cyrozap@gmail.com>
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

use std::collections::HashMap;
use std::fs::File;
use std::fs::OpenOptions;
use std::io::prelude::*;
use std::io::SeekFrom;
use std::process::exit;
use std::time::Instant;

use clap::Parser;
use memmap::{MmapMut, MmapOptions};

#[derive(Clone)]
struct DeviceInfo {
    name: String,
    has_config: bool,
    has_mmio: bool,
}

impl DeviceInfo {
    fn new(name: &str, has_config: bool, has_mmio: bool) -> Self {
        Self {
            name: name.to_string(),
            has_config,
            has_mmio,
        }
    }
}

struct PciConfig {
    regs: File,
}

impl PciConfig {
    fn new(device_address: &str) -> Result<Self, std::io::Error> {
        let regs = OpenOptions::new()
            .read(true)
            .write(true)
            .open(format!("/sys/bus/pci/devices/{}/config", &device_address))?;
        Ok(Self { regs })
    }

    fn readl(&mut self, reg: u16) -> Result<u32, std::io::Error> {
        self.regs.seek(SeekFrom::Start(reg.into()))?;
        let mut buf: [u8; 4] = [0; 4];
        self.regs.read_exact(&mut buf)?;
        Ok(u32::from_le_bytes(buf))
    }

    fn writel(&mut self, reg: u16, value: u32) -> Result<(), std::io::Error> {
        self.regs.seek(SeekFrom::Start(reg.into()))?;
        self.regs.write_all(&value.to_le_bytes())
    }
}

struct PciBar0 {
    regs: MmapMut,
}

impl PciBar0 {
    fn new(dbsf: &str) -> Result<Self, std::io::Error> {
        let file = OpenOptions::new()
            .read(true)
            .write(true)
            .open(format!("/sys/bus/pci/devices/{}/resource0", &dbsf))?;
        let regs = unsafe { MmapOptions::new().map_mut(&file)? };
        Ok(Self { regs })
    }

    fn readw(&mut self, reg: usize) -> u16 {
        u16::from_le_bytes(self.regs[reg..reg + 2].try_into().unwrap())
    }
}

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Trigger a device reset before tracing
    #[arg(short, long, default_value_t = false)]
    reset: bool,

    /// The number of samples to take
    #[arg(short = 'c', long, default_value_t = 1_000_000)]
    samples: usize,

    /// Unbind the device driver, if bound
    #[arg(short, long, default_value_t = false)]
    unbind: bool,

    /// The "<domain>:<bus>:<slot>.<func>" for the ASMedia USB 3 host controller
    dbsf: String,
}

fn get_u16_from_file(path: &str) -> Result<u16, std::io::Error> {
    let mut value: u16 = 0;
    let mut file = File::open(path)?;
    file.seek(SeekFrom::Start(2))?;
    let mut buf: [u8; 4] = [0; 4];
    file.read_exact(&mut buf)?;
    for b in buf.iter() {
        let v: u8 = if (b'0'..=b'9').contains(b) {
            b - b'0'
        } else if (b'A'..=b'F').contains(b) {
            b - b'A' + 0xa
        } else if (b'a'..=b'f').contains(b) {
            b - b'a' + 0xa
        } else {
            panic!("Invalid hex char: {:#04x}", b);
        };
        value <<= 4;
        value |= <u8 as Into<u16>>::into(v);
    }
    Ok(value)
}

fn main() {
    let args = Args::parse();

    let device_info_map = HashMap::from([
        ((0x1b21, 0x1042), DeviceInfo::new("ASM1042", false, false)),
        ((0x1b21, 0x1142), DeviceInfo::new("ASM1042A", true, true)),
        ((0x1b21, 0x1242), DeviceInfo::new("ASM1142", true, true)),
        (
            (0x1b21, 0x2142),
            DeviceInfo::new("ASM2142/ASM3142", false, true),
        ),
        ((0x1b21, 0x3242), DeviceInfo::new("ASM3242", false, true)),
    ]);

    let vid = match get_u16_from_file(&format!("/sys/bus/pci/devices/{}/vendor", args.dbsf)) {
        Ok(id) => id,
        Err(err) => {
            eprintln!("Error: Failed to read PCI VID: {:?}", err);
            exit(1);
        }
    };
    let did = match get_u16_from_file(&format!("/sys/bus/pci/devices/{}/device", args.dbsf)) {
        Ok(id) => id,
        Err(err) => {
            eprintln!("Error: Failed to read PCI DID: {:?}", err);
            exit(1);
        }
    };

    let device_info = match device_info_map.get(&(vid, did)) {
        Some(info) => info.clone(),
        None => DeviceInfo::new("Unknown", false, false),
    };

    println!("Device: {} ({:04x}:{:04x})", device_info.name, vid, did);

    if !(device_info.has_config || device_info.has_mmio) {
        eprintln!("Error: Device is not supported.");
        exit(1);
    }

    let driver_is_bound: bool = match OpenOptions::new()
        .write(true)
        .open(format!("/sys/bus/pci/devices/{}/driver/unbind", args.dbsf))
    {
        Ok(mut file) => {
            if args.unbind {
                match file.write_all(args.dbsf.as_bytes()) {
                    Ok(_) => false,
                    Err(err) => {
                        eprintln!("Error: Failed to unbind driver: {}", err);
                        exit(1);
                    }
                }
            } else {
                true
            }
        }
        Err(err) => {
            if err.kind() == std::io::ErrorKind::NotFound {
                false
            } else {
                eprintln!("Error: Failed to unbind driver: {}", err);
                exit(1);
            }
        }
    };

    if driver_is_bound && !device_info.has_config {
        eprintln!("Error: Can't read PC from device: A driver is bound to the device and the device doesn't support falling back to PCI config access.");
        exit(1);
    }

    let mut statuses: Vec<u32> = Vec::with_capacity(args.samples);
    let elapsed = if driver_is_bound || !device_info.has_mmio {
        let mut config = match PciConfig::new(&args.dbsf) {
            Ok(c) => c,
            Err(err) => {
                eprintln!("Error: Failed to initialize PciConfig: {:?}", err);
                exit(1);
            }
        };
        if args.reset {
            println!("Resetting device...");
            match config.writel(0xec, 1 << 31) {
                Ok(_) => (),
                Err(err) => {
                    eprintln!("Error: Failed to set reset flag: {:?}", err);
                    exit(1);
                }
            }
            match config.writel(0xec, 0) {
                Ok(_) => (),
                Err(err) => {
                    eprintln!("Error: Failed to clear reset flag: {:?}", err);
                    exit(1);
                }
            }
            println!("Reset complete!");
        }
        let now = Instant::now();
        for _ in 0..statuses.capacity() {
            match config.readl(0xe4) {
                Ok(val) => statuses.push(val),
                Err(err) => {
                    eprintln!("Error: Failed to read status: {:?}", err);
                    exit(1);
                }
            }
        }
        now.elapsed().as_micros()
    } else {
        let mut bar0 = match PciBar0::new(&args.dbsf) {
            Ok(c) => c,
            Err(err) => {
                eprintln!("Error: Failed to initialize PciBar0: {:?}", err);
                exit(1);
            }
        };
        let now = Instant::now();
        for _ in 0..statuses.capacity() {
            statuses.push(bar0.readw(0x300a).into());
        }
        now.elapsed().as_micros()
    };

    println!(
        "Logged {} statuses in {}.{:06} seconds ({} statuses per second)",
        statuses.len(),
        elapsed / 1_000_000,
        elapsed % 1_000_000,
        ((statuses.len() as u128) * 1_000_000) / elapsed
    );
    for val in statuses.iter() {
        println!("{:#06x}", val & 0xffff);
    }
}

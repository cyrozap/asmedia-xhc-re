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

use std::fs::File;
use std::fs::OpenOptions;
use std::io::prelude::*;
use std::io::SeekFrom;
use std::process::exit;
use std::time::Instant;

use clap::Parser;

struct PciConfig {
    //device_address: String,
    reg: File,
}

impl PciConfig {
    fn new(device_address: &str) -> Result<PciConfig, std::io::Error> {
        match OpenOptions::new()
            .read(true)
            .write(true)
            .open(format!("/sys/bus/pci/devices/{}/config", &device_address))
        {
            Ok(config) => Ok(PciConfig {
                //device_address: String::from(device_address),
                reg: config,
            }),
            Err(err) => Err(err),
        }
    }

    fn readl(&mut self, reg: u16) -> Result<u32, std::io::Error> {
        self.reg.seek(SeekFrom::Start(reg.into()))?;
        let mut buf: [u8; 4] = [0; 4];
        self.reg.read_exact(&mut buf)?;
        Ok(u32::from_le_bytes(buf))
    }

    fn writel(&mut self, reg: u16, value: u32) -> Result<(), std::io::Error> {
        self.reg.seek(SeekFrom::Start(reg.into()))?;
        self.reg.write_all(&value.to_le_bytes())
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

    /// The "<domain>:<bus>:<slot>.<func>" for the ASMedia USB 3 host controller
    dbsf: String,
}

fn main() {
    let args = Args::parse();

    let mut config = match PciConfig::new(&args.dbsf) {
        Ok(c) => c,
        Err(err) => {
            eprintln!("Error: Failed to initialize PciConfig: {:?}", err);
            exit(1);
        }
    };
    let mut statuses: Vec<u32> = Vec::with_capacity(args.samples);
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
    let elapsed = now.elapsed().as_micros();
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

use std::fs::File;
use std::fs::OpenOptions;
use std::io::prelude::*;
use std::io::SeekFrom;
use std::process::exit;
use std::str::FromStr;
use std::time::Instant;

use byteorder::{LittleEndian, ReadBytesExt, WriteBytesExt};
use clap::{App, Arg};

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

    fn readl(&mut self, reg: u64) -> Result<u32, std::io::Error> {
        match self.reg.seek(SeekFrom::Start(reg)) {
            Ok(_) => (),
            Err(err) => return Err(err),
        }
        self.reg.read_u32::<LittleEndian>()
    }

    fn writel(&mut self, reg: u64, value: u32) -> Result<(), std::io::Error> {
        match self.reg.seek(SeekFrom::Start(reg)) {
            Ok(_) => (),
            Err(err) => return Err(err),
        }
        self.reg.write_u32::<LittleEndian>(value)
    }
}

fn main() {
    let matches = App::new("asmedia-xhc-trace")
        .arg(
            Arg::with_name("device_address")
                .help("The address of the PCI device to use.")
                .required(true)
                .index(1),
        )
        .arg(
            Arg::with_name("reset")
                .short("r")
                .long("reset")
                .help("Trigger a device reset before tracing."),
        )
        .arg(
            Arg::with_name("sample_count")
                .short("c")
                .long("samples")
                .takes_value(true)
                .help("The number of samples to take. Default is 1,000,000."),
        )
        .get_matches();
    let device_address = matches.value_of("device_address").unwrap();
    let reset_device = matches.is_present("reset");
    let sample_count: usize = match matches.value_of("sample_count") {
        Some(s) => match usize::from_str(s) {
            Ok(c) => c,
            Err(err) => {
                eprintln!("Error: Failed to parse sample_count: {:?}", err);
                exit(1);
            }
        },
        None => 1_000_000,
    };
    let mut config = match PciConfig::new(&device_address) {
        Ok(c) => c,
        Err(err) => {
            eprintln!("Error: Failed to initialize PciConfig: {:?}", err);
            exit(1);
        }
    };
    let mut statuses: Vec<u32> = Vec::with_capacity(sample_count);
    if reset_device {
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

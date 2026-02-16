# epicsdev_rohde
Python-based EPICS PVAccess server for Rohde&Schwarz oscilloscopes.

It is based on [p4p](https://epics-base.github.io/p4p/) and [epicsdev](https://github.com/ASukhanov/epicsdev) packages 
and it can run standalone on Linux, OSX, and Windows platforms.

This implementation is designed to work with Rohde&Schwarz MXO4 and similar series oscilloscopes.
It was developed using the epicsdev_rigol_scope as a template and adapted for Rohde&Schwarz SCPI commands.

## Features

- Multi-channel waveform acquisition (up to 4 channels)
- Configurable trigger settings (edge, pulse, width, slope, runt)
- Horizontal and vertical scale control
- Real-time waveform data streaming via EPICS PVAccess
- Support for various record lengths (1k to 200M points)
- Setup save/recall functionality
- Direct SCPI command interface

## Installation

```bash
pip install epicsdev_rohde
```

For control GUI and plotting:
```bash
pip install pypeto pvplot
```

## Usage

To start the server:
```bash
python -m epicsdev_rohde -r 'TCPIP::192.168.1.100::INSTR'
```

Or using the rohde module directly:
```bash
python -m epicsdev_rohde.rohde -r 'TCPIP::192.168.1.100::INSTR'
```

### Command Line Arguments

- `-r, --resource`: VISA resource string (default: `TCPIP::192.168.1.100::INSTR`)
- `-c, --channels`: Number of channels (default: 4)
- `-d, --device`: Device name prefix (default: `rohde`)
- `-i, --index`: Device index (default: `0`)
- `-v, --verbose`: Increase verbosity (-v or -vv)

### VISA Resource Examples

- TCP/IP INSTR: `TCPIP::192.168.1.100::INSTR`
- TCP/IP HiSLIP: `TCPIP::192.168.1.100::hislip0`
- USB: `USB::0x0AAD::0x01D6::12345678::INSTR`

## Control GUI

```bash
python -m pypeto -c path_to_config -f epicsdev_rohde
```

## Supported Oscilloscopes

- Rohde&Schwarz MXO4 series
- Rohde&Schwarz RTO6 series
- Other R&S oscilloscopes with compatible SCPI commands

## Programming Reference

Based on the Rohde&Schwarz MXO4 User Manual:
https://scdn.rohde-schwarz.com/ur/pws/dl_downloads/pdm/cl_manuals/user_manual/1335_5337_01/MXO4_UserManual_en_16.pdf

## License

MIT License - see LICENSE file for details

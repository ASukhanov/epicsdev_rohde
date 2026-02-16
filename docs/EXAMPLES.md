# Examples

## Basic Usage

### Starting the Server

Connect to a Rohde&Schwarz oscilloscope via TCP/IP:

```bash
python -m epicsdev_rohde -r 'TCPIP::192.168.1.100::INSTR'
```

Using HiSLIP protocol (faster):

```bash
python -m epicsdev_rohde -r 'TCPIP::192.168.1.100::hislip0'
```

### Advanced Options

Start with verbose logging:

```bash
python -m epicsdev_rohde -r 'TCPIP::192.168.1.100::INSTR' -v
```

Very verbose (debug level):

```bash
python -m epicsdev_rohde -r 'TCPIP::192.168.1.100::INSTR' -vv
```

Custom device name and 2 channels:

```bash
python -m epicsdev_rohde -r 'TCPIP::192.168.1.100::INSTR' -d scope -i 1 -c 2
```

This will create PVs with prefix `scope1:` and only 2 channels.

## Accessing PVs

Once the server is running, you can access PVs using any EPICS PVAccess client:

```python
from p4p.client.thread import Context

ctx = Context('pva')

# Read instrument IDN
idn = ctx.get('rohde0:instrCmdR')

# Set trigger level
ctx.put('rohde0:trigLevel', 0.5)

# Get waveform from channel 1
waveform = ctx.get('rohde0:c01Waveform')

# Enable channel 2
ctx.put('rohde0:c02OnOff', 'ON')
```

## Using pvget/pvput Commands

```bash
# Read a value
pvget rohde0:trigLevel

# Set a value
pvput rohde0:trigMode AUTO

# Monitor waveform updates
pvget -m rohde0:c01Waveform
```

## Control GUI with pypeto

```bash
python -m pypeto -c config -f epicsdev_rohde
```

## Plotting with pvplot

```bash
python -m pvplot rohde0:c01Waveform rohde0:c02Waveform
```

## Common PV Names

### Instrument Control
- `rohde0:visaResource` - VISA resource string (read-only)
- `rohde0:instrCmdS` - Send SCPI command
- `rohde0:instrCmdR` - Response from SCPI command
- `rohde0:acqCount` - Number of acquisitions

### Horizontal Settings
- `rohde0:timePerDiv` - Time per division
- `rohde0:recLengthS` - Record length selector
- `rohde0:samplingRate` - Sampling rate (Hz)
- `rohde0:tAxis` - Time axis array

### Trigger Settings
- `rohde0:trigger` - Force trigger
- `rohde0:trigMode` - Trigger mode (NORM/AUTO/SING)
- `rohde0:trigType` - Trigger type (EDGE/PULS/WIDTH/SLOP/RUNT)
- `rohde0:trigSource` - Trigger source (CHAN1/CHAN2/etc.)
- `rohde0:trigLevel` - Trigger level (V)
- `rohde0:trigSlope` - Trigger slope (POS/NEG/EITH)

### Channel Settings (example for channel 1)
- `rohde0:c01OnOff` - Enable/disable channel (ON/OFF)
- `rohde0:c01Coupling` - Coupling (DC/AC/GND)
- `rohde0:c01VoltsPerDiv` - Volts per division
- `rohde0:c01VoltOffset` - Vertical offset (V)
- `rohde0:c01Waveform` - Waveform data array
- `rohde0:c01Mean` - Waveform mean value
- `rohde0:c01Peak2Peak` - Peak-to-peak amplitude

## Troubleshooting

### Connection Issues

1. Verify network connectivity:
   ```bash
   ping 192.168.1.100
   ```

2. Check VISA resource availability:
   ```python
   import pyvisa
   rm = pyvisa.ResourceManager('@py')
   print(rm.list_resources())
   ```

3. Test basic SCPI communication:
   ```python
   import pyvisa
   rm = pyvisa.ResourceManager('@py')
   scope = rm.open_resource('TCPIP::192.168.1.100::INSTR')
   print(scope.query('*IDN?'))
   ```

### Common Error Messages

- **"Could not open resource"**: Check IP address and network connection
- **"VI_ERROR_TMO"**: Timeout - scope may be busy or not responding
- **"Scope was stopped externally"**: Scope front panel was used to stop acquisition

### Performance Tips

- Use HiSLIP protocol (`hislip0`) for better performance
- Reduce record length for faster acquisition rates
- Use AUTO trigger mode for continuous acquisition
- Disable unused channels to improve data transfer speed

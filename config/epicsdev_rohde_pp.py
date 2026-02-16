"""Configuration file for pypeto control GUI for Rohde&Schwarz oscilloscopes."""

# Device configuration
device_name = 'rohde0'

# Page layouts for control GUI
pages = {
    'Main': {
        'layout': [
            ['server', 'status'],
            ['visaResource', 'dateTime'],
            ['acqCount', 'scopeAcqCount', 'lostTrigs'],
            ['instrCtrl', 'instrCmdS', 'instrCmdR'],
        ]
    },
    'Horizontal': {
        'layout': [
            ['timePerDiv', 'recLengthS', 'recLengthR'],
            ['samplingRate'],
            ['tAxis'],
        ]
    },
    'Trigger': {
        'layout': [
            ['trigger', 'trigMode', 'trigState'],
            ['trigType', 'trigSource', 'trigSlope'],
            ['trigLevel', 'trigDelay'],
            ['trigCoupling'],
        ]
    },
    'Channel1': {
        'layout': [
            ['c01OnOff', 'c01Coupling', 'c01Termination'],
            ['c01VoltsPerDiv', 'c01VoltOffset'],
            ['c01Mean', 'c01Peak2Peak'],
            ['c01Waveform'],
        ]
    },
    'Channel2': {
        'layout': [
            ['c02OnOff', 'c02Coupling', 'c02Termination'],
            ['c02VoltsPerDiv', 'c02VoltOffset'],
            ['c02Mean', 'c02Peak2Peak'],
            ['c02Waveform'],
        ]
    },
    'Channel3': {
        'layout': [
            ['c03OnOff', 'c03Coupling', 'c03Termination'],
            ['c03VoltsPerDiv', 'c03VoltOffset'],
            ['c03Mean', 'c03Peak2Peak'],
            ['c03Waveform'],
        ]
    },
    'Channel4': {
        'layout': [
            ['c04OnOff', 'c04Coupling', 'c04Termination'],
            ['c04VoltsPerDiv', 'c04VoltOffset'],
            ['c04Mean', 'c04Peak2Peak'],
            ['c04Waveform'],
        ]
    },
    'Setup': {
        'layout': [
            ['setup'],
            ['timing'],
        ]
    },
}

# PV prefix
pv_prefix = f'{device_name}:'

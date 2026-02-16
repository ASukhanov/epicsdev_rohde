"""Main module for Rohde&Schwarz oscilloscope device support.

This module provides EPICS PVAccess server functionality for Rohde&Schwarz oscilloscopes.
It is based on the epicsdev framework and uses PyVISA for instrument communication.

Usage:
    python -m epicsdev_rohde.rohde -r 'TCPIP::192.168.1.100::INSTR'
    
Or simply:
    python -m epicsdev_rohde -r 'TCPIP::192.168.1.100::INSTR'
"""

# Import the main module functionality
from epicsdev_rohde.__main__ import *

if __name__ == "__main__":
    # This allows running: python -m epicsdev_rohde.rohde
    # The main execution is handled by __main__.py
    pass

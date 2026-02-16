"""EPICS PVAccess server for Rohde&Schwarz oscilloscopes using epicsdev module."""
# pylint: disable=invalid-name
__version__= 'v1.0.0 26-02-16'# Initial version based on epicsdev_rigol_scope

import sys
import time
from time import perf_counter as timer
import argparse
import threading
import numpy as np

import pyvisa as visa
from pyvisa.errors import VisaIOError

from epicsdev import epicsdev as edev

#``````````````````PVs defined here```````````````````````````````````````````
def myPVDefs():
    """PV definitions"""
    SET,U,LL,LH,SCPI = 'setter','units','limitLow','limitHigh','scpi'
    alarm = {'valueAlarm':{'lowAlarmLimit':-9., 'highAlarmLimit':9.}}
    pvDefs = [
# instruments's PVs
['setup', 'Save/recall instrument state to/from latest or operational setup',
    edev.SPV(['Setup','Save latest','Save oper','Recall latest','Recall oper'],'WD'),
    {SET:set_setup}],
['visaResource', 'VISA resource to access the device', edev.SPV(pargs.resource,'R'), {}],
['dateTime',    'Scope\'s date & time', edev.SPV('N/A'), {}],
['acqCount',    'Number of acquisition recorded', edev.SPV(0), {}],
['scopeAcqCount',  'Acquisition count of the scope', edev.SPV(0), {}],
['lostTrigs',   'Number of triggers lost',  edev.SPV(0), {}],
['instrCtrl',   'Scope control commands',
    edev.SPV('*IDN?,*RST,*CLS,*ESR?,*OPC?,*STB?'.split(','),'WD'), {}],
['instrCmdS',   'Execute a scope command. Features: RWE',  edev.SPV('*IDN?','W'), {
    SET:set_instrCmdS}],
['instrCmdR',   'Response of the instrCmdS',  edev.SPV(''), {}],
#``````````````````Horizontal PVs
['recLengthS',   'Number of points per waveform',
    edev.SPV(['AUTO','1k','10k','100k','1M','10M','50M','100M','200M'],'WD'), {
    SET:set_recLengthS}],
['recLengthR',   'Number of points per waveform read', edev.SPV(0.), {
    SCPI:'ACQuire:POINts'}],
['samplingRate', 'Sampling Rate',  edev.SPV(0.), {U:'Hz',
    SCPI:'ACQuire:SRATe'}],
['timePerDiv', f'Horizontal scale (1/{NDIVSX} of full scale)', edev.SPV(2.e-6,'W'), {U:'S/du',
    SCPI: 'TIMebase:SCALe', SET:set_scpi}],
['tAxis',       'Horizontal axis array', edev.SPV([0.]), {U:'S'}],

#``````````````````Trigger PVs
['trigger',     'Click to force trigger event to occur',
    edev.SPV(['Trigger','Force!'],'WD'), {SET:set_trigger}],
['trigType',   'Trigger type', edev.SPV(['EDGE','PULS','WIDTH','SLOP','RUNT'],'WD'),{
    SCPI:'TRIGger:TYPE', SET:set_scpi}],
['trigCoupling',   'Trigger coupling', edev.SPV(['DC','AC','LFR','HFR'],'WD'),{
    SCPI:'TRIGger:EDGE:COUPling', SET:set_scpi}],
['trigState',   'Current trigger status', edev.SPV('?'),{
    SCPI:'TRIGger:STATe'}],
['trigMode',   'Trigger mode', edev.SPV(['NORM','AUTO','SING'],'WD'),{
    SCPI:'TRIGger:MODE', SET:set_scpi}],
['trigDelay',   'Trigger delay/position', edev.SPV(0.,'W'), {U:'S',
    SCPI:'TIMebase:HORizontal:POSition', SET:set_scpi}],
['trigSource', 'Trigger source',
    edev.SPV('CHAN1,CHAN2,CHAN3,CHAN4,EXT'.split(','),'WD'),{
    SCPI:'TRIGger:SOURce', SET:set_scpi}],
['trigSlope',  'Trigger slope', edev.SPV(['POS','NEG','EITH'],'WD'),{
    SCPI:'TRIGger:EDGE:SLOPe', SET:set_scpi}],
['trigLevel', 'Trigger level', edev.SPV(0.,'W'), {U:'V',
    SCPI:'TRIGger:LEVel', SET:set_scpi}],
#``````````````````Auxiliary PVs
['timing',  'Performance timing', edev.SPV([0.]), {U:'S'}],
    ]

    #``````````````Templates for channel-related PVs.
    # The <n> in the name will be replaced with channel number.
    # Important: SPV cannot be used in this list!
    ChannelTemplates = [
['c<n>OnOff', 'Enable/disable channel', (['ON','OFF'],'WD'),{
    SCPI:'CHANnel<n>:STATe', SET:set_scpi}],
['c<n>Coupling', 'Channel coupling', (['DC','AC','GND'],'WD'),{
    SCPI:'CHANnel<n>:COUPling', SET:set_scpi}],
['c<n>VoltsPerDiv',  'Vertical scale',  (1E-3,'W'), {U:'V/du',
    SCPI:'CHANnel<n>:SCALe', SET:set_scpi, LL:500E-6, LH:10.}],
['c<n>VoltOffset',  'Vertical offset',  (0.,'W'), {U:'V',
    SCPI:'CHANnel<n>:OFFSet', SET:set_scpi}],
['c<n>Termination', 'Input termination', ('1M','R'), {U:'Ohm'}],# typically 50 or 1M
['c<n>Waveform', 'Waveform array',           ([0.],), {U:'du'}],
['c<n>Mean',     'Mean of the waveform',     (0.,'A'), {U:'V'}],
['c<n>Peak2Peak','Peak-to-peak amplitude',   (0.,'A'), {U:'V',**alarm}],
    ]
    # extend PvDefs with channel-related PVs
    for ch in range(pargs.channels):
        for pvdef in ChannelTemplates:
            newpvdef = pvdef.copy()
            newpvdef[0] = pvdef[0].replace('<n>',f'{ch+1:02}')
            newpvdef[2] = edev.SPV(*pvdef[2])
            pvDefs.append(newpvdef)
    return pvDefs
#,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
#``````````````````Constants
Threadlock = threading.Lock()
OK = 0
NotOK = -1
IF_CHANGED =True
ElapsedTime = {}
NDIVSX = 10# number of horizontal divisions of the scope display
NDIVSY = 10# number of vertical divisions
#,,,,,,,,,,,,,,,,,,
class C_():
    """Namespace for module properties"""
    scope = None
    scpi = {}# {pvName:SCPI} map
    setterMap = {}
    PvDefs = []
    readSettingQuery = None
    exceptionCount = {}
    numacq = 0
    triggersLost = 0
    trigTime = 0
    previousScopeParametersQuery = ''
    channelsTriggered = []
    xorigin = 0.
    xincrement = 0.
    npoints = 0
    ypars = None
#``````````````````Setters````````````````````````````````````````````````````
def scopeCmd(cmd):
    """Send command to scope, return reply if any."""
    edev.printv(f'>scopeCmd: {cmd}')
    reply = None
    try:
        with Threadlock:
            if '?' in cmd:
                reply = C_.scope.query(cmd)
            else:
                C_.scope.write(cmd)
    except:
        handle_exception(f'in scopeCmd{cmd}')
    return reply

def set_instrCmdS(cmd, *_):
    """Setter for the instrCmdS PV"""
    edev.publish('instrCmdR','')
    reply = scopeCmd(cmd)
    if reply is not None:
        edev.publish('instrCmdR',reply)
    edev.publish('instrCmdS',cmd)

def serverStateChanged(newState:str):
    """Start device function called when server is started"""
    if newState == 'Start':
        edev.printi('start_device called')
        configure_scope()
        adopt_local_setting()
        C_.scope.write(':RUN')
        wait_for_scopeReady()

    elif newState == 'Stop':
        edev.printi('stop_device called')
    elif newState == 'Clear':
        edev.printi('clear_device called')

def set_setup(action_slot, *_):
    """setter for the setup PV"""
    if action_slot == 'Setup':
        return
    action,slot = str(action_slot).split()
    fileName = {'latest':'SETUP1.SET','oper':'SETUP2.SET'}[slot]
    status = f'Setup was saved to {fileName}'
    if action == 'Save':
        with Threadlock:
            C_.scope.write(f'MMEMory:STORe:STATe 1,"{fileName}"')
    elif action == 'Recall':
        status = f'Setup was recalled from {fileName}'
        if str(edev.pvv('server')).startswith('Start'):
            edev.printw('Please set server to Stop before Recalling')
            edev.publish('setup','Setup')
            return NotOK
        with Threadlock:
            C_.scope.write(f'MMEMory:LOAD:STATe 1,"{fileName}"')
    edev.publish('setup','Setup')
    edev.publish('status', status)
    if action == 'Recall':
        adopt_local_setting()

def set_trigger(value, *_):
    """setter for the trigger PV"""
    edev.printv(f'set_trigger: {value}')
    if str(value) == 'Force!':
        with Threadlock:
            C_.scope.write('TRIGger:FORCe')
        edev.publish('trigger','Trigger')

def set_recLengthS(value, *_):
    """setter for the recLengthS PV"""
    edev.printv(f'set_recLengthS: {value}')
    with Threadlock:
        C_.scope.write(f'ACQuire:POINts {value}')
    edev.publish('recLengthS', value)
    update_scopeParameters()

def set_scpi(value, pv, *_):
    """setter for SCPI-associated PVs"""
    print(f'set_scpi({value},{pv.name})')
    scpi = C_.scpi.get(pv.name,None)
    if scpi is None:
        edev.printe(f'No SCPI defined for PV {pv.name}')
        return
    scpi = scpi.replace('<n>',pv.name[2])# replace <n> with channel number
    print(f'set_scpi: {scpi} {value}')
    scpi += f' {value}' if pv.writable else '?'
    edev.printv(f'set_scpi command: {scpi}')
    reply = scopeCmd(scpi)
    if reply is not None:
        edev.publish(pv.name, reply)
    edev.publish(pv.name, value)

#``````````````````Instrument communication functions`````````````````````````
def query(pvnames, explicitSCPIs=None):
    """Execute query request of the instrument for multiple PVs"""
    scpis = [C_.scpi[pvname] for pvname in pvnames]
    if explicitSCPIs:
        scpis += explicitSCPIs
    combinedScpi = '?;:'.join(scpis) + '?'
    print(f'combinedScpi: {combinedScpi}')
    with Threadlock:
        r = C_.scope.query(combinedScpi)
    return r.split(';')

def configure_scope():
    """Send commands to configure data transfer"""
    edev.printi('configure_scope')
    with Threadlock:
        # R&S specific configuration for binary data transfer
        C_.scope.write(":FORMat:DATA INT,16")  # 16-bit integer data
        C_.scope.write(":FORMat:BORDer NORM")  # Normal byte order

def wait_for_scopeReady():
    """Wait for scope to be in RUN state after acquisition"""
    for attempt in range(5):
        trigStatus = C_.scope.query(':TRIGger:STATe?')
        if trigStatus != 'STOP':
            break
        time.sleep(0.1)
    if attempt == 4:
        edev.set_server('Stop')
        edev.printw(f'Scope still stopped {attempt*0.1} seconds after acquisition, Server will be stopped')

def update_scopeParameters():
    """Update scope timing PVs"""
    # Query parameters from the scope
    xscpi = (":TIMebase:RANGe?;:ACQuire:POINts?;:CHAN1:STATe?;"
                ":CHAN2:STATe?;:CHAN3:STATe?;:CHAN4:STATe?;:TRIGger:LEVel?")
    with Threadlock:
        r = C_.scope.query(xscpi)
    if r != (C_.previousScopeParametersQuery):
        edev.printi(f'Scope parameters changed: {r}')
        l = r.split(';')
        timeRange = float(l[0])  # Total time range
        C_.npoints = int(l[1])
        C_.xincrement = timeRange / C_.npoints
        C_.xorigin = -timeRange / 2.0  # R&S typically centers around trigger
        taxis = np.arange(0, C_.npoints) * C_.xincrement + C_.xorigin
        edev.publish('tAxis', taxis)
        edev.publish('recLengthR', C_.npoints, IF_CHANGED)
        edev.publish('timePerDiv', timeRange/NDIVSX, IF_CHANGED)
        edev.publish('samplingRate', 1./C_.xincrement, IF_CHANGED)
        C_.channelsTriggered = []
        for ch in range(pargs.channels):
            state = l[ch+2]
            # R&S returns '1' or '0' for state
            state_str = 'ON' if state == '1' else 'OFF'
            edev.publish(f'c{ch+1:02}OnOff', state_str, IF_CHANGED)
            if state == '1':
                C_.channelsTriggered.append(ch+1)
        edev.publish('trigLevel', float(l[6]), IF_CHANGED)
    C_.previousScopeParametersQuery = r

def init_visa():
    '''Init VISA interface to device'''
    try:
        rm = visa.ResourceManager('@py')
    except ModuleNotFoundError as e:
        edev.printe(f'in visa.ResourceManager: {e}')
        sys.exit(1)

    resourceName = pargs.resource.upper()
    edev.printv(f'Opening resource {resourceName}')
    try:
        C_.scope = rm.open_resource(resourceName)
    except visa.errors.VisaIOError as e:
        edev.printe(f'Could not open resource {resourceName}: {e}')
        sys.exit(1)
    
    C_.scope.timeout = 5000 # ms - R&S may need more time
    C_.scope.read_termination = '\n'
    C_.scope.write_termination = '\n'
    try:
        C_.scope.clear()
        print("Instrument buffer cleared successfully.")
    except Exception as e:
        print(f"An error occurred during clearing the buffer: {e}")
        sys.exit(1)

    try:
        idn = C_.scope.query('*IDN?')
    except Exception as e:
        edev.printe(f"An error occurred during IDN query: {e}")
        if 'SOCKET' in resourceName:
            print('You may need to check VXI or network settings on the instrument.')
        sys.exit(1)
    edev.printi(f'IDN: {idn}')
    if not ('ROHDE' in idn.upper() or 'SCHWARZ' in idn.upper() or 'R&S' in idn.upper()):
        print('WARNING: instrument may not be a Rohde&Schwarz device')
        print(f'IDN: {idn}')

    try:
        C_.scope.write('*CLS') # clear ESR, previous error messages will be cleared
    except Exception as e:
        edev.printe(f'Resource {resourceName} not responding: {e}')
        sys.exit()

#``````````````````````````````````````````````````````````````````````````````
def handle_exception(where):
    """Handle exception"""
    exceptionText = str(sys.exc_info()[1])
    tokens = exceptionText.split()
    msg = 'ERR:'+tokens[0] if tokens[0] == 'VI_ERROR_TMO' else exceptionText
    msg = msg+': '+where
    edev.printe(msg)
    with Threadlock:
        C_.scope.write('*CLS')
    return -1

def adopt_local_setting():
    """Read scope setting and update PVs"""
    edev.printi('adopt_local_setting')
    ct = time.time()
    nothingChanged = True
    try:
        edev.printvv(f'readSettingQuery: {C_.readSettingQuery}')
        with Threadlock:
            values = C_.scope.query(C_.readSettingQuery).split(';')
        edev.printvv(f'parnames: {C_.scpi.keys()}')
        edev.printvv(f'C_.readSettingQuery: {C_.readSettingQuery}')
        edev.printvv(f'values: {values}')
        if len(C_.scpi) != len(values):
            l = min(len(C_.scpi),len(values))
            edev.printe(f'ReadSetting failed for {list(C_.scpi.keys())[l]}')
            sys.exit(1)
        for parname,v in zip(C_.scpi, values):
            pv = edev.pvobj(parname)
            pvValue = pv.current()
            if pv.discrete:
                pvValue = str(pvValue)
            else:
                try:
                    v = type(pvValue.raw.value)(v)
                except ValueError:
                    edev.printe(f'ValueError converting {v} to {type(pvValue.raw.value)} for PV {parname}')
                    sys.exit(1)
            valueChanged = pvValue != v
            if valueChanged:
                edev.printv(f'posting {pv.name}={v}')
                pv.post(v, timestamp=ct)
                nothingChanged = False

    except visa.errors.VisaIOError as e:
        edev.printe('VisaIOError in adopt_local_setting:'+str(e))
    if nothingChanged:
        edev.printi('Local setting did not change.')

#,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,
#``````````````````Acquisition-related functions``````````````````````````````
def trigger_is_detected():
    """check if scope was triggered"""
    ts = timer()
    try:
        with Threadlock:
            trigStatus = C_.scope.query(':TRIGger:STATe?')
            if trigStatus == 'STOP':
                edev.set_server('Stop')
                edev.printw('Scope was stopped externally. Server stopped.')
    except visa.errors.VisaIOError as e:
        edev.printe(f'VisaIOError in query for trigger: {e}')
        for exc in C_.exceptionCount:
            if exc in str(e):
                C_.exceptionCount[exc] += 1
                errCountLimit = 2
                if C_.exceptionCount[exc] >= errCountLimit:
                    edev.printe(f'Processing stopped due to {exc} happened {errCountLimit} times')
                    edev.set_server('Exit')
                else:
                    edev.printw(f'Exception  #{C_.exceptionCount[exc]} during processing: {exc}')
        return False
    except Exception as e:
        edev.printe(f'Exception in query for trigger: {e}')
        sys.exit(1)

    # last query was successfull, clear error counts
    for i in C_.exceptionCount:
        C_.exceptionCount[i] = 0
    edev.publish('trigState', trigStatus, IF_CHANGED)

    # R&S scopes use different trigger states - check for completion
    if trigStatus not in ['COMP', 'COMPLETE']:  # Adjust based on actual R&S responses
        return False

    # trigger detected
    C_.numacq += 1
    C_.trigTime = time.time()
    ElapsedTime['trigger_detection'] = round(timer() - ts, 6)
    edev.printv(f'Trigger detected {C_.numacq}')
    return True

#``````````````````Acquisition-related functions``````````````````````````````
def acquire_waveforms():
    """Acquire waveforms from the device and publish them."""
    edev.printv(f'>acquire_waveform for channels {C_.channelsTriggered}')
    edev.publish('acqCount', edev.pvv('acqCount') + 1, t=C_.trigTime)
    start_time = timer()
    ElapsedTime['preamble'] = 0.
    ElapsedTime['query_wf'] = 0.
    ElapsedTime['publish_wf'] = 0.
    
    # Stop acquisition for consistent reading
    C_.scope.write(':STOP')
    
    for ch in C_.channelsTriggered:
        ts = timer()
        operation = 'getting waveform'
        try:
            # Select the channel
            C_.scope.write(f'CHANnel{ch}:DATA?')
            
            # Query scale and offset for conversion
            scale_query = f'CHANnel{ch}:SCALe?;:CHANnel{ch}:OFFSet?'
            with Threadlock:
                scale_offset = C_.scope.query(scale_query).split(';')
            scale = float(scale_offset[0])
            offset_display = float(scale_offset[1])
            
            ElapsedTime['preamble'] += timer() - ts
            
            # Acquire the waveform data
            ts = timer()
            operation = 'getting waveform data'
            waveform = C_.scope.query_binary_values(f'CHANnel{ch}:DATA?',
                datatype='h', container=np.array)  # signed 16-bit
            ElapsedTime['query_wf'] += timer() - ts
            
            # R&S conversion: raw values typically range from -32768 to 32767
            # Convert to voltage
            v = waveform.astype(float) * scale / 25.0  # 25 divisions typical
            
            # publish
            ts = timer()
            operation = 'publishing'
            edev.publish(f'c{ch:02}Waveform', v, t=C_.trigTime)
            edev.publish(f'c{ch:02}Peak2Peak', np.ptp(v), t = C_.trigTime)
            edev.publish(f'c{ch:02}Mean', v.mean(), t = C_.trigTime)
        except visa.errors.VisaIOError as e:
            edev.printe(f'Visa exception in {operation} for {ch}:{e}')
            break
        except Exception as e:
            edev.printe(f'Exception in {operation} of channel {ch}: {e}')

        ElapsedTime['publish_wf'] += timer() - ts
    
    # Restart acquisition
    C_.scope.write(':RUN')
    wait_for_scopeReady()
    ElapsedTime['acquire_wf'] = timer() - start_time
    edev.printvv(f'elapsedTime: {ElapsedTime}')

def make_readSettingQuery():
    """Create combined SCPI query to read all settings at once"""
    for pvdef in C_.PvDefs:
        pvname = pvdef[0]
        # if setter is defined, add it to the setterMap
        setter = pvdef[3].get('setter',None)
        if setter is not None:
            C_.setterMap[pvname] = setter
        # if SCPI is defined, add it to the readSettingQuery
        scpi = pvdef[3].get('scpi',None)
        if scpi is None:
            continue
        scpi = scpi.replace('<n>',pvname[2])#
        scpi = ''.join([char for char in scpi if not char.islower()])# remove lowercase letters
        # check if scpi is correct:
        s = scpi+'?'
        try:
            with Threadlock:
                r = C_.scope.query(s)
        except VisaIOError as e:
            edev.printe(f'Invalid SCPI in PV {pvname}: {scpi}? : {e}')
            sys.exit(1)
        edev.printvv(f'SCPI for PV {pvname}: {scpi}, reply: {r}')
        if not scpi[0] in '!*':# only SCPI starting with !,* are not added
            C_.scpi[pvname] = scpi
        
    C_.readSettingQuery = '?;'.join(C_.scpi.values()) + '?'
    edev.printv(f'readSettingQuery: {C_.readSettingQuery}')
    edev.printv(f'setterMap: {C_.setterMap}')

def init():
    """Module initialization"""
    init_visa()
    make_readSettingQuery()
    adopt_local_setting()

def periodicUpdate():
    """Called for infrequent updates"""
    while Threadlock.locked():
        edev.printi('periodicUpdate waiting for lock to be released')
        time.sleep(0.1)
    try:
        update_scopeParameters()
    except:
        handle_exception('in update_scopeParameters')
    edev.publish('lostTrigs', C_.triggersLost, IF_CHANGED)
    edev.publish('timing', [(round(-i,6)) for i in ElapsedTime.values()])

def poll():
    """Instrument polling function"""
    if trigger_is_detected():
        with Threadlock:
            acquire_waveforms()

#``````````````````Main```````````````````````````````````````````````````````
if __name__ == "__main__":
    # Argument parsing
    parser = argparse.ArgumentParser(description = __doc__,
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    epilog=f'{__version__}')
    parser.add_argument('-c', '--channels', type=int, default=4, help=
    'Number of channels per device')
    parser.add_argument('-d', '--device', default='rohde', help=
    'Device name, the PV name will be <device><index>:')
    parser.add_argument('-i', '--index', default='0', help=
    'Device index, the PV name will be <device><index>:') 
    parser.add_argument('-r', '--resource', default='TCPIP::192.168.1.100::INSTR', help=
    'Resource string to access the device, e.g. TCPIP::192.168.1.100::hislip0')
    parser.add_argument('-v', '--verbose', action='count', default=0, help=
    'Show more log messages (-vv: show even more)') 
    pargs = parser.parse_args()
    print(f'pargs: {pargs}')

    # Initialize epicsdev and PVs
    pargs.prefix = f'{pargs.device}{pargs.index}:'
    C_.PvDefs = myPVDefs()
    PVs = edev.init_epicsdev(pargs.prefix, C_.PvDefs, pargs.verbose, serverStateChanged)

    # Initialize the device, using pargs if needed.
    init()

    # Start the Server
    edev.set_server('Start')

    # Main loop
    server = edev.Server(providers=[PVs])
    edev.printi(f'Server for {pargs.prefix} started. Sleeping per cycle: {repr(edev.pvv("sleep"))} S.')
    while True:
        state = edev.serverState()
        if state.startswith('Exit'):
            break
        if not state.startswith('Stop'):
            poll()
        if not edev.sleep():
            periodicUpdate()
    edev.printi('Server is exited')

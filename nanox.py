# -*- coding: utf-8 -*-
"""
Created on Thu Nov 23 14:00:58 2023

@author: farge
"""

import time 
from matplotlib import pyplot
from pipython import GCSDevice, pitools, datarectools
import numpy as np


CONTROLLERNAME = 'E-754' 
STAGES = None  
REFMODES = None
TABLERATE = 10  
NUMVALUES = 1024

            
def AutoZero(pidevice) :
    '''Set Automatic Zero Point Calibration.
    
    Internally, the method calls the ATZ command : ATZ [{<AxisID> <LowValue>}]
    '''
    print('AutoZero initialisation...')
    pidevice.ATZ(1, 0)
    pitools.waitonautozero(pidevice, 1)
    print('AutoZero done')
    
    time.sleep(1)
    
def ServoMode(pidevice) :
    '''Set Servo Mode : False (Openloop) or True (Closeloop).
    
    Internally, the method calls the SVO command : SVO {<AxisID> <ServoState>}
    '''
    ServoMode = input('servo mode ON or OFF ? ')
    if ServoMode == 'OFF':
        pidevice.SVO(1, False)
        print(pidevice.qSVO(1))
    if ServoMode == 'ON' :
        pidevice.SVO(1, True)
        print(pidevice.qSVO(1))
    
        
def Position(pos, pidevice) :
    """Apply a given voltage to the piezo actuator.

    Set the given voltage to the atcuator. Internally, the method calls the SVA command 
    on the first axis (we only have one) : SVA{<AxisID> <Amplitude>}

    @param float pos: the input voltage
    """
    print('device to starting position')
    pidevice.SVA(1, pos)
    
def sinus(np, n, amp, pos, pidevice) :
    """Function to create a sine wave signal.

    This function creates a sine wave with the specified parameters with the WAVE_SIN_P command.
    The WSL command set the connection of Wave Table to Wave Generator.
    The WGC command set the number of cycles.
    The WTR command set the Wave Table rate.
    The command is started with WGO.  

    @param int np: the number of points in one cycle.
    @param int n: the number cycles.
    @param float amp: the amplitude in Volts (max is 135 volts).
    """
    
    print(pos)
    wavegens = 1
    wavetables = 2
    print('define sine waveforms for wave tables {}'.format(wavetables))
    pidevice.WAV_SIN_P(table=wavetables, firstpoint=0, numpoints=int(np), append='X',
                       center=np/2, amplitude=amp, offset=pos, seglength=int(np))
    pitools.waitonready(pidevice)
    if pidevice.HasWSL(): 
        print('connect wave generators {} to wave tables {}'.format(wavegens, wavetables))
        pidevice.WSL(wavegens, wavetables)
    if pidevice.HasWGC(): 
        print('set wave generators {} to run for {} cycles'.format(wavegens, n))
        pidevice.WGC(wavegens, [n])
    pidevice.WTR(wavegens=0, tablerates=1, interpol=[1])
    print('start wave generators {}'.format(wavegens))
    move(pos, pidevice)
    pidevice.WGO(wavegens, mode=[1])
    while any(list(pidevice.IsGeneratorRunning(wavegens).values())):
        print('.', end='')
        time.sleep(1.0)
    print('\nreset wave generators {}'.format(wavegens))
    pidevice.WGO(wavegens, mode=[0])
    print('done')


def fatigue(pidevice) :
    '''This function set and start the fatigue test.
    
    It sets the test with a user interface in the console and calling the functions AutoZero, ServoMode and Position.
    It start the test with calling the sinus function while the recorddata function record the test.
    At the end this function returns the plots of the test with calling the processdata function.
    '''
    TIME = 1/(float(input('entrer la fréquence de votre essai : '))) 
    NUMPOINTS = TIME/0.00002
    STARTPOS = int(input('entrer la position de départ de votre essai : '))  
    VMIN = (float(input('entrer l amplitude min de votre essai en V : ')))
    VMAX = (float(input('entrer l amplitude max de votre essai en V : ')))  
    NUMCYLES = int(input('entrer le nombre de cycle de votre essai : '))  
    
    AutoZero(pidevice)
    ServoMode(pidevice)
    Position(STARTPOS, pidevice)
    go=input('ready to go : YES or NO ? ')        
    if go =='YES' :
        AMPLITUDE = VMAX-VMIN
        drec = datarectools.Datarecorder(pidevice)
        recorddata(drec, TIME*NUMCYLES)
        sinus(NUMPOINTS, NUMCYLES, AMPLITUDE, VMIN, pidevice)
        processdata(drec)
    elif go == 'NO' :
        print('no test done')

def rampe(n, amp, pos, t, pidevice):
    """Function to create a ramp signal.
    
    This function creates a ramp wave with the specified parameters with the WAVE_RAMP command.
    The WSL command set the connection of Wave Table to Wave Generator.
    The WGC command set the number of cycles.
    The WTR command set the Wave Table rate.
    The command is started with WGO.  

    @param int n: the number cycles.
    @param float amp: the amplitude in Volts (max is 135 volts).
    @param int pos: the offset : the starting position of the tensile test.
    @param int t: the duartion of the test in seconds.
    """
    wavegens = 1
    wavetables = 1
    print('define sine waveforms for wave tables {}'.format(wavetables))
    pidevice.WAV_RAMP(table=wavetables, firstpoint=0, numpoints=1000, append='X',
                           center=1000, speedupdown=0, amplitude=amp, offset=pos, seglength=1000)
    pitools.waitonready(pidevice)
    if pidevice.HasWSL(): 
        print('connect wave generators {} to wave tables {}'.format(wavegens, wavetables))
        pidevice.WSL(wavegens, wavetables)
    if pidevice.HasWGC(): 
        print('set wave generators {} to run for {} cycles'.format(wavegens, n))
        pidevice.WGC(wavegens, [n])
    print('start wave generators {}'.format(wavegens))
    pidevice.WTR(wavegens=0, tablerates=t/0.02, interpol=[1])
    rate=pidevice.qWTR()
    print(rate)
    
    move(pos, pidevice)
    pidevice.WGO(wavegens, mode=[1])
    while any(list(pidevice.IsGeneratorRunning(wavegens).values())):
        print('.', end='')
        time.sleep(1.0)
    print('\nreset wave generators {}'.format(wavegens))
    pidevice.WGO(wavegens, mode=[0])
    print('done')
        
def traction(pidevice) :
    '''This function set and start the tensile test.
    
    It sets the test with a user interface in the console and calling the functions AutoZero, ServoMode and Position.
    It start the test with calling the sinus function while the recorddata function record the test.
    At the end this function returns the plots of the test with calling the processdata function.
    '''
    TIME = int(input('entrer la période de votre essai : ')) 
    STARTPOS = float(input('entrer la position de départ de votre essai : '))  
    NUMCYLES=1
    AMPLITUDE = (float(input('entrer l amplitude de votre essai en V : '))) 
    AutoZero(pidevice)
    ServoMode(pidevice)
    Position(STARTPOS, pidevice)        
    go=input('ready to go : YES or NO ? ')
    if go =='YES' :
        drec = datarectools.Datarecorder(pidevice)
        recorddata(drec, TIME)
        rampe(NUMCYLES, AMPLITUDE, STARTPOS, TIME, pidevice)
        processdata(drec)  
    elif go == 'NO' :
         print('no test done') 
    
def move(amp, pidevice) :
    '''This function allows for simplified traction in the case where you wish to start a fatigue test at a load greater than 0N.
    
    Set the given voltage to the actuator with a step of 0.1V every 0.1s. Internally, the method calls the SVA command 
    on the first axis (we only have one) : SVA{<AxisID> <Amplitude>}
    '''
    STARTPOS=0
    AMPLITUDE=amp
    for i in np.arange(int(STARTPOS),AMPLITUDE,0.1):
        pidevice.SVA(1, i) 
        print(pidevice.qSVA(1)[1])
        time.sleep(0.1)
     
   
def recorddata(drec, t):
    '''Function to plot the recorded data
    
    This function creates 2 record table : the first one is the output voltage of the controller
    the second one is the recorded load by the analog IN of the controller.
    It also set the record time of the test.
        
    @param drec : instance to the data recorder tools Datarecorder.
    @param int t : the duration of the test in seconds.
    '''
    drec.numvalues = NUMVALUES
    drec.samplefreq = 1/(t/1000)
    print('data recorder rate: {:.2f} Hz'.format(drec.samplefreq))
    drec.options = (datarectools.RecordOptions.ACTUAL_POSITION_2,
                    datarectools.RecordOptions.COMMANDED_POSITION_1)
    drec.sources = drec.gcs.axes[0]
    drec.trigsources = datarectools.TriggerSources.POSITION_CHANGING_COMMAND_1
    
    
def processdata(drec):
    '''Function to plot the recorded data
    
    This function creates 2 plot with the library matplotlib : 
    figure 1 is the Volt / Time plot with the output voltage of the controller.
    figure 2 is the Load / Time plot with the recorded load by the Clipx.
        
    @param drec : instance to the data recorder tools Datarecorder.
    '''
    if pyplot is None:
        print('matplotlib is not installed')
        return
    pyplot.figure(1)
    pyplot.plot(drec.timescale, drec.data[0], color='red')
    pyplot.xlabel('time (s)')
    pyplot.ylabel('Volt (V)')
    pyplot.title('fatigue test')
    
    pyplot.grid(True)
    pyplot.show()
    pyplot.figure(2)
    pyplot.plot(drec.timescale, drec.data[1], color='blue')
    pyplot.xlabel('time (s)')
    pyplot.ylabel('load (N)')
    pyplot.title('fatigue test')
    pyplot.grid(True)
    pyplot.show()
    print(drec.data[0])
    print(drec.timescale)
    
    print('save GCSArray to file "gcsarray.dat"')
    pitools.savegcsarray('gcsarray.dat', drec.header, drec.data)
                    
    
def main():
    with GCSDevice() as pidevice:
        # pidevice.ConnectTCPIP(ipaddress='')
        pidevice.ConnectUSB(serialnum='123014723')
        # pidevice.ConnectRS232(comport=1, baudrate=115200)

        print('connected: {}'.format(pidevice.qIDN().strip()))

        if pidevice.HasqVER():
            print('version info: {}'.format(pidevice.qVER().strip()))

        print('initialize connected stages...')
        pitools.startup(pidevice, stages=STAGES, refmodes=REFMODES)
        test = input('Quel type de test souhaitez vous effectuer : traction ou fatigue ? ')
        if test == 'fatigue':
            fatigue(pidevice)
        elif test == 'traction' :
            traction(pidevice)
     
main() 
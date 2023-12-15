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
TABLERATE = 10  # duration of a wave table point in multiples of servo cycle times as integer
NUMVALUES = 1024  # number of data sets to record as integer
#RECRATE = 200 #number of recordings per second, i.e. in Hz



with GCSDevice() as pidevice:
    
    # pidevice.ConnectTCPIP(ipaddress='')
    pidevice.ConnectUSB(serialnum='123014723')
    # pidevice.ConnectRS232(comport=1, baudrate=115200)

    print('connected: {}'.format(pidevice.qIDN().strip()))

    if pidevice.HasqVER():
        print('version info: {}'.format(pidevice.qVER().strip()))
        
    print('initialize connected stages...')
    pitools.startup(pidevice, stages=STAGES, refmodes=REFMODES)
            
    def AutoZero() :
        print('AutoZero initialisation...')
        pidevice.ATZ(1, 0)
        pitools.waitonautozero(pidevice, 1)
        print('AutoZero done')
        
        time.sleep(1)
        
    def ServoMode() :
        ServoMode = input('servo mode ON or OFF ? ')
        if ServoMode == 'OFF':
            pidevice.SVO(1, False)
            print(pidevice.qSVO(1))
        if ServoMode == 'ON' :
            pidevice.SVO(1, True)
            print(pidevice.qSVO(1))
        
            
    def Position(pos) :
        """Apply a given voltage to the piezo actuator.

        Set the given voltage to the atcuator. Internally, the method calls the SVA command 
        on the first axis (we only have one) : SVA{<AxisID> <Amplitude>}

        @param float pos: the input voltage
        """
        print('device to starting position')
        pidevice.SVA(1, pos)
        
    def sinus(np, n, amp, pos, t, start) :
        """Function to create a sine wave signal.

        This function creates a sine wave with the specified parameters with the WAVE_SIN_P command.
        The command is started with WGO.  

        @param int np: the number of points in one cycle.
        @param int n: the number cycles.
        @param float amp: the amplitude in Volts (max is 135 volts).
        """
        #FIXME remove parameters t and start
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
        move(pos)
        pidevice.WGO(wavegens, mode=[1])
        while any(list(pidevice.IsGeneratorRunning(wavegens).values())):
            print('.', end='')
            time.sleep(1.0)
        print('\nreset wave generators {}'.format(wavegens))
        pidevice.WGO(wavegens, mode=[0])
        print('done')

    
    def fatigue() :
        TIME = 1/(float(input('entrer la fréquence de votre essai : '))) # number of points for one sine period as integer (servo uptade time : 20us)
        NUMPOINTS = TIME/0.00002
        STARTPOS = int(input('entrer la position de départ de votre essai : '))  # start position of the circular motion as float for both axes
        VMIN = (float(input('entrer l amplitude min de votre essai en V : ')))
        VMAX = (float(input('entrer l amplitude max de votre essai en V : ')))  # amplitude of the circular motion as float for both axes
        NUMCYLES = int(input('entrer le nombre de cycle de votre essai : '))  # number of cycles for wave generator output
        
        AutoZero()
        ServoMode()
        Position(STARTPOS)
        go=input('ready to go : YES or NO ? ')        
        if go =='YES' :
            AMPLITUDE = VMAX-VMIN
            drec = datarectools.Datarecorder(pidevice)
            recorddata(drec, TIME*NUMCYLES)
            sinus(NUMPOINTS, NUMCYLES, AMPLITUDE, VMIN, TIME, STARTPOS)
            processdata(drec)
        elif go == 'NO' :
            print('no test done')
    
    def rampe(n, amp, pos, t):
        """Function to create a ramp signal.
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
        
        move(pos)
        pidevice.WGO(wavegens, mode=[1])
        while any(list(pidevice.IsGeneratorRunning(wavegens).values())):
            print('.', end='')
            time.sleep(1.0)
        print('\nreset wave generators {}'.format(wavegens))
        pidevice.WGO(wavegens, mode=[0])
        print('done')
            
    def traction() :
        TIME = int(input('entrer la période de votre essai : ')) # number of points for one sine period as integer (servo uptade time : 20us)
        STARTPOS = float(input('entrer la position de départ de votre essai : '))  # start position of the circular motion as float for both axes
        NUMCYLES=1
        AMPLITUDE = (float(input('entrer l amplitude de votre essai en V : ')))  # amplitude of the circular motion as float for both axes
        AutoZero()
        ServoMode()
        Position(STARTPOS)        
        go=input('ready to go : YES or NO ? ')
        if go =='YES' :
            drec = datarectools.Datarecorder(pidevice)
            recorddata(drec, TIME)
            rampe(NUMCYLES, AMPLITUDE, STARTPOS, TIME)
            processdata(drec)  
        elif go == 'NO' :
             print('no test done') 
        
    def move(amp) :
        STARTPOS=0
        AMPLITUDE=amp
        for i in np.arange(int(STARTPOS),AMPLITUDE,0.1):
            pidevice.SVA(1, i) 
            print(pidevice.qSVA(1)[1])
            time.sleep(0.1)
        
     
           
       
    def recorddata(drec, t):
        drec.numvalues = NUMVALUES
        drec.samplefreq = 1/(t/1000)
        print('data recorder rate: {:.2f} Hz'.format(drec.samplefreq))
        drec.options = (datarectools.RecordOptions.ACTUAL_POSITION_2,
                        datarectools.RecordOptions.COMMANDED_POSITION_1)
        drec.sources = drec.gcs.axes[0]
        drec.trigsources = datarectools.TriggerSources.POSITION_CHANGING_COMMAND_1
        
        
    def processdata(drec):
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
        test = input('Quel type de test souhaitez vous effectuer : traction ou fatigue ? ')
        if test == 'fatigue':
            fatigue()
        elif test == 'traction' :
            traction()
        
        
        
    main() 
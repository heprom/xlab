from __future__ import print_funtion, division
#%% librairie standard
import os
import time
#%% dépendances tierces
import PyTango
import numpy as np
from matplotlib import pyplot as plt
import tifffile
#%%


class MechanicalTest(object):

    _actuators = {'bulky': 'd13-1-mines/ex/bulky'}
    _sai = {'sai': 'd13-1-mines/ca/sai.1'}
    _camera = {'basler': 'd13-1-mines/dt/baslermines.1'}

    def __init__(self, config='xlab'):
        self.load_config(config)
        self.signal_sensors = []
        self.signal_sensors_lbl = []
        self.image_sensors = []

    def set_actuator(self, name):
        if '/' not in name:
            name = self._actuators[name]
        self.actuator = PyTango.DeviceProxy(name)
        self.actuator_velocity = self.actuator.velocity
        self.actuator_isset = True
        self.actuator_ischecked = False
        self.signal_senors.append(lambda: self.actuator.position)
        self.signal_sensors_lbl .append('position [mm]')

    def check_actuator(self):
        if self.actuator.state() is PyTango._PyTango.DevState.STANDBY:
            self.actuator_ischecked = True
        #if self.actuator.state() is PyTango._PyTango.DevState.FAULT:
            #print('Device is not responding, please check address or restart Tango server')
            #return False
        #elif self.actuator.state() is PyTango._PyTango.DevState.OFF:
            #s = raw_input('Motor is off, ready to start ? [y/n]')
            #if s.lower() in 'yes oui 1':
            #   motor.on()
            #   print('ON')
            #return False
        else:
            self.actuator_ischecked = False
        return self.actuator_ischecked

    def set_load_path(self, ):
        pass

    def load_config(self, config):
        pass

    def save_config(self, filename):
        pass

    def add_signal_sensor(self, function, label):
        self.signal_sensors.append(function)
        self.signal_sensors_lbl.append(label)

    def add_sai_sensor(self, name, attribute='', channel=-1, label=None):
        if not hasattr(self, 'sai'):
            if '/' not in name:
                name = self._sai[name]
            self.sai = PyTango.DeviceProxy(name)
        if channel in [0, 1, 2, 3]:
            attribute = 'averagechannel' + str(channel)
        if hasattr(self.sai, attribute):
            if label is None:
                label = name + '.' + attribute
            self.add_signal_sensor(lambda _: getattr(self.sai, attribute), label)
        else:
            raise TypeError
        ## start the sai !
        ## limité à une sai pour l'instant

    def add_image_sensor(self, function):
        self.image_sensors.append(function)

    def add_camera(self, name):
        """for tango camera devices"""
        if '/' not in name:
            name = self._camera[name]
        self.camera = PyTango.DeviceProxy(name)
        ## limitation une camera !
        ## tester l'état, arreter un mode live...
        def snap():
            self.camera.Snap()
            while self.camera.state() is PyTango._PyTango.DevState.RUNNING:
                time.sleep(0.001)
            return self.camera.image
        self.add_image_sensor(snap)

    def set_load_path(self, function=monotonous, args=(1e-3, -1)):
        self.load_path = function
        self.load_path_args = args
        self.load_path_kwargs = kwargs
#%%
def monotonous(mt, speed=1e-3, direction=-1)
    """mt is a MechanicalTest instance
    speed in mm/s (if good settings of the device !)
    direction is a relative non-zero float"""
    if mt.actuator_isset and mt.actuator_ischecked:
        direction = direction/abs(direction)
        mt.actuator.velocity = speed
        if direction > 0:
            mt.actuator.forward() # attention arrêt, limites...
        else:
            mt.actuator.backwards() # attention, gérer l'arret moteur 
    else:
        raise ValueError

from __future__ import print_funtion, division
#%% librairie standard
import os
import time
from threading import Thread
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

    def set_sample(self, sample_name, base_directory):
        self.sample_name = sample_name
        self.out_directory = os.path.join(base_directory, sample_name)

    def check_all(self, strict=True):
        errors = []
        if not self.check_actuator():
            errors.append('The actuator is not in the right state')
        for f in self.signal_sensors:
            try:
                f()
            except Exception as e:
                errors.append(e)
        for f in self.image_sensors:
            try:
                f()
            except Exception as e:
                errors.append(e)
        try:
            os.makedirs(self.out_directory)
        except OSError:
            if strict:
                errors.append('The output directory already exists')
        if len(errors):
            print(errors)
        else:
            print('All seems correct')
            return True

    class Data_Acquisition(Thread): # modulaire mais moins efficace que la version initiale

        def __init__(self, mt, dt=0.12):
            self.dt = dt
            Thread.__init__(self)

        def _wait(self, t_ref):
            try:
                time.sleep(t_ref + self.dt - time.time())
            except ValueError:
                print('Warning: Impossible to maintain the requested rate!')
            
        def run(self):
            counter = 0
            with open(mt.out_directory + mt.sample_name + '_data.log', 'a') as data_file:
                pattern = ';'.join(['{:.4f}' for _ in ['time'] + mt.signal_sensors]) + '\n'
                t0 = time.time()
                while mt.data_acquisition:
                    t_ref = time.time()
                    data_file.write(pattern.format(time.time()-t0, *[f() for f in mt.signal_sensors])
                    for i, get_img in enumerate(mt.image_sensors):
                        tifffile.imsave(out_directory + sample_name + '_img{}_{:04d}.tiff'.format(i, counter), get_img)#(basler.image/2**4).astype(np.uint8))
                    self._wait(t_ref)
                    counter += 1

    class Data_Display(Thread):
        pass

    def set_load_path(self, function=monotonous, args=(1e-3, -1), kwargs={}):
        self.load_path = function
        self.load_path_args = args
        self.load_path_kwargs = kwargs

    def run(self, **kwargs):
        # acquisition
        mt.data_acquisition = True
        mt.data_acquisition_thread = Data_Acquisition({k:v for k,v in kwargs.items() if k in ['dt']})
        # visualisation
        # mouvement
        try:
            mt.data_acquisition_thread.run()
            self.load_path(*self.load_path_args, **self.load_path_kwargs)
        except BaseException as e:
            self.actuator.stop()
            mt.data_acquisition = False
            self.last_error = e
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
#%%
if __name__ == '__main__':
    test = MechanicalTest()
    test.set_actuator('bulky')
    test.add_sai_sensor('sai', channel=1)
    test.set_sample('test_xlab.py', '/root/Desktop/Maxime')
    test.set_load_path()
    if test.check_all():
        test.run()

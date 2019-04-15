from __future__ import print_function, division
#%% from the Python Standard Library
import os
import time
from threading import Thread
import traceback, sys
#%% third party code (available through PIP)
import PyTango
import numpy as np
from matplotlib import pyplot as plt
import tifffile
#%%

def monotonous(mt, speed=1e-3, direction=-1):
    """Simple monotounous loading.
    
    Parameters
    ----------
    mt: a `xlab.MechanicalTest` instance
    speed: float, optional
        Crosshead velocity in the same unit than the actuator configuration (usually mm/s).
    direction: non-zero float, optional
        The sign gives the direction of the displacement and the value stands for an extra gear ratio.
        .. warning:: Depending on how the wiring has been connected, this can be reversed, 
        always check and make a small movement after installing the machine.
    """
    if mt.actuator_isset and mt.actuator_ischecked:
        direction = direction / abs(direction)
        mt.actuator.velocity = speed
        if direction > 0:
            mt.actuator.forward()  # attention arrêt, limites...
        else:
            mt.actuator.backward()  # attention, gérer l'arret moteur
    else:
        raise ValueError("You have to check the actuator before lauching the test.")
#%%

class MechanicalTest(object):

    # list of known devices and alias
    _actuators = {'bulky': 'd13-1-mines/ex/bulky'}
    _sai = {'sai': 'd13-1-mines/ca/sai.1'}
    _camera = {'basler': 'd13-1-mines/dt/baslermines.1'}

    def __init__(self, config='bulky_xlab', channel=-1):
        self.load_config(config, channel)
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
        self.signal_sensors.append(lambda: self.actuator.position)
        self.signal_sensors_lbl.append('position [mm]')

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

    def load_config(self, config, channel):
        if config == 'xlab_bulky':
            self.set_actuator('d13-1-mines/ex/bulky')
            self.add_sai_sensor('d13-1-mines/ca/sai.1', channel=channel)
        #elif config == 'psiche_bulky':  # non fonctionnel
        #    self.set_actuator('tango-mines:d13-1-mines/ex/bulky')
        #    self.add_sai_sensor('i03-c-c00/ca/sai.1', channel=channel)

    def save_config(self, filename):
        pass

    def add_signal_sensor(self, function, label):
        self.signal_sensors.append(function)
        self.signal_sensors_lbl.append(label)

    def add_sai_sensor(self, name, attribute='', channel=-1, label=None, gain=1):
        # :todo: application du gain et sauvegarde des deux signaux
        if not hasattr(self, 'sai'):
            if '/' not in name:
                name = self._sai[name]
            self.sai = PyTango.DeviceProxy(name)
        if channel in [0, 1, 2, 3]:
            attribute = 'averagechannel' + str(channel)
        if hasattr(self.sai, attribute):
            if label is None:
                label = name + '.' + attribute + ' [V]'
            self.add_signal_sensor(lambda: getattr(self.sai, attribute), label)
        else:
            raise TypeError
        # :todo: vérifier l'état de la sai et démarrer l'acquisition le cas échéant
        # :todo: gérer plus d'une sai

    def add_image_sensor(self, function, save_pattern):
        self.image_sensors.append(function)
        filename, ext = os.splitext(save_pattern)
        if not ext:
            ext = '.tif'
            print("Info: Images will be saved as TIFF.")
        elif ext not in ['.tif', '.tiff']:
            print("Warning: Other format than TIFF are not supported for the moment.")
            ext = '.tif'
            print("Info: Images will be saved as TIFF.")
        if '{' not in filename:
            filename += '_{:05d}'
        self.image_sensors_filename.append(filename + ext)

    def add_camera(self, name, save_pattern):
        """for tango camera devices"""
        if '/' not in name:
            name = self._camera[name]
        self.camera = PyTango.DeviceProxy(name)
        # :todo: gérer plus d'une caméra
        # :todo: tester l'état, arreter un mode live...
        def snap():
            self.camera.Snap()
            while self.camera.state() is PyTango._PyTango.DevState.RUNNING:
                time.sleep(0.001)
            return self.camera.image
        self.add_image_sensor(snap, save_pattern)

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
            self.errors = errors
            return False
        else:
            print('All seems correct')
            return True

    def set_load_path(self, function=monotonous, args=tuple(), **kwargs):
        self.load_path = function
        self.load_path_args = args
        self.load_path_kwargs = kwargs

    def run(self, display=True, acquisition=True, **kwargs):
        # acquisition
        if acquisition:
            self.data_acquisition = True
            kw = {k: v for k, v in kwargs.items() if k in ['dt']}
            # :todo: ajouter une différente cadence pour les images que pour les signaux
            self.data_acquisition_thread = DataAcquisition(self, **kw)
        # visualisation
        if display:
            self.data_display = True
            # :todo: ajouter le relai des arguments
            self.data_display_thread = DataDisplay(self, dt=.5)
        # mouvement
        try:
            self.data_acquisition_thread.start() if acquisition else None
            self.data_display_thread.start() if display else None
            self.load_path(self, *self.load_path_args, **self.load_path_kwargs)
        except BaseException as e:
            self.last_error = e
            t, msg, tb = sys.exc_info()
            print(t, msg)
            traceback.print_tb(tb)
            self.stop()
            
    def stop(self):
        self.actuator.stop()
        self.data_acquisition = False
        self.data_display = False


class DataAcquisition(Thread):  # modulaire mais moins efficace que la version initiale
    # :todo: récupérer les images en parralèle pour augmenter l'efficacité

    def __init__(self, mt, dt=0.12):
        self.dt = dt
        self.mt = mt
        Thread.__init__(self)

    def _wait(self, t_ref):
        try:
            time.sleep(t_ref + self.dt - time.time())
        except ValueError:
            print('Warning: Impossible to maintain the requested rate!')

    def run(self):
        counter = 0
        with open(os.path.join(self.mt.out_directory, self.mt.sample_name + '_data.log'), 'a') as data_file:
            pattern = ';'.join(['{:.4f}' for _ in ['time'] + self.mt.signal_sensors]) + '\n'
            t0 = time.time()
            while self.mt.data_acquisition:
                t_ref = time.time()
                data_file.write(pattern.format(time.time() - t0, *[f() for f in self.mt.signal_sensors]))
                for i, get_img in enumerate(self.mt.image_sensors):
                    path = self.mt.out_directory + self.mt.sample_name + self.mt.image_sensors_filename[i].format(i, counter)
                    tifffile.imsave(path, get_img)  # (basler.image/2**4).astype(np.uint8))
                self._wait(t_ref)
                counter += 1

class DataDisplay(Thread):

    def __init__(self, mt, ind=[0, 1], gain=1, dt=0.12, figsize=(20, 10)):
        self.dt = dt
        self.mt = mt
        self.x = ind[0]
        self.y = ind[-1]
        self.l_x = []
        self.l_y = []
        self.gain = gain
        self.figsize = figsize # non utilisé
        Thread.__init__(self)

    def _wait(self, t_ref):
        try:
            time.sleep(t_ref + self.dt - time.time())
        except ValueError:
            print('Warning: Impossible to maintain the requested rate!')

    def run(self):
        x0 = self.mt.signal_sensors[self.x]()
        y0 = self.mt.signal_sensors[self.y]()
        for i in range(10):
            self.l_x.append(self.mt.signal_sensors[self.x]() - x0)
            self.l_y.append((self.mt.signal_sensors[self.y]() - y0) * self.gain)
            time.sleep(.05)
        self.fig = plt.figure()
        plt.ion()
        plt.show()
        ax = self.fig.add_subplot(111)
        ax.set_xlabel("Position moteur (mm)")
        ax.set_ylabel("Force (N)")
        line, = ax.plot(self.l_x, self.l_y)
        while self.mt.data_display:
            self.l_x.append(self.mt.signal_sensors[self.x]() - x0)
            self.l_y.append((self.mt.signal_sensors[self.y]() - y0) * self.gain)
            ax.set_xlim(min(self.l_x), max(self.l_x))
            ax.set_ylim(min(self.l_y), max(self.l_y))
            line.set_data(self.l_x, self.l_y)
        plt.savefig(os.path.join(self.mt.out_directory, self.mt.sample_name + '_plot.pdf'))

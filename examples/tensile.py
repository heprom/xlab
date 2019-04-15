from xlab import MechanicalTest

test = MechanicalTest()
test.set_actuator('bulky')
test.add_sai_sensor('sai', channel=0)
test.set_sample('test_1', '/root/Desktop/Maxime')
test.set_load_path(speed=3e-3)
if test.check_all():
    test.run(display=False)

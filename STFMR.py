import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

import sys
import tempfile
import random
from time import sleep
import time
from statistics import stdev
from pymeasure.log import console_log

from pymeasure.display.Qt import QtWidgets
# from pymeasure.display.windows import ManagedWindow
from pymeasure.display.windows.managed_dock_window import ManagedDockWindow #from latest version
from pymeasure.display.widgets.image_widget import ImageWidget

from pymeasure.experiment import Procedure, Results, unique_filename
from pymeasure.experiment import IntegerParameter, FloatParameter, Parameter

from pymeasure.instruments.agilent import AgilentN5183A
from pymeasure.instruments.keithley import Keithley2182A
from pymeasure.instruments.adcmt import Adcmt6240A
from pymeasure.instruments.keithley import Keithley2450

class NetAnaProcedure(Procedure):

    delay = FloatParameter('Delay Time', units='ms', default=20)
    freq_cw = FloatParameter("cw frequency",units="GHz",default=7)
    power = IntegerParameter("power",units="dbm",default=20)
    # sweeptime = FloatParameter("sweep time",units="s",default=100)#ポイント数をあげるとこれを短くしないとだめ　なぜ？
    voltagepoints = IntegerParameter("number of points for magnetic field", default=1000)
    startvoltage = FloatParameter('start voltage for magnetic field', units='V', default=-7)
    endvoltage = FloatParameter('end voltage for magnetic field', units='V', default=7)
    RateMH = FloatParameter("magnetic field / voltage", units="mT/V", default=43.1) 
    averagePoints = IntegerParameter("number of points for average", default=1) 
    angle = IntegerParameter("angle", default=135) 
    # DCpoints = IntegerParameter("number of points for DC current for JH", default=100)
    # mincurrent = FloatParameter('minimum current for JH', units='mA', default=-10)
    # maxcurrent = FloatParameter('maximum current for JH', units='mA', default=10)
    memo = Parameter("memo",default="")
# averaging??

    DATA_COLUMNS = ['frequency',"power","magnetic field",'V',"angle","theta","memo"]#must be same names to data columns
    def startup(self):
        # Set conditions here
        log.info("Setting the nanovoltmeter")
        nanovol.reset()
        nanovol.set_filter()
        nanovol.set_rate(PLC=1)

        log.info("Setting the adcmt")
        adcmt.initialize()
        adcmt.source_enabled(enable=True)


        log.info("Setting the signal generator")
        signalgenerator.initialize()
        signalgenerator.set_config()




    def execute(self):
        # Put the runnning codes here
        # netana.parse_data(n=1)
        # x1,theta1,r1 = netana.get_data(n=1)

        freq_cw = self.freq_cw
        power = self.power

        log.info("Starting the loop of %d iterations" % self.voltagepoints)
        # sleep(3)
 
        signalgenerator.set_frequency(freq_cw) #GHz
        signalgenerator.set_power(power)
        signalgenerator.source_enabled(True)
        sleep(1)


        adcmt.apply_voltage(self.startvoltage)
        
        for i in range(self.voltagepoints):
            start = time.time()

            deltaVoltage = self.startvoltage + (self.endvoltage-self.startvoltage)/self.voltagepoints*i
            adcmt.apply_voltage(source_voltage=deltaVoltage)
            V_ave = (nanovol.measure_voltage())
            measureTime = time.time()
            # V_l = []
            # for j in range(self.averagePoints):
            #     V_l.append(nanovol.measure_voltage())
            #     sleep(self.delay*10**-3)
            #     # sleep(2*10**-3)
            # if self.averagePoints > 1:
            #     V_ave = sum(V_l)/self.averagePoints
            #     std_s21 = stdev(V_l)
            # else:
            #     V_ave = sum(V_l)
            #     std_s21 = 0
            

#must be same names to DATA_COLUMNS
            # data={"inter":i}


            data = {
                'frequency':freq_cw,
                "power":self.power,
                "magnetic field":self.RateMH*deltaVoltage,
                'V':V_ave,
                "angle":self.angle,
                "memo":self.memo
            }
            # now = time.time()
            # dif = now-start
            # log.info(f"now is {dif}s")

            self.emit('results', data)
            log.debug("Emitting results: %s" % data)
            # period = end-start
            # self.emit('progress', 100 * i /self.voltagepoints)
            self.emit('progress', 100 * i /self.voltagepoints)

            end = time.time()
            # sleep(self.delay-dif)
            log.info(f"measurement period is {end-start}s")
            if end-measureTime<20*10**-3:
                    sleep(self.delay*10**-3)

            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                break


        #     # self.emit('results', data)
        # log.info("Setting the keithley2450")
        # keithley.reset()
        # keithley.apply_current()                # Sets up to source voltage
        # keithley.source_current_range = 0.1  # Sets the source voltage range to 1
        # keithley.compliance_voltage = 20       # Sets the compliance current to 0.01A
        # keithley.source_current = 0        # Sets the source current to 0 V
        # keithley.enable_source() 
        # keithley.measure_current()              # Sets up to measure voltage
        # stepcurrent_min=self.mincurrent*10**-3/(self.DCpoints/2)
        # stepcurrent_max=self.maxcurrent*10**-3/(self.DCpoints/2)
        # nanovol.measure_voltage()
        # for i in range(self.DCpoints):
        #     if i%2 == 0:
        #         keithley.ramp_to_current(stepcurrent_min*i/2)          # Ramps the current ot target 
        #         sleep(20*30*10**-3)
        #         R=abs(nanovol.measure_voltage()/ keithley.current)
        #         data={
        #         "R_dc":R,
        #         "I_dc":keithley.current
        #         }        
        #     else:
        #         keithley.ramp_to_current(stepcurrent_max*(i+1)/2)
        #         sleep(20*30*10**-3)
        #         R=abs(nanovol.measure_voltage()/ keithley.current)
        #         data={
        #         "R_dc":R,
        #         "I_dc":keithley.current
        #         }        
        #     self.emit('results', data)


        # log.info("parse netana data")
        # netana.parse_data(n=1)
        # x1,theta1,r1 = netana.get_data(n=1)
        # log.info(f"{r1[0]}")
        # for k in range(len(x1)):
        #     deltaVoltage = self.startvoltage + (self.endvoltage-self.startvoltage)/len(x1)*k
        #     data["magnetic field"] = self.RateMH*deltaVoltage
        #     data["theta"] =theta1[k]
        #     data["S"] = r1[k]
        #     self.emit('results', data)
        
        signalgenerator.source_enabled(False)
        signalgenerator.shutdown()
        adcmt.shutdown()
        # keithley.disable_source()



class MainWindow(ManagedDockWindow):

    def __init__(self):
        super().__init__(
            procedure_class=NetAnaProcedure,
            inputs=['delay',"freq_cw","angle","power","voltagepoints","startvoltage","endvoltage","RateMH","averagePoints","memo"],#must be all input columns
            displays=['delay',"freq_cw","angle","power","voltagepoints","startvoltage","endvoltage","RateMH","averagePoints","memo"],#include in progress
            x_axis=['magnetic field'],#default(must be in data columns) if you use ManagedDockWindow, use list of columns
            y_axis=["V"],
            sequencer=True,
            sequencer_inputs=['delay',"freq_cw","angle","power","voltagepoints","endvoltage","RateMH","averagePoints","memo"],
            # sequence_file = "gui_sequencer_example.txt",
            directory_input=True,
        )
        self.setWindowTitle('ST-FMR measurement')
        self.directory = r"C:/Users/Ando_lab/Documents/Haku/measureingSystems"

    def queue(self,procedure=None):
        # filename = tempfile.mktemp()
        directory=self.directory
        # filename=unique_filename(directory)
        # filename = f"{directory}/{}"

        if procedure is None:
            procedure = self.make_procedure()
        filename=unique_filename(directory=directory,procedure=procedure,dated_folder=False,\
                                 prefix="",suffix="STFMR_{angle}deg_{cw frequency}GHz_{power}dbm_{memo}")
        results = Results(procedure, filename)

        experiment = self.new_experiment(results)

        self.manager.queue(experiment)



if __name__ == "__main__":
    nanovol = Keithley2182A("GPIB::06")
    signalgenerator = AgilentN5183A('GPIB0::19')
    adcmt = Adcmt6240A('GPIB::01')
    keithley = Keithley2450("GPIB::18")


    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
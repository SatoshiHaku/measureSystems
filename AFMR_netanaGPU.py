import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

import sys
import tempfile
import random
from time import sleep
from statistics import stdev
from pymeasure.log import console_log

from pymeasure.display.Qt import QtWidgets
# from pymeasure.display.windows import ManagedWindow
from pymeasure.display.windows.managed_dock_window import ManagedDockWindow #from latest version
from pymeasure.display.widgets.image_widget import ImageWidget

from pymeasure.experiment import Procedure, Results, unique_filename
from pymeasure.experiment import IntegerParameter, FloatParameter, Parameter

from pymeasure.instruments.agilent import AgilentN5222A
from pymeasure.instruments.keithley import Keithley2182A
from pymeasure.instruments.adcmt import Adcmt6240A

class NetAnaProcedure(Procedure):

    delay = FloatParameter('Delay Time', units='s', default=0.3)
    freq_cw = FloatParameter("cw frequency",units="GHz",default=1.94)
    power = IntegerParameter("power",units="dbm",default=13)
    # sweeptime = FloatParameter("sweep time",units="s",default=100)#ポイント数をあげるとこれを短くしないとだめ　なぜ？
    points = IntegerParameter("number of points", default=1000)
    voltagepoints = IntegerParameter("number of points for magnetic field", default=500) 
    startvoltage = FloatParameter('start voltage for magnetic field', units='V', default=-0.7)
    endvoltage = FloatParameter('end voltage for magnetic field', units='V', default=0.7)
    RateMH = FloatParameter("magnetic field / voltage", units="mT/V", default=43.1) 
    Spara = Parameter("S21 or S12",default="S21" )
    averagePoints = IntegerParameter("number of points for average", default=1) 
    angle = IntegerParameter("angle", default=135) 
    memo = Parameter("memo",default="")
# averaging??

    DATA_COLUMNS = ['frequency',"power","magnetic field",'VolS21',"stdS21","S21 or S12","angle","theta","S","memo"]#must be same names to data columns
    def startup(self):
        # Set conditions here
        log.info("Setting the nanovoltmeter")
        nanovol.reset()
        nanovol.set_filter()
        nanovol.set_rate()

        log.info("Setting the adcmt")
        adcmt.initialize()
        adcmt.source_enabled(enable=True)


        log.info("Setting the netana")
        netana.set_preset()




    def execute(self):
        # Put the runnning codes here
        # netana.parse_data(n=1)
        # x1,theta1,r1 = netana.get_data(n=1)
        sweeptime = self.delay*self.voltagepoints

        freq_cw = self.freq_cw * 10**9

        log.info("Starting the loop of %d iterations" % self.voltagepoints)
        # sleep(3)
        netana.setup_SPARM(n=1,SPAR=self.Spara)
        #if increase band width(counts), require longer time  

        adcmt.apply_voltage(self.startvoltage)
        import time
        # netana.set_sweep(n=1,type="CW",fCW=freq_cw,time=self.sweeptime,num=self.points,BW=1)
        netana.set_sweep(n=1,type="CW",fCW=freq_cw,time=sweeptime,num=self.points,BW=1)
        
        netana.set_power(n=1,P=self.power)
        netana.set_autoYscale(n=1)
        netana.set_average(n=1,counts=10)
        sleep(1)

        # netana.set_sweep(n=1,type="CW",fCW=freq_cw,time=self.sweeptime,num=self.points,BW=1)
        netana.set_sweep(n=1,type="CW",fCW=freq_cw,time=sweeptime,num=self.points,BW=1)

        netana.set_average(n=1,counts=10)
        netana.set_power(n=1,P=self.power)
        netana.set_autoYscale(n=1)
        sleep(1)
        for i in range(self.voltagepoints):
            start = time.time()

            deltaVoltage = self.startvoltage + (self.endvoltage-self.startvoltage)/self.voltagepoints*i
            adcmt.apply_voltage(source_voltage=deltaVoltage)
            Vs21_l = []
            nanovol.measure_voltage()
            for j in range(self.averagePoints):
                Vs21_l.append(nanovol.measure_voltage())
                sleep(20*10**-3)
            if self.averagePoints > 1:
                V_s21_ave = sum(Vs21_l)/self.averagePoints
                std_s21 = stdev(Vs21_l)
            else:
                V_s21_ave = sum(Vs21_l)
                std_s21 = 0
            

#must be same names to DATA_COLUMNS
            # data={"inter":i}


            data = {
                'frequency':freq_cw,
                "power":self.power,
                "magnetic field":self.RateMH*deltaVoltage,
                'VolS21':V_s21_ave,
                "stdS21":std_s21,
                "S21 or S12":self.Spara,
                "angle":self.angle,
                "memo":self.memo
            }
            now = time.time()
            dif = now-start
            log.info(f"now is {dif}s")

            self.emit('results', data)
            log.debug("Emitting results: %s" % data)
            self.emit('progress', 100 * i /self.voltagepoints)


            sleep(self.delay-dif)
            end = time.time()
            log.info(f"measurement period is {end-start}s")

            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                break


            # self.emit('results', data)


        log.info("parse netana data")
        netana.parse_data(n=1)
        x1,theta1,r1 = netana.get_data(n=1)
        log.info(f"{r1[0]}")
        for k in range(len(x1)):
            deltaVoltage = self.startvoltage + (self.endvoltage-self.startvoltage)/len(x1)*k
            data["magnetic field"] = self.RateMH*deltaVoltage
            data["theta"] =theta1[k]
            data["S"] = r1[k]
            self.emit('results', data)
        netana.set_power_off()
        netana.set_preset()
        adcmt.shutdown()


class MainWindow(ManagedDockWindow):

    def __init__(self):
        super().__init__(
            procedure_class=NetAnaProcedure,
            inputs=['delay',"freq_cw","angle","power","points","voltagepoints","startvoltage","endvoltage","RateMH","averagePoints","Spara","memo"],#must be all input columns
            displays=['delay',"freq_cw","angle","power","points","voltagepoints","startvoltage","endvoltage","RateMH","averagePoints","Spara","memo"],#include in progress
            x_axis=['magnetic field'],#default(must be in data columns) if you use ManagedDockWindow, use list of columns
            y_axis=["VolS21","S"],
            sequencer=True,
            sequencer_inputs=['delay',"freq_cw","angle","power","points","voltagepoints","endvoltage","RateMH","averagePoints","Spara","memo"],
            # sequence_file = "gui_sequencer_example.txt",
            directory_input=True,
        )
        self.setWindowTitle('AFMR measurement')
        self.directory = r"C:/Users/Ando_lab/Documents/Haku/measureingSystems"

    def queue(self,procedure=None):
        # filename = tempfile.mktemp()
        directory=self.directory
        # filename=unique_filename(directory)
        # filename = f"{directory}/{}"

        if procedure is None:
            procedure = self.make_procedure()
        filename=unique_filename(directory=directory,procedure=procedure,dated_folder=False,\
                                 prefix="",suffix="AFMR_{angle}deg_{S21 or S12}_{cw frequency}Hz_{power}dbm_{memo}")
        results = Results(procedure, filename)

        experiment = self.new_experiment(results)

        self.manager.queue(experiment)



if __name__ == "__main__":
    nanovol = Keithley2182A("GPIB::06")
    netana = AgilentN5222A('GPIB::16')
    adcmt = Adcmt6240A('GPIB::01')

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
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

    delay = FloatParameter('Delay Time', units='s', default=3)
    freq_cw = IntegerParameter("cw frequency",units="Hz",default=4.83e8)
    power = IntegerParameter("power",units="dbm",default=13)
    sweeptime = FloatParameter("sweep time",units="s",default=50)#ポイント数をあげるとこれを短くしないとだめ　なぜ？
    points = IntegerParameter("number of points", default=10000)
    anglepoints = IntegerParameter("number of points for angle", default=36) 
    voltage = IntegerParameter('voltage for magnetic field', units='mV', default=1000)
    RateMH = FloatParameter("magnetic field / voltage", units="mT/V", default=43.1) 
    Spara = Parameter("S21 or S12",default="S21" )
    averagePoints = IntegerParameter("number of points for average", default=10) 
# averaging??

    DATA_COLUMNS = ['frequency',"angle",'VolS21',"stdS21","magnetic field","S21 or S12"]#must be same names to data columns
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
        voltage = self.voltage*10**-3

        log.info("Starting the loop of %d iterations" % self.anglepoints)
        adcmt.apply_voltage(source_voltage=voltage)
        sleep(3)
        netana.setup_SPARM(n=1,SPAR=self.Spara)
        netana.set_sweep(n=1,type="CW",fCW=self.freq_cw,time=self.sweeptime,num=self.points)
        netana.set_power(n=1,P=self.power)
        netana.set_autoYscale(n=1)
        netana.set_average(n=1)
    

        sleep(1)

        for i in range(self.anglepoints):
            # netana.set_preset()
            deltaAngle = 360/self.anglepoints*i

            Vs21_l = []
            sleep(0.5)
            for j in range(self.averagePoints):
                Vs21_l.append(nanovol.measure_voltage())
            V_s21_ave = sum(Vs21_l)/self.averagePoints
            std_s21 = stdev(Vs21_l)



            data = {
                'frequency':self.freq_cw,
                "angle":deltaAngle,
                'VolS21':V_s21_ave,
                "stdS21":std_s21,
                "magnetic field":self.RateMH*self.voltage,
                "S21 or S12":self.Spara
            }#must be same names to DATA_COLUMNS
            # data={"inter":i}
            self.emit('results', data)
            log.debug("Emitting results: %s" % data)
            self.emit('progress', 100 * i /self.anglepoints)
            sleep(self.delay)

            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                break
        netana.set_power_off()
        netana.set_preset()
        adcmt.shutdown()

# netana = rm.open_resource('GPIB::16')

class MainWindow(ManagedDockWindow):

    def __init__(self):
        super().__init__(
            procedure_class=NetAnaProcedure,
            inputs=['delay',"freq_cw","power","sweeptime","points","anglepoints","voltage","RateMH","averagePoints","Spara"],#must be all input columns
            displays=['delay',"freq_cw","power","sweeptime","points","voltage","RateMH","averagePoints","Spara"],#include in progress
            x_axis=['angle'],#default(must be in data columns) if you use ManagedDockWindow, use list of columns
            y_axis=["VolS21"],
            sequencer=True,
            sequencer_inputs=['delay',"freq_cw","power","sweeptime","points","anglepoints","voltage","RateMH","averagePoints","Spara"],
            # sequence_file = "gui_sequencer_example.txt",
            directory_input=True,
        )
        self.setWindowTitle('ASHE measurement')
        self.directory = r"C:/Users/Ando_lab/Documents/Haku/measureingSystems"

    # def queue(self,procedure=None):
    #     # filename = tempfile.mktemp()
    #     directory=self.directory
    #     filename=unique_filename(directory,)

    #     if procedure is None:
    #         procedure = self.make_procedure()
    #     results = Results(procedure, filename)

    #     experiment = self.new_experiment(results)

    #     self.manager.queue(experiment)
    def queue(self,procedure=None):
        # filename = tempfile.mktemp()
        directory=self.directory

        if procedure is None:
            procedure = self.make_procedure()
        filename=unique_filename(directory=directory,procedure=procedure,dated_folder=False,prefix="",suffix="_{S21 or S12}_{cw frequency}Hz_{voltage for magnetic field}mV_{power}dbm_angle")

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
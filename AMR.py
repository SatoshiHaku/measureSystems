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

from pymeasure.instruments.keithley import Keithley2450
from pymeasure.instruments.keithley import Keithley2182A
from pymeasure.instruments.adcmt import Adcmt6240A

class NetAnaProcedure(Procedure):

    delay = FloatParameter('Delay Time', units='s', default=3)
    anglepoints = IntegerParameter("number of points for angle", default=36) 
    voltage = IntegerParameter('voltage for magnetic field', units='mV', default=1000)
    RateMH = FloatParameter("magnetic field / voltage", units="mT/V", default=43.1) 
    averagePoints = IntegerParameter("number of points for average", default=10) 
    dccurrent = FloatParameter('dc current', units='mA', default=0.1)

# averaging??

    DATA_COLUMNS = ["angle",'R',"Rstd","magnetic_field"]#must be same names to data columns
    def startup(self):
        # Set conditions here
        log.info("Setting the nanovoltmeter")
        nanovol.reset()
        nanovol.set_filter()
        nanovol.set_rate()

        log.info("Setting the adcmt")
        adcmt.initialize()
        adcmt.source_enabled(enable=True)




    def execute(self):
        # Put the runnning codes here
        # netana.parse_data(n=1)
        # x1,theta1,r1 = netana.get_data(n=1)

        log.info("Setting the nanovoltmeter")
        nanovol.reset()
        nanovol.set_filter()
        nanovol.set_rate(PLC=1)

        log.info("Setting the keithley2450")
        keithley.reset()
        keithley.apply_current()                # Sets up to source voltage
        keithley.source_current_range = 0.1  # Sets the source voltage range to 1
        keithley.compliance_voltage = 20       # Sets the compliance current to 0.01A
        keithley.source_current = 0        # Sets the source current to 0 V
        keithley.enable_source() 
        keithley.measure_current()              # Sets up to measure voltage
        keithley.ramp_to_current(self.dccurrent*10**-3)
        sleep(20*30*10**-3)

        log.info("Setting adcmt")
        voltage = self.voltage*10**-3
        adcmt.apply_voltage(source_voltage=voltage)

        sleep(1)


        for i in range(self.anglepoints):
            # netana.set_preset()
            deltaAngle = 360/self.anglepoints*i

            V_l = []
            sleep(0.5)
            for j in range(self.averagePoints):
                V_l.append(nanovol.measure_voltage())
                sleep(20*10**-3)
            R_ave = sum(V_l)/self.averagePoints / keithley.current
            R_std = stdev(V_l) / keithley.current



            data = {
                "angle":deltaAngle,
                'R':R_ave,
                "Rstd":R_std,
                "magnetic_field":self.RateMH*self.voltage,
            }#must be same names to DATA_COLUMNS
            # data={"inter":i}
            self.emit('results', data)
            log.debug("Emitting results: %s" % data)
            self.emit('progress', 100 * i /self.anglepoints)
            sleep(self.delay)

            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                break
        keithley.disable_source()
        keithley.reset()
        adcmt.shutdown()

class MainWindow(ManagedDockWindow):

    def __init__(self):
        super().__init__(
            procedure_class=NetAnaProcedure,
            inputs=['delay',"anglepoints","voltage","RateMH","averagePoints","dccurrent"],#must be all input columns
            displays=['delay',"anglepoints","voltage","RateMH","averagePoints","dccurrent"],#include in progress
            x_axis=['angle'],#default(must be in data columns) if you use ManagedDockWindow, use list of columns
            y_axis=["R"],
            sequencer=True,
            sequencer_inputs=['delay',"anglepoints","voltage","RateMH","averagePoints","dccurrent"],
            # sequence_file = "gui_sequencer_example.txt",
            directory_input=True,
        )
        self.setWindowTitle('AMR measurement')
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
        filename=unique_filename(directory=directory,procedure=procedure,dated_folder=False,prefix="",suffix="_AMR_{voltage for magnetic field}mV")

        results = Results(procedure, filename)

        experiment = self.new_experiment(results)

        self.manager.queue(experiment)



if __name__ == "__main__":
    nanovol = Keithley2182A("GPIB::06")
    keithley = Keithley2450("GPIB::18")
    adcmt = Adcmt6240A('GPIB::01')

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
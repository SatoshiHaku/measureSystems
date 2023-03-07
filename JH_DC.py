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
    DCpoints = IntegerParameter("number of points for DC current for JH", default=40)
    mincurrent = FloatParameter('minimum current for JH (absolute value)', units='mA', default=2)
    maxcurrent = FloatParameter('maximum current for JH (absolute value)', units='mA', default=10)
    averagePoints = IntegerParameter("number of points for average", default=1) 
    memo = Parameter("memo",default="")
# averaging??

    DATA_COLUMNS = ['R_dc',"I_dc","V"]#must be same names to data columns
    def startup(self):
        # Set conditions here
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


    def execute(self):
        # Put the runnning codes here
        # netana.parse_data(n=1)
        # x1,theta1,r1 = netana.get_data(n=1)


        log.info("Starting the loop of %d iterations" % self.DCpoints)


        stepcurrent_min=-(self.maxcurrent - self.mincurrent)*10**-3/(self.DCpoints/2)
        stepcurrent_max=(self.maxcurrent - self.mincurrent)*10**-3/(self.DCpoints/2)
        for i in range(self.DCpoints):
            if i%2 == 0:
                keithley.ramp_to_current(stepcurrent_min*i/2-self.mincurrent*10**-3)          # Ramps the current ot target 
                sleep(20*30*10**-3)
                V=nanovol.measure_voltage()
                R=abs(V/ keithley.current)
                data={
                "R_dc":R,
                "I_dc":keithley.current,
                "V":V
                }        
            else:
                keithley.ramp_to_current(stepcurrent_max*(i+1)/2+self.mincurrent*10**-3)
                sleep(20*30*10**-3)
                R=abs(nanovol.measure_voltage()/ keithley.current)
                data={
                "R_dc":R,
                "I_dc":keithley.current,
                "V":V
                }   
             

            self.emit('results', data)
            log.debug("Emitting results: %s" % data)
            # period = end-start
            # self.emit('progress', 100 * i /self.voltagepoints)
            self.emit('progress', 100 * i /self.DCpoints)


            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                break
        keithley.disable_source()
        keithley.reset()



class MainWindow(ManagedDockWindow):

    def __init__(self):
        super().__init__(
            procedure_class=NetAnaProcedure,
            inputs=['delay',"DCpoints","mincurrent","maxcurrent","averagePoints","memo"],#must be all input columns
            displays=['delay',"DCpoints","mincurrent","maxcurrent","averagePoints","memo"],#include in progress
            x_axis=["I_dc"],#default(must be in data columns) if you use ManagedDockWindow, use list of columns
            y_axis=["R_dc"],
            sequencer=True,
            sequencer_inputs=['delay',"freq_cw","angle","power","voltagepoints","endvoltage","RateMH","averagePoints","memo"],
            # sequence_file = "gui_sequencer_example.txt",
            directory_input=True,
        )
        self.setWindowTitle('JH_DC measurement')
        self.directory = r"C:/Users/Ando_lab/Documents/Haku/measureingSystems"

    def queue(self,procedure=None):
        # filename = tempfile.mktemp()
        directory=self.directory
        # filename=unique_filename(directory)
        # filename = f"{directory}/{}"

        if procedure is None:
            procedure = self.make_procedure()
        filename=unique_filename(directory=directory,procedure=procedure,dated_folder=False,\
                                 prefix="",suffix="JHDC_{memo}")
        results = Results(procedure, filename)

        experiment = self.new_experiment(results)

        self.manager.queue(experiment)



if __name__ == "__main__":
    nanovol = Keithley2182A("GPIB::06")
    keithley = Keithley2450("GPIB::18")


    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
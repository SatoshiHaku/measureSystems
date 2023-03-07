import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

import sys
import tempfile
import random
from time import sleep
import time
from statistics import stdev
import numpy as np
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


    delay = FloatParameter('Delay Time', units='ms', default=50)
    freq_cw = FloatParameter("cw frequency",units="GHz",default=7)
    powerpoints = IntegerParameter("number of points for RF power for JH ", default=20)
    minpower = FloatParameter('minimum power for JH (absolute value)', units='mW', default=50)
    maxpower = FloatParameter('maximum power for JH (absolute value)', units='mW', default=250)
    averagePoints = IntegerParameter("number of points for average", default=5) 
    dccurrent = FloatParameter('dc current', units='mA', default=0.1)
    memo = Parameter("memo",default="")
# averaging??

    DATA_COLUMNS = ["Pmw",'R_rf',"R_rf_std","V","I_dc","frequency_GHz"]#must be same names to data columns
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

        log.info("Setting the signal generator")
        signalgenerator.initialize()
        signalgenerator.set_config()

    def execute(self):
        # Put the runnning codes here
        # netana.parse_data(n=1)
        # x1,theta1,r1 = netana.get_data(n=1)


        log.info("Starting the loop of %d iterations" % self.powerpoints)
        keithley.ramp_to_current(self.dccurrent*10**-3)

        signalgenerator.set_frequency(self.freq_cw) #GHz
        signalgenerator.set_power(0)
        signalgenerator.source_enabled(True)
        

        for i,p in enumerate(np.linspace(self.minpower,self.maxpower,self.powerpoints)):
            Pdbm = 10*np.log10(p)
            signalgenerator.set_power(Pdbm)
            sleep(50*10**-3)
            V_l=[]
            for j in range(self.averagePoints):
                V_l.append(nanovol.measure_voltage())
                sleep(self.delay*10**-3)

            R=np.mean(V_l) / keithley.current
            V=np.mean(V_l)
            if self.averagePoints>1:
                R_rf_std = stdev(V_l)/np.sqrt(self.averagePoints) / keithley.current
            else:
                R_rf_std=0

            data={
            "R_rf":R,
            "R_rf_std":R_rf_std,
            "Pmw":p,
            "V":V,
            "I_dc":keithley.current,
            "frequency_GHz":self.freq_cw
            }        
             

            self.emit('results', data)
            log.debug("Emitting results: %s" % data)
            # period = end-start
            # self.emit('progress', 100 * i /self.voltagepoints)
            self.emit('progress', 100 * i /self.powerpoints)


            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                break
        keithley.disable_source()
        keithley.reset()
        signalgenerator.source_enabled(False)
        signalgenerator.shutdown()

class MainWindow(ManagedDockWindow):

    def __init__(self):
        super().__init__(
            procedure_class=NetAnaProcedure,
            inputs=  ['delay',"freq_cw","powerpoints","minpower","maxpower","averagePoints","dccurrent","memo"],#must be all input columns
            displays=['delay',"freq_cw","powerpoints","minpower","maxpower","averagePoints","dccurrent","memo"],#include in progress
            x_axis=["Pmw"],#default(must be in data columns) if you use ManagedDockWindow, use list of columns
            y_axis=["R_rf"],
            sequencer=True,

            sequencer_inputs=['delay',"freq_cw","powerpoints","minpower","maxpower","averagePoints","dccurrent","memo"],
            # sequence_file = "gui_sequencer_example.txt",
            directory_input=True,
        )
        self.setWindowTitle('JH_RF measurement')
        self.directory = r"C:/Users/Ando_lab/Documents/Haku/measureingSystems"

    def queue(self,procedure=None):
        # filename = tempfile.mktemp()
        directory=self.directory
        # filename=unique_filename(directory)
        # filename = f"{directory}/{}"

        if procedure is None:
            procedure = self.make_procedure()
        filename=unique_filename(directory=directory,procedure=procedure,dated_folder=False,\
                                 prefix="",suffix="JHRF_{cw frequency}GHz_{memo}")
        results = Results(procedure, filename)

        experiment = self.new_experiment(results)

        self.manager.queue(experiment)



if __name__ == "__main__":
    nanovol = Keithley2182A("GPIB::06")
    keithley = Keithley2450("GPIB::18")
    signalgenerator = AgilentN5183A('GPIB0::19')


    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
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
# from pymeasure.display.windows.managed_dock_window import ManagedDockWindow #from latest version
from pymeasure.display.windows.managed_dock_window_multitabs import ManagedDockWindow #from latest version

from pymeasure.display.widgets.image_widget import ImageWidget
from pymeasure.display.widgets.dock_widget import DockWidget

from pymeasure.experiment import Procedure, Results, unique_filename
from pymeasure.experiment import IntegerParameter, FloatParameter, Parameter

from pymeasure.instruments.agilent import AgilentN5183A
from pymeasure.instruments.keithley import Keithley2182A
from pymeasure.instruments.adcmt import Adcmt6240A
from pymeasure.instruments.keithley import Keithley2450

import numpy as np

class JHRF_Procedure(Procedure):
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

class JHRF_MainWindow(ManagedDockWindow):

    def __init__(self):
        super().__init__(
            procedure_class=JHRF_Procedure,
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


##############################################################################################################


class JHDC_Procedure(Procedure):

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


class JHDC_MainWindow(ManagedDockWindow):

    def __init__(self):
        super().__init__(
            procedure_classes=[JHDC_Procedure,JHRF_Procedure],
            inputs=[['delay',"DCpoints","mincurrent","maxcurrent","averagePoints","memo"],['delay',"freq_cw","powerpoints","minpower","maxpower","averagePoints","dccurrent","memo"]],#must be all input columns
            displays=[['delay',"DCpoints","mincurrent","maxcurrent","averagePoints","memo"],['delay',"freq_cw","powerpoints","minpower","maxpower","averagePoints","dccurrent","memo"]],#include in progress
            x_axis=[["I_dc"],["Pmw"]],#default(must be in data columns) if you use ManagedDockWindow, use list of columns
            y_axis=[["R_dc"],["R_rf"]],
            sequencer=True,
            sequencer_inputs=[['delay',"DCpoints","mincurrent","maxcurrent","averagePoints","memo"],['delay',"freq_cw","powerpoints","minpower","maxpower","averagePoints","dccurrent","memo"]],
            # sequence_file = "gui_sequencer_example.txt",
            directory_input=True,
            N=2,
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

# class JHDC_MainWindow(ManagedDockWindow):

#     def __init__(self):
#         super().__init__(
#             procedure_class=JHDC_Procedure,
#             inputs=['delay',"DCpoints","mincurrent","maxcurrent","averagePoints","memo"],#must be all input columns
#             displays=['delay',"DCpoints","mincurrent","maxcurrent","averagePoints","memo"],#include in progress
#             x_axis=["I_dc"],#default(must be in data columns) if you use ManagedDockWindow, use list of columns
#             y_axis=["R_dc"],
#             sequencer=True,
#             sequencer_inputs=['delay',"freq_cw","angle","power","voltagepoints","endvoltage","RateMH","averagePoints","memo"],
#             # sequence_file = "gui_sequencer_example.txt",
#             directory_input=True,
#             N=2,
#         )
#         self.setWindowTitle('JH_DC measurement')
#         self.directory = r"C:/Users/Ando_lab/Documents/Haku/measureingSystems"

#         self.dock_widget = DockWidget("savae tab",procedure_class=JHDC_Procedure,x_axis_labels=["I_dc"],y_axis_labels=["R_dc"])

#     def queue(self,procedure=None):
#         # filename = tempfile.mktemp()
#         directory=self.directory
#         # filename=unique_filename(directory)
#         # filename = f"{directory}/{}"

#         if procedure is None:
#             procedure = self.make_procedure()
#         filename=unique_filename(directory=directory,procedure=procedure,dated_folder=False,\
#                                  prefix="",suffix="JHDC_{memo}")
#         results = Results(procedure, filename)

#         experiment = self.new_experiment(results)

#         self.manager.queue(experiment)



if __name__ == "__main__":
    nanovol = Keithley2182A("GPIB::06")
    keithley = Keithley2450("GPIB::18")
    signalgenerator = AgilentN5183A('GPIB0::19')


    app = QtWidgets.QApplication(sys.argv)
    window = JHDC_MainWindow()
    # window1 = JHRF_MainWindow()
    window.show()
    # window1.show()
    sys.exit(app.exec())
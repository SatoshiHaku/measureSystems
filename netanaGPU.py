import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

import sys
import tempfile
import random
from time import sleep
from pymeasure.log import console_log

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows import ManagedWindow

from pymeasure.experiment import Procedure, Results
from pymeasure.experiment import IntegerParameter, FloatParameter, Parameter

from pymeasure.instruments.keithley import Keithley2182A
from pymeasure.instruments.agilent import AgilentN5222A


class RandomProcedure(Procedure):

    iterations = IntegerParameter('Loop Iterations')
    delay = FloatParameter('Delay Time', units='s', default=0.2)
    seed = Parameter('Random Seed', default='12345')

    DATA_COLUMNS = ['Iteration', 'Random Number']

    def startup(self):
        log.info("Setting the seed of the random number generator")
        random.seed(self.seed)

    def execute(self):
        log.info("Starting the loop of %d iterations" % self.iterations)
        for i in range(self.iterations):
            data = {
                'Iteration': i,
                'Random Number': random.random()
            }
            self.emit('results', data)
            log.debug("Emitting results: %s" % data)
            self.emit('progress', 100 * i / self.iterations)
            sleep(self.delay)
            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                break


class MultimeterProcedure(Procedure):

    iterations = IntegerParameter('Loop Iterations') #name in () is title
    delay = FloatParameter('Delay Time', units='s', default=0.2)
    filename = Parameter('File Name', default='aaa.csv')

    DATA_COLUMNS = ['Iteration', 'Voltage']

    def startup(self):
        # Set conditions here
        log.info("Setting the multimeter")
        multimeter.set_filter()
        multimeter.set_rate()
        ADCMT.write('*RST')
        ADCMT.write('VF')

    def execute(self):
        # Put the runnning codes here
        log.info("Starting the loop of %d iterations" % self.iterations)
        for i in range(self.iterations):
            Vol = i*10**-3
            ADCMT.write(f'SOV{Vol},LMI0.003')
            data = {
                'Iteration':Vol,
                'Voltage': multimeter.measure_voltage()
            }
            self.emit('results', data)
            log.debug("Emitting results: %s" % data)
            self.emit('progress', 100 * i / self.iterations)
            sleep(self.delay)
            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                break

class NetAnaProcedure(Procedure):

    iterations = IntegerParameter('Loop Iterations',default=1) #name in () is title
    delay = FloatParameter('Delay Time', units='s', default=0.2)
    filename = Parameter('File Name', default='aaa.csv')
    startFreq = IntegerParameter("start frequency",units="Hz",default=1e8)
    endFreq = IntegerParameter("end frequency",units="Hz",default=1e9)
    power = IntegerParameter("power",units="dbm",default=0)
    sweeptime = FloatParameter("sweep time",units="s",default=1)
    points = IntegerParameter("number of points", default=101)

    DATA_COLUMNS = ['frequency','r',"N"]#must be same names to data columns

    def startup(self):
        # Set conditions here
        log.info("Setting the netana")
        netana.set_preset()
        netana.setup_SPARM()
        netana.set_sweep(startFreq=self.startFreq,endFreq=self.endFreq,time=self.sweeptime,num=self.points)
        netana.set_power(P=self.power)
        netana.set_autoYscale()
        netana.set_average()
        sleep(1)


    def execute(self):
        # Put the runnning codes here
        netana.parse_data()
        x,theta,r = netana.get_data()
        log.info("Starting the loop of %d iterations" % len(x))
        for i in range(len(x)):

            data = {
                'frequency':x[i],
                'r': r[i],
                "N":i
            }#must be same names to DATA_COLUMNS
            # data={"inter":i}
            self.emit('results', data)
            log.debug("Emitting results: %s" % data)
            self.emit('progress', 100 * i /len(x))
            sleep(self.delay)

            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                break
# netana = rm.open_resource('GPIB::16')


class MainWindow(ManagedWindow):

    def __init__(self):
        super().__init__(
            procedure_class=NetAnaProcedure,
            inputs=['iterations', 'delay',"filename","startFreq","endFreq","power","sweeptime","points"],
            displays=['iterations', 'delay',"filename","startFreq","endFreq","power","sweeptime","points"],#include in progress
            x_axis='N',#default(must be in data columns)
            y_axis='r',
            # sequencer=True,
            # sequencer_inputs=['iterations','delay',"filename","startFreq","endFreq","power","sweeptime"]
            # sequence_file = "gui_sequencer_example.txt",
            # directory_input=True,
        )
        self.setWindowTitle('Netana GUI Example')
        # self.directory = r"C:\Users\Ando_lab\Documents\Haku\measureingSystems"

    def queue(self,procedure=None):
        filename = tempfile.mktemp()
        # directory=self.directory
        # filename=directory
        # filename = filename

        if procedure is None:
            procedure = self.make_procedure()
        results = Results(procedure, filename)

        experiment = self.new_experiment(results)

        self.manager.queue(experiment)



if __name__ == "__main__":
    netana = AgilentN5222A('GPIB::16')
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
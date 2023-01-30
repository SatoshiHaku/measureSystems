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

    iterations = IntegerParameter('Loop Iterations')
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

class MainWindow(ManagedWindow):

    def __init__(self):
        super().__init__(
            procedure_class=MultimeterProcedure,
            inputs=['iterations', 'delay',"filename"],
            displays=['iterations', 'delay'],
            x_axis='Iteration',
            y_axis='Voltage',
            sequencer=True,
            sequencer_inputs=['iterations','delay','filename'],
            # sequence_file = "gui_sequencer_example.txt",
            # directory_input=True,
        )
        self.setWindowTitle('GUI Example')
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
    multimeter = Keithley2182A("GPIB::06")
    import pyvisa
    rm = pyvisa.ResourceManager()
    ADCMT = rm.open_resource('GPIB::01')

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
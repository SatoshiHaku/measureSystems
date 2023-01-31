import logging
log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

import sys
import tempfile
import random
from time import sleep
from pymeasure.log import console_log

from pymeasure.display.Qt import QtWidgets
# from pymeasure.display.windows import ManagedWindow
from pymeasure.display.windows.managed_dock_window import ManagedDockWindow #from latest version
from pymeasure.display.widgets.image_widget import ImageWidget

from pymeasure.experiment import Procedure, Results
from pymeasure.experiment import IntegerParameter, FloatParameter, Parameter

from pymeasure.instruments.agilent import AgilentN5222A


class NetAnaProcedure(Procedure):

    iterations = IntegerParameter('Loop Iterations',default=1) #name in () is title
    delay = FloatParameter('Delay Time', units='s', default=0.01)
    filename = Parameter('File Name', default='aaa.csv')
    startFreq = IntegerParameter("start frequency",units="Hz",default=1e8)
    endFreq = IntegerParameter("end frequency",units="Hz",default=1e9)
    power = IntegerParameter("power",units="dbm",default=0)
    sweeptime = FloatParameter("sweep time",units="s",default=0.1)#ポイント数をあげるとこれを短くしないとだめ　なぜ？
    points = IntegerParameter("number of points", default=501)

    DATA_COLUMNS = ['frequency','S21',"S11","N"]#must be same names to data columns

    def startup(self):
        # Set conditions here
        log.info("Setting the netana")
        netana.set_preset()
        netana.setup_SPARM(n=1,SPAR="S21")
        netana.setup_SPARM(n=2,SPAR="S11")

        netana.set_sweep(n=1,startFreq=self.startFreq,endFreq=self.endFreq,time=self.sweeptime,num=self.points)
        netana.set_sweep(n=2,startFreq=self.startFreq,endFreq=self.endFreq,time=self.sweeptime,num=self.points)

        netana.set_power(n=1,P=self.power)
        netana.set_power(n=2,P=self.power)

        netana.set_autoYscale(n=1)
        netana.set_autoYscale(n=2)

        netana.set_average(n=1)
        netana.set_average(n=2)

        sleep(1)


    def execute(self):
        # Put the runnning codes here
        netana.parse_data(n=1)
        netana.parse_data(n=2)

        x1,theta1,r1 = netana.get_data(n=1)
        x2,theta2,r2 = netana.get_data(n=2)

        log.info("Starting the loop of %d iterations" % len(x1))
        for i in range(len(x1)):

            data = {
                'frequency':x1[i],
                'S21': r1[i],
                "S11": r2[i],
                "N":i
            }#must be same names to DATA_COLUMNS
            # data={"inter":i}
            self.emit('results', data)
            log.debug("Emitting results: %s" % data)
            self.emit('progress', 100 * i /len(x1))
            sleep(self.delay)

            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                break
        netana.set_power_off()
        netana.set_preset()

# netana = rm.open_resource('GPIB::16')


class MainWindow(ManagedDockWindow):

    def __init__(self):
        super().__init__(
            procedure_class=NetAnaProcedure,
            inputs=['iterations', 'delay',"filename","startFreq","endFreq","power","sweeptime","points"],
            displays=['iterations', 'delay',"filename","startFreq","endFreq","power","sweeptime","points"],#include in progress
            x_axis=['frequency',"frequency"],#default(must be in data columns) if you use ManagedDockWindow, use list of columns
            y_axis=['S21',"S11"],
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
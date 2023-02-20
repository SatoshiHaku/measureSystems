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

from pymeasure.experiment import Procedure, Results, unique_filename
from pymeasure.experiment import IntegerParameter, FloatParameter, Parameter

from pymeasure.instruments.agilent import AgilentN5222A


class NetAnaProcedure(Procedure):

    iterations = IntegerParameter('Loop Iterations',default=1) #name in () is title
    delay = FloatParameter('Delay Time', units='s', default=0.01)
    startFreq = FloatParameter("start frequency",units="GHz",default=1)
    endFreq = FloatParameter("end frequency",units="GHz",default=3)
    power = IntegerParameter("power",units="dbm",default=0)
    sweeptime = FloatParameter("sweep time",units="s",default=0.1)#ポイント数をあげるとこれを短くしないとだめ　なぜ？
    points = IntegerParameter("number of points", default=501)
    filename = Parameter('memo', default='')



    DATA_COLUMNS = ['frequency','S21',"S11","S12","S22","N"]#must be same names to data columns

    def startup(self):
        # Set conditions here
        log.info("Setting the netana")
        netana.set_preset()




    def execute(self):
        # Put the runnning codes here
        startFreq = self.startFreq*10**9
        endFreq = self.endFreq*10**9
        netana.setup_SPARM(n=1,SPAR="S21")
        netana.setup_SPARM(n=2,SPAR="S11")
        netana.setup_SPARM(n=3,SPAR="S12")
        netana.setup_SPARM(n=4,SPAR="S22")

        netana.set_sweep(n=1,startFreq=startFreq,endFreq=endFreq,time="AUTO",num=self.points)
        netana.set_sweep(n=2,startFreq=startFreq,endFreq=endFreq,time="AUTO",num=self.points)
        netana.set_sweep(n=3,startFreq=startFreq,endFreq=endFreq,time="AUTO",num=self.points)
        netana.set_sweep(n=4,startFreq=startFreq,endFreq=endFreq,time="AUTO",num=self.points)
        # netana.set_sweep(n=1,startFreq=self.startFreq,endFreq=self.endFreq,time=self.sweeptime,num=self.points)
        # netana.set_sweep(n=2,startFreq=self.startFreq,endFreq=self.endFreq,time=self.sweeptime,num=self.points)
        # netana.set_sweep(n=3,startFreq=self.startFreq,endFreq=self.endFreq,time=self.sweeptime,num=self.points)
        # netana.set_sweep(n=4,startFreq=self.startFreq,endFreq=self.endFreq,time=self.sweeptime,num=self.points)

        netana.set_power(n=1,P=self.power)
        netana.set_power(n=2,P=self.power)
        netana.set_power(n=3,P=self.power)
        netana.set_power(n=4,P=self.power)

        netana.set_autoYscale(n=1)
        netana.set_autoYscale(n=2)
        netana.set_autoYscale(n=3)
        netana.set_autoYscale(n=4)

        netana.set_average(n=1)
        netana.set_average(n=2)
        netana.set_average(n=3)
        netana.set_average(n=4)

        sleep(1)
        netana.parse_data(n=1)
        netana.parse_data(n=2)
        netana.parse_data(n=3)
        netana.parse_data(n=4)

        x1,theta1,r1 = netana.get_data(n=1)
        x2,theta2,r2 = netana.get_data(n=2)
        x3,theta3,r3 = netana.get_data(n=3)
        x4,theta4,r4 = netana.get_data(n=4)

        log.info("Starting the loop of %d iterations" % len(x1))
        for i in range(len(x1)):

            data = {
                'frequency':x1[i],
                'S21': r1[i],
                "S11": r2[i],
                'S12': r3[i],
                'S22': r4[i],
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
            inputs=['iterations', 'delay',"startFreq","endFreq","power","sweeptime","points","filename"],
            displays=['iterations', 'delay',"startFreq","endFreq","power","sweeptime","points","filename"],#include in progress
            x_axis=['frequency'],#default(must be in data columns) if you use ManagedDockWindow, use list of columns
            y_axis=['S21',"S11","S12","S22"],
            sequencer=True,
            sequencer_inputs=['iterations', 'delay',"startFreq","endFreq","power","sweeptime","points","filename"],
            # sequence_file = "gui_sequencer_example.txt",
            directory_input=True,
        )
        self.setWindowTitle('S parameters measurement')
        self.directory = r"C:/Users/Ando_lab/Documents/Haku/measureingSystems"

    def queue(self,procedure=None):
        # filename = tempfile.mktemp()
        directory=self.directory
        # filename = f"{directory}/{}"

        if procedure is None:
            procedure = self.make_procedure()
        filename=unique_filename(directory=directory,procedure=procedure,dated_folder=False,prefix="",suffix="_{memo}_Spara")
        results = Results(procedure, filename)

        experiment = self.new_experiment(results)

        self.manager.queue(experiment)



if __name__ == "__main__":
    netana = AgilentN5222A('GPIB::16')
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
import qcodes
from qcodes.dataset import Measurement
from qcodes import Parameter, ParamSpec
from qcodes.utils.validators import Numbers
from qcodes.instrument.base import Instrument
from qcodes.dataset.data_set import DataSet

from .instrument_drivers.Keithley_6517A import Keithley_6517A

import os
import json
import pandas
import numpy as np
from tqdm import tqdm
from functools import partial
from time import localtime, strftime, sleep

tqdm = partial(tqdm, position=0, leave=True)


class StaircaseSweep(Measurement):
    """
    Make staircase sweep measurement

    ARgs:
        high_res: high resistance mode or not
        experiment: Experiment object
        station: Station object that holds all the instruments
        sample: Sample object
        filepath: filepath to store all the files related to this measurement
    """

    def __init__(self, high_res: bool, experiment, station,
                 sample, name=""):
        super().__init__(experiment, station, name)
        self._mode = ""
        self.high_res = high_res
        # name is empty string here, wil be given after setting up parameters
        self.sample = sample  # instance of Sample class
        self.filepath = self.sample.file_path
        # If high resistance mode is true, check if keithley 6517a is present
        self.instruments = self.station.components

        if self.high_res:
            for name, instr in self.instruments.items():
                if isinstance(instr, Keithley_6517A):
                    self.k6517a = instr
                    self.k6517a_name = name
            if not hasattr(self, 'k6517a'):
                raise RuntimeError(f"Please add Keithley 6517A \
                    to the station, I only have these instruments: \
                    {self.instruments}")

        self.add_before_run(self.door_closed_or_not, args=())

    def set_parameters(self, max_v, step_v, npts_per_step,
                       time_step, num_sweep, start_from='max', relax_time=0):
        """
        Set staircase sweep measurement parameters
        Args:
            max_v: maximum voltage
            step_v: step voltage
            npts_per_step: number of data points per step
            time_step: time of each step
            num_sweep: number of sweeps
            relax_time: relax time after each sweep, set to 0 by default
        """
        Numbers(0, 1000).validate(max_v)
        Numbers(0, max_v).validate(step_v)

        self.sweep_arguments = dict(
            max_v=max_v,
            step_v=step_v,
            npts_per_step=npts_per_step,
            time_step=time_step,
            num_sweep=num_sweep,
            start_from=start_from,
            relax_time=relax_time
        )  # these keys will be converted to a string
        self.get_meas_name()

    def door_closed_or_not(self):
        # Make sure the enclosure door is closed for hazardous voltage
        if self.sweep_arguments["max_v"] >= 36:
            if self.k6517a.interlock() == False:
                raise RuntimeError("Please close the cabinet door before \
                        using hazardous voltage!")

    def print_info(self):
        # print these information before starting sweep
        print("Current working directory: {}".format(os.getcwd()))
        print("Database file path: {}".format(qcodes.config.core.db_location))
        print("Experiment name: {}".format(self.experiment.name))
        print("High resistance mode: {}".format(self.high_res))
        print("Instrument(s): {}".format(self.instruments))
        print("Sample name: {}".format(self.sample.full_name))
        print("Measurement name: {}".format(self.name))

    def log_data(self, dataset: DataSet, data_dict: dict):
        #date = strftime("%Y%m%d", localtime())
        csvname = f"Run_id {dataset.captured_run_id} {dataset.name}" + ".csv"
        csvpath = os.path.join(self.filepath, csvname)
        with open(csvpath, 'a', encoding='utf-8') as f:
            # write information about the measurement
            f.write(f"""
Time, \t{dataset.run_timestamp()}
Database file path, \t{qcodes.config.core.db_location}
Experiment, \t{self.experiment.name}
Staircase Sweep mode, \t{self._mode}
High resistance mode, \t{self.high_res}
Measurement name, \t{self.name}

Sample:
\tSample full name, {self.sample.full_name}
\tContact method, {self.sample.contact_method}
\tProbe distance, {self.sample.probe_distance} mm

Parameters:
""")
            # write the sweep parameters
            for k, v in self.sweep_arguments.items():
                f.write("\t%s,\t%s\n" % (k, v))
            f.write(f"""
\tNominal sweep rate, \t{self.sweep_rate}
\tReal sweep rate, \t{self.real_sweep_rate(dataset)}
            """)
            # write the data
            f.write(f"""\n
Dataset run_id, \t{dataset.captured_run_id}
Dataset guid, \t{dataset.guid}

Data:
            """)
        f.close()
        pandas.DataFrame(data_dict).to_csv(csvpath, mode='a', sep=',')

    def log_run_id(self, dataset: DataSet):
        """
        Record the sample and measurement name and their run-id's.
        """
        filename = self.sample.full_name + "_runid.log"
        filepath = os.path.join(self.filepath, filename)
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(f"{dataset.captured_run_id}:{self._mode}, {self.name}\n")
        f.close()

    def get_meas_name(self):
        """
        Get the measurement name based on given parameters
        """
        params = self.sweep_arguments
        sr = params["step_v"]/params["time_step"]
        self.sweep_rate = str(sr) + ' V/s'
        if not params["step_v"] % params["time_step"]:
            sr_str = str(int(sr))
        else:
            sr_str = str(sr).replace('.', '-')
        sweep_rate_str = sr_str + 'V-s'

        volt_range = str(params["max_v"]) + 'V'
        num_sweep = str(params["num_sweep"]) + ' sweeps'
        start_mode = "start from " + params["start_from"]
        relax = 'relax ' + str(int(params["relax_time"]/60)) + 'mins' if (
            params["relax_time"] != 0) else ''
        params_list = [self.sample.full_name, self.experiment.name,
                       self.sample.contact_method, sweep_rate_str, volt_range,
                       num_sweep, start_mode, relax]
        self.name = "__".join(params_list).strip('_')
        return self.name

    @staticmethod
    def real_sweep_rate(dataset):
        data = dataset.get_parameter_data()
        for key, value in data.items():
            if 'current' in key:
                for k, v in value.items():
                    if 'voltage' in k:
                        voltage = v
            if 'time' in key:
                time = list(value.values())[0]
        sr = np.array([])
        for i in range(len(voltage)):
            idx = np.isfinite(voltage[i]) & np.isfinite(time[i])
            s = np.polyfit(time[i][idx], voltage[i][idx], 1)[0]
            sr = np.append(sr, s)
        real_sr = "{:.2f} V/s".format(np.abs(sr).mean())
        return real_sr


class TSEQStaircaseSweep(StaircaseSweep):
    """
    The built-in function of keithley 6517A
    """

    def __init__(self, high_res: bool, experiment, station,
                 sample, name=""):
        super().__init__(high_res, experiment, station, sample, name)
        self.register_parameter(self.k6517a.tseq_voltage)
        self.register_parameter(self.k6517a.tseq_current)
        self.register_parameter(self.k6517a.tseq_time)
        self._mode = "Test Sequence Staircase Sweep"

    def configure_k6517a(self,
                         sense_function='current',
                         auto_meas_range=True,
                         elements_for_data=(
                             'reading', 'units', 'timestamp', 'vsource'),
                         timestamp_format='relative',
                         current_damping=True):

        self.k6517a.zerocheck(1)
        self.k6517a.datetime_calibrate()
        self.k6517a.preset()
        self.k6517a.sense_function(sense_function)
        self.k6517a.current_damping(current_damping)
        self.k6517a.meter_connect(1)
        self.k6517a.elements_for_data(*elements_for_data)
        self.k6517a.auto_meas_range(auto_meas_range)

        self._auto_range = auto_meas_range
        self.k6517a.timestamp(timestamp_format)
        self.k6517a.tseq_type('stsweep')
        self.k6517a.tseq_trigger_source('immediate')

    def start_sweep(self):
        """
        Start the measuring
        """
        self.print_info()

        self.data_dict = {}

        # initialize the start, stop, and step voltage
        if self.sweep_arguments["start_from"] == 'max':
            start_voltage = self.sweep_arguments["max_v"]
            stop_voltage = -self.sweep_arguments["max_v"]
            step_voltage = -self.sweep_arguments["step_v"]
        elif self.sweep_arguments["start_from"] == '-max':
            start_voltage = -self.sweep_arguments["max_v"]
            stop_voltage = self.sweep_arguments["max_v"]
            step_voltage = self.sweep_arguments["step_v"]
        step_time = self.sweep_arguments["time_step"]

        self._do_sweep(start_voltage, step_voltage, stop_voltage, step_time)

    def _do_sweep(self, start, step, stop, stime):

        with self.run() as datasaver:
            for s in range(self.sweep_arguments['num_sweep']):
                try:
                    print("\n Start sweep No. {}".format(s+1))

                    self.k6517a.tseq_stsweep_start(start)
                    self.k6517a.tseq_stsweep_step(step)
                    self.k6517a.tseq_stsweep_stop(stop)
                    self.k6517a.tseq_stsweep_stime(stime)

                    self.k6517a.tseq_arm()

                    t = 0
                    while t < ((stop-start)//step+1)*(0.8+stime)+10:
                        t += 1
                        sleep(1)
                        print(self.k6517a.read_display_top())

                    voltage = self.k6517a.tseq_voltage()
                    current = self.k6517a.tseq_current()
                    time = self.k6517a.tseq_time()
                    # remove bad points
                    current[current > 1] = np.nan

                    datasaver.add_result((self.k6517a.tseq_voltage, voltage),
                                         (self.k6517a.tseq_current, current),
                                         (self.k6517a.tseq_time, time))
                    self.data_dict.update({
                        f"Current-{s+1}": current,
                        f"Voltage-{s+1}": voltage,
                        f"Time-{s+1}": time
                    })

                    self.k6517a.zerocheck(1)
                    start, step, stop = -start, -step, -stop

                except KeyboardInterrupt:
                    self.k6517a.tseq_abort()
                    self.k6517a.operate(0)
                    print("Stop the test sequence")
                    break
                self.k6517a.operate(0)

            self.dataset = datasaver.dataset
            self.log_data(self.dataset, self.data_dict)
            self.log_run_id(self.dataset)


class CustomizedStaircaseSweep(StaircaseSweep):
    """
    Customized staircase sweep, compared to the built-in test sequence
    staircase sweep
    """

    def __init__(self, high_res: bool, experiment, station,
                 sample, name=""):
        super().__init__(high_res, experiment, station, sample, name)
        self._mode = "Customized Staircase Sweep"
        self.sweep_voltage = Parameter(name='voltage',
                                       label='Voltage',
                                       unit='V')
        self.sweep_time = Parameter(name='time',
                                    label='Time',
                                    unit='s')
        self.sweep_current = Parameter(name='current',
                                       label='Current',
                                       unit='A')
        # by default, register voltage, time, and current for staircase sweep
        self.register_parameter(self.sweep_voltage, paramtype='array')
        self.register_parameter(self.sweep_time, paramtype='array')
        self.register_parameter(self.sweep_current, paramtype='array',
                                setpoints=(self.sweep_voltage,))
        # sweep time is an independent parameter now

    def configure_k6517a(self,
                         sense_function='current',
                         auto_meas_range=True,
                         elements_for_data=(
                             'reading', 'units', 'timestamp', 'vsource'),
                         timestamp_format='relative',
                         current_damping=True):
        """    
        Configure the Keithley 6517A for the staircase sweep measurement

        Args:
            sense_function: by default we source voltage measure current
            auto_meas_range: auto meas range, by default it is False because
                the 2 nA range is problematic
            elements_for_data: by default we only include current reading,
                units, timestamp, and vsource to the raw data string
            timestamp_format: relative to the first data point
        """
        self.k6517a.zerocheck(1)
        self.k6517a.datetime_calibrate()
        # self.k6517a.reset()
        self.k6517a.preset()
        self.k6517a.sense_function(sense_function)
        self.k6517a.current_damping(current_damping)
        self.k6517a.meter_connect(1)
        self.k6517a.res_auto_vsource(0)
        vs_range = 1000 if self.sweep_arguments["max_v"] > 100 else 100
        self.k6517a.res_vsource_range(vs_range)
        self.k6517a.elements_for_data(*elements_for_data)
        self.k6517a.auto_meas_range(auto_meas_range)

        # here we define a internal variable to record the state of
        # auto_meas_range every time we change it, by default it's True
        self._auto_range = auto_meas_range

        self.k6517a.timestamp(timestamp_format)
        # self.k6517a.meas_range(2e-9)
        self.k6517a.zerocheck(0)

    def start_sweep(self):
        """
        Start the measuring
        """
        self.print_info()

        # initialize the data list
        self.current = np.array([])
        self.time = np.array([])
        self.voltage = np.array([])
        self.data_dict = {}

        # initialize the start, stop, and step voltage
        if self.sweep_arguments["start_from"] == 'max':
            start_voltage = self.sweep_arguments["max_v"]
            stop_voltage = -self.sweep_arguments["max_v"]
            step_voltage = -self.sweep_arguments["step_v"]
        elif self.sweep_arguments["start_from"] == '-max':
            start_voltage = -self.sweep_arguments["max_v"]
            stop_voltage = self.sweep_arguments["max_v"]
            step_voltage = self.sweep_arguments["step_v"]

        self._do_sweep(start_voltage, step_voltage, stop_voltage)

        self.k6517a.res_vsource_operate(0)

    def _do_sweep(self, start, step, stop):

        with self.run() as datasaver:
            for i in range(self.sweep_arguments['num_sweep']):
                print("\n Start sweep No. {}".format(i+1))
                current, time, voltage = self._single_run(start, step, stop)
                # if relax time is not zero, turn off the voltage source now
                if self.sweep_arguments["relax_time"] != 0:
                    self.k6517a.res_vsource_operate(0)

                # append single run data to data array
                # if i == 0:
                #     self.current, self.time, self.voltage = (
                #         current, time, voltage)
                # else:
                #     self.current = np.vstack((self.current, current))
                #     self.time = np.vstack((self.time, time))
                #     self.voltage = np.vstack((self.voltage, voltage))

                # append single run data to data dictionary
                self.data_dict.update({
                    f"Current-{i+1}": current,
                    f"Voltage-{i+1}": voltage,
                    f"Time-{i+1}": time
                })

                # sweep back
                start, step, stop = -start, -step, -stop

            # data list saved to database file
                datasaver.add_result((self.sweep_current, current),
                                     (self.sweep_voltage, voltage),
                                     (self.sweep_time, time)
                                     )
            self.dataset = datasaver.dataset
            self.log_data(self.dataset, self.data_dict)
            self.log_run_id(self.dataset)

    def _single_run(self, start, step, stop):
        """
        Do single sweep. Be careful, don't name this method as run(), because
        run() method already exists in qcodes and it returns a Runner object
        """
        # empty nummpy array to store data for one single sweep
        _curr, _volt, _time = [], [], []

        # when change to 200 pA range the next two or three points are bad,
        # need to remove them
        # flag200pAidx = None
        # sometimes the current is stuck to 142 pA
        flag142pA = 0
        flag142pAidx = []
        # make sure vsource range is correct
        if abs(stop) > 100 and float(self.k6517a.res_vsource_range()) <= 100:
            self.k6517a.res_vsource_range(1000)
        # sweep from start to stop
        self.k6517a.res_vsource_operate(1)
        self._meas_range = float(self.k6517a.meas_range())
        for v in tqdm(np.arange(start, stop, step)):
            self.k6517a.res_vsource_level(v)
            i = 0
            # data list for one reading
            c, t = [], []
            while i < self.sweep_arguments["npts_per_step"]:
                sleep(self.sweep_arguments["time_step"])
                dat = self.k6517a.get_data(tseq=False)
                ci = dat['reading']
                ti = dat['timestamp']
                c.append(ci[0])
                t.append(ti[0])
                i += 1

            # absolute value of reading
            absr = np.abs(c[0])
            mr_now = self._meas_range
            # if 0.5e-9<absr<2.5e-9:
            #     if self._auto_range:
            #         self.k6517a.auto_meas_range(0)
            #         self._auto_range = False
            #         self.k6517a.meas_range(2e-8)
            # else:
            #     if not self._auto_range:
            #         self.k6517a.auto_meas_range(1)
            #         self._auto_range = True
            if self._auto_range == False:
                # Change the measure range when necessary
                # mr_now: measure range now
                # get the floor and ceiling measure range of the current reading
                flr = 2*10**(np.floor(np.log10(absr/2)))
                cer = 2*10**(np.ceil(np.log10(absr/2)))
                # if the measure range is too large the reading can be zero,
                # then we search suitable range from 20 pA,
                if flr < 2e-15:
                    flr = 2e-13
                if cer < 2e-15:
                    cer = 2e-11

                cer = cer*10 if (cer == 2e-9 and absr > 0.8e-9) else cer
                #flr = flr/10 if flr == 2e-9 else flr
                # current measure range too large for the reading
                if mr_now > cer:
                    # this usually happens for current absolute value change from
                    # large to small, which is the following condition:
                    # if (step>0 and c[0]<0) or (step<0 and 1>c[0]>0):
                    # then we narrow down the measure range
                    self.k6517a.meas_range(cer)
                    self._meas_range = cer
                    # when measure range change from 2e-8 to 2e-10,
                    # the next 3 points are usually bad
                    # flag200pAidx = int((v-start)/step) if cer == 2e-10 else None
                # current exceeds the mr_now
                elif mr_now <= flr:
                    # this usually happens for current absolute value change from
                    # small to large, there are two conditions:
                    # 1. current exceeds but not oveflow
                    if (0 < absr < 1):
                        self.k6517a.meas_range(cer)
                        self._meas_range = cer
                    # 2. current overflow
                    elif absr > 1:
                        if mr_now <= 2e-3:
                            self.k6517a.meas_range(mr_now*10)
                            self._meas_range = mr_now*10

                if round(mr_now*10**10) == 2:
                    if 1.4e-10 <= absr <= 1.44e-10:
                        flag142pA += 1
                        flag142pAidx.append(int((v-start)/step))
                    if flag142pA >= 5:
                        self.k6517a.meas_range(2e-9)
                        self._meas_range = 2e-9

            # add data points to list
            for i in range(len(c)):
                _curr.append(c[i])
                _volt.append(v)
                _time.append(t[i])

        # convert to numpy array
        current = np.array(_curr)
        voltage = np.array(_volt)
        time = np.array(_time)
        # remove the next two points when changing measure range from 20 nA
        # to 200 pA
        if flag142pA >= 5:
            for i in flag142pAidx:
                current[i] = np.nan
                time[i] = np.nan
                voltage[i] = np.nan
        # remove bad points, (usually infinite values)
        current[current > 1] = np.nan

        return current, time, voltage

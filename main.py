# %% import modules
import sys
if not "C:\\Users\\Lapo\\kfm\\Measurement" in sys.path:
    sys.path.insert(1,"C:\\Users\\Lapo\\kfm\\Measurement")

import os
import qcodes
from qcodes.dataset.sqlite.database import initialise_or_create_database_at
from qcodes.station import Station
from qcodes.instrument.base import Instrument
from qcodes import load_or_create_experiment

from hrms.instrument_drivers.Keithley_6517A import Keithley_6517A
from hrms.sample import Sample
from hrms.experiment import staircase_sweep
from hrms.measurement import CustomizedStaircaseSweep, TSEQStaircaseSweep
from hrms.plotting import plot_by_meas, plot_by_id, plot_av_by_meas, plot_av_by_id

qcodes.config.logger.start_logging_on_import = 'always'
os.chdir("C:/Users/Lapo/kfm/Measurement")
qcodes.config.save_to_cwd()

# %% Specify the sample information
sp = Sample(name="Nothing",
            label=1,
            contact_method='pad',
            probe_distance=1)
print(sp)

sp.create_database()

# %% Set parameters
max_v = 800
step_v = 2
npts_per_step = 1
time_step = 1
num_sweep = 2

stsweep_mode = 'customized'
#stsweep_mode = 'tseq'

auto_meas_range = False

# %% Create experiment, instrument, station, and measurement object
exp = staircase_sweep(sp)
#exp = load_or_create_experiment("test_new_code",sample_name=sp.full_name)

station = Station()
Instrument.close_all()
k = Keithley_6517A('keithley6517a', 'GPIB0::15::INSTR')
station.add_component(k)

# %% create measurement object
if stsweep_mode == 'customized':
    meas = CustomizedStaircaseSweep(sample=sp,
                                    station=station,
                                    experiment=exp,
                                    high_res=True)
elif stsweep_mode == 'tseq':
    meas = TSEQStaircaseSweep(sample=sp,
                              station=station,
                              experiment=exp,
                              high_res=True)

# %% setup parameters and configure keithley

meas.set_parameters(
    max_v=max_v,
    step_v=step_v,
    npts_per_step=npts_per_step,
    time_step=time_step,
    num_sweep=num_sweep
)

meas.configure_k6517a(auto_meas_range=auto_meas_range)
# %% start sweep
meas.start_sweep()

# %% plot dataset
if k.operate():
    k.operate(False)
plot_by_meas(meas, scatter=False)

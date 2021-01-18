#%% 

import os
os.chdir("C:/Users/Lapo/kfm/Github/hrms")

import qcodes
from qcodes.dataset.sqlite.database import initialise_or_create_database_at
from qcodes.station import Station
from qcodes.instrument.base import Instrument

from instrument_drivers.Keithley_6517A import Keithley_6517A
from sample import Sample
from experiment import staircase_sweep
from measurement import MeasureStaircaseSweep
from plotting import plot_by_meas, plot_by_id

qcodes.config.logger.start_logging_on_import = 'always'
os.chdir("C:/Users/Lapo/kfm/Measurement")
qcodes.config.save_to_cwd()

#%% Specify the sample information
sp = Sample(name = "Dy-NIT", 
            label = 2, 
            contact_method = 'sliver_paste',
            probe_distance = 1)
print(sp)

filepath = os.path.join(os.getcwd(), f"{sp.name}\\{sp.full_name}")

#%% Set parameters
max_v = 950
step_v = 1
npts_per_step = 1
time_step = 1
num_sweep = 2

#%% Create experiment, instrument, station, and measurement object
exp = staircase_sweep(sp)
station = Station()
Instrument.close_all()
k = Keithley_6517A('keithley6517a', 'GPIB0::15::INSTR')
station.add_component(k)

db_path = os.path.join(filepath, f"{sp.full_name}.db")
#%%
initialise_or_create_database_at(db_path)

#%%
meas = MeasureStaircaseSweep(sample=sp,
                             station=station,
                             experiment=exp,
                             high_res=True,
                             filepath=filepath)

#%% 

meas.set_parameters(
    max_v=max_v,
    step_v = step_v,
    npts_per_step = npts_per_step,
    time_step = time_step,
    num_sweep = num_sweep
)

meas.configure_k6517a(auto_meas_range=True)
#%%
meas.start_sweep()

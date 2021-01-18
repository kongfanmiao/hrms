"""
Experiment object imported from qcodes.
"""
from typing import Union

from qcodes import load_or_create_experiment
from qcodes.dataset.experiment_container import Experiment
from qcodes.dataset.sqlite.database import get_DB_location

from sample import Sample

def staircase_sweep(sample: Union[str, Sample], 
                    expname = 'staircase_sweep',
                    **kwargs) -> Experiment:
    
    if isinstance(sample, Sample):
        spname = sample.full_name
    elif isinstance(sample, str):
        spname = sample
    return load_or_create_experiment(expname, spname, **kwargs)
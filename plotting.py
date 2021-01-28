import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from typing import Optional, Union

from qcodes.dataset.data_set import load_by_id, load_by_run_spec
#from qcodes.dataset.sqlite.database import connect

from .measurement import MeasureStaircaseSweep
from .sample import Sample


unit_map = {3: r'$mA$',
            6: r'$\mu A$',
            9: r'$nA$',
            12: r'$pA$'}

def plot_by_meas(meas, **kwargs):
    """
    Args:
        meas: Measurement object
        kwargs: other optional arguments for matplotlib.pyplot
    """
    dataset = meas.dataset
    figtitle = f"Run id: {dataset.captured_run_id}\n" + meas.name + '\n'
    figname = f"Run_id {dataset.captured_run_id} {meas.name}"
    figpath = os.path.join(meas.filepath, figname)

    plot(dataset, figpath, figtitle, **kwargs)


def plot_by_id(run_id,
               sample: Optional[Union[Sample, str]]=None,
               **kwargs):

    if sample is None:
        dataset = load_by_id(run_id)
        sample_name = dataset.sample_name
    else:
        if isinstance(sample, Sample):
            sample_name = sample.full_name
        elif isinstance(sample, str):
            sample_name = sample
        dataset = load_by_run_spec(sample_name=sample_name,
                                   captured_run_id=run_id)
    
    figtitle = f"Run id: {run_id}\n" + dataset.name + '\n'
    figname = f"Run_id {run_id}\n" + dataset.name
    db_path = dataset.path_to_db
    figpath = os.path.join(os.path.dirname(db_path), figname)

    plot(dataset, figpath, figtitle, **kwargs)


def plot_av_by_meas(meas, **kwargs):

    dataset = meas.dataset
    figtitle = '{} AVERAGE\n'.format(meas.name)
    figname = meas.name + " AVERAGE"
    figpath = os.path.join(meas.filepath, figname)

    plot_av(dataset, figpath, figtitle, **kwargs)


def plot_av_by_id(run_id,
               sample: Optional[Union[Sample, str]]=None,
               **kwargs):

    if sample is None:
        dataset = load_by_id(run_id)
        sample_name = dataset.sample_name
    else:
        if isinstance(sample, Sample):
            sample_name = sample.full_name
        elif isinstance(sample, str):
            sample_name = sample
        dataset = load_by_run_spec(sample_name=sample_name,
                                   captured_run_id=run_id)
    
    figtitle = '{} AVERAGE\n'.format(dataset.name)
    figname = dataset.name + " AVERAGE"
    db_path = dataset.path_to_db
    figpath = os.path.join(os.path.dirname(db_path), figname)

    plot_av(dataset, figpath, figtitle, **kwargs)


def plot(dataset, figpath, figtitle,
         ticksfont=24, titlefont=24, legendfont=18,
         lg_border_linewidth=1, figsize=(15,15), **kwargs):
    """

    """
    current = dataset.get_parameter_data()['current']['current'][0]
    voltage = dataset.get_parameter_data()['current']['voltage'][0]
    #time = dataset['current']['time']

    matplotlib.rcParams["axes.linewidth"] = 2
    plt.figure(figsize=figsize)
    plt.xlabel('Voltage (V)', fontsize=ticksfont)
    yscale = _auto_yscale(current)
    plt.ylabel(f'Current ({unit_map[yscale]})', fontsize=ticksfont)
    plt.title(figtitle, fontsize=titlefont)

    def _plot(i:int, **kwargs):
        c = current[i]
        v = voltage[i]
        #t = time[i]
        numdict = {1: '$1^{st}$', 2: '$2^{nd}$', 3: '$3^{rd}$'}
        label = "The {} {} sweep"
        if i % 2:
            if i <= 5:
                label = label.format(numdict[(i + 1) / 2], 'backward')
            else:
                label = label.format(f'{i // 2 + 1}' + '$^{th}$', 'backward')
        else:
            if i <= 4:
                label = label.format(numdict[1 + (i / 2)], 'forward')
            else:
                label = label.format(f'{i // 2 + 1}' + '$^{th}$', 'forward')
        plt.plot(v,c*10**yscale, label=label, **kwargs)
    
    for i in range(current.shape[0]):
        _plot(i, **kwargs)
    
    plt.xticks(fontsize=ticksfont)
    plt.yticks(fontsize=ticksfont)
    legend = plt.legend(fontsize=legendfont)
    legend.get_frame().set_linewidth(lg_border_linewidth)
    legend.get_frame().set_edgecolor("black")
    
    plt.savefig(figpath)


def plot_av(dataset, figpath, figtitle,
            ticksfont=24, titlefont=24, legendfont=18,
            lg_border_linewidth=1, figsize=(15,15), **kwargs):

    current = dataset.get_parameter_data()['current']['current'][0]
    voltage = dataset.get_parameter_data()['current']['voltage'][0]
    current_av = np.nanmean(current, 0)
    voltage_av = np.nanmean(voltage, 0)

    matplotlib.rcParams["axes.linewidth"] = 2
    plt.figure(figsize=figsize)
    plt.xlabel('Voltage (V)', fontsize=ticksfont)
    yscale = _auto_yscale(current_av)
    plt.ylabel(f'Current ({unit_map[yscale]})', fontsize=ticksfont)
    plt.title(figtitle, fontsize=titlefont)

    plt.plot(voltage_av, current_av)
    plt.xticks(fontsize=ticksfont)
    plt.yticks(fontsize=ticksfont)

    plt.savefig(figpath)
    

def _auto_yscale(yarray):
    
    yarray = yarray[np.logical_not(np.isnan(yarray))]
    scale = int(np.ceil(np.abs(np.log10(np.abs(yarray).max()))/3)*3)
    return scale

    

import os
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from typing import Optional, Union

from qcodes.dataset.data_set import load_by_id, load_by_run_spec
#from qcodes.dataset.sqlite.database import connect

#from .measurement import StaircaseSweep
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

    plot_ds(dataset, figpath=figpath, figtitle=figtitle, **kwargs)


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

    plot_ds(dataset, figpath=figpath, figtitle=figtitle, **kwargs)


def plot_av_by_meas(meas, **kwargs):

    dataset = meas.dataset
    figtitle = '{} \nAVERAGE\n'.format(meas.name)
    figname = meas.name + " AVERAGE"
    figpath = os.path.join(meas.filepath, figname)

    plot_av_ds(dataset,figpath=figpath, figtitle=figtitle, **kwargs)


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
    
    figtitle = '{} \nAVERAGE\n'.format(dataset.name)
    figname = dataset.name + " AVERAGE"
    db_path = dataset.path_to_db
    figpath = os.path.join(os.path.dirname(db_path), figname)

    plot_av_ds(dataset, figpath=figpath, figtitle=figtitle, **kwargs)


def plot_ds(dataset, **kwargs):
    """
    Plot the dataset
    """
    current, voltage, _ = extract_data(dataset)
    plot(voltage, current, **kwargs)


def plot_av_ds(dataset, **kwargs):
    """
    Plot the averaged data of datasets
    """
    current, voltage, _ = extract_data(dataset)
    plot_av(voltage, current, **kwargs)


def extract_data(dataset):
    data = dataset.get_parameter_data()
    for key, value in data.items():
        if 'current' in key:
            for k, v in value.items():
                if 'voltage' in k:
                    voltage = v
                if 'current' in k:
                    current = v
                # this is the old dataset framework
                if "time" in k:
                    time = v
        # this is the new dataset framework
        if 'time' in key:
            time = list(value.values())[0]
    return current, voltage, time


def plot(x, y, figtitle, figpath=None, 
         ticksfont=18, titlefont=20, legendfont=10,
         lg_border_linewidth=1, figsize=(10,8), bbox_to_anchor=(1.4,1),
         scatter=False, save=False, **kwargs):
    """
    The low level method of plot
    """

    matplotlib.rcParams["axes.linewidth"] = 2
    plt.figure(figsize=figsize)
    plt.xlabel('Voltage (V)', fontsize=ticksfont)
    yscale = _auto_yscale(y)
    plt.ylabel(f'Current ({unit_map[yscale]})', fontsize=ticksfont)
    plt.title(figtitle, fontsize=titlefont)

    # in the old framework all data are added as one element of an array
    if len(y) == 1:
        x, y = x[0], y[0]

    def _plot(i:int, **kwargs):
        c = y[i]
        v = x[i]
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
        if scatter== False:
            plt.plot(v,c*10**yscale, label=label, **kwargs)
        else:
            plt.scatter(v,c*10**yscale, label=label, **kwargs)
    
    for i in range(y.shape[0]):
        _plot(i, **kwargs)
    
    plt.xticks(fontsize=ticksfont)
    plt.yticks(fontsize=ticksfont)
    legend = plt.legend(fontsize=legendfont,
                        bbox_to_anchor=bbox_to_anchor)
    legend.get_frame().set_linewidth(lg_border_linewidth)
    legend.get_frame().set_edgecolor("black")
    
    if save:
        if not figpath:
            raise KeyError("Please provide a figurepath to save your figure")
        plt.savefig(figpath)


def plot_av(x, y, figtitle, figpath=None,
            ticksfont=18, titlefont=20, legendfont=10,
            lg_border_linewidth=1, figsize=(10,8),
            scatter=False, save=False,**kwargs):

    if len(y) == 1:
        y = y[0]
        x = x[0]
    current_fw = y[0::2]
    current_fw_av = np.nanmean(current_fw, 0)
    current_bw = y[1::2]
    current_bw_av = np.nanmean(current_bw, 0)
    voltage_fw_av = x[0,:]
    voltage_bw_av = x[1,:]

    matplotlib.rcParams["axes.linewidth"] = 2
    plt.figure(figsize=figsize)
    plt.xlabel('Voltage (V)', fontsize=ticksfont)
    yscale = _auto_yscale(current_fw_av)
    plt.ylabel(f'Current ({unit_map[yscale]})', fontsize=ticksfont)
    plt.title(figtitle, fontsize=titlefont)

    if scatter:
        plt.scatter(voltage_fw_av, current_fw_av*10**yscale,
                    label="Forward Average")
        plt.scatter(voltage_bw_av, current_bw_av*10**yscale,
                    label="Forward Average")
    else:
        plt.plot(voltage_fw_av, current_fw_av*10**yscale,
                 label="Forward Average")
        plt.plot(voltage_bw_av, current_bw_av*10**yscale,
                 label="Backward Average")

    plt.xticks(fontsize=ticksfont)
    plt.yticks(fontsize=ticksfont)
    plt.legend()

    if save:
        if not figpath:
            raise KeyError("Please provide a figurepath to save your figure")
        plt.savefig(figpath)
    

def _auto_yscale(yarray):
    
    yarray = yarray[np.logical_not(np.isnan(yarray))]
    scale = int(np.ceil(np.abs(np.log10(np.abs(yarray).max()))/3)*3)
    return scale

    

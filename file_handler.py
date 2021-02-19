from qcodes.dataset.data_set import load_by_id
from qcodes.dataset.data_set import DataSet

import numpy as np
import pandas
import xlsxwriter


def write_excel(what, file):
    # provide the run id
    if isinstance(what, int):
        ds = load_by_id(what)
        data = ds.get_parameter_data()
        current = data["current"]["current"]
        voltage = data["current"]["voltage"]
    # provide the DataSet object
    elif isinstance(what, DataSet):
        data = what.get_parameter_data()
        current = data["current"]["current"]
        voltage = data["current"]["voltage"]
    # provide the voltage and current array (voltage, current) or [voltage, current]
    elif isinstance(what, (tuple, list)) & isinstance(what[0], np.ndarray):
        current = what[1]
        voltage = what[0]

    if len(current) == 1:
        current = current[0]
        voltage = voltage[0]

    dict_lin = {}
    dict_lin_half = {}
    dict_log = {}
    dict_log_half = {}
    num = len(current)

    for i in range(num):
        voltage[i][voltage[i] == 0] = np.nan
        volt = voltage[i]
        curr = current[i]
        dict_lin.update({f"V-{i+1}": volt,
                         f"I-{i+1}": curr})

        dict_log.update({f"logV-{i+1}": np.multiply(1-2*np.less(volt, 0, where=~np.isnan(volt)), np.log10(np.abs(volt))),
                         f"logI-{i+1}": np.log10(np.abs(curr))})

        volth = volt.copy()
        currh = curr.copy()
        if i % 2:
            volth[np.greater(volth, 0, where=~np.isnan(volth))] = np.nan
            currh[np.greater(volth, 0, where=~np.isnan(volth))] = np.nan
        else:
            volth[np.less(volth, 0, where=~np.isnan(volth))] = np.nan
            currh[np.less(volth, 0, where=~np.isnan(volth))] = np.nan
        dict_lin_half.update({f"V-{i+1}": volth,
                              f"I-{i+1}": currh})
        dict_log_half.update({f"logV-{i+1}": np.multiply(1-2*np.less(volth, 0, where=~np.isnan(volth)), np.log10(np.abs(volth))),
                              f"logI-{i+1}": np.log10(np.abs(currh))})

    pd_lin = pandas.DataFrame(dict_lin)
    pd_lin_half = pandas.DataFrame(dict_lin_half)
    pd_log = pandas.DataFrame(dict_log)
    pd_log_half = pandas.DataFrame(dict_log_half)

    with pandas.ExcelWriter(file, engine='xlsxwriter') as writer:
        pd_lin.to_excel(writer, sheet_name="linear", index=False)
        pd_lin_half.to_excel(writer, sheet_name="linear half", index=False)
        pd_log.to_excel(writer, sheet_name="log", index=False)
        pd_log_half.to_excel(writer, sheet_name="log half", index=False)

    return pd_lin, pd_lin_half, pd_log, pd_log_half

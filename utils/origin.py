import os

def write_excel2origin_script(sample_name, path, files):
    """
    This method create the script for importing data in the embeded Python of 
    Origin. Open Origin and click code builder, open this script file and run it,
    then it will import the data from the specified excel files.
    """
    path = os.path.normpath(path)
    path = path.replace('\\', '\\\\')
    with open(os.path.join(path, "excel2origin.py"), 'w') as py:
        py.write(f"""

import os
import pandas as pd
import originpro as op

spname = "{sample_name}"
path = "{path}"
files = {files}

def shorten_string(s:str):
    s = s.replace('_', '')
    s = s.replace('-', '')
    s = s.replace(' ', '')
    return s

for f in files:
    # for each excel file, create a origin workbook
    # Firstly, create the short name and long name for workbook
    # the file name is flexible, it can have or doesn't have the suffix ".xlsx"
    if f.endswith('.xlsx'):
        wb_lname = f[:-5]
    else:
        wb_lname = f
        # correct file name should contain suffix in order to open it
        f += '.xlsx'
    wb_sname = shorten_string(wb_lname)

    # Make sure a good short name is provided
    if not op.project._is_good_sn(wb_sname):
        raise ValueError(f"The short name for workbook: {{wb_sname}} is not good,\
                         please check the file name and provide a valid one")

    # create the workbook
    wb = op.find_book('w', name=wb_sname)
    if not wb:
        wb = op.new_book('w', wb_sname)
        wb.lname = wb_lname
    
    # read excel data and save as pandas dataframe
    fex = pd.ExcelFile(os.path.join(path,f), engine='openpyxl')
    # create origin worksheets for for the sheets in the excel file
    for sh in fex.sheet_names:
        df = pd.read_excel(os.path.join(path,f), sheet_name=sh, engine="openpyxl")
        try:
            wks = wb[sh]
            wks.from_df(df)
        except TypeError:
            wks = wb.add_sheet(name=sh)
            wks.from_df(df)
        # set columns axes
        wks.cols_axis('XY', repeat=True)
""")
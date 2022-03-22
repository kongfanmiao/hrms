import numpy as np
import json
import os
import sys
import pkg_resources as pkgr
from typing import Dict


# class NumpyEncoder(json.JSONEncoder):
#     def default(self, obj):
#         if isinstance(obj, np.ndarray):
#             return obj.tolist()
#         if type(obj) == int32:
#             return str(obj)
#         return json.JSONEncoder.default(self, obj)


class ConfigBase():
    pass


class ConfigInstrument(ConfigBase):

    def __init__(self, path: str):
        self.path = path
        # self.k_js_path = os.path.join(self.path, self.k6517a_snapshot)
        # self.k_log_path = os.path.join(self.path, self.k6517a_snapshot_rdb)
        # # load file or create empty file when instantiate StationConfig
        # self.k_snapshot = self.load_or_create_file(self.k_js_path)
        # self.k_snapshot_rdb = self.load_or_create_file(self.k_log_path)

    @staticmethod
    def load_file(path: str):
        with open(path, 'r') as f:
            if path.endswith('.json'):
                content = json.load(f)
            else:
                content = f.readlines()
        return content

    def load_or_create_file(self, path: str):
        try:
            content = self.load_file(path)
        except FileNotFoundError:
            content = ''
            with open(path, 'w') as f:
                f.write(content)
        return content

    def write_file(self, path: str, content=None, from_print=False, print_func=None):
        temp = sys.stdout
        with open(path, 'w') as f:
            if path.endswith('.json'):
                assert isinstance(content, Dict)
                dump = json.dumps(content, indent=4, cls=NumpyEncoder)
                f.write(dump)
            else:
                if from_print:
                    sys.stdout = f
                    print_func()
                    sys.stdout = temp
                else:
                    f.write(content)


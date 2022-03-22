# from qcodes import Station
# from .configuration.config import StationConfig


# class CachedStation(Station):
#     def __init__(self):
#         super().__init__()
#         self.config = StationConfig()
#         # try to read snapshot from json file
#         self.station_snapshot = self.config.st_snapshot
#         # update during the instantiation only when json file is empty
#         # if json file is not empty, then the json will be updated every time 
#         # when configure method is called from measurement class
#         self.update = False if self.station_snapshot else True
        
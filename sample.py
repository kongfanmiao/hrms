"""

"""



class Sample():
    """

    """
    def __init__(self, name:str, label:int, 
                 contact_method, probe_distance):
        self.name = name
        self.label = label
        self.orientation = None
        self.contact_method = contact_method
        self.probe_distance = probe_distance

    @property
    def full_name(self):
        """
        Sample name + label
        """
        spname = self.name
        spname += '-0' if self.label < 10 else '-'
        spname += str(self.label)
        return spname

    # @property
    # def contact_method(self):
    #     """
    #     Probes directlly contact the sample or using siver paste
    #     """
    #     try:
    #         return self._contact_method
    #     except:
    #         raise NameError("Please specify the probe contact method")

    # @contact_method.setter
    # def contact_method(self, method:str):
    #     self._contact_method = method

    # @property
    # def probe_distance(self):
    #     """
    #     The distance between two probes
    #     Here we consider two probes measurement. Need to update for four-probe measurement
    #     """
    #     try:
    #         return self._probe_distance
    #     except:
    #         raise NameError("Please specify the distance between two probes")

    # @probe_distance.setter
    # def probe_distance(self, dist:float):
    #     # by default, the unit is mm
    #     self._probe_distance = str(dist) + ' mm'


    def __str__(self):
        s = f"""
Compound: {self.name}
Label: {self.label}
Sample name: {self.full_name}
Contact method: {self.contact_method}
Probe distance: {self.probe_distance} mm
"""
        return s
    
    

    



    


    
import os

from qcodes.dataset.sqlite.database import initialise_or_create_database_at


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
    

    @property
    def file_path(self):
        """
        The folder for a specific sample
        """
        try:
            return self._file_path
        except:
            raise NameError("Please specify the file path")


    @file_path.setter
    def file_path(self, filepath):
        self._file_path = filepath
    

    def create_database(self):
        if not os.path.exists(f"./{self.name}/{self.full_name}"):
            os.makedirs(f"./{self.name}/{self.full_name}", exist_ok=True)
        filepath = os.path.join(os.getcwd(), f"{self.name}\\{self.full_name}")
        self.file_path = filepath
        db_path = os.path.join(filepath, f"{self.full_name}.db")
        initialise_or_create_database_at(db_path)


    def __str__(self):
        s = f"""
Compound: {self.name}
Label: {self.label}
Sample name: {self.full_name}
Contact method: {self.contact_method}
Probe distance: {self.probe_distance} mm
"""
        return s
    
    

    



    


    
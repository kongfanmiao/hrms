from qcodes import VisaInstrument, Parameter, ParameterWithSetpoints
from qcodes.utils.validators import Enum, Ints, Numbers, Arrays,\
                                    Strings, Nothing, MultiType
from qcodes.utils.helpers import create_on_off_val_mapping

from typing import Optional, Dict, Union

from functools import partial
import numpy as np
from datetime import datetime


class Keithley_6517A(VisaInstrument):
    """
    The QCoDeS driver for Keithley_6517A high resistance electrometer.
    """
    def __init__(self, name, address, **kwargs):
        """
        Args:
            name (str): The name used internally by qcodes in the datset.
            address (str): The VISA device address.
        
        """
        super().__init__(name, address, terminator='\n', **kwargs)
        
        # Create a map for all the front panel keys in Keithley 6517A.
        # In case a fucntion of keithely 6517A is not defined in this driver.
        # You can still use the self.pree_key() as a backup method.
# =============================================================================
#         key_numbers = [i for i in range(1, 24)] + [i for i in range(26, 32)]
#         key_parameters = ('Range Up Arrow', 'V-Source Up Arrow', 'Left Arrow', 
#                           'MENU', 'Q', 'FILTER', 'LOCAL', 'PREV', 'AUTO', 
#                           'Right Arrow', 'EXIT', 'CARD', 'MATH', 'STORE', 'V',
#                           'NEXT', 'Range Down Arrow', 'ENTER', 'OPER', 'TRIG',
#                           'RECALL', 'I', 'Z-CHK', 'V-Source Down', 'SEQ', 
#                           'CONFIG', 'R', 'REL', 'INFO')
#         self.front_panel_keys_map = dict(zip(key_parameters, key_numbers))
# =============================================================================

        self.elements_list = {'reading': 'READ', 'status': 'STAT',
                              'reading number': 'RNUM', 'units': 'UNIT',
                              'timestamp': 'TST', 'humidity': 'HUM',
                              'channel': 'CHAN', 'temperature': 'ETEM',
                              'vsource': 'VSO'}
        # 'None' changes nothing
        self.inv_elements_list = {v: k for k, v in self.elements_list.items()}

        # The resistance function has two ranges, corresponding to the 
        # Auto and Manual Vsource respectively.
        self.sense_function_map = {'voltage': ('"VOLT:DC"', 
                                               Numbers(0, 210), 'V'),
                                   'current': ('"CURR:DC"', 
                                               Numbers(0, 21e-3), 'A'),
                                   'resistance': ('"RES"',
                                                  (Numbers(0, 100e18),
                                                   Numbers(0, 21e3)), 'Ohm'),
                                   'charge': ('"CHAR"',
                                              Numbers(0, 2.1e-6), 'C')}

        # This parameters map is specially for resistivity measurement,
        # Which belongs to 'resistance' sense mode.
        self.resistivity_mapping = {
            'fixture': ('FSELect', 'select test fixture',
                        Enum('M8009', 'USER'), ''),
            'thickness': ('STHickness', 'sample thickness (volume mode)',
                          Numbers(0.0001, 99.9999), 'mm'),
            'Ks': ('KSURface', 'Ks parameter',
                   Numbers(0.001, 999.999), ''),
            'Kv': ('KVOLume', 'Kv parameter',
                   Numbers(0.001, 999.999), '')
            }

        # The frame of tseq_mapping:
        # tseq_name: (tseq_name_raw, tseq_name_label,
        #             {'tseq_name_parameter: (parameter_rawname, parameter_label,
        #                                     Validators(), parameter_unit)})}

        # The following test are not included in this driver:
        # 'DLEakage', 'Diode Leakage Test'
        # 'CLEakage', 'Capacitor Leakage Test'
        # 'CIResistance', 'Cable Insulation Resistance Test'
        # 'RVCoefficient', 'Resistor Voltage Coefficient Test'
        # 'SIResistivity', 'Surface Insulation Resistance Test'),

        vals1 = Numbers(0, 99999.9)
        vals2 = Numbers(0, 9999.9)
        vals3 = Numbers(-1000, 1000)

        # This mapping includes all the information (name, label, validators,
        # and unit) about the parameters of all the test sequences types
        # that may be commonly used (surface and volume resistivity, square
        # sweep, staircase sweep, and alternating polarity sequence).
        self.tseq_mapping = {
            'sresistivity': ('SRES', 'Surface Resistivity Test',
                             {'spdtime': ('PDTime', 'pre-discharge time',
                                          vals1, 's'),
                              'ssvoltage': ('SVOLtage', 'bias voltage',
                                            vals3, 'V'),
                              'sstime': ('STIMe', 'bias time',
                                         vals1, 's'),
                              'smvoltage': ('MVOLtage', 'measure voltage',
                                            vals3,'V'),
                              'smtime': ('MTIMe', 'measure time',
                                         vals2, 's'),
                              'sdtime': ('DTIMe', 'discharge time',
                                         vals1, 's')}),
            'vresistivity': ('VRES', 'Volume Resistivity Test',
                             {'vpdtime': ('PDTime', 'pre-discharge time',
                                          vals1, 's'),
                              'vsvoltage': ('SVOLtage', 'bias voltage',
                                            vals3, 'V'),
                              'vstime': ('STIMe', 'bias time',
                                         vals1, 's'),
                              'vmvoltage': ('MVOLtage', 'measure voltage',
                                            vals3,'V'),
                              'vmtime': ('MTIMe', 'measure time',
                                         vals2, 's'),
                              'vdtime': ('DTIMe', 'discharge time',
                                         vals1, 's')}),
            'sqsweep': ('SQSW', 'Square Wave Sweep Test',
                        {'hlevel': ('HLEVel', 'high level voltage',
                                    vals3, 'V'),
                         'htime': ('HTIMe', 'high level time',
                                   vals2, 's'),
                         'llevel': ('LLEVel', 'low level voltage',
                                    vals3, 'V'),
                         'ltime': ('LTIMe', 'low level time',
                                   vals2, 's'),
                         'count': ('COUNt', 'cycle count',
                                   Ints(0, 3500), '')}), 
                         # The count depends on the buffer capacity,
                         # refer to Table 2-22
            'stsweep': ('STSW', 'Staircase Sweep Test',
                        {'start': ('STARt', 'start voltage',
                                   vals3, 'V'),
                         'step': ('STEP', 'step voltage',
                                  vals3, 'V'),
                         'stop': ('STOP', 'stop voltage',
                                  vals3, 'V'),
                         'stime': ('STIMe', 'bias time',
                                   vals2, 's')}),
            'altpolarity': ('ALTP', 
                            'Alternating Polarity Resistance/Resistivity Test',
                            {'ofsvoltage': ('OFSVoltage', 'offset voltage',
                                            vals3, 'V'),
                             'altvoltage': ('ALTVoltage', 'alternating voltage',
                                            vals3, 'V'),
                             'mtime': ('MTIMe', 'measure time',
                                       Numbers(0.5, 9999.9), 's'),
                             'store': ('READings',
                                       'number of readings to store',
                                        Ints(0, 3500), ''), # default: 1
                             'discard': ('DISCard', 
                                         'number of reading to discard',
                                         Ints(0, 9999), '')})
            }

        self.add_parameter('sense_function',
                           set_cmd=self._set_sense_function,
                           get_cmd=':SENSe:FUNCtion?',
                           val_mapping={k: v[0] 
                                        for k, v in self.sense_function_map.items()})
        
        # The sense function (both readable name and raw name) will be
        # frequently used below.
        # MUST be after the definition of 'sense_function' parameter
        self._sense_function = self._get_sense_function()
        self._raw_sense_function = _parse_get_string(
            self.sense_function_map[self._sense_function][0])
        self._sfunc_unit = self.sense_function_map[self._sense_function][2]

        # For the following two parameters, vsource_range, and operate
        # I don't know their difference with the vsource_range and 
        # vsource_operate for resistance mode.
        self.add_parameter('vsource_range',
                           set_cmd=':SOURce:VOLTage:RANGe {}',
                           get_cmd=':SOURce:VOLTage:RANGe?',
                           label='Voltage source range',
                           unit='V',
                           vals=Numbers(100,1000))

        self.add_parameter('operate',
                           set_cmd=':OUTPut {}',
                           get_cmd=':OUTPut?',
                           label='Voltage source operate',
                           docstring='Enable or disable the voltage source\
                               output. V-source is standby for OFF/0, operate\
                               for ON/1.',
                           val_mapping=create_on_off_val_mapping(on_val=1,
                                                                  off_val=0))

        self.add_parameter('zerocheck',
                           set_cmd=':SYSTem:ZCHeck {}',
                           get_cmd=':SYSTem:ZCHeck?',
                           val_mapping=create_on_off_val_mapping(on_val=1,
                                                                  off_val=0))
        
        self.add_parameter('interlock',
                           get_cmd=':SYSTem:INTerlock?',
                           docstring="If interlock cable isn't connected,\
                           6517A can't determine the state of test fixture lid,\
                           or read the test fixture switch settings, A potential\
                           hazard is present when lid is open",
                           val_mapping=create_on_off_val_mapping(on_val=1,
                                                                  off_val=0))
        
        self.add_parameter('speed',
                           set_cmd=f'SENSe:{self._raw_sense_function}:NPLCycles {{}}',
                           get_cmd=f'SENSe:{self._raw_sense_function}:NPLCycles?',
                           vals=MultiType(Numbers(0.01, 10),
                                          Enum('default',
                                               'minimum', 
                                               'maximum')),
                           docstring='Accept both number (nplc) and string, \
                               default(1.0), minimum(0.01), maximum(10)')
        
        self.add_parameter('digits',
                           set_cmd=f':SENSe:{self._raw_sense_function}:DIGits {{}}',
                           get_cmd=f':SENSe:{self._raw_sense_function}:DIGits?',
                           initial_value=6,
                           vals=Ints(4, 7),
                           docstring='{4: 3.5 digits, 5: 4.5 digits\
                                       6: 5.5 digits, 7: 6.5 digits}')

        self.add_parameter('current_damping',
                            set_cmd=f':SENSe:CURRent:DAMPing {{}}',
                            get_cmd=f':SENSe:CURRent:DAMPing?',
                            docstring='Only for current and resistance measurement',
                            val_mapping=create_on_off_val_mapping(on_val=1,
                                                                  off_val=0))

        self.add_parameter('res_auto_vsource',
                           set_cmd=':SENSe:RESistance:VSControl {}',
                           get_cmd=':SENSe:RESistance:VSControl?',
                           val_mapping={0: 'MAN', 1: 'AUTO'})

        self._vsource_mode = self.res_auto_vsource()
        self.vsauto = 1 if self._vsource_mode == 'auto' else 0

        self.add_parameter('res_vsource_range',
                           set_cmd=self._set_res_vsource_range,
                           get_cmd=':SENSe:RESistance:MANual:VSOurce:RANGe?',
                           unit='V',
                           label='Voltage source range (Resistance mode)',
                           vals=Numbers(100, 1000))
        
        self.add_parameter('res_vsource_level',
                           set_cmd=':SENSe:RESistance:MANual:VSOurce:AMPLitude {}',
                           get_cmd=':SENSe:RESistance:MANual:VSOurce:AMPLitude?',
                           unit='V',
                           label='Voltage source level (manual range)',
                           vals=Numbers(-100, 100))    

        self.add_parameter('res_vsource_operate',
                           set_cmd=':SENSe:RESistance:MANual:VSOurce:OPERate {}',
                           get_cmd=':SENSe:RESistance:MANual:VSOurce:OPERate?',
                           label='Voltage source operation (Resistance mode)',
                           val_mapping=create_on_off_val_mapping(on_val=1,
                                                                 off_val=0))
       
        self.add_parameter('auto_meas_range',
                           set_cmd=partial(self._meas_range, True, False, 
                                           value=None),
                           get_cmd=partial(self._meas_range, False, False, 
                                           False, value=None),
                           val_mapping=create_on_off_val_mapping(on_val=1,
                                                                 off_val=0))
       
        self.add_parameter('meas_range',
                           set_cmd=partial(self._meas_range, True, True, 0),
                           get_cmd=partial(self._meas_range, False, True, 0,
                                           value=None),
                           unit=self._sfunc_unit,
                           vals=self._meas_range_vals())

        self.add_parameter('res_meas_type',
                           set_cmd=':SENSe:RESistance:MSELect {}',
                           get_cmd=':SENSe:RESistance:MSELect?',
                           val_mapping={'resistance': 'NORM',
                                         'resistivity': 'RES'})
        
        self.add_parameter('tseq_type',
                           set_cmd=':TSEQuence:TYPE {}',
                           get_cmd=':TSEQuence:TYPE?',
                           val_mapping={key: value[0]
                                         for key, value in self.tseq_mapping.items()})

        # Add all the parameters of all the test sequence types to instrument
        for tname, tspec in self.tseq_mapping.items():
            trname, tlabel, tpspec = tspec
            for pname, pspec in tpspec.items():
                prname, plabel, pvals, punit = pspec
                pfullname = '_'.join(('tseq', tname, pname))
                pfulllabel = plabel + ' (' + tlabel + ')'
                pset_cmd = f':TSEQuence:{trname}:{prname} {{}}'
                pget_cmd = f':TSEQuence:{trname}:{prname}?'
                self.add_parameter(name=pfullname,
                                   set_cmd=pset_cmd,
                                   get_cmd=pget_cmd,
                                   label=pfulllabel,
                                   unit=punit,
                                   vals=pvals)
        
        # meter-connect
        self.add_parameter('meter_connect',
                           set_cmd=':SOURce:VOLTage:MCONnect {}',
                           get_cmd=':SOURce:VOLTage:MCONnect?',
                           docstring='Control the internal connection between\
                               V-Source LOW and Ammeter Low.',
                           val_mapping=create_on_off_val_mapping(on_val=1,
                                                                 off_val=0))
        
        # Take 6517A out of idle
        self.add_function('initiate', call_cmd=':INITiate')
        
        # If continuous initiate is on, the instrument is taken out of the idle.
        # At the conclusion of all programmed operations, 
        # instrument returns to arm layer 1
        self.add_parameter('initiate_continuous',
                           set_cmd=':INITiate:CONTinuous {}',
                           get_cmd=':INITiate:CONTinuous?',
                           val_mapping=create_on_off_val_mapping(on_val=1,
                                                                 off_val=0))
        
        # The instrument must be waiting for sth when this cmd is sent.
        self.add_function('trigger_immediate', call_cmd=':TRIGger:IMMediate')
        
        self.add_parameter('trigger_count',
                           set_cmd=':TRIGger:COUNt {}',
                           get_cmd=':TRIGger:COUNt?',
                           label='Meausre layer count',
                           vals=MultiType(Ints(1, 99999),
                                          Enum('inf',
                                               'default',
                                               'minimum',
                                               'maximum')),
                           docstring='default: 1, minimum: 1, maximum: 99999')
        
        self.add_parameter('trigger_delay',
                           set_cmd=':TRIGger:DELay {}',
                           get_cmd=':TRIGger:DELay?',
                           label='Measure layer delay',
                           unit='s',
                           vals=MultiType(Numbers(0,999999.999),
                                          Enum('default',
                                               'minimum',
                                               'maximum')),
                           docstring='default: 0, min: 0, max: 999999.999')
        
        # For arm layer 1 the source can also be real-time clock.
# =============================================================================
#         self.add_parameter('trigger_source', 
#                            set_cmd=':TRIGger:SOURce {}',
#                            get_cmd=':TRIGger:SOURce?',
#                            val_mapping={'hold': 'HOLD',
#                                         'immediate': 'IMM',
#                                         'manual': 'MAN',
#                                         'GPIB': 'BUS',
#                                         'trigger link': 'TLIN',
#                                         'external': 'EXT',
#                                         'timer': 'TIM'})
# =============================================================================
        
        # Arms the test sequence
        self.add_function('tseq_arm', call_cmd=':TSEQuence:ARM')
        
        # Not sure about the differenct between trigger source, as weel as arm
        # in test sequence and the general one.
        self.add_parameter('tseq_trigger_source',
                           set_cmd=':TSEQuence:TSOurce {}',
                           get_cmd=':TSEQuence:TSOurce?',
                           val_mapping={'manual': 'MAN',
                                        'immediate': 'IMM',
                                        'GPIB': 'BUS',
                                        'external': 'EXT',
                                        'trigger link': 'TLIN',
                                        'fixture lid': 'LCL'})
        
        # Must set the trigger source as timer before using this command.
        self.add_parameter('trigger_timer',
                           set_cmd=':TRIGger:TIMer {}',
                           get_cmd=':TRIGger:TIMer?',
                           unit='s',
                           vals=MultiType(Numbers(0.001, 999999.999),
                                          Enum('default',
                                               'minmum',
                                               'maximum')),
                           docstring='default: 0.1')

        # Aborts operation and returns to the top of the trigger model
        self.add_function('abort', call_cmd=':ABORt')
        # Abort the test sequence in progress
        self.add_function('tseq_abort', call_cmd=':TSEQuence:ABORt')
        
# =============================================================================
#         # The last resort
#         self.add_parameter('press_key',
#                            set_cmd=":SYSTem:KEY {}",
#                            get_cmd=':SYSTem:KEY?',
#                            get_parser=int,
#                            val_mapping=self.front_panel_keys_map)
#         
# =============================================================================
        self.display_position = {'top': 'WINDow1', 'bottom': 'WINDow2'}
        for pos, rawpos in self.display_position.items():
            
            state_param = '_'.join(('display', pos, 'state'))
            data_param = '_'.join(('display', pos))
            read_param = '_'.join(('read', 'display', pos))
            state_setcmd = f':DISPlay:{rawpos}:TEXT:STATe {{}}'
            state_getcmd = f':DISPlay:{rawpos}:TEXT:STATe?'
            data_setcmd = f':DISPlay:{rawpos}:TEXT:DATA {{}}'
            data_getcmd = f':DISPlay:{rawpos}:TEXT:DATA?'
            read_getcmd = f':DISPlay:{rawpos}:DATA?'
            
            self.add_parameter(name=state_param,
                               set_cmd=state_setcmd,
                               get_cmd=state_getcmd,
                               val_mapping=create_on_off_val_mapping(on_val=1,
                                                                 off_val=0))
            # USE QUOTED STRING, like "'I am using'".
            self.add_parameter(name=data_param,
                               set_cmd=data_setcmd,
                               get_cmd=data_getcmd,
                               vals=Strings())
            
            self.add_parameter(name=read_param,
                               get_cmd=read_getcmd)
            
        self.add_parameter('buffer_feed_control', 
                           set_cmd=':TRACe:FEED:CONTrol {}',
                           get_cmd=':TRACe:FEED:CONTrol?',
                           val_mapping={'disable': 'NEV',
                                        'fill_and_stop': 'NEXT',
                                        'continuous': 'ALW',
                                        'pretrigger': 'PRET'})

        self.add_parameter('read_buffer_raw_data',
                           get_cmd=':TRACe:DATA?')
        
        self.add_parameter('read_latest',
                           get_cmd=':SENSe:DATA?')
        
        self.add_parameter('timestamp_format',
                           set_cmd=':TRACe:TSTamp:FORMat {}',
                           get_cmd=':TRACe:TSTamp:FORMaT?',
                           label='timestamp format for buffer readings',
                           val_mapping={'refer_to_first': 'ABS',
                                        'between_two_readings': 'DELT'})
        
        self.add_parameter('timestamp',
                           set_cmd=':SYSTem:TSTamp:TYPE {}',
                           get_cmd=':SYSTem:TSTamp:TYPE?',
                           val_mapping={'relative': 'REL',
                                        'real': 'rtc'})
        
        # Reset relative timestamp to 0
        self.add_function('relative_timestamp_reset',
                          call_cmd=':SYSTem:TSTamp:RELative:RESet')
        

        self.add_parameter('tseq_voltage',
                           label='voltage',
                           get_cmd=self._get_tseq_voltage,
                           unit='V',
                           vals=Arrays(shape=(self.npts,)),
                           parameter_class=Parameter)
        
        self.add_parameter('tseq_current',
                           label='current',
                           get_cmd=self._get_tseq_current,
                           unit='A',
                           vals=Arrays(shape=(self.npts,)),
                           parameter_class=ParameterWithSetpoints)
        
        self.add_parameter("tseq_time",
                           label='time',
                           get_cmd=self._get_tseq_time,
                           unit='s',
                           vals=Arrays(shape=(self.npts,)),
                           parameter_class=Parameter)
        
        self.tseq_current.setpoints = (self.tseq_voltage,)
        
        self.add_parameter('voltage',
                           label='voltage',
                           get_cmd=self._get_voltage,
                           unit='V',
                           vals=Numbers(-1000,1000))
        
        self.add_parameter('current',
                           label='current',
                           get_cmd=self._get_current,
                           unit='A',  
                           vals=Numbers(-0.02, 0.02))


        # Returns the instrument to states optimized for front panel operation
        self.add_function('preset', call_cmd=':SYSTem:PRESet')
        
        # Returns the instrument to default conditions
        self.add_function('reset', call_cmd='*RST')
        
        # Clears all event registers, and Error Queue
        self.add_function('clear', call_cmd='*CLS')

        # Clears the error queue of messages
        self.add_function('clear_error', call_cmd=':SYSTem:CLEar')
        
        # Clear buffer
        self.add_function('clear_buffer', call_cmd=':TRACe:CLEar')
        
        # Read status of memory
        self.add_parameter('memory', get_cmd=':TRACe:FREE?', unit='bytes')
        
        # Wait until all the previous commands are finished
        self.add_function('wait', call_cmd='*WAI')
        
        self._elements = self.elements_for_data()

        self.connect_message()
        
    
    def _set_res_vsource_range(self, value):
        """
        Set the vsource range and update the validators for res_vsource_level
        at the same time.
        """
        self.write(f":SENSe:RESistance:MANual:VSOurce:RANGe {value}")
        self.res_vsource_level.vals = Numbers(-value, value)


    def _set_sense_function(self, sfunc: str):
        """
        Set the sense_function,
        and updata _sense_function every time when this is called.
        """
        # Don't map the sfunc to raw value here, This method will be wrapped
        # and it will be mapped  by the _wrap_set function in parameter.py
        self.write(f":SENSe:FUNCtion {sfunc}",)
        # The following items need to be updated.
        self._sense_function = self.sense_function.inverse_val_mapping[sfunc]
        self._raw_sense_function = _parse_get_string(
            self.sense_function_map[self._sense_function][0])
        self._sfunc_unit = self.sense_function_map[self._sense_function][2]
        
    
    def _get_sense_function(self):
        """
        .cache() is recommended over the use of get_latest().
        """
        _sense_function = self.sense_function.cache() or self.sense_function()
        return _sense_function
    
    def _timestamp(self):
        """
        cache of timestamp
        """
        return self.timestamp.cache() or self.timestamp()


    # Actually this can also make use of add_parameter()...
    def resistivity_config(self,
                           fixture, 
                           thickness: Optional[float] = None,
                           Ks: Optional[float] = None,
                           Kv: Optional[float] = None):
        """
        Before running this function, SET THE RES_MEAS_TYPE AS RESISTIVITY FIRST!!!
        args:
            fixture: can either be 'M8009' or 'USER'
            thickness: thickness (in mm) of the sample for volume resistivity measurement
            Ks: Ks = P/g, P = Effective perimeter (in mm) of the guarded electrode,
                          g = Distance (in mm) between the guarded electrode 
                          and the ring electorde
            Kv: Kv is the effective area of the guarded electrode
                Kv can be calculated as Kv = pi(D1/2)^2,
                where D1 is the outside diameter of guarded electrode.
        """
        # Create the strings to be written to instrument
        c = ':SENSe:RESistance:RESistivity:'
        cu = c + 'USER:'
        fxc, thc = c+'FSElect {}', c+'STHickness {}'
        ksc, kvc = cu+'KSURface {}', cu+'KVOLume {}'

        # Register the parameters in instrument
        self.fixture, self.thickness, self.Ks, self.Kv = fixture, thickness, Ks, Kv

        # Validate the parameter before writing them to instrument
        self.fixture_vals = self.resistivity_mapping['fixture'][2]
        self.fixture_vals.validate(self.fixture)
        self.write(fxc.format(self.fixture))

        if fixture == 'USER':
            # Some parameters are optional, so we don't create for loop to write
            if Ks:
                self.Ks_vals = self.resistivity_mapping['Ks'][2]
                self.Ks_vals.validate(self.Ks)
                self.write(ksc.format(self.Ks))

            if Kv:
                self.th_vals = self.resistivity_mapping['thickness'][2]
                self.th_vals.validate(self.thickness)
                self.write(thc.format(self.thickness))

                self.Kv_vals = self.resistivity_mapping['Kv'][2]
                self.Kv_vals.validate(self.Kv)
                self.write(kvc.format(self.Kv))

    
    def _meas_range(self, setnotget, automset, autom, value):
        """
        The parent function for the auto_meas_range, and meas_range method.
        Make use of functools.partial to customize it for difference uses.
    
        Args:
            setnotget: Customize it to be either get_cmd or set_cmd
            automset: "Auto measurement range is already set or not". If set
                      (and set to be 0, which means manual measurement range),
                      then this function is customized to be the meas_range method,
                      which set the measurement range. If not set yet, this
                      function will be the auto_meas_range method, which controls
                      the measurement range to be auto or manual.
            autom: "Auto measurement", should be 0 or 1,
                   to be used in auto_meas_range method
            value: The measurement range value, to be given when calling
                   meas_range method.
        """
        rsfunc = self._raw_sense_function # raw sense function
        vsauto = self.vsauto # voltage source auto mode (1 or 0)

        # Create the command strings
        # ms_c: Manual measurement range, Set Command
        # mms_c: Manual measuremetn range, Manual voltage source (resistance mode), Set Command
        # as_c: Auto measurement range, Set Command
        # ams_c: Auto measurement range, Manual voltage source (resistance mode), Set Command
        # g is the get commands.
        c = ':SENSe:{}'
        ca, cm = c+':RANGe', c+':CRANge'
        ms_c, mms_c, mg_c, mmg_c = ca+' {}', cm+' {}', ca+'?', cm+'?'
        caa, cma = ca+':AUTO', cm+':AUTO'
        as_c, ams_c, ag_c, amg_c = caa+' {}', cma+' {}', caa+'?', cma+'?'
        
        if rsfunc != 'RESistance' or (rsfunc == 'RESistance' and vsauto == 1):
            setcmd = ms_c.format(rsfunc, value) if automset else as_c.format(rsfunc, autom)
            getcmd = mg_c.format(rsfunc) if automset else ag_c.format(rsfunc)
        else: # rsfunc == 'RES' and vsauto = 0
            setcmd = mms_c.format(rsfunc, value) if automset else ams_c.format(rsfunc, autom)
            getcmd = mmg_c.format(rsfunc) if automset else amg_c.format(rsfunc)
        if setnotget:
            self.write(setcmd)
        else:
            return self.ask(getcmd)


    def _meas_range_vals(self):
        """
        Returns the validators for measurement range of four sense modes.
        """
        sfunc = self._sense_function # sense function
        fvals = self.sense_function_map[sfunc][1] # function meas range validator
        if sfunc == 'resistance':
            return fvals[0] if self.vsauto else fvals[1]
        else:
            return fvals
        
    
    def _elements_for(self, cmd, *args):
        """
        Get or set elements list for buffer or data string.

        """
        getcmd, setcmd = cmd + '?', cmd + ' {}'
        if len(args) == 0: # get
            relem = self.ask(getcmd) # raw elements
            relemlist = list(map(str.strip, relem.split(',')))
            elemlist = [self.inv_elements_list[i] for i in relemlist]
            return elemlist
        else: # set
            if ('reading' and 'units') not in args:
                raise ValueError("'reading' and 'units' must be included in data")
            relem = ','.join(tuple([self.elements_list[i] for i in args]))
            self.write(setcmd.format(relem))
        
    
    def elements_for_buffer(self, *args):
        """ 
        Specify the elements to feed the buffer.
        READings, STATus, RNUMber (reading number), and UNIT are always enabled
        for the buffer and are included in the response for the query.
        """
        # The default is including all of this! Then how to remove elements???
        cmd = ':TRACe:ELEMents'
        return self._elements_for(cmd, *args)
            
        
    def elements_for_data(self, *args):
        """
        Specify data elements for data string.

        """
        cmd = ':FORMat:ELEMents'
        self._elements = list(args)
        return self._elements_for(cmd, *args)
    
    
    def read_error(self):
        """Read the error messages queue"""
        self.ask('SYSTem:ERRor?')


    def get_idn(self):
        """ Query the identitiy number. """
        idn = self.ask('*IDN?')
        # Use str.strip to remove the white spaces before and after the string
        vendor, model, serial, firmware = map(str.strip, idn.split(','))
        model = model[6:]

        idn = {'vendor': vendor, 'model': model, 
               'serial': serial, 'firmware': firmware}
        return idn


    def datetime_calibrate(self):
        """ Calibrate the date and time. """
        t = datetime.now()
        self.write(f':SYSTem:DATE {t.year},{t.month},{t.day}')
        self.write(f':SYSTem:TIME {t.hour},{t.minute},{t.second}')
        #print(f'Current time is: {t}')
        
    
    def npts(self) -> int:
        """
        Get the number of points of the sweep axis.
        Only applies to square sweep, staircase sweep, alternate polarity sequence.
        """
        ts_type = self.tseq_type()
        if ts_type == 'sqsweep':
            n = 2*int(self.tseq_sqsweep_count()) 
        elif ts_type == 'stsweep':
            stopv = float(self.tseq_stsweep_stop())
            startv = float(self.tseq_stsweep_start())
            stepv = float(self.tseq_stsweep_step())
            n = int(np.floor((stopv - startv)/stepv)) + 1
        elif ts_type == 'altpolarity':
            n = int(self.tseq_altpolarity_store())
        else:
            raise ValueError('npts only applies to sqsweep, stsweep and altpolarity')
            
        return n
    
    
    def _get_tseq_current(self) -> np.ndarray:
        """
        Get the reading of tseq experiment.
        """
        return self.get_data('reading', tseq=True)
    
    
    def _get_tseq_voltage(self) -> np.ndarray:
        """
        Get the sweep axis (vsource) of tseq experiment.
        """
        return self.get_data('vsource', tseq=True)

    
    def _get_tseq_time(self) -> np.ndarray:
        """
        Get the tiem stamp of tseq experiment.
        """
        return self.get_data('timestamp', tseq=True)
    
    
    def _get_current(self):
        """
        Get single reading of current.
        """
        return self.get_data('reading', tseq=False)
    
    def _get_voltage(self):
        """
        Get voltage value of single point.
        """
        return self.get_data('vsource', tseq=False)
        
    
    def get_data(self, element=None, tseq=True):
        """
        Get the parsed data and convert list to numpy array.
        """
        if tseq:
            raw_data = self.read_buffer_raw_data()
        else:
            raw_data = self.read_latest()
        parsed_data = self._parse_raw_data(raw_data)
        if not element or element=='all':
            return {e: parsed_data[e] for e in self._elements}
        else:
            if element not in self.elements_list.keys():
                raise KeyError('The elements must be one of {}'.format(
                               list(self.elements_list.keys())))
            return parsed_data[element]
        
    
    def _parse_raw_data(self, raw_data: str):
        """
        Convert the raw data string to arrays.
        Currently only include reading, units, and vsource.
        Only consider voltage, current, resistance measurement.
        'units' and 'channel' are single string, the others are np.array
        """
        # The most general data string is in the following form:
        # "ReadingStatusUnits, Timestamp, Readingnumber, Channel, Temperature,
        # Humidity, Vsource"
        # Reading and Units Must be included
        
        if 'reading' not in self._elements:
            raise ValueError('Reading must be included in the data')
        
        first_str = {'reading', 'status', 'units'}
        N = len(set(self._elements) - first_str)
        N = N + 2 if (('timestamp' in self._elements) 
                      and self._timestamp()=='real') else N + 1       
        
        raw_data_list = list(map(str.strip, raw_data.split(',')))
        
        rsu = raw_data_list[0::N] # 'reading'+'status'+'units'
        reading = np.array([float(r[:13]) for r in rsu]) # for ASCII format
        
        
        status_map = {'N': 'Normal', 'Z': 'Zero Check Enabled', 'O': 'Overflow',
                      'U': 'Underflow', 'R': 'Reference', 'L': 'Out of Limit'}
        units_map= {'VDC': 'V', 'ADC': 'A', 'OHM': 'Ohm', 'OHMCM': 'Ohm·cm',
                    'OHMSQ': 'Ohm/Sq', '%/V': '%/V', 'COUL': 'C'}
        status = []
        if 'status' in self._elements:
            status = [status_map[s[13]] for s in rsu]
            units = units_map[rsu[0][14:]] # SINGLE STRING
        else:
            units = units_map[rsu[0][13:]]
        status = np.array(status)
        
        tsi = int('timestamp' in self._elements) # timestamp index
        time = raw_data_list[1::N] if tsi==1 else []
        if self._timestamp()=='real': # including date
            date = raw_data_list[2::N] if tsi==1 else []
            timestamp = [time[i] + ', ' + date[i] for i in range(len(time))]
        else: # use relative timestamp format, date not included
            # if use relative timestamp format we transform the time format
            # from string to float with unit of seconds
            date = []
            timestamp = [float(t[:-4]) for t in time]
        timestamp = np.array(timestamp)
        
        rni = int('reading number' in self._elements) # reading number index
        reading_number = raw_data_list[2*tsi+1::N] if rni==1 else []
        reading_number = np.array(reading_number)
        
        ci = int('channel' in self._elements) # channel index
        channel = raw_data_list[2*tsi+rni+1::N][0] if ci==1 else [] # SINGLE STRING
        channel = np.array(channel)
        
        ti = int('temperature' in self._elements) # temperature index
        temperature = raw_data_list[2*tsi+rni+ci+1::N] if ti==1 else []
        temperature = np.array(temperature)
        
        hi = int('humidity' in self._elements) # humidity index
        humidity = raw_data_list[2*tsi+rni+ci+ti+1::N] if hi==1 else []
        humidity = np.array(humidity)
        
        vi = int('vsource' in self._elements)
        vsource = [float(v[:-4]) for v in raw_data_list[N-1::N]] if vi==1 else []
        vsource = np.array(vsource)
            
        return {'reading': reading, 'status': status, 'units': units, 
                'timestamp': timestamp, 'reading number': reading_number,
                'channel': channel, 'temperature': temperature, 
                'humidity': humidity, 'vsource': vsource}


    def stsweep_setup(self,
                      start_voltage,
                      step_voltage,
                      stop_voltage,
                      step_time):
        
        """
        Configure the instrument to make staircase sweep measuremnent
        """
        self.tseq_type('stsweep')
        self.tseq_stsweep_start(start_voltage)
        self.tseq_stsweep_step(step_voltage)
        self.tseq_stsweep_stop(stop_voltage)
        self.tseq_stsweep_stime(step_time)


def _parse_get_string(string_vlaue: str):
    """
    Remove the surronding quotes of the string
    """
    raw_str = string_vlaue.strip()
    if raw_str.startswith(("'",'"')) and raw_str.endswith(("'",'"')):
        raw_str = raw_str[1:-1]
    return raw_str
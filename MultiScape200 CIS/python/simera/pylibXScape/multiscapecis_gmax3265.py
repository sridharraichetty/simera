'''
Simera Sense MultiScapeCIS_GMAX3265 Class
Copyright (c) 2019-2020 Simera Sense (info@simerasense.com)
Released under MIT License.
'''


import numpy as np
import time

from . import exceptions
from . import xscape
from . import triscape
from . import multiscape




# Module Constants
IMAGING_PARAMID_GMAX3265_PGA_GAIN = 0x10
IMAGING_PARAMID_GMAX3265_ADC_GAIN = 0x11
IMAGING_PARAMID_GMAX3265_DARK_OFFSET = 0x12


class MultiScapeCIS_GMAX3265(multiscape.MultiScape, triscape.TriScape):
    """
    MultiScapeCIS_GMAX3265 class

    Inherits from the MultiScape class and extends it for GMAX3265 specific commands and requests.
    Also inherits from the TriScape class, to allow snapshot imaging.
    """

    def __init__(self, EGSE = None, I2Caddr = None):
        """
        MultiScapeCIS_GMAX3265 Constructor
    
        __init__(EGSE = None, I2Caddr = None, threadLock = None)
    
        Optional Arguments:
            EGSE        - Instance of Simera EGSE class
            I2Caddr     - Set if using the I2C control interface
        """
        print("####### This class has been replaced. Please use MultiScapeCIS200 class")
        return
        # run the parent (xScape) instance constructor
        super().__init__(EGSE, I2Caddr)

        # add the product specific functions to the parent (xscape) instance variable
        self.imaging_param_parser.update( {
                IMAGING_PARAMID_GMAX3265_PGA_GAIN        : lambda x : self._parseImagingParameter_SensorPgaGain(x),
                IMAGING_PARAMID_GMAX3265_ADC_GAIN        : lambda x : self._parseImagingParameter_SensorAdcGain(x),
                IMAGING_PARAMID_GMAX3265_DARK_OFFSET     : lambda x : self._parseImagingParameter_SensorDarkOffset(x)                
            })

        self.imaging_param_req_handlers.update( {
                IMAGING_PARAMID_GMAX3265_PGA_GAIN        : lambda  : self._handleImagingParameterReq_SensorPgaGain(),
                IMAGING_PARAMID_GMAX3265_ADC_GAIN        : lambda  : self._handleImagingParameterReq_SensorAdcGain(),
                IMAGING_PARAMID_GMAX3265_DARK_OFFSET     : lambda  : self._handleImagingParameterReq_SensorDarkOffset()
            })            

        # add the produt specific telemetry information
        self.ce_tlm_info = [
                            {'Name':'V_FeeSmps'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':    0, 'Max':  300}, 'Range_FeeOn':{'Min': 1300, 'Max': 1400}},
                            {'Name':'C_FeeSmps'    , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':    0, 'Max':   25}, 'Range_FeeOn':{'Min':  100, 'Max':  400}},
                            {'Name':'C_FeeLdo'     , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':    0, 'Max':   25}, 'Range_FeeOn':{'Min':  375, 'Max':  550}},
                            {'Name':'V_FeeNegSmps' , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min': -750, 'Max':    0}, 'Range_FeeOn':{'Min':-4300, 'Max':-4150}},
                            {'Name':'C_Brd5V0'     , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':    0, 'Max':   80}, 'Range_FeeOn':{'Min':  100, 'Max':  200}},
                            {'Name':'V_FeeOpAmp'   , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':    0, 'Max':  300}, 'Range_FeeOn':{'Min': 4150, 'Max': 4300}},
                            {'Name':'V_SdramVtt'   , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':  585, 'Max':  615}, 'Range_FeeOn':{'Min':  585, 'Max':  615}},
                            {'Name':'V_Brd3V3'     , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min': 3280, 'Max': 3400}, 'Range_FeeOn':{'Min': 3280, 'Max': 3400}},
                            {'Name':'V_Brd2V5'     , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min': 2490, 'Max': 2560}, 'Range_FeeOn':{'Min': 2490, 'Max': 2560}},
                            {'Name':'V_RefCal0'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min': 1020, 'Max': 1030}, 'Range_FeeOn':{'Min': 1020, 'Max': 1030}},
                            {'Name':'V_FeeLdo'     , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':    0, 'Max':   50}, 'Range_FeeOn':{'Min': 3800, 'Max': 3900}},
                            {'Name':'V_IntTst0'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':    0, 'Max':    0}, 'Range_FeeOn':{'Min':    0, 'Max':    0}},
                            {'Name':'V_REFM0'      , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':    0, 'Max':    0}, 'Range_FeeOn':{'Min':    0, 'Max':    0}},
                            {'Name':'V_REFP0'      , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':    0, 'Max':    0}, 'Range_FeeOn':{'Min':    0, 'Max':    0}},
                            {'Name':'C_BrdLdo'     , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':   85, 'Max':  130}, 'Range_FeeOn':{'Min':   85, 'Max':  130}},
                            {'Name':'C_Smps3V3'    , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':  100, 'Max':  220}, 'Range_FeeOn':{'Min':  150, 'Max':  250}},
                            {'Name':'V_Smps1V2'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min': 1190, 'Max': 1240}, 'Range_FeeOn':{'Min': 1190, 'Max': 1240}},
                            {'Name':'V_Smps1V0'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':  990, 'Max': 1010}, 'Range_FeeOn':{'Min':  990, 'Max': 1010}},
                            {'Name':'C_Smps1V0'    , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':  450, 'Max': 1000}, 'Range_FeeOn':{'Min':  550, 'Max': 1000}},
                            {'Name':'C_Smps1V2'    , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':   20, 'Max':  140}, 'Range_FeeOn':{'Min':   20, 'Max':  140}},
                            {'Name':'V_Brd1V8'     , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min': 1790, 'Max': 1840}, 'Range_FeeOn':{'Min': 1790, 'Max': 1840}},
                            {'Name':'C_SdramVtt'   , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':    0, 'Max':   15}, 'Range_FeeOn':{'Min':    0, 'Max':   15}},
                            {'Name':'V_RefCal1'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min': 1020, 'Max': 1030}, 'Range_FeeOn':{'Min': 1020, 'Max': 1030}},
                            {'Name':'V_IntTst1'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':    0, 'Max':    0}, 'Range_FeeOn':{'Min':    0, 'Max':    0}},
                            {'Name':'V_REFM1'      , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':    0, 'Max':    0}, 'Range_FeeOn':{'Min':    0, 'Max':    0}},
                            {'Name':'V_REFP1'      , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':    0, 'Max':    0}, 'Range_FeeOn':{'Min':    0, 'Max':    0}},
                            {'Name':'V_Fpga1V0'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':  970, 'Max': 1030}, 'Range_FeeOn':{'Min':  970, 'Max': 1030}},
                            {'Name':'V_Fpga1V8'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min': 1745, 'Max': 1855}, 'Range_FeeOn':{'Min': 1745, 'Max': 1855}},
                            {'Name':'V_Fpga2V5'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min': 2425, 'Max': 2575}, 'Range_FeeOn':{'Min': 2425, 'Max': 2575}},
                            {'Name':'T_Fpga'       , 'Unit':'`C', 'Used':True  , 'Range_FeeOff':{'Min':  -25, 'Max':   80}, 'Range_FeeOn':{'Min':  -25, 'Max':   80}}
                           ]
        self.fee_tlm_info = [
                            {'Name':'T_SnsDiode'      , 'Unit':'`C', 'Used':False , 'Range':{'Min':    0, 'Max':    0}},
                            {'Name':'V_FeeLdo'        , 'Unit':'mV', 'Used':True  , 'Range':{'Min': 3750, 'Max': 3850}},
                            {'Name':'V_VDD33A'        , 'Unit':'mV', 'Used':True  , 'Range':{'Min': 3225, 'Max': 3375}},
                            {'Name':'V_VDDPIX'        , 'Unit':'mV', 'Used':True  , 'Range':{'Min': 3750, 'Max': 3850}},
                            {'Name':'V_VTX_GRSTH'     , 'Unit':'mV', 'Used':True  , 'Range':{'Min': 3500, 'Max': 3650}},
                            {'Name':'V_VDD13'         , 'Unit':'mV', 'Used':True  , 'Range':{'Min': 1250, 'Max': 1350}},
                            {'Name':'V_VDDCL'         , 'Unit':'mV', 'Used':True  , 'Range':{'Min':  650, 'Max':  750}},
                            {'Name':'V_NEGSMPS'       , 'Unit':'mV', 'Used':True  , 'Range':{'Min':-4300, 'Max':-4100}},
                            {'Name':'V_VTXL'          , 'Unit':'mV', 'Used':True  , 'Range':{'Min':-1350, 'Max':-1250}},
                            {'Name':'V_GRSTL'         , 'Unit':'mV', 'Used':True  , 'Range':{'Min':-1350, 'Max':-1250}},
                            {'Name':'V_FeeOpAmp'      , 'Unit':'mV', 'Used':True  , 'Range':{'Min': 3900, 'Max': 4300}},
                            {'Name':'V_IntTst'        , 'Unit':'mV', 'Used':False , 'Range':{'Min':    0, 'Max':    0}},
                            {'Name':'V_REFM'          , 'Unit':'mV', 'Used':False , 'Range':{'Min':    0, 'Max':    0}},
                            {'Name':'V_REFP'          , 'Unit':'mV', 'Used':False , 'Range':{'Min':    0, 'Max':    0}},
                            {'Name':'T_Sensor'        , 'Unit':'`C', 'Used':True  , 'Range':{'Min':  -10, 'Max':   55}}
                            ]
        
        self.ofe_tlm_info = [
                            {'Name':'T_OFE-X-Y34'     , 'Unit':'`C', 'Used':True  , 'Range':{'Min':  -20, 'Max':   60}},
                            {'Name':'T_OFE-X-Y140'    , 'Unit':'`C', 'Used':True  , 'Range':{'Min':  -20, 'Max':   60}},
                            {'Name':'T_OFE-X-Y246'    , 'Unit':'`C', 'Used':True  , 'Range':{'Min':  -20, 'Max':   60}},
                            {'Name':'T_OFE-X+Y34'     , 'Unit':'`C', 'Used':True  , 'Range':{'Min':  -20, 'Max':   60}},
                            {'Name':'T_OFE-X+Y140'    , 'Unit':'`C', 'Used':True  , 'Range':{'Min':  -20, 'Max':   60}},
                            {'Name':'T_OFE-X+Y246'    , 'Unit':'`C', 'Used':True  , 'Range':{'Min':  -20, 'Max':   60}},
                            {'Name':'T_OFE+X+Y34'     , 'Unit':'`C', 'Used':True  , 'Range':{'Min':  -20, 'Max':   60}},
                            {'Name':'T_OFE+X+Y140'    , 'Unit':'`C', 'Used':True  , 'Range':{'Min':  -20, 'Max':   60}},
                            {'Name':'T_OFE+X+Y246'    , 'Unit':'`C', 'Used':True  , 'Range':{'Min':  -20, 'Max':   60}},
                            {'Name':'T_OFE+X-Y34'     , 'Unit':'`C', 'Used':True  , 'Range':{'Min':  -20, 'Max':   60}},
                            {'Name':'T_OFE+X-Y140'    , 'Unit':'`C', 'Used':True  , 'Range':{'Min':  -20, 'Max':   60}},
                            {'Name':'T_OFE+X-Y246'    , 'Unit':'`C', 'Used':True  , 'Range':{'Min':  -20, 'Max':   60}}
                            ]        
        
        # add product specific current consumption
        self.total_current_info = {'Name':'Current', 'Unit':'mA',  'Range_FeeOff':{'Min': 500, 'Max':  1100}, 'Range_FeeOn':{'Min': 1300, 'Max':  2100}}
        
        # add product specific current limtis (latch-up protection)
        self.current_limits = [
                            {'Name':'C_FeeSmps'    ,'Limit':600},
                            {'Name':'C_FeeLdo'     ,'Limit':750},
                            {'Name':'C_Brd5V0'     ,'Limit':300},
                            {'Name':'C_BrdLdo'     ,'Limit':500},
                            {'Name':'C_Smps3V3'    ,'Limit':850},
                            {'Name':'C_Smps1V0'    ,'Limit':1200},
                            {'Name':'C_Sdrm1V2'    ,'Limit':300},
                            {'Name':'C_SdramVtt'   ,'Limit':20},
                            ]     

        # Default number of bands
        self.bands = 8
        
        # Default number of OFE Temperature Sensors
        self.ofe_temps = 12
        
    # --- Product Specific Requests --- #
    
    def ReqOfeTelemetry(self):
        """
        Returns the Optical Front-End Telemetry, previously retrieved using the GetOfeTelemetry Command.

        tlm = ReqOfeTelemetry()

        Returns the telemetry value(s) as a list.
         """

        req_id = 0x8F
        req_length = self.ofe_temps
        try:
            tlm = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqOfeTelemetry request.\n{e}')                   
               
        # Adjust for 2's compliment (negative). All values are int8
        for i in range(len(tlm)):
            if tlm[i] >= 0x80:
                tlm[i] -= 0x100            
        
        return tlm        
        
    # --- Sensor Specific Requests --- #
        
    def ReqSensorDiagnostics(self):
        # kept for backwards compatibility
        # this method will be deprecated in future releases
        print("The 'ReqSensorDiagnostics()' method will be deprecated in future releases. Please use 'ReqSensorDiagnosticsChannelStatus()'")
        return self.ReqSensorDiagnosticsChannelStatus()

    def ReqSensorDiagnosticsChannelStatus(self):
        """
        Returns the Sensor Diagnostic Information (for a GMAX3265 sensor).
        
        lower_chan_status, upper_chan_status, ctrl_chan_status = ReqSensorDiagnosticsChannelStatus()
    
        Returns the failed sensor interface channels as bit vectors.
        """
               
        req_id = 0x94
        req_length = 9
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSensorDiagnosticsChannelStatus request.\n{e}')                   

        if isinstance(retval, list):
            lower_chan_status  = retval[0] + (retval[1]<<8) + (retval[2]<<16) + (retval[3]<<24)
            upper_chan_status  = retval[4] + (retval[5]<<8) + (retval[6]<<16) + (retval[7]<<24)
            ctrl_chan_status = retval[8]

        return lower_chan_status, upper_chan_status, ctrl_chan_status

    def ReqSensorDiagnosticsChannelTiming(self):
        """
        Returns the Sensor Window Diagnostic Information (for a GMAX3265 sensor).
        
        raw = ReqSensorDiagnosticsChannelTiming()
    
        Returns the sensor window centre values for each channel
        """
               
        req_id = 0x9D
        req_length = 57
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSensorDiagnosticsChannelTiming request.\n{e}')                   

        return retval
        
    # --- Parse the Imaging Parameters --- #

    def _parseImagingParameter_SensorPgaGain(self, *Values):
        """
        GMAX3265 Sensor PGA Gain
    
        Mandatory Arguments:
            Value   - 75 = 0.75 gain, 100 - 1.0 gain, 125 = 1.25 gain
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value not in [75,100,125]:
            raise exceptions.InputError(f'Value parameter must be 75, 100 or 125, but "{Value}" was supplied.')                      

        return Value

    def _parseImagingParameter_SensorAdcGain(self, *Values):
        """
        GMAX3265 Sensor ADC Gain
    
        Mandatory Arguments:
            Value   -  Range 34 to 40.
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 34 or Value > 40:
            raise exceptions.InputError(f'Value parameter must be between 34 and 40, but "{Value}" was supplied.')

        return Value

    def _parseImagingParameter_SensorDarkOffset(self, *Values):
        """
        GMAX3265 Sensor Dark Offset.
        
        Mandatory Arguments:
            Value   - Range -8192 to 8191
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < -8192 or Value > 8191:
            raise exceptions.InputError(f'Value parameter must be in range -8192 to 8191, but "{Value}" was supplied.')

        byte0 = (Value>>0)%256
        byte1 = (Value>>8)%256
        
        return [byte0, byte1]
        
    # --- Handle the Imaging Parameter Requests --- #
        
    def _handleImagingParameterReq_SensorPgaGain(self):
        """
        Return the Sensor PGA Gain.
        """        
        req_id = 0x89
        req_length = 1

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqImagingParameter request.\n{e}')               
                   
        if isinstance(retval, list):
            raw = retval[0]
        else:
            raw = retval
        
        return raw    
        
    def _handleImagingParameterReq_SensorAdcGain(self):
        """
        Return the Sensor ADC Gain.
        """        
        req_id = 0x89
        req_length = 1

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqImagingParameter request.\n{e}')               
                   
        if isinstance(retval, list):
            raw = retval[0]
        else:
            raw = retval
        
        return raw         
        
    def _handleImagingParameterReq_SensorDarkOffset(self):
        """
        Return the Sensor Dark Offset.
        """        
        req_id = 0x89
        req_length = 2

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqImagingParameter request.\n{e}')               
                   
        if isinstance(retval, list):
            raw = retval[0] + (retval[1]<<8)
            
        # Adjust for 2's compliment (negative)     
        if raw >= 0x8000:
            raw -= 0x10000
            
        return raw        

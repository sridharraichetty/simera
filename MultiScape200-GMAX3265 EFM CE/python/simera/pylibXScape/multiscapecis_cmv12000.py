'''
Simera Sense MultiScapeCIS_CMV12000 Class
Copyright (c) 2019-2020 Simera Sense (info@simerasense.com)
Released under MIT License.
'''


import numpy as np
import time

from . import exceptions
from . import xscape
from . import triscape
from . import multiscape




#Module Constants
IMAGING_PARAMID_CMV12K_ADC_RANGE = 0x10
IMAGING_PARAMID_CMV12K_BOT_OFFSET = 0x11
IMAGING_PARAMID_CMV12K_TOP_OFFSET = 0x12
IMAGING_PARAMID_CMV12K_GAIN = 0x13
IMAGING_PARAMID_CMV12K_BLACKREF_ENABLE = 0x14


class MultiScapeCIS_CMV12000(multiscape.MultiScape, triscape.TriScape):
    """
    MultiScapeCIS_CMV12000 class

    Inherits from the MultiScape class and extends it for CMV12000 specific commands and requests.
    Also inherits from the TriScape class, to allow snapshot imaging.
    """

    def __init__(self, EGSE = None, I2Caddr = None):
        """
        MultiScapeCIS_CMV12000 Constructor
    
        __init__(EGSE = None, I2Caddr = None, threadLock = None)
    
        Optional Arguments:
            EGSE        - Instance of Simera EGSE class
            I2Caddr     - Set if using the I2C control interface
        """
        print("####### This class has been replaced. Please use MultiScapeCIS50 or MultiScapeCIS100 class")
        return
        # run the parent (xScape) instance constructor
        super().__init__(EGSE, I2Caddr)

        # add the product specific functions to the parent (xscape) instance variable
        self.imaging_param_parser.update( {
                IMAGING_PARAMID_CMV12K_ADC_RANGE        : lambda x : self._parseImagingParameter_SensorAdcRange(x),
                IMAGING_PARAMID_CMV12K_BOT_OFFSET       : lambda x : self._parseImagingParameter_SensorBotOffset(x),
                IMAGING_PARAMID_CMV12K_TOP_OFFSET       : lambda x : self._parseImagingParameter_SensorTopOffset(x),
                IMAGING_PARAMID_CMV12K_GAIN             : lambda x : self._parseImagingParameter_SensorGain(x),
                IMAGING_PARAMID_CMV12K_BLACKREF_ENABLE  : lambda x : self._parseImagingParameter_SensorBlackRefEnable(x)
            })

        self.imaging_param_req_handlers.update( {
                IMAGING_PARAMID_CMV12K_ADC_RANGE        : lambda  : self._handleImagingParameterReq_SensorAdcRange(),
                IMAGING_PARAMID_CMV12K_BOT_OFFSET       : lambda  : self._handleImagingParameterReq_SensorBotOffset(),
                IMAGING_PARAMID_CMV12K_TOP_OFFSET       : lambda  : self._handleImagingParameterReq_SensorTopOffset(),
                IMAGING_PARAMID_CMV12K_GAIN             : lambda  : self._handleImagingParameterReq_SensorGain(),
                IMAGING_PARAMID_CMV12K_BLACKREF_ENABLE  : lambda  : self._handleImagingParameterReq_SensorBlackRefEnable()
            })            

        # add the produt specific telemetry information
        self.ce_tlm_info = [
                            {'Name':'V_FeeSmps'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':   0, 'Max': 300}, 'Range_FeeOn':{'Min':2000, 'Max':2060}},
                            {'Name':'C_FeeSmps'    , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':   0, 'Max':  25}, 'Range_FeeOn':{'Min': 190, 'Max': 450}},
                            {'Name':'C_FeeLdo'     , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':   0, 'Max':  25}, 'Range_FeeOn':{'Min':   0, 'Max':  55}},
                            {'Name':'V_FeeNegSmps' , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'C_Brd5V0'     , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':   0, 'Max':  80}, 'Range_FeeOn':{'Min':   0, 'Max':  80}},
                            {'Name':'V_FeeOpAmp'   , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_SdramVtt'   , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min': 585, 'Max': 615}, 'Range_FeeOn':{'Min': 585, 'Max': 615}},
                            {'Name':'V_Brd3V3'     , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':3280, 'Max':3400}, 'Range_FeeOn':{'Min':3280, 'Max':3400}},
                            {'Name':'V_Brd2V5'     , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':2490, 'Max':2560}, 'Range_FeeOn':{'Min':2490, 'Max':2560}},
                            {'Name':'V_RefCal0'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':1016, 'Max':1032}, 'Range_FeeOn':{'Min':1016, 'Max':1032}},
                            {'Name':'V_FeeLdo'     , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':   0, 'Max':  10}, 'Range_FeeOn':{'Min':2950, 'Max':3150}},
                            {'Name':'V_IntTst0'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_REFM0'      , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_REFP0'      , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'C_BrdLdo'     , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':  85, 'Max': 130}, 'Range_FeeOn':{'Min':  85, 'Max': 130}},
                            {'Name':'C_Smps3V3'    , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':  90, 'Max': 220}, 'Range_FeeOn':{'Min': 310, 'Max': 500}},
                            {'Name':'V_Smps1V2'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':1190, 'Max':1240}, 'Range_FeeOn':{'Min':1190, 'Max':1240}},
                            {'Name':'V_Smps1V0'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min': 990, 'Max':1010}, 'Range_FeeOn':{'Min': 990, 'Max':1010}},
                            {'Name':'C_Smps1V0'    , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min': 310, 'Max': 730}, 'Range_FeeOn':{'Min': 310, 'Max': 850}},
                            {'Name':'C_Smps1V2'    , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':  20, 'Max': 110}, 'Range_FeeOn':{'Min':  20, 'Max': 110}},
                            {'Name':'V_Brd1V8'     , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':1790, 'Max':1840}, 'Range_FeeOn':{'Min':1790, 'Max':1840}},
                            {'Name':'C_SdramVtt'   , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':   0, 'Max':  15}, 'Range_FeeOn':{'Min':   0, 'Max':  15}},
                            {'Name':'V_RefCal1'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':1016, 'Max':1032}, 'Range_FeeOn':{'Min':1016, 'Max':1032}},
                            {'Name':'V_IntTst1'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_REFM1'      , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_REFP1'      , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_Fpga1V0'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min': 970, 'Max':1030}, 'Range_FeeOn':{'Min': 970, 'Max':1030}},
                            {'Name':'V_Fpga1V8'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':1745, 'Max':1855}, 'Range_FeeOn':{'Min':1745, 'Max':1855}},
                            {'Name':'V_Fpga2V5'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':2425, 'Max':2575}, 'Range_FeeOn':{'Min':2425, 'Max':2575}},
                            {'Name':'T_Fpga'       , 'Unit':'`C', 'Used':True  , 'Range_FeeOff':{'Min': -25, 'Max':  80}, 'Range_FeeOn':{'Min': -25, 'Max':  80}}
                           ]
        self.fee_tlm_info = [
                            {'Name':'V_FeeSmps'    , 'Unit':'mV', 'Used':True  , 'Range':{'Min':1980, 'Max':2060}},
                            {'Name':'V_FeeLdo'     , 'Unit':'mV', 'Used':True  , 'Range':{'Min':2950, 'Max':3150}},
                            {'Name':'(unused)'     , 'Unit':'mV', 'Used':False , 'Range':{'Min':   0, 'Max':   0}},
                            {'Name':'V_TFLLow2'    , 'Unit':'mV', 'Used':False  , 'Range':{'Min':  40, 'Max':  55}},
                            {'Name':'V_TFLLow3'    , 'Unit':'mV', 'Used':False  , 'Range':{'Min':  40, 'Max':  55}},
                            {'Name':'V_Bandgap'    , 'Unit':'mV', 'Used':False  , 'Range':{'Min':1125, 'Max':1175}},
                            {'Name':'V_ResetL'     , 'Unit':'mV', 'Used':False  , 'Range':{'Min':  36, 'Max':  56}},
                            {'Name':'V_RefADC'     , 'Unit':'mV', 'Used':False  , 'Range':{'Min':1750, 'Max':1875}},
                            {'Name':'V_CmvRef'     , 'Unit':'mV', 'Used':False  , 'Range':{'Min': 530, 'Max': 585}},
                            {'Name':'V_Ramp2'      , 'Unit':'mV', 'Used':False , 'Range':{'Min':   0, 'Max':   0}},
                            {'Name':'V_Ramp1'      , 'Unit':'mV', 'Used':False , 'Range':{'Min':   0, 'Max':   0}},
                            {'Name':'V_IntTst'     , 'Unit':'mV', 'Used':False , 'Range':{'Min':   0, 'Max':   0}},
                            {'Name':'V_REFM'       , 'Unit':'mV', 'Used':False , 'Range':{'Min':   0, 'Max':   0}},
                            {'Name':'V_REFP'       , 'Unit':'mV', 'Used':False , 'Range':{'Min':   0, 'Max':   0}},
                            {'Name':'T_CMV'        , 'Unit':'`C', 'Used':True  , 'Range':{'Min': -15, 'Max':  65}}
                            ]

        # add product specific current consumption
        self.total_current_info = {'Name':'Current', 'Unit':'mA',  'Range_FeeOff':{'Min': 500, 'Max':  900}, 'Range_FeeOn':{'Min': 1150, 'Max':  1600}}
        
        # Default number of bands
        self.bands = 7

    def ReqSensorDiagnostics(self):
        # kept for backwards compatibility
        # this method will be deprecated in future releases
        print("The 'ReqSensorDiagnostics()' method will be deprecated in future releases. Please use 'ReqSensorDiagnosticsChannelStatus()'")
        return self.ReqSensorDiagnosticsChannelStatus()

    def ReqSensorDiagnosticsChannelStatus(self):
        """
        Returns the Sensor Diagnostic Information (for a CMV12000 sensor).
        
        bot_chan_fail, top_chan_fail, ctrl_chan_fail = ReqSensorDiagnosticsChannelStatus()
    
        Returns the failed sensor interface channels as bit vectors.
        """
               
        req_id = 0x94
        req_length = 9
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSensorDiagnosticsChannelStatus request.\n{e}')                   

        if isinstance(retval, list):
            bot_chan_fail  = retval[0] + (retval[1]<<8) + (retval[2]<<16) + (retval[3]<<24)
            top_chan_fail  = retval[4] + (retval[5]<<8) + (retval[6]<<16) + (retval[7]<<24)
            ctrl_chan_fail = retval[8]

        return bot_chan_fail, top_chan_fail, ctrl_chan_fail

    def ReqSensorDiagnosticsChannelTiming(self):
        """
        Returns the Sensor Window Diagnostic Information (for a CMV12000 sensor).
        
        raw = ReqSensorDiagnosticsChannelTiming()
    
        Returns the sensor window centre values for each channel
        """
               
        req_id = 0x9D
        req_length = 65
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSensorDiagnosticsChannelTiming request.\n{e}')                   

        return retval

    # --- Parse the Imaging Parameters --- #

    def _parseImagingParameter_SensorAdcRange(self, *Values):
        """
        CMV12000 Register Address 116, bits 9:0
    
        Mandatory Arguments:
            Value   - The register value
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value >= 2**10:
            raise exceptions.InputError(f'Value parameter must be 10-bit unsigned, but "{Value}" was supplied.')                      

        byte0 = (Value>>0)%256
        byte1 = (Value>>8)%256
        
        return [byte0, byte1]

    def _parseImagingParameter_SensorBotOffset(self, *Values):
        """
        CMV12000 Register Address 87, bits 11:0
    
        Mandatory Arguments:
            Value   - The register value
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value >= 2**12:
            raise exceptions.InputError(f'Value parameter must be 12-bit unsigned, but "{Value}" was supplied.')

        byte0 = (Value>>0)%256
        byte1 = (Value>>8)%256
        
        return [byte0, byte1]

    def _parseImagingParameter_SensorTopOffset(self, *Values):
        """
        CMV12000 Register Address 88, bits 11:0
        
        Mandatory Arguments:
            Value   - The register value
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value >= 2**12:
            raise exceptions.InputError(f'Value parameter must be 12-bit unsigned, but "{Value}" was supplied.')

        byte0 = (Value>>0)%256
        byte1 = (Value>>8)%256
        
        return [byte0, byte1]

    def _parseImagingParameter_SensorGain(self, *Values):
        """
        CMV12000 Register Address 115, bits 3:0
    
        Mandatory Arguments:
            Value   - The register value
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value >= 2**4:
            raise exceptions.InputError(f'Value parameter must be 4-bit unsigned, but "{Value}" was supplied.')

        return Value

    def _parseImagingParameter_SensorBlackRefEnable(self, *Values):
        """
        CMV12000 Register Address 89, bit 15
    
        Mandatory Arguments:
            Value   - 0 or False
                    1 or True
        """
        try:
            Value = int(Values[0]) #this converts a bool to 0 (False) or 1 (True)
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer or bool, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value > 1:
            raise exceptions.InputError(f'Value parameter must be 0, 1, True or False, but "{Value}" was supplied.')

        return Value
        
    # --- Handle the Imaging Parameter Requests --- #
        
    def _handleImagingParameterReq_SensorAdcRange(self):
        """
        Return the Sensor ADC range (CMV12000 Register Address 116, bits 9:0).
        """        
        req_id = 0x89
        req_length = 2

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqImagingParameter request.\n{e}')               
                   
        if isinstance(retval, list):
            raw = retval[0] + (retval[1]<<8)
            
        return raw 
        
    def _handleImagingParameterReq_SensorBotOffset(self):
        """
        Return the Sensor Bottom Offset (CMV12000 Register Address 87, bits 11:0).
        """        
        req_id = 0x89
        req_length = 2

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqImagingParameter request.\n{e}')               
                   
        if isinstance(retval, list):
            raw = retval[0] + (retval[1]<<8)
            
        return raw       
        
    def _handleImagingParameterReq_SensorTopOffset(self):
        """
        Return the Sensor Bottom Offset (CMV12000 Register Address 88, bits 11:0).
        """        
        req_id = 0x89
        req_length = 2

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqImagingParameter request.\n{e}')               
                   
        if isinstance(retval, list):
            raw = retval[0] + (retval[1]<<8)
            
        return raw       

    def _handleImagingParameterReq_SensorGain(self):
        """
        Return the Sensor Gain (CMV12000 Register Address 115, bits 3:0).
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
        
    def _handleImagingParameterReq_SensorBlackRefEnable(self):
        """
        Return the Black Reference Enable (CMV12000 Register Address 89, bit 15).
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

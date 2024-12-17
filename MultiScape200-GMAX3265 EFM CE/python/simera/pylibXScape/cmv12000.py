'''
Simera Sense TriScape_CMV12000 Class
Copyright (c) 2019-2020 Simera Sense (info@simerasense.com)
Released under MIT License.
'''

from . import exceptions
from . import xscape


# Module Constants
IMAGING_PARAMID_CMV12K_ADC_RANGE = 0x10
IMAGING_PARAMID_CMV12K_BOT_OFFSET = 0x11
IMAGING_PARAMID_CMV12K_TOP_OFFSET = 0x12
IMAGING_PARAMID_CMV12K_GAIN = 0x13
IMAGING_PARAMID_CMV12K_BLACKREF_ENABLE = 0x14


class CMV12000(xscape.xScape):
    """
    CMV12000 class

    Inherits from the xSCape class and extends it for CMV12000 specific commands and requests.
    """

    def __init__(self, EGSE = None, I2Caddr = None):
        """
        CMV12000 Constructor
    
        __init__(EGSE = None, I2Caddr = None, threadLock = None)
    
        Optional Arguments:
            EGSE        - Instance of Simera EGSE class
            I2Caddr     - Set if using the I2C control interface
        """

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
    
    # --- Sensor Specific Requests --- #

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

'''
Simera Sense GMAX3265 Class
Copyright (c) 2019-2020 Simera Sense (info@simerasense.com)
Released under MIT License.
'''

from . import exceptions
from . import xscape




# Module Constants
IMAGING_PARAMID_GMAX3265_PGA_GAIN = 0x10
IMAGING_PARAMID_GMAX3265_ADC_GAIN = 0x11
IMAGING_PARAMID_GMAX3265_DARK_OFFSET = 0x12


class GMAX3265(xscape.xScape):
    """
    TriScape_GMAX3265 class

    Inherits from the xScape class and extends it for GMAX3265 specific commands and requests.
    """

    def __init__(self, EGSE = None, I2Caddr = None):
        """
        GMAX3265 Constructor
    
        __init__(EGSE = None, I2Caddr = None, threadLock = None)
    
        Optional Arguments:
            EGSE        - Instance of Simera EGSE class
            I2Caddr     - Set if using the I2C control interface
        """

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
            
    # --- Sensor Specific Requests --- #

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
        
    def ReqSensorDiagnosticsChannelSteps(self):
        """
        Returns Detailed Sensor Channel Diagnostic Information (for a GMAX3265 sensor).
        
        raw = ReqSensorDiagnosticsChannelTiming()
    
        Returns the sensor window calibration step results for one channel.
        """
               
        req_id = 0x9E
        req_length = 16
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSensorDiagnosticsChannelSteps request.\n{e}')                   

        return retval   

    def ReqSensorDiagnosticsChannelVerification(self):
        """
        Returns the Sensor Channel Diagnostic Verification Information (for a GMAX3265 sensor).
        
        raw = ReqSensorDiagnosticsChannelVerification()
    
        Returns the sensor validation values for each channel as well as the validation attempts.
        """
               
        req_id = 0x9F
        req_length = 113
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSensorDiagnosticsChannelVerification request.\n{e}')                   

        varify_val = [0]*56

        for i in range(56):
            varify_val[i] = retval[(i*2)+0] + (retval[(i*2)+1]<<8)

        return varify_val, retval[112]              
        
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

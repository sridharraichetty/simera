'''
Simera Sense MultiScapeCIS_CMV12000 Class
Copyright (c) 2019-2020 Simera Sense (info@simerasense.com)
Released under MIT License.
'''


import numpy as np
import time

from . import exceptions
from . import xscape



# Module Constants
IMAGING_PARAMID_LINESCAN_NUM_LINES = 0x30
IMAGING_PARAMID_LINESCAN_LINE_PERIOD = 0x31
IMAGING_PARAMID_LINESCAN_BAND_SETUP = 0x32
IMAGING_PARAMID_LINESCAN_BAND_START_ROW = 0x33
IMAGING_PARAMID_LINESCAN_SCAN_DIRECTION = 0x34
IMAGING_PARAMID_LINESCAN_BLACK_LEVEL = 0x35
IMAGING_PARAMID_LINESCAN_ENCODING = 0x36
IMAGING_PARAMID_LINESCAN_ENCODING_OFFSET = 0x37
IMAGING_PARAMID_LINESCAN_BAND_CWL = 0x38
IMAGING_PARAMID_LINESCAN_EXPOSURE_TIME = 0x39

class MultiScape(xscape.xScape):
    """
    MultiScape class

    Inherits from the xScape class and extends it for multiscape specific commands and requests
    """

    def __init__(self, EGSE = None, I2Caddr = None): # override the constructor
        """
        MultiScape Constructor
    
        __init__(EGSE = None, I2Caddr = None, threadLock = None)
    
        Optional Arguments:
            EGSE        - Instance of Simera EGSE class
            I2Caddr     - Set if using the I2C control interface
        """

        # run the parent (xScape) instance constructor
        super().__init__(EGSE, I2Caddr)

        # add the product specific functions to the parent (xscape) instance variable
        self.imaging_param_parser.update( {
                IMAGING_PARAMID_LINESCAN_NUM_LINES          : lambda x  : self._parseImagingParameter_LinescanNumLines(x),
                IMAGING_PARAMID_LINESCAN_LINE_PERIOD        : lambda x  : self._parseImagingParameter_LinescanLinePeriod(x),
                IMAGING_PARAMID_LINESCAN_BAND_SETUP         : lambda *x : self._parseImagingParameter_LinescanBandSetup(*x),
                IMAGING_PARAMID_LINESCAN_BAND_START_ROW     : lambda *x : self._parseImagingParameter_LinescanBandStartRow(*x),
                IMAGING_PARAMID_LINESCAN_SCAN_DIRECTION     : lambda x  : self._parseImagingParameter_LinescanScanDirection(x),
                IMAGING_PARAMID_LINESCAN_BLACK_LEVEL        : lambda x  : self._parseImagingParameter_LinescanBlackLevel(x),
                IMAGING_PARAMID_LINESCAN_ENCODING           : lambda x  : self._parseImagingParameter_LinescanEncoding(x),
                IMAGING_PARAMID_LINESCAN_ENCODING_OFFSET    : lambda x  : self._parseImagingParameter_LinescanEncodingOffset(x),
                IMAGING_PARAMID_LINESCAN_BAND_CWL           : lambda *x : self._parseImagingParameter_LinescanBandCwl(*x),
                IMAGING_PARAMID_LINESCAN_EXPOSURE_TIME      : lambda x  : self._parseImagingParameter_LinescanExposureTime(x)
            })

        self.imaging_param_req_handlers.update( {
                IMAGING_PARAMID_LINESCAN_NUM_LINES          : lambda  : self._handleImagingParameterReq_LinescanNumLines(),
                IMAGING_PARAMID_LINESCAN_LINE_PERIOD        : lambda  : self._handleImagingParameterReq_LinescanLinePeriod(),
                IMAGING_PARAMID_LINESCAN_BAND_SETUP         : lambda  : self._handleImagingParameterReq_LinescanBandSetup(),
                IMAGING_PARAMID_LINESCAN_BAND_START_ROW     : lambda  : self._handleImagingParameterReq_LinescanBandStartRow(),
                IMAGING_PARAMID_LINESCAN_SCAN_DIRECTION     : lambda  : self._handleImagingParameterReq_LinescanScanDirection(),
                IMAGING_PARAMID_LINESCAN_BLACK_LEVEL        : lambda  : self._handleImagingParameterReq_LinescanBlackLevel(),
                IMAGING_PARAMID_LINESCAN_ENCODING           : lambda  : self._handleImagingParameterReq_LinescanEncoding(),
                IMAGING_PARAMID_LINESCAN_ENCODING_OFFSET    : lambda  : self._handleImagingParameterReq_LinescanEncodingOffset(),
                IMAGING_PARAMID_LINESCAN_BAND_CWL           : lambda  : self._handleImagingParameterReq_LinescanBandCwl(),
                IMAGING_PARAMID_LINESCAN_EXPOSURE_TIME      : lambda  : self._handleImagingParameterReq_LinescanExposureTime()
            })
                
    # --- Parse the Imaging Parameters --- #

    def _parseImagingParameter_LinescanNumLines(self, *Values):
        """
        Parse command payload for Number of lines to capture per Session
    
        _parseImagingParameter_LinescanNumLines(Value)
    
        Mandatory Arguments:
            Value (uint32)  - Number of Lines
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value >= 2**32:
            raise exceptions.InputError(f'Value parameter must be unsigned 32-bit, but "{Value}" was supplied.')
        
        byte0 = (Value>>0)%256
        byte1 = (Value>>8)%256
        byte2 = (Value>>16)%256
        byte3 = (Value>>24)%256
        
        return [byte0, byte1, byte2, byte3]

    def _parseImagingParameter_LinescanLinePeriod(self, *Values):
        """
        Parse command payload for Line Period in microseconds
    
        _parseImagingParameter_LinescanLinePeriod(Value)
    
        Mandatory Arguments:
            Value (uint24)  - Line Period in microseconds
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value >= 2**32:
            raise exceptions.InputError(f'Value parameter must be unsigned 32-bit, but "{Value}" was supplied.')

        byte0 = (Value>>0)%256
        byte1 = (Value>>8)%256
        byte2 = (Value>>16)%256
        byte3 = (Value>>24)%256
        
        return [byte0, byte1, byte2, byte3]                

    def _parseImagingParameter_LinescanBandSetup(self, *Values): #(Band, NumTdiStages):
        """
        Parse command payload for Number of TDI stages for the specified band
    
        _parseImagingParameter_LinescanBandSetup(Band, NumTdiStages)
    
        Mandatory Arguments:
            Band         (uint8) - The Band Number
            NumTdiStages (uint8) - Number of TDI Stages for this band
        """
        try:
            Band = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Band parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Band < 0 or Band >= self.bands:
            raise exceptions.InputError(f'Band parameter must be between 0 and {self.bands-1}, but "{Band}" was supplied.')

        try:
            NumTdiStages = int(Values[1])           
        except ValueError as e:
            raise exceptions.InputError(f'NumTdiStages parameter must be an integer, but "{Values[1]}" was supplied.\n{e}')
        if NumTdiStages < 0 or NumTdiStages >= 32:
            raise exceptions.InputError(f'NumTdiStages parameter must be between 0 and 32, but "{NumTdiStages}" was supplied.')

        return [Band, NumTdiStages]

    def _parseImagingParameter_LinescanBandStartRow(self, *Values): #(Band, StartRow):
        """
        Parse command payload for Start Row for the specified band
    
        _parseImagingParameter_LinescanBandStartRow(Band, StartRow)
    
        Mandatory Arguments:
            Band         (uint8)  - The Band Number
            StartRow     (uint16) - Start Row for this band
        """
        try:
            Band = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Band parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Band < 0 or Band >= self.bands:
            raise exceptions.InputError(f'Band parameter must be between 0 and {self.bands-1}, but "{Band}" was supplied.')

        try:
            StartRow = int(Values[1])
        except ValueError as e:
            raise exceptions.InputError(f'StartRow parameter must be an integer, but "{Values[1]}" was supplied.\n{e}')
        if StartRow < 0 or StartRow >= 2**16:
            raise exceptions.InputError(f'StartRow parameter must be unsigned 16-bit, but "{StartRow}" was supplied.')

        StartRow_byte0 = (StartRow>>0)%256
        StartRow_byte1 = (StartRow>>8)%256

        return [Band, StartRow_byte0, StartRow_byte1]

    def _parseImagingParameter_LinescanScanDirection(self, *Values):
        """
        Parse command payload for Linescan Direction command
    
        _parseImagingParameter_LinescanScanDirection(Value)
    
        Mandatory Arguments:
            Value (bool) - True for positive scan direction
                         - False for negative scan direction
        """
        try:
            Value = int(Values[0]) #this converts a bool to 0 (False) or 1 (True)
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer or bool, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value > 1:
            raise exceptions.InputError(f'Value parameter must be 0, 1, True or False, but "{Value}" was supplied.')

        return [Value]
        
    def _parseImagingParameter_LinescanBlackLevel(self, *Values):
        """
        Parse command payload for Linescan BlackLevel command
    
        _parseImagingParameter_LinescanBlackLevel(Value)
    
        Mandatory Arguments:
            Value (uint16) - Black Level for TDI processing.
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Black Level parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value >= 2**10:
            raise exceptions.InputError(f'Band parameter must be unsigned 10-bit, but "{Value}" was supplied.')

        byte0 = (Value>>0)%256
        byte1 = (Value>>8)%256
        
        return [byte0, byte1]   

    def _parseImagingParameter_LinescanEncoding(self, *Values):
        """
        Parse command payload for Encoding (pixel depth)
    
        _parseImagingParameter_LinescanEncoding(Value)
    
        Mandatory Arguments:
            Value (uint8) - Number of bits (8 or 12)
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Encoding parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value not in (8,12):
            raise exceptions.InputError(f'Encoding parameter must be 8 or 12, but "{Value}" was supplied.')       

        return [Value]  

    def _parseImagingParameter_LinescanEncodingOffset(self, *Values):
        """
        Parse command payload for Encoding Offset (only applicable to 8-bit encoding and thumbnails)
    
        _parseImagingParameter_LinescanEncodingOffset(Value)
    
        Mandatory Arguments:
            Value (uint8) - Bit Offset (0 = High, 1 = Middle, 2 = Low)
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Encoding Offset parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value not in (0,1,2):
            raise exceptions.InputError(f'Encoding Offset parameter must be 0, 1 or 2, but "{Value}" was supplied.')       

        return [Value]              

    def _parseImagingParameter_LinescanBandCwl(self, *Values): #(Band, Cwl):
        """
        Parse command payload for Centre Wave Length for a specified band (only applicable for Hyperspectral Imagers)
    
        _parseImagingParameter_LinescanCwl(Band, Cwl)
    
        Mandatory Arguments:
            Band    (uint8)  - The Band Number
            Cwl     (uint16) - Centre Wave Length for this band (in nanometers)
        """
        try:
            Band = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Band parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Band < 0 or Band >= self.bands:
            raise exceptions.InputError(f'Band parameter must be between 0 and {self.bands-1}, but "{Band}" was supplied.')

        try:
            Cwl = int(Values[1])
        except ValueError as e:
            raise exceptions.InputError(f'StartRow parameter must be an integer, but "{Values[1]}" was supplied.\n{e}')
        if Cwl < 0 or Cwl >= 2**16:
            raise exceptions.InputError(f'StartRow parameter must be unsigned 16-bit, but "{StartRow}" was supplied.')

        Cwl_byte0 = (Cwl>>0)%256
        Cwl_byte1 = (Cwl>>8)%256

        return [Band, Cwl_byte0, Cwl_byte1]

    def _parseImagingParameter_LinescanExposureTime(self, *Values):
        """
        Parse command payload for Exposure Time in microseconds
    
        _parseImagingParameter_LinescanExposureTime(Value)
    
        Mandatory Arguments:
            Value (uint32)  - Exposure time in microseconds
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value >= 2**24:
            raise exceptions.InputError(f'Value parameter must be unsigned 32-bit, but "{Value}" was supplied.')

        byte0 = (Value>>0)%256
        byte1 = (Value>>8)%256
        byte2 = (Value>>16)%256
        byte3 = (Value>>24)%256
        
        return [byte0, byte1, byte2, byte3]        
        
    # --- Handle the Imaging Parameter Requests --- #
        
    def _handleImagingParameterReq_LinescanNumLines(self):
        """
        Return the Number of Lines    
        """        
        req_id = 0x89
        req_length = 4

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqImagingParameter request.\n{e}')               
                   
        if isinstance(retval, list):
            raw = retval[0] + (retval[1]<<8) + (retval[2]<<16) + (retval[3]<<24)
            
        return raw 

    def _handleImagingParameterReq_LinescanLinePeriod(self):
        """
        Return the Line Scan Period  
        """        
        req_id = 0x89
        req_length = 4

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqImagingParameter request.\n{e}')               
                   
        if isinstance(retval, list):
            raw = retval[0] + (retval[1]<<8) + (retval[2]<<16) + (retval[3]<<24)
            
        return raw 
        
    def _handleImagingParameterReq_LinescanBandSetup(self):
        """
        Return the Band Setup (TDI stages per Band, 0 = disabled)    
        """        
        req_id = 0x89
        req_length = self.bands

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqImagingParameter request.\n{e}')                                          
            
        return retval 

    def _handleImagingParameterReq_LinescanBandStartRow(self):
        """
        Return the Band Start Row    
        """        
        req_id = 0x89
        req_length = self.bands*2

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqImagingParameter request.\n{e}')                                          

        raw = [0]*self.bands
        
        if isinstance(retval, list):                        
            for i in range(len(retval)//2):                
                # list of 16-bit values
                raw[i] = (retval[(i*2)+0]<<0) + (retval[(i*2)+1]<<8)
                
        return raw 

    def _handleImagingParameterReq_LinescanScanDirection(self):
        """
        Return the Scan Direction    
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

    def _handleImagingParameterReq_LinescanBlackLevel(self):
        """
        Return the Black Level.    
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

    def _handleImagingParameterReq_LinescanEncoding(self):
        """
        Return the Encoding (pixel depth)    
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
        
    def _handleImagingParameterReq_LinescanEncodingOffset(self):
        """
        Return the Encoding Offset (bit offset for 8-bit encoding)    
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
        
    def _handleImagingParameterReq_LinescanBandCwl(self):
        """
        Return the Centre Wave Lengths
        """        
        req_id = 0x89
        req_length = self.bands*2

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqImagingParameter request.\n{e}')                                          

        raw = [0]*self.bands
        
        if isinstance(retval, list):                        
            for i in range(len(retval)//2):                
                # list of 16-bit values
                raw[i] = (retval[(i*2)+0]<<0) + (retval[(i*2)+1]<<8)            
                
        return raw
        
    def _handleImagingParameterReq_LinescanExposureTime(self):
        """
        Return the Exposure Time    
        """        
        req_id = 0x89
        req_length = 4

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqImagingParameter request.\n{e}')                                 
            
        if isinstance(retval, list):
            raw = retval[0] + (retval[1]<<8) + (retval[2]<<16) + (retval[3]<<24)
            
        return raw
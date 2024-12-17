'''
Simera Sense SnapShot Class
Copyright (c) 2019-2022 Simera Sense (info@simera-sense.com)
Released under MIT License.
'''

from . import exceptions
from . import xscape



# Module Constants
IMAGING_PARAMID_SNAPSHOT_NUM_FRAMES = 0x20
IMAGING_PARAMID_SNAPSHOT_FRAME_INTERVAL = 0x21
IMAGING_PARAMID_SNAPSHOT_ENCODING = 0x22
IMAGING_PARAMID_SNAPSHOT_EXPOSURE_TIME = 0x23
IMAGING_PARAMID_SNAPSHOT_ENCODING_OFFSET = 0x24

class SnapShot(xscape.xScape):
    """
    SnapShot class

    Inherits from the xScape class and extends it for snapshot specific commands and requests
    """

    def __init__(self, EGSE = None, I2Caddr = None): # override the constructor
        """
        SnapShot Constructor
    
        __init__(EGSE = None, I2Caddr = None, threadLock = None)
    
        Optional Arguments:
            EGSE        - Instance of Simera EGSE class
            I2Caddr     - Set if using the I2C control interface
        """

        # run the parent (xScape) instance constructor
        super().__init__(EGSE, I2Caddr)

        # add the product specific functions to the parent (xscape) instance variable
        self.imaging_param_parser.update( {
                IMAGING_PARAMID_SNAPSHOT_NUM_FRAMES      : lambda x : self._parseImagingParameter_SnapshotNumFrames(x),
                IMAGING_PARAMID_SNAPSHOT_FRAME_INTERVAL  : lambda x : self._parseImagingParameter_SnapshotFrameInterval(x),
                IMAGING_PARAMID_SNAPSHOT_ENCODING        : lambda x : self._parseImagingParameter_SnapshotEncoding(x),
                IMAGING_PARAMID_SNAPSHOT_EXPOSURE_TIME   : lambda x : self._parseImagingParameter_SnapshotExposureTime(x),
                IMAGING_PARAMID_SNAPSHOT_ENCODING_OFFSET : lambda x : self._parseImagingParameter_SnapshotEncodingOffset(x)
            })

        self.imaging_param_req_handlers.update( {
                IMAGING_PARAMID_SNAPSHOT_NUM_FRAMES      : lambda  : self._handleImagingParameterReq_SnapshotNumFrames(),
                IMAGING_PARAMID_SNAPSHOT_FRAME_INTERVAL  : lambda  : self._handleImagingParameterReq_SnapshotFrameInterval(),
                IMAGING_PARAMID_SNAPSHOT_ENCODING        : lambda  : self._handleImagingParameterReq_SnapshotEncoding(),
                IMAGING_PARAMID_SNAPSHOT_EXPOSURE_TIME   : lambda  : self._handleImagingParameterReq_SnapshotExposureTime(),
                IMAGING_PARAMID_SNAPSHOT_ENCODING_OFFSET : lambda  : self._handleImagingParameterReq_SnapshotEncodingOffset()
            })            

    # --- Parse the Imaging Parameters --- #

    def _parseImagingParameter_SnapshotNumFrames(self, *Values):
        """
        Parse command payload for Number of frames to capture (burst)
    
        _parseImagingParameter_SnapshotNumFrames(Value)
    
        Mandatory Arguments:
            Value (uint8)  - Number of frames
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value >= 2**8:
            raise exceptions.InputError(f'Value parameter must be unsigned 8-bit, but "{Value}" was supplied.')       
        
        return [Value]

    def _parseImagingParameter_SnapshotFrameInterval(self, *Values):
        """
        Parse command payload for Frame Interval in microseconds
    
        _parseImagingParameter_SnapshotFrameInterval(Value)
    
        Mandatory Arguments:
            Value (uint32)  - Frame Interval in microseconds
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

    def _parseImagingParameter_SnapshotEncoding(self, *Values):
        """
        Parse command payload for Encoding (pixel depth)
    
        _parseImagingParameter_SnapshotEncoding(Value)
    
        Mandatory Arguments:
            Value (uint8) - Number of bits (8 or 10)
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Encoding parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value not in (8,10):
            raise exceptions.InputError(f'Encoding parameter must be 8 or 10, but "{Value}" was supplied.')       

        return [Value]

    def _parseImagingParameter_SnapshotExposureTime(self, *Values):
        """
        Parse command payload for Exposure Time in microseconds
    
        _parseImagingParameter_SnapshotExposureTime(Value)
    
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
        
    def _parseImagingParameter_SnapshotEncodingOffset(self, *Values):
        """
        Parse command payload for Encoding Offset (only applicable to 8-bit encoding and thumbnails)
    
        _parseImagingParameter_SnapshotEncodingOffset(Value)
    
        Mandatory Arguments:
            Value (uint8) - Bit Offset from MSB (0 = High, 1 = Middle, 2 = Low)
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Encoding Offset parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value not in (0,1,2):
            raise exceptions.InputError(f'Encoding Offset parameter must be 0, 1 or 2, but "{Value}" was supplied.')       

        return [Value]

    # --- Handle the Imaging Parameter Requests --- #
        
    def _handleImagingParameterReq_SnapshotNumFrames(self):
        """
        Return the Number of frames    
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

    def _handleImagingParameterReq_SnapshotFrameInterval(self):
        """
        Return the Frame Interval (in microseconds)  
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
        
    def _handleImagingParameterReq_SnapshotEncoding(self):
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

    def _handleImagingParameterReq_SnapshotExposureTime(self):
        """
        Return the Exposure Time (in microseonds)
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
        
    def _handleImagingParameterReq_SnapshotEncodingOffset(self):
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
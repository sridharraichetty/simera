'''
Simera Sense Video Functionality
Copyright (c) 2019-2022 Simera Sense (info@simera-sense.com)
Released under MIT License.
'''

from . import exceptions
from . import xscape
import types


# Module Constants
IMAGING_PARAMID_VIDEO_DURATION = 0x40
IMAGING_PARAMID_VIDEO_EXPOSURE_TIME = 0x41
IMAGING_PARAMID_VIDEO_MODE = 0x42
IMAGING_PARAMID_VIDEO_QUANIZATION = 0x43
IMAGING_PARAMID_VIDEO_ENCODING_OFFSET = 0x44
IMAGING_PARAMID_VIDEO_SIZE_DIVIDER = 0x45


# --- Video specific commands --- #
    
def CaptureVideo(self):
    """
    Initiate the video capture process        
    """              
    data = [0x28]

    try:
        retval = self._CtrlIfWrite(data)
    except Exception as e:
        raise exceptions.Error(f'Error sending CaptureImage command.\n{e}')         


# --- Parse the Imaging Parameters --- #

def _parseImagingParameter_VideoDuration(self, *Values):
    """
    Parse command payload for Video Duration in seconds

    _parseImagingParameter_VideoDuration(Value)

    Mandatory Arguments:
        Value (uint16)  - Duration seconds
    """
    try:
        Value = int(Values[0])
    except ValueError as e:
        raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
    if Value < 0 or Value >= 2**16:
        raise exceptions.InputError(f'Value parameter must be unsigned 16-bit, but "{Value}" was supplied.')

    byte0 = (Value>>0)%256
    byte1 = (Value>>8)%256
    
    return [byte0, byte1]      

def _parseImagingParameter_VideoExposureTime(self, *Values):
    """
    Parse command payload for Video Exposure Time in microseconds

    _parseImagingParameter_VideoExposureTime(Value)

    Mandatory Arguments:
        Value (uint32)  - Exposure time in microseconds
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
    
def _parseImagingParameter_VideoMode(self, *Values):
    """
    Parse command payload for Video Mode (crop, binned, sub-sampled)

    _parseImagingParameter_VideoMode(Value)

    Mandatory Arguments:
        Value (uint8) - Video Mode (0 = Crop, 1 = Binned2x, 2 = Sub-sampled 2x, 3 = Sub-sampled 4x)
    """
    try:
        Value = int(Values[0])
    except ValueError as e:
        raise exceptions.InputError(f'Video Mode parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
    if Value not in (0,1,2,3):
        raise exceptions.InputError(f'Video Mode parameter must be 0, 1, 2 or 3, but "{Value}" was supplied.')       

    return [Value]          

def _parseImagingParameter_VideoQuantization(self, *Values):
    """
    Parse command payload for Video Quantization Parameter

    _parseImagingParameter_VideoQuantization(Value)

    Mandatory Arguments:
        Value (uint8) - Quantization Parameter
    """
    try:
        Value = int(Values[0])
    except ValueError as e:
        raise exceptions.InputError(f'Quantization parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
    if Value < 0 or Value >= 2**8:
        raise exceptions.InputError(f'Quantization parameter must be unsigned 8-bit, but "{Value}" was supplied.')       

    return [Value]      
    
def _parseImagingParameter_VideoEncodingOffset(self, *Values):
    """
    Parse command payload for Video Encoding Offset

    _parseImagingParameter_VideoEncodingOffset(Value)

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
    
def _parseImagingParameter_VideoSizeDivider(self, *Values):
    """
    Parse command payload for Video Size Divider

    _parseImagingParameter_VideoSizeDivider(Value)

    Mandatory Arguments:
        Value (uint8) - Divide to calculate storage space (uncompressed vs compressed video size)
    """
    try:
        Value = int(Values[0])
    except ValueError as e:
        raise exceptions.InputError(f'Video Size Divider parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
    if Value < 0 or Value >= 2**8:
        raise exceptions.InputError(f'Video Size Divider parameter must be unsigned 8-bit, but "{Value}" was supplied.')       

    return [Value]            

# --- Handle the Imaging Parameter Requests --- #

def _handleImagingParameterReq_VideoDuration(self):
    """
    Return the Video Duration (in seconds)
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
    
def _handleImagingParameterReq_VideoExposureTime(self):
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

def _handleImagingParameterReq_VideoMode(self):
    """
    Return the Video Mode (Crop or Binned)   
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

def _handleImagingParameterReq_VideoQuantization(self):
    """
    Return the Video Quantization Parameter
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
    
def _handleImagingParameterReq_VideoEncodingOffset(self):
    """
    Return the Video Encoding Offset (bit offset for 8-bit encoding)    
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
    
def _handleImagingParameterReq_VideoSizeDivider(self):
    """
    Return the Video Size DIvider
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


def Init(xScapeInstance):
    """
    Expand xScape class Instance with Video H.264 functionality.
    """

    #Extend the xScape's local dictionary variables.
    xScapeInstance.imaging_param_parser.update( {
            IMAGING_PARAMID_VIDEO_DURATION           : lambda x : xScapeInstance._parseImagingParameter_VideoDuration(x),
            IMAGING_PARAMID_VIDEO_EXPOSURE_TIME      : lambda x : xScapeInstance._parseImagingParameter_VideoExposureTime(x),
            IMAGING_PARAMID_VIDEO_MODE               : lambda x : xScapeInstance._parseImagingParameter_VideoMode(x),
            IMAGING_PARAMID_VIDEO_QUANIZATION        : lambda x : xScapeInstance._parseImagingParameter_VideoQuantization(x),
            IMAGING_PARAMID_VIDEO_ENCODING_OFFSET    : lambda x : xScapeInstance._parseImagingParameter_VideoEncodingOffset(x),
            IMAGING_PARAMID_VIDEO_SIZE_DIVIDER       : lambda x : xScapeInstance._parseImagingParameter_VideoSizeDivider(x)
        })
        
    xScapeInstance.imaging_param_req_handlers.update( {
            IMAGING_PARAMID_VIDEO_DURATION           : lambda  : xScapeInstance._handleImagingParameterReq_VideoDuration(),
            IMAGING_PARAMID_VIDEO_EXPOSURE_TIME      : lambda  : xScapeInstance._handleImagingParameterReq_VideoExposureTime(),
            IMAGING_PARAMID_VIDEO_MODE               : lambda  : xScapeInstance._handleImagingParameterReq_VideoMode(),
            IMAGING_PARAMID_VIDEO_QUANIZATION        : lambda  : xScapeInstance._handleImagingParameterReq_VideoQuantization(),
            IMAGING_PARAMID_VIDEO_ENCODING_OFFSET    : lambda  : xScapeInstance._handleImagingParameterReq_VideoEncodingOffset(),
            IMAGING_PARAMID_VIDEO_SIZE_DIVIDER       : lambda  : xScapeInstance._handleImagingParameterReq_VideoSizeDivider()
        })

    
    #The functions that get added as methods for this instance only
    xScapeInstance.CaptureVideo                                     = types.MethodType(CaptureVideo, xScapeInstance)
    xScapeInstance._parseImagingParameter_VideoDuration             = types.MethodType(_parseImagingParameter_VideoDuration, xScapeInstance)
    xScapeInstance._parseImagingParameter_VideoExposureTime         = types.MethodType(_parseImagingParameter_VideoExposureTime, xScapeInstance)
    xScapeInstance._parseImagingParameter_VideoMode                 = types.MethodType(_parseImagingParameter_VideoMode, xScapeInstance)
    xScapeInstance._parseImagingParameter_VideoQuantization         = types.MethodType(_parseImagingParameter_VideoQuantization, xScapeInstance)
    xScapeInstance._parseImagingParameter_VideoEncodingOffset       = types.MethodType(_parseImagingParameter_VideoEncodingOffset, xScapeInstance)
    xScapeInstance._parseImagingParameter_VideoSizeDivider          = types.MethodType(_parseImagingParameter_VideoSizeDivider, xScapeInstance)
    xScapeInstance._handleImagingParameterReq_VideoDuration         = types.MethodType(_handleImagingParameterReq_VideoDuration, xScapeInstance)
    xScapeInstance._handleImagingParameterReq_VideoExposureTime     = types.MethodType(_handleImagingParameterReq_VideoExposureTime, xScapeInstance)
    xScapeInstance._handleImagingParameterReq_VideoMode             = types.MethodType(_handleImagingParameterReq_VideoMode, xScapeInstance)
    xScapeInstance._handleImagingParameterReq_VideoQuantization     = types.MethodType(_handleImagingParameterReq_VideoQuantization, xScapeInstance)
    xScapeInstance._handleImagingParameterReq_VideoEncodingOffset   = types.MethodType(_handleImagingParameterReq_VideoEncodingOffset, xScapeInstance)
    xScapeInstance._handleImagingParameterReq_VideoSizeDivider      = types.MethodType(_handleImagingParameterReq_VideoSizeDivider, xScapeInstance)
    xScapeInstance._handleImagingParameterReq_VideoEncodingOffset   = types.MethodType(_handleImagingParameterReq_VideoEncodingOffset, xScapeInstance)
    xScapeInstance._handleImagingParameterReq_VideoEncodingOffset   = types.MethodType(_handleImagingParameterReq_VideoEncodingOffset, xScapeInstance)
    xScapeInstance._handleImagingParameterReq_VideoEncodingOffset   = types.MethodType(_handleImagingParameterReq_VideoEncodingOffset, xScapeInstance)
    xScapeInstance._handleImagingParameterReq_VideoEncodingOffset   = types.MethodType(_handleImagingParameterReq_VideoEncodingOffset, xScapeInstance)
    
    print(f'Extended instance with H.264 Video functionality')
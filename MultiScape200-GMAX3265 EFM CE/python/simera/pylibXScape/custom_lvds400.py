'''
Simera Sense Custom LVDS Data Interface 400 Mbps Functionality
Copyright (c) 2019-2022 Simera Sense (info@simera-sense.com)
Released under MIT License.
'''

from . import exceptions
from . import xscape
import types


# Module Constants
SYSTEM_PARAMID_LVDS_DATA_LANES = 0x50
SYSTEM_PARAMID_LVDS_DATA_RATE_MODE = 0x51

# --- Parse the System Parameters --- #

def _parseSystemParameter_LvdsDataLanes(self, *Values):  
    """
    HSDIF Lvds Data Lanes
     - Sets the number of data lanes
     - Accepted values are 1 and 2

    Mandatory Arguments:
        Value (uint8)  - 1 or 2
    """
    try:
        Value = int(Values[0])
    except ValueError as e:
        raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
    if Value not in (1,2):
        raise exceptions.InputError(f'Value parameter must be 1 or 2, but "{Value}" was supplied.')
    
    return Value        
    
def _parseSystemParameter_LvdsDataRateMode(self, *Values):  
    """
    SpaceWire Data Payload Limit
     - Limits the size of the Standard Data Format Payload Field, generating sub-packets.
     - A typical values is 1024 bytes or no limit (zero)

    Mandatory Arguments:
        Value (uint16)  - Unlimited (0) or Limit (must be a multiple of 4)
    """
    try:
        Value = int(Values[0])
    except ValueError as e:
        raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
    if Value < 0 or Value > 7:
        raise exceptions.InputError(f'Value parameter must be 0 to 7, but "{Value}" was supplied.')             
    
    return Value     

# --- Handle System Parameter Requests --- //  

def _handleSystemParameterReq_LvdsDataLanes(self):
    """
    Return the number of LVDS Data lanes.

    """        
    req_id = 0x8E
    req_length = 1
    
    try:
        retval = self._CtrlIfRead(req_id, req_length)
    except Exception as e:
        raise exceptions.Error(f'Error sending ReqSystemParameter request.\n{e}')
        
    if isinstance(retval, list):
        raw = retval[0]
    else:
        raw = retval
        
    return raw               
    
def _handleSystemParameterReq_LvdsDataRateMode(self):
    """
    Return the LVDS Data Rate Mode.

    """        
    req_id = 0x8E
    req_length = 1
    
    try:
        retval = self._CtrlIfRead(req_id, req_length)
    except Exception as e:
        raise exceptions.Error(f'Error sending ReqSystemParameter request.\n{e}')
        
    if isinstance(retval, list):
        raw = retval[0]
    else:
        raw = retval
        
    return raw      

def Init(xScapeInstance):
    """
    Expand xScape class Instance with Custom LVDS 400 Mbps functionality.
    """

    # Extend the xScape's local dictionary variables.
    xScapeInstance.system_param_parser.update( {
            SYSTEM_PARAMID_LVDS_DATA_LANES                      : lambda x  : xScapeInstance._parseSystemParameter_LvdsDataLanes(x),
            SYSTEM_PARAMID_LVDS_DATA_RATE_MODE                  : lambda x  : xScapeInstance._parseSystemParameter_LvdsDataRateMode(x)
        } )
        
    xScapeInstance.system_param_req_handlers.update( {            
            SYSTEM_PARAMID_LVDS_DATA_LANES                      : lambda : xScapeInstance._handleSystemParameterReq_LvdsDataLanes(),
            SYSTEM_PARAMID_LVDS_DATA_RATE_MODE                  : lambda : xScapeInstance._handleSystemParameterReq_LvdsDataRateMode()
        })

    
    # Extend the instance    
    xScapeInstance._parseSystemParameter_LvdsDataLanes              = types.MethodType(_parseSystemParameter_LvdsDataLanes, xScapeInstance)
    xScapeInstance._parseSystemParameter_LvdsDataRateMode           = types.MethodType(_parseSystemParameter_LvdsDataRateMode, xScapeInstance)
    xScapeInstance._handleSystemParameterReq_LvdsDataLanes          = types.MethodType(_handleSystemParameterReq_LvdsDataLanes, xScapeInstance)
    xScapeInstance._handleSystemParameterReq_LvdsDataRateMode       = types.MethodType(_handleSystemParameterReq_LvdsDataRateMode, xScapeInstance)
    
    print(f'Extended instance with Custom 400 Mbps LVDS functionality.')
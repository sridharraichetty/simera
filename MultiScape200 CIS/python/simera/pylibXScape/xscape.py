'''
Base Class to interface with Simera Sense xScape range of products
Copyright (c) 2019-2022 Simera Sense (info@simera-sense.com)
Released under MIT License.
'''



import numpy
import time

# Get _tread.allocate_lock() to make class thread-safe. Import _thread instead of threading to reduce startup cost
try:
    from _thread import allocate_lock as Lock
except ImportError: # should never happen - threading always included in Python 3.7+
    from _dummy_thread import allocate_lock as Lock


from . import exceptions
import simera.pylibEgseFx3



# Module Constants
CONTROL_INTERFACE_I2C = 1
CONTROL_INTERFACE_SPI = 2
CONTROL_INTERFACE_SpW = 3
CONTROL_INTERFACE_CAN = 4
CONTROL_INTERFACE_RS4xx = 5

PLATFORM_TIME_FORMAT_TAI = 0
PLATFORM_TIME_FORMAT_UTC = 1
PLATFORM_TIME_FORMAT_OTHER = 2

# System Parameters
SYSTEM_PARAMID_FLASH_TARGETS = 0x00
SYSTEM_PARAMID_FLASH_LUNS_DISABLE = 0x01
SYSTEM_PARAMID_DATA_INTERFACE = 0x02
SYSTEM_PARAMID_SENSOR_TEMP_CAL_A = 0x03
SYSTEM_PARAMID_SENSOR_TEMP_CAL_B = 0x04
SYSTEM_PARAMID_LATCH_CHAN_EN = 0x20
SYSTEM_PARAMID_LATCH_CHAN_LIMITS = 0x21
SYSTEM_PARAMID_LATCH_FILTER_COUNT = 0x22
SYSTEM_PARAMID_MONITOR_ECC_SETUP = 0x23
SYSTEM_PARAMID_MONITOR_WDT_ENABLE = 0x24
SYSTEM_PARAMID_MONITOR_WDT_DIVISOR = 0x25
SYSTEM_PARAMID_SPACEWIRE_BAUD_RATE = 0x40
SYSTEM_PARAMID_SPACEWIRE_IMAGER_LOG_ADDR = 0x41
SYSTEM_PARAMID_SPACEWIRE_CONTROL_HOST_LOG_ADDR = 0x42
SYSTEM_PARAMID_SPACEWIRE_CONTROL_HOST_ROUTING_BYTE = 0x43
SYSTEM_PARAMID_SPACEWIRE_DATA_HOST_LOG_ADDR = 0x44
SYSTEM_PARAMID_SPACEWIRE_DATA_HOST_ROUTING_BYTE = 0x45
SYSTEM_PARAMID_SPACEWIRE_DATA_PROTOCOL_SELECT = 0x46
SYSTEM_PARAMID_SPACEWIRE_DATA_PAY_LIMIT = 0x47

# Imaging Parameters
IMAGING_PARAMID_THUMB_FACTOR = 0x00
IMAGING_PARAMID_PLATFORM_ID = 0x01
IMAGING_PARAMID_INSTRUMENT_ID = 0x02
IMAGING_PARAMID_BINNING_FACTOR = 0x03

IMAGING_PARAM_THUMBNAIL_FACTORS = [0, 8, 16, 32, 64]
IMAGING_PARAM_BINNING_FACTORS = [0, 2, 4]

CONFIGURE_MODES = [0, 1, 2, 3, 4, 5]

# Protocol Options (SpaceWire and RS422)
CONTROL_PROTOCOL_STANDARD = 0
CONTROL_PROTOCOL_CCSDS_BASIC = 2 # Primary Header
CONTROL_PROTOCOL_CCSDS_FULL = 3 # Primary and Secondary Headers
CONTROL_PROTOCOLS = [CONTROL_PROTOCOL_STANDARD, CONTROL_PROTOCOL_CCSDS_BASIC, CONTROL_PROTOCOL_CCSDS_FULL]

# Command Status Strings
COMMAND_STATUS_STRINGS = {0:'Done',                                 # Command has completed
                          1:'Busy',                                 # Command is busy (still executing)
                          2:'Invalid command ID',                   # Command ID is unknown (not valid)
                          3:'Invalid transaction length',           # Command transaction length is incorrect
                          4:'Invalid parameter',	                # Command Parameter is invalid (out of range)
                          5:'Session is already open',	            # Can’t open a session that is already open or active
                          6:'Session directory is full',	        # Can’t create/open a new session (Directory full).
                          7:'Session not open',	                    # Can’t Activate a session unless it is already open.
                          8:'Imager not configured',	            # Auto Mode activation requires configured state.
                          9:'Not enough free space in Flash memory',# Space required for session is not available in Flash.
                         10:'Session not found',	                # Session not found.
                         11:'Session not active',                   # Session not active, can’t store packet.
                         12:'Invalid user data length',	            # User packet data payload length incorrect.
                         13:'Timeout storing user data to Flash',	# User packet timeout storing to Flash.
                         14:'Flash erase failed',	                # Flash Erase failed.                         
                         15:'Flash capture setup failed',           # Flash Capture Setup failed
                         16:'Session Invalid',                      # Session Checksum failed
                         17:'Flash Read Setup',                     # Session could not be read out as Flash setup failed
                         18:'Flash No Repsonse',	                # Session read out failed as flash does not respond (don't go busy)
                         19:'Flash Already Busy',	                # Session read out failed as flash is already busy
                         20:'Imager not configured',	            # Can’t capture image when not configured.
                         24:'Line Limit Exceeded',                  # Can't configure line scan as line limit is exceeded.
                         25:'No bands enabled',	                    # Can't Configure line scan with no bands enabled.
                         26:'Imaging parameter error',	            # Can't configure since one or more Imaging Parameters are invalid.
                         27:'Burst Exposure Time Incompatible',     # Can't configure snapshot burst as Exposure is larger than maximum for specified Frame Interval.
                         28:'Linescan Exposure Time Incompatible',  # Can't configure line scan as Exposure is larger than maximum for specified Line Period.
                         29:'Total TDI Limit Exceeded',             # Can't configure line scan as total TDI limit is exceeded.
                         30:'Sensor not ready',	                    # Sensor not ready after power-up.
                         31:'Sensor not enabled',	                # Sensor is disabled, can’t capture or read FEE telemetry.
                         32:'Sensor busy capturing',	            # Sensor is busy capturing, so cannot access the FEE ADC telemetry.
                         33:'FEE ADC remains busy',	                # Reading the FEE Telemtry failed, as the ADC remained busy.
                         34:'Sensor LVDS failed',	                # LVDS channels of the sensor did not initialise correctly.
                         41:'Magic number incorret',                # Magic number provided is incorrect, command won't execute.
                         42:'Bad Block Invalid',                    # Cannot set or clear the bad block as it is already at hte requested state
                         50:'No SpaceWire Link',                    # Cannot enable SpaceWire Data Output as a link is not established.
                         51:'Encryption already enabled',           # Cannot setup Encryption if it is already enabled.
                         52:'Encryption not ready',                 # Cannot enable Encryption if it is busy or Key is not setup.
                         53:'Compress Error No Scene',              # Cannot compress a session without a scene start packet
                         54:'Compress Error No Line',               # Cannot compress a session without line data packets
                         55:'Compress Error Size',                  # Compression request is too large (cannot generate more than 2 Gbytes)                            
                         56:'Compress Error Height',                # Cannot Compression a session with less than 128 lines
                         57:'One-Wire Temp Sensor Timeout',         # Timeout while accessing a One-Wire Temperature Sensor
                         58:'One-Wire Sensor ID not found',         # One-Wire Temperature Sensor IDs are not found/programmed.
                         70:'Boot Applcation Number',               # Cannot boot, invlad application number
                         71:'Program No Setup',                     # Cannot program bad before setup
                         72:'Program Setup Header',                 # Programming Setup provided header is invalid
                         73:'Program Data No Space',                # Programming Data failed as there is no more space
                         74:'Program Checksum',                     # Programmed Data calculated checksum does not match that in the header
                         75:'Program Length',                       # Programmed Data length does not match that in the header
                         76:'Program Written Header',               # Programmed header written does not pass checksum
                         77:'Boot Header Invalid',                  # Applcation header is invalid, cannot boot
                         78:'Boot Protection Done',                 # Cannot diable protection since it is already enabled (too late)
                         79:'Boot No Manual'                        # Cannot boot manually, as automatic boot has started (too late)
                         }
# Reset Reason Strings                         
RESET_REASON_STRINGS  = { 1:'Power-Up',
                          2:'Instruction Cache DED',
                          4:'Data Cache DED',
                          8:'Bootloader RAM DED',
                         16:'Application RAM DED',
                         32:'Watchdog Time Out',
                         64:'Reset Command',
                        128:'Latch-up Power Off'
                        }                         

# Latch-up Flags Strings
LATCH_UP_CHANNEL_STRINGS = { 0:'C_FeeSmps',
                             1:'C_FeeLdo',
                             2:'C_Brd5V0',
                             3:'C_BrdLdo',
                             4:'C_Smps3V3',
                             5:'C_Smps1V0',
                             6:'C_Smps1V2',
                             7:'C_SdramVtt'
                           }



class xScape:
    """
    
    Simera Sense xScape Imager base class
    
    """


    def __init__(self, EGSE = None, I2Caddr = None):
        """
        xScape Imager Constructor
        
        Optional Arguments:
            EGSE        - instance of simera.pylibEgseFx3.EGSE class
            I2Caddr     - I2C address of the xScape Imager instance
                          If an I2C address is specified, the control interface is set to I2C automatically
        """
        self.debug = False
        self.EGSE = EGSE
        self.debug_interface_type = 'Control Interface' # Set a debug interface type (used to identify this as a Control Interface, on the xScape imager)

        self.i2c_address = I2Caddr
        if not self.i2c_address == None:
            #i2c address specified, so set control interface to I2C
            self.control_interface = CONTROL_INTERFACE_I2C
        else:
            self.control_interface = None

        self.PacketProtocol = None
        self.ccsds_enable = False
        self.ccsds_sec_enable = False
        self.ccsds_apid = 0x000
        self.ccsds_ancillary = []

        self._threadLock = Lock()

        self.system_param_parser = {        
                SYSTEM_PARAMID_FLASH_TARGETS                        : lambda x  : self._parseSystemParameter_FlashTargets(x),
                SYSTEM_PARAMID_FLASH_LUNS_DISABLE                   : lambda x  : self._parseSystemParameter_FlashLunsDisable(x),
                SYSTEM_PARAMID_DATA_INTERFACE                       : lambda x  : self._parseSystemParameter_DataInterface(x),
                SYSTEM_PARAMID_SENSOR_TEMP_CAL_A                    : lambda x  : self._parseSystemParameter_SensorTempCalibrateFactorA(x),
                SYSTEM_PARAMID_SENSOR_TEMP_CAL_B                    : lambda x  : self._parseSystemParameter_SensorTempCalibrateFactorB(x),
                SYSTEM_PARAMID_LATCH_CHAN_EN                        : lambda x  : self._parseSystemParameter_LatchupChannelEnable(x),
                SYSTEM_PARAMID_LATCH_CHAN_LIMITS                    : lambda *x : self._parseSystemParameter_LatchupChannelLimits(*x),
                SYSTEM_PARAMID_LATCH_FILTER_COUNT                   : lambda x  : self._parseSystemParameter_LatchupFilterCount(x),                
                SYSTEM_PARAMID_MONITOR_ECC_SETUP                    : lambda x  : self._parseSystemParameter_MonitorEccSetup(x),
                SYSTEM_PARAMID_MONITOR_WDT_ENABLE                   : lambda x  : self._parseSystemParameter_MonitorWdtEnable(x),
                SYSTEM_PARAMID_MONITOR_WDT_DIVISOR                  : lambda x  : self._parseSystemParameter_MonitorWdtDivisor(x),
                SYSTEM_PARAMID_SPACEWIRE_BAUD_RATE                  : lambda x  : self._parseSystemParameter_SpaceWireBaudRate(x),
                SYSTEM_PARAMID_SPACEWIRE_IMAGER_LOG_ADDR            : lambda x  : self._parseSystemParameter_SpaceWireImagerLogAddr(x),
                SYSTEM_PARAMID_SPACEWIRE_CONTROL_HOST_LOG_ADDR      : lambda x  : self._parseSystemParameter_SpaceWireControlHostLogAddr(x),
                SYSTEM_PARAMID_SPACEWIRE_CONTROL_HOST_ROUTING_BYTE  : lambda *x : self._parseSystemParameter_SpaceWireControlHostRoutingByte(*x),
                SYSTEM_PARAMID_SPACEWIRE_DATA_HOST_LOG_ADDR         : lambda x  : self._parseSystemParameter_SpaceWireDataHostLogAddr(x),
                SYSTEM_PARAMID_SPACEWIRE_DATA_HOST_ROUTING_BYTE     : lambda *x : self._parseSystemParameter_SpaceWireDataHostRoutingByte(*x),
                SYSTEM_PARAMID_SPACEWIRE_DATA_HOST_LOG_ADDR         : lambda x  : self._parseSystemParameter_SpaceWireDataHostLogAddr(x),
                SYSTEM_PARAMID_SPACEWIRE_DATA_HOST_ROUTING_BYTE     : lambda *x : self._parseSystemParameter_SpaceWireDataHostRoutingByte(*x),
                SYSTEM_PARAMID_SPACEWIRE_DATA_PROTOCOL_SELECT       : lambda x  : self._parseSystemParameter_SpaceWireDataProtocolSelect(x),
                SYSTEM_PARAMID_SPACEWIRE_DATA_PAY_LIMIT             : lambda x  : self._parseSystemParameter_SpaceWireDataPayloadLimit(x),                
            }
            
        self.system_param_req_handlers = {
                SYSTEM_PARAMID_FLASH_TARGETS                        : lambda : self._handleSystemParameterReq_FlashTargets(),
                SYSTEM_PARAMID_FLASH_LUNS_DISABLE                   : lambda : self._handleSystemParameterReq_FlashLunsDisable(),
                SYSTEM_PARAMID_DATA_INTERFACE                       : lambda : self._handleSystemParameterReq_DataInterface(),
                SYSTEM_PARAMID_SENSOR_TEMP_CAL_A                    : lambda : self._handleSystemParameterReq_SensorTempCalibrateFactorA(),
                SYSTEM_PARAMID_SENSOR_TEMP_CAL_B                    : lambda : self._handleSystemParameterReq_SensorTempCalibrateFactorB(),
                SYSTEM_PARAMID_FLASH_LUNS_DISABLE                   : lambda : self._handleSystemParameterReq_FlashLunsDisable(),
                SYSTEM_PARAMID_DATA_INTERFACE                       : lambda : self._handleSystemParameterReq_DataInterface(),
                SYSTEM_PARAMID_LATCH_CHAN_EN                        : lambda : self._handleSystemParameterReq_LatchupChannelEnable(),
                SYSTEM_PARAMID_LATCH_CHAN_LIMITS                    : lambda : self._handleSystemParameterReq_LatchupChannelLimits(),
                SYSTEM_PARAMID_LATCH_FILTER_COUNT                   : lambda : self._handleSystemParameterReq_LatchupFilterCount(),
                SYSTEM_PARAMID_MONITOR_ECC_SETUP                    : lambda : self._handleSystemParameterReq_MonitorEccSetup(),
                SYSTEM_PARAMID_MONITOR_WDT_ENABLE                   : lambda : self._handleSystemParameterReq_MonitorWdtEnable(),
                SYSTEM_PARAMID_MONITOR_WDT_DIVISOR                  : lambda : self._handleSystemParameterReq_MonitorWdtDivisor(),
                SYSTEM_PARAMID_SPACEWIRE_BAUD_RATE                  : lambda : self._handleSystemParameterReq_SpaceWireBaudRate(),
                SYSTEM_PARAMID_SPACEWIRE_IMAGER_LOG_ADDR            : lambda : self._handleSystemParameterReq_SpaceWireImagerLogAddr(),
                SYSTEM_PARAMID_SPACEWIRE_CONTROL_HOST_LOG_ADDR      : lambda : self._handleSystemParameterReq_SpaceWireControlHostLogAddr(),
                SYSTEM_PARAMID_SPACEWIRE_CONTROL_HOST_ROUTING_BYTE  : lambda : self._handleSystemParameterReq_SpaceWireControlHostRoutingByte(),
                SYSTEM_PARAMID_SPACEWIRE_DATA_HOST_LOG_ADDR         : lambda : self._handleSystemParameterReq_SpaceWireDataHostLogAddr(),
                SYSTEM_PARAMID_SPACEWIRE_DATA_HOST_ROUTING_BYTE     : lambda : self._handleSystemParameterReq_SpaceWireDataHostRoutingByte(),
                SYSTEM_PARAMID_SPACEWIRE_DATA_PROTOCOL_SELECT       : lambda : self._handleSystemParameterReq_SpaceWireDataProtocolSelect(),
                SYSTEM_PARAMID_SPACEWIRE_DATA_PAY_LIMIT             : lambda : self._handleSystemParameterReq_SpaceWireDataPayloadLimit(),
            }            

        self.imaging_param_parser = {
                IMAGING_PARAMID_THUMB_FACTOR        : lambda x  : self._parseImagingParameter_ThumbnailFactor(x),
                IMAGING_PARAMID_PLATFORM_ID         : lambda x  : self._parseImagingParameter_PlatformID(x),
                IMAGING_PARAMID_INSTRUMENT_ID       : lambda x  : self._parseImagingParameter_InstrumentID(x),
                IMAGING_PARAMID_BINNING_FACTOR      : lambda x  : self._parseImagingParameter_BinningFactor(x),
            }

        self.imaging_param_req_handlers = {
                IMAGING_PARAMID_THUMB_FACTOR        : lambda : self._handleImagingParameterReq_ThumbnailFactor(),
                IMAGING_PARAMID_PLATFORM_ID         : lambda : self._handleImagingParameterReq_PlatformID(),
                IMAGING_PARAMID_INSTRUMENT_ID       : lambda : self._handleImagingParameterReq_InstrumentID(),
                IMAGING_PARAMID_BINNING_FACTOR      : lambda : self._handleImagingParameterReq_BinningFactor(),
            }
            
        self.RetreivedImgParamId = None
        self.RetreivedSysParamId = None

        self.RetrievedDataDumpLength = None


        self.ce_tlm_info = [
                            {'Name':'V_FeeSmps'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'C_FeeSmps'    , 'Unit':'mA', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'C_FeeLdo'     , 'Unit':'mA', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_FeeNegSmps' , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'C_Brd5V0'     , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':   0, 'Max':  30}, 'Range_FeeOn':{'Min':   0, 'Max':  30}},
                            {'Name':'V_FeeOpAmp'   , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_SdramVtt'   , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min': 585, 'Max': 615}, 'Range_FeeOn':{'Min': 585, 'Max': 615}},
                            {'Name':'V_Brd3V3'     , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':3280, 'Max':3400}, 'Range_FeeOn':{'Min':3280, 'Max':3400}},
                            {'Name':'V_Brd2V5'     , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':2490, 'Max':2560}, 'Range_FeeOn':{'Min':2490, 'Max':2560}},
                            {'Name':'V_RefCal0'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':1020, 'Max':1030}, 'Range_FeeOn':{'Min':1020, 'Max':1030}},
                            {'Name':'V_FeeLdo'     , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':  10}, 'Range_FeeOn':{'Min':   0, 'Max':  10}},
                            {'Name':'V_IntTst0'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_REFM0'      , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_REFP0'      , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'C_BrdLdo'     , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':  85, 'Max': 130}, 'Range_FeeOn':{'Min':  85, 'Max': 130}},
                            {'Name':'C_Smps3V3'    , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':  90, 'Max': 250}, 'Range_FeeOn':{'Min': 330, 'Max': 430}},
                            {'Name':'V_Smps1V2'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':1190, 'Max':1240}, 'Range_FeeOn':{'Min':1190, 'Max':1240}},
                            {'Name':'V_Smps1V0'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min': 990, 'Max':1010}, 'Range_FeeOn':{'Min': 990, 'Max':1010}},
                            {'Name':'C_Smps1V0'    , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min': 900, 'Max':1200}, 'Range_FeeOn':{'Min': 900, 'Max':1200}},
                            {'Name':'C_Smps1V2'    , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':  20, 'Max': 110}, 'Range_FeeOn':{'Min':  20, 'Max': 110}},
                            {'Name':'V_Brd1V8'     , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':1790, 'Max':1840}, 'Range_FeeOn':{'Min':1790, 'Max':1840}},
                            {'Name':'C_SdramVtt'   , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':   0, 'Max':  15}, 'Range_FeeOn':{'Min':   0, 'Max':  15}},
                            {'Name':'V_RefCal1'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':1020, 'Max':1030}, 'Range_FeeOn':{'Min':1020, 'Max':1030}},
                            {'Name':'V_IntTst1'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_REFM1'      , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_REFP1'      , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_Fpga1V0'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min': 990, 'Max':1010}, 'Range_FeeOn':{'Min': 990, 'Max':1010}},
                            {'Name':'V_Fpga1V8'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':1790, 'Max':1840}, 'Range_FeeOn':{'Min':1790, 'Max':1840}},
                            {'Name':'V_Fpga2V5'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':2490, 'Max':2560}, 'Range_FeeOn':{'Min':2490, 'Max':2560}},
                            {'Name':'T_Fpga'       , 'Unit':'`C', 'Used':True  , 'Range_FeeOff':{'Min': -25, 'Max':  85}, 'Range_FeeOn':{'Min': -25, 'Max':  85}}
                           ]



    def enableDebug(self):
        """
        Enable debug output to console
        """
        self.debug = True

    def disableDebug(self):
        """
        Disable debug output to console
        """
        self.debug = False

    def LatchupChannelString(self, channel):
        if not 0 <= channel <= 7:
            raise exceptions.InputError(f'Channel parameter must be between 0 and 7 but "{channel}" was supplied')
        return LATCH_UP_CHANNEL_STRINGS[channel]

    ############################################################################
    ## COMMANDS ##
    ##############
    def OpenSession(self):
        """
        Create a new storage session
        """
        data = [0x00]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending OpenSession command.\n{e}')

    def ActivateSession(self, ManualMBytes = 0):
        """
        Activate a session and enable storage
    
        Optional Arguments:
            ManualMBytes (uint32) - Manual mode number of megabytes (Leave out, or specify '0' for automatic mode activation)
        """
        try:
            ManualMBytes = int(ManualMBytes)
        except ValueError as e:
            raise exceptions.InputError(f'ManualMBytes parameter must be an integer, but "{ManualMBytes}" was supplied.\n{e}')
        if ManualMBytes < 0 or ManualMBytes >= (126*1024):
            raise exceptions.InputError(f'ManualMBytes parameter must be less than 129 024, but "{ManualMBytes}" was supplied.')

        byte0 = (ManualMBytes & 0x000000FF)
        byte1 = (ManualMBytes & 0x0000FF00)>>8
        byte2 = (ManualMBytes & 0x00FF0000)>>16
        byte3 = (ManualMBytes & 0xFF000000)>>24

        data = [0x01, byte0, byte1, byte2, byte3]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending ActivateSession command.\n{e}')

    def CloseSession(self):
        """
        Close the active session and disable storage
        """
        data = [0x02]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending CloseSession command.\n{e}')

    def ReadOutSession(self, SessionID, FilterMask = 0xffff, BandMask = 0xffffffff):
        """
        Initiate data read out from a session
    
        Mandatory Arguments:
            SessionID - Identifies the session
    
        Optional Arguments:
            FilterMask (uint16) - Bit mask to Include/Exclude packets. Include all by default.
            BandMask (uint32) - Bit mask to include/exclude spectral band data. Include all by default.
        """
        try:
            SessionID = int(SessionID)
        except ValueError as e:
            raise exceptions.InputError(f'SessionID parameter must be an integer, but "{SessionID}" was supplied.\n{e}')

        try:
            FilterMask = int(FilterMask)
        except ValueError as e:
            raise exceptions.InputError(f'FilterMask parameter must be an integer, but "{FilterMask}" was supplied.\n{e}')

        try:
            BandMask = int(BandMask)
        except ValueError as e:
            raise exceptions.InputError(f'BandMask parameter must be an integer, but "{BandMask}" was supplied.\n{e}')

        byte0 = (SessionID & 0x000000FF)
        byte1 = (SessionID & 0x0000FF00)>>8
        byte2 = (SessionID & 0x00FF0000)>>16
        byte3 = (SessionID & 0xFF000000)>>24

        byte4 = (FilterMask & 0x000000FF)
        byte5 = (FilterMask & 0x0000FF00)>>8

        byte6 = (BandMask & 0x000000FF)
        byte7 = (BandMask & 0x0000FF00)>>8
        byte8 = (BandMask & 0x00FF0000)>>16
        byte9 = (BandMask & 0xFF000000)>>24

        data = [0x03, byte0, byte1, byte2, byte3, byte4, byte5, byte6, byte7, byte8, byte9]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReadOutSession command.\n{e}')

    def DeleteSession(self, SessionID):
        """
        Delete a session
    
        Mandatory Arguments:
            SessionID (uint32) - Session Identifier
        """
        try:
            SessionID = int(SessionID)
        except ValueError as e:
            raise exceptions.InputError(f'SessionID parameter must be an integer, but "{SessionID}" was supplied.\n{e}')

        byte0 = (SessionID & 0x000000FF)
        byte1 = (SessionID & 0x0000FF00)>>8
        byte2 = (SessionID & 0x00FF0000)>>16
        byte3 = (SessionID & 0xFF000000)>>24

        data = [0x04, byte0, byte1, byte2, byte3]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending DeleteSession command.\n{e}')

    def StoreTimeSync(self, Format, Value):
        """
        Store a Time Sync Ancillary Data packet
    
        Mandatory Arguments:
            Format (uint8) - Platform Time Formatas defined in User Manual
            Value (uint64) - 64-bit Platform Time Value
        """
        try:
            Format = int(Format)
        except ValueError as e:
            raise exceptions.InputError(f'Format parameter must be an integer, but "{Format}" was supplied.\n{e}')
        if (Format > 255):
            raise exceptions.InputError(f'Format parameter must be 8-bit, but "{Format}" was supplied.\n{e}')

        try:
            Value = int(Value)
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Value}" was supplied.\n{e}')

        byte0 = Format
        byte1 = (Value & 0x00000000000000FF)
        byte2 = (Value & 0x000000000000FF00)>>8
        byte3 = (Value & 0x0000000000FF0000)>>16
        byte4 = (Value & 0x00000000FF000000)>>24
        byte5 = (Value & 0x000000FF00000000)>>32
        byte6 = (Value & 0x0000FF0000000000)>>40
        byte7 = (Value & 0x00FF000000000000)>>48
        byte8 = (Value & 0xFF00000000000000)>>56

        data = [0x05, byte0, byte1, byte2, byte3, byte4, byte5, byte6, byte7, byte8]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending StoreTimeSync command.\n{e}')

    def StoreUserAncillaryData(self, ID, Payload):
        """
        Store a User Ancillary Data packet
    
        Mandatory Arguments:
            ID (uint8) - User specified ID to identify the ancillary data.
            Payload (varies) - list or numpy.ndarray, maximum of 1024 bytes
        """
        try:
            ID = int(ID)
        except ValueError as e:
            raise exceptions.InputError(f'ID parameter must be an integer, but "{ID}" was supplied.\n{e}')
        if (ID > 255):
            raise exceptions.InputError(f'ID parameter must be 8-bit, but "{ID}" was supplied.')

        if not isinstance(Payload, list) and not isinstance(Payload, numpy.ndarray): Payload = [ Payload ]
        length = len(Payload)
        length_byte0 = (length & 0x00ff)
        length_byte1 = (length & 0xff00)>>8

        if isinstance(Payload, list):
            data = [0x06, ID, length_byte0, length_byte1]
            data.extend(Payload)
        else:
            data = numpy.insert(Payload, 0, [0x06, ID, length_byte0, length_byte1])

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending StoreUserAncillaryData command.\n{e}')

    def GetSessionInformation(self, SessionID):
        """
        Retrieve the information for a session
    
        Mandatory Arguments:
            SessionID (uint32) - Session Identifier
        """
        try:
            SessionID = int(SessionID)
        except ValueError as e:
            raise exceptions.InputError(f'SessionID parameter must be an integer, but "{SessionID}" was supplied.\n{e}')

        byte0 = (SessionID & 0x000000FF)
        byte1 = (SessionID & 0x0000FF00)>>8
        byte2 = (SessionID & 0x00FF0000)>>16
        byte3 = (SessionID & 0xFF000000)>>24

        data = [0x07, byte0, byte1, byte2, byte3]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending GetSessionInformation command.\n{e}')

    def GenerateSessionList(self):
        """
        Generates the Session List.
        """
        data = [0x08]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending GenerateSessionList command.\n{e}')
            
    def GetSessionListEntry(self):
        """
        Retrieve a single entry from the Sessions List.
        """
        data = [0x09]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending GetSessionListEntry command.\n{e}')

    def AbortReadOut(self):
        """
        Abort the current session read out.
        """
        data = [0x0A]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending AbortReadOut command.\n{e}')
            
    def DeleteAllSessions(self, MagicNum):
        """
        Deletes all of the sessions from the imager. All session data will be lost.
        
        Mandatory Arguments:
            MagicNum (uint8) - The magic nubmer with the value 0x25 (37) must be provided.
        """
        try:
            MagicNum = int(MagicNum)
        except ValueError as e:
            raise exceptions.InputError(f'MagicNum parameter must be an integer, but "{MagicNum}" was supplied.\n{e}')
        if MagicNum != 0x25:
            raise exceptions.InputError(f'MagicNum must be equal to 0x25 or 37 decimal (to process the command), but "{MagicNum}" was supplied.')        
        
        data = [0x0B, MagicNum]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending DeleteAllSessions command.\n{e}')   

    def CompressSession(self, SessionID, Bands = 0x7f, Ratio = 10):
        """
        Compress an existing Session (Using CCSDS 122.0)

        Mandatory Arguments:
            SessionID   (uint32)  - Identifies the original session (source of raw images).
            Bands       (uint32)  - Bit mask to select which spectral bands to compress. (Bit 0 = Band 0, Bit 1 = Band 1, etc).
            Ratio       (uint8)   - Compression Ratio 1 = lossless, 10 to 255 = lossy, from 10 = 1.0:1 to 255 = 25.5:1.
            
        """
        try:
            SessionID = int(SessionID)
        except ValueError as e:
            raise exceptions.InputError(f'SessionID parameter must be an integer, but "{SessionID}" was supplied.\n{e}')

        try:
            Bands = int(Bands)
        except ValueError as e:
            raise exceptions.InputError(f'Bands parameter must be an integer, but "{Bands}" was supplied.\n{e}')
        if Bands < 0 or Bands >= 2**32:
            raise exceptions.InputError(f'Bands parameter must be 32-bit, but "{Bands}" was supplied.')
            
        try:
            Ratio = int(Ratio)
        except ValueError as e:
            raise exceptions.InputError(f'Ratio parameter must be an integer, but "{Ratio}" was supplied.\n{e}')
        if Ratio < 0 or Ratio >= 2**8:
            raise exceptions.InputError(f'Ratio parameter must be 8-bit, but "{Ratio}" was supplied.')            

        byte0 = (SessionID & 0x000000FF)
        byte1 = (SessionID & 0x0000FF00)>>8
        byte2 = (SessionID & 0x00FF0000)>>16
        byte3 = (SessionID & 0xFF000000)>>24
        byte4 = (Bands & 0x000000FF)
        byte5 = (Bands & 0x0000FF00)>>8
        byte6 = (Bands & 0x00FF0000)>>16
        byte7 = (Bands & 0xFF000000)>>24
        byte8 = Ratio

        data = [0x0C, byte0, byte1, byte2, byte3, byte4, byte5, byte6, byte7, byte8]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending CompressSession command.\n{e}')

    def CompressSessionAbort(self):
        """
        Abort the current Compress Session operation.    
        """
        
        data = [0x0D]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending CompressSessionAbort command.\n{e}')

    def EncryptionKeySetup(self, Key=[]):
        """
        Setup the Encryption Key

        Mandatory Arguments:
            Key   (32 x uint8) - 256-bit AES Encryption Key (32 bytes in big endian)
        """

        if len(Key) != 32:
            raise exceptions.InputError(f'Key must be a list of 32 values, but "{len(Key)}" values was supplied.')

        data = [0x0E]
        key_reverse = Key[::-1] # Note: Key is reversed as it supplied is in big endian, but the Imager expects little endian.
        data.extend(key_reverse)

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending EncryptionKeySetup command.\n{e}')

    def EncryptionSetup(self, Mask=0, InitVec=[], CntMode=0):
        """
        Setup the Encryption

        Mandatory Arguments:
            Mask     (uint16)     - Encryption Packet Mask
            InitVec  (16 x uint8) - 128-bit AES Initilization Vector (16 bytes in big endian)
            CntMode  (uint8)      - Counter Mode (0 = Packet Mode, 1 = Stream Mode)
        """
        try:
            Mask = int(Mask)
        except ValueError as e:
            raise exceptions.InputError(f'Mask parameter must be an integer, but "{Mask}" was supplied.\n{e}')
        if Mask < 0 or Mask >= 2**16:
            raise exceptions.InputError(f'Mask must be 16-bit, but "{Mask}" was supplied.')

        if len(InitVec) != 16:
            raise exceptions.InputError(f'InitVec must be a list of 16 values, but "{len(InitVec)}" values was supplied.')

        try:
            CntMode = int(CntMode)
        except ValueError as e:
            raise exceptions.InputError(f'CntMode parameter must be an integer, but "{CntMode}" was supplied.\n{e}')
        if CntMode < 0 or CntMode >= 2:
            raise exceptions.InputError(f'CntMode must be 0 or 1, but "{CntMode}" was supplied.')

        byte0  = (Mask & 0x000000FF)
        byte1  = (Mask & 0x0000FF00)>>8
        byte18 = CntMode

        data = [0x0F, byte0, byte1]
        init_reverse = InitVec[::-1] # Note: InitVec is reversed as it supplied is in big endian, but the Imager expects little endian.
        data.extend(init_reverse)
        data.extend([byte18])

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending EncryptionSetup command.\n{e}')

    def EnableEncryption(self):
        """
        Enable Read Out Encryption
        """
        data = [0x10]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending EnableEncryption command.\n{e}')

    def DisableEncryption(self):
        """
        Disable Read Out Encryption
        """
        data = [0x11]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending DisableEncryption command.\n{e}')

    def ReadOutRangeSetup(self, Mode=0, RangeStart=0, RangeStop=0, RangeStartBand=0, RangeStopBand=0):
        """
        Setup the ReadOut Range Filter
    
        Mandatory Arguments:
            Mode           (uint8)  - 0 = Disabled, 1 = Filter on Line Number, 2 = Filter on CCSDS Segment Number
            RangeStart     (uint32) - Start Number for filtering (inclusive)
            RangeStop      (uint32) - Stop Number for filtering (inclusive)
            RangeStartBand (uint32) - Start Band for filtering
            RangeStopBand  (uint32) - Stop Band for filtering          
        """
        try:
            Mode = int(Mode)
        except ValueError as e:
            raise exceptions.InputError(f'Mode parameter must be an integer, but "{Mode}" was supplied.\n{e}')
        if Mode < 0 or Mode >= 2**8:
            raise exceptions.InputError(f'Mode must be 8-bit, but "{Mode}" was supplied.')                        

        try:
            RangeStart = int(RangeStart)
        except ValueError as e:
            raise exceptions.InputError(f'RangeStart parameter must be an integer, but "{RangeStart}" was supplied.\n{e}')
        if RangeStart < 0 or RangeStart >= 2**32:
            raise exceptions.InputError(f'RangeStart must be 32-bit, but "{RangeStart}" was supplied.')                        

        try:
            RangeStop = int(RangeStop)
        except ValueError as e:
            raise exceptions.InputError(f'RangeStop parameter must be an integer, but "{RangeStop}" was supplied.\n{e}')
        if RangeStop < 0 or RangeStop >= 2**32:
            raise exceptions.InputError(f'RangeStop must be 32-bit, but "{RangeStop}" was supplied.')                        
            
        try:
            RangeStartBand = int(RangeStartBand)
        except ValueError as e:
            raise exceptions.InputError(f'RangeStartBand parameter must be an integer, but "{RangeStartBand}" was supplied.\n{e}')
        if RangeStartBand < 0 or RangeStartBand >= 32:
            raise exceptions.InputError(f'RangeStartBand must be between 0 and 31, but "{RangeStartBand}" was supplied.')                        

        try:
            RangeStopBand = int(RangeStopBand)
        except ValueError as e:
            raise exceptions.InputError(f'RangeStopBand parameter must be an integer, but "{RangeStopBand}" was supplied.\n{e}')
        if RangeStopBand < 0 or RangeStopBand >= 32:
            raise exceptions.InputError(f'RangeStopBand must be between 0 and 31, but "{RangeStopBand}" was supplied.')             

        byte0 = Mode
        
        byte1 = (RangeStart & 0x000000FF)
        byte2 = (RangeStart & 0x0000FF00)>>8
        byte3 = (RangeStart & 0x00FF0000)>>16
        byte4 = (RangeStart & 0xFF000000)>>24

        byte5 = (RangeStop & 0x000000FF)
        byte6 = (RangeStop & 0x0000FF00)>>8
        byte7 = (RangeStop & 0x00FF0000)>>16
        byte8 = (RangeStop & 0xFF000000)>>24
        
        byte9 = (RangeStartBand & 0x000000FF)
        byte10 = (RangeStartBand & 0x0000FF00)>>8
        byte11 = (RangeStartBand & 0x00FF0000)>>16
        byte12 = (RangeStartBand & 0xFF000000)>>24     

        byte13 = (RangeStopBand & 0x000000FF)
        byte14 = (RangeStopBand & 0x0000FF00)>>8
        byte15 = (RangeStopBand & 0x00FF0000)>>16
        byte16 = (RangeStopBand & 0xFF000000)>>24  

        data = [0x12, byte0, byte1, byte2, byte3, byte4, byte5, byte6, byte7, byte8, byte9, byte10, byte11, byte12, byte13, byte14, byte15, byte16]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReadOutRangeSetup command.\n{e}')

    def EnableSensor(self):
        """
        Power up the FEE and configure the sensor
        """
        data = [0x20]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending EnableSensor command.\n{e}')

    def DisableSensor(self):
        """
        Power down the FEE
        """
        data = [0x21]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending DisableSensor command.\n{e}')

    def SetImagingParameter(self, ParamID, *Values):
        """
        Set an imaging parameter (volatile)
    
        SetImagingParameter(ParamID, ParamValue1, ParamValue2 ...)
    
        Mandatory Arguments:
            ParamID (uint8) - The parameter number
            Values (varies) - The new parameter value(s), depends on the Parameter to be set
        """
        try:
            ParamID = int(ParamID)
        except ValueError as e:
            raise exceptions.InputError(f'ParamID parameter must be an integer, but "{ParamID}" was supplied.\n{e}')
        if ParamID < 0 or ParamID >= 2**8:
            raise exceptions.InputError(f'ParamID parameter must be 8-bit, but "{ParamID}" was supplied.')

        try:
            Value = self.imaging_param_parser[ParamID](*Values)
        except KeyError as e:
            raise exceptions.InputError(f'Supplied Parameter Number "{ParamID}" is not valid.\n{e}')
        except Exception as e:
            raise exceptions.InputError(f'Error parsing imaging parameter number.\n{e}')

        if isinstance(Value, list):
            data = [0x22, ParamID]
            data.extend(Value)
        else:
            data = [0x22, ParamID, Value]
        
        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending SetImagingParameter command.\n{e}')
            
    def SetDefaultImagingParameter(self, ParamID, *Values):
        """
        Set a default imaging parameter (non-volatile)
    
        SetDefaultImagingParameter(ParamID, ParamValue1, ParamValue2 ...)
    
        Mandatory Arguments:
            ParamID (unit8) - The parameter number
            Values (varies) - The new parameter value(s), depends on the Parameter to be set
        """
        try:
            ParamID = int(ParamID)
        except ValueError as e:
            raise exceptions.InputError(f'ParamID parameter must be an integer, but "{ParamID}" was supplied.\n{e}')
        if ParamID < 0 or ParamID >= 2**8:
            raise exceptions.InputError(f'ParamID parameter must be 8-bit, but "{ParamID}" was supplied.')

        try:
            Value = self.imaging_param_parser[ParamID](*Values)
        except KeyError as e:
            raise exceptions.InputError(f'Supplied Parameter Number "{ParamID}" is not valid.\n{e}')
        except Exception as e:
            raise exceptions.InputError(f'Error parsing imaging parameter command.\n{e}')

        if isinstance(Value, list):
            data = [0x23, ParamID]
            data.extend(Value)            
        else:
            data = [0x23, ParamID, Value]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending SetDefaultImagingParameter command.\n{e}')

    def GetImagingParameter(self, ParamID):
        """
        Retrieve an imaging parameter
        
        Mandatory Arguments:
            ParamID - The parameter number            
        """
        try:
            ParamID = int(ParamID)
        except ValueError as e:
            raise exceptions.InputError(f'ParamID parameter must be an integer, but "{ParamID}" was supplied.\n{e}')
        if ParamID < 0 or ParamID >= 2**8:
            raise exceptions.InputError(f'ParamID parameter must be 8-bit, but "{ParamID}" was supplied.')

        # Save the most recent Parameter retrieved, to be used by the Imager Parameter Request
        self.RetreivedImgParamId = ParamID

        data = [0x24, ParamID]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending GetImagingParameter command.\n{e}')     
            
    def RestoreImagingParameters(self):
        """
        Restore imaging parameters to factory defaults             
        """       
        data = [0x25]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending RestoreImagingParameters command.\n{e}')        

    def Configure(self, Mode):
        """
        Configure the Imager
        
        Mandatory Arguments:
            Mode - Snapshot (0) or Line Scan (1) or Test Pattern (2).
        """
        try:
            Mode = int(Mode)
        except ValueError as e:
            raise exceptions.InputError(f'Mode parameter must be an integer, but "{Mode}" was supplied.\n{e}')
        if Mode not in CONFIGURE_MODES:
            raise exceptions.InputError(f'Mode parameter must be one of {CONFIGURE_MODES}, but "{Mode}" was supplied.')
        
        data = [0x26, Mode]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending Configure command.\n{e}')   

    def CaptureImage(self, PPSDelay):
        """
        Initiate the image capture process
        
        Mandatory Arguments:
            PPSDelay - 0 for immediate, or 1 to 255 for number of PPS delays
        """
        try:
            PPSDelay = int(PPSDelay)
        except ValueError as e:
            raise exceptions.InputError(f'PPSDelay parameter must be an integer, but "{PPSDelay}" was supplied.\n{e}')
        if PPSDelay < 0 or PPSDelay >= 2**8:
            raise exceptions.InputError(f'PPSDelay parameter must be 8-bit, but "{PPSDelay}" was supplied.')
        
        data = [0x27, PPSDelay]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending CaptureImage command.\n{e}')          

    def Reset(self):
        """
        Reset the imager (full system).
        """
        data = [0x40, 0x72] # 0x72 is a magic number, to confirm the reset
        
        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending Reset command.\n{e}')         

    def GetFeeTelemetry(self):
        """
        Retrieve the FEE Telemetry
        """
        data = [0x42]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending GetFeeTelemetry command.\n{e}')     

    def SetupPPS(self, Settings):
        """
        Sets the options for the external PPS input
        
        Mandatory Arguments:
            Settings - 8-bit integer. Bit 0 = Enable/Disable, Bit 1 = Edge Detection. Bit 2 = Primiary/Secondary
        """
        try:
            Settings = int(Settings)
        except ValueError as e:
            raise exceptions.InputError(f'Settings parameter must be an integer, but "{Settings}" was supplied.\n{e}')
        if Settings < 0 or Settings > 7:
            raise exceptions.InputError(f'Settings parameter must be less than 4, but "{Settings}" was supplied.')
        
        data = [0x43, Settings]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending SetupPPS command.\n{e}')     

    def GetCeTelemetry(self):
        """
        Retrieve the CE Telemetry
        """
        data = [0x44]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending GetCeTelemetry command.\n{e}')

    def GetOfeTelemetry(self):
        """
        Retrieve the OFE Telemetry
        """
        data = [0x45]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending GetOfeTelemetry command.\n{e}')            
            
    def SetDefaultSystemParameter(self, ParamID, *Values):
        """
        Set a default system parameter (non-volatile)
    
        SetDefaultSystemParameter(ParamID, ParamValue1, ParamValue2 ...)
    
        Mandatory Arguments:
            ParamID (unit8) - The parameter number
            Values (varies) - The new parameter value(s), depends on the Parameter to be set
        """
        try:
            ParamID = int(ParamID)
        except ValueError as e:
            raise exceptions.InputError(f'ParamID parameter must be an integer, but "{ParamID}" was supplied.\n{e}')
        if ParamID < 0 or ParamID >= 2**8:
            raise exceptions.InputError(f'ParamID parameter must be 8-bit, but "{ParamID}" was supplied.')

        try:
            Value = self.system_param_parser[ParamID](*Values)
        except KeyError as e:
            raise exceptions.InputError(f'Supplied Parameter Number "{ParamID}" is not valid.\n{e}')
        except Exception as e:
            raise exceptions.InputError(f'Error parsing system parameter command.\n{e}')

        if isinstance(Value, list):
            data = [0x46, ParamID]
            data.extend(Value)            
        else:
            data = [0x46, ParamID, Value]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending SetDefaultSystemParameter command.\n{e}')

    def GetSystemParameter(self, ParamID):
        """
        Retrieve a system parameter
        
        Mandatory Arguments:
            ParamID - The parameter number            
        """
        try:
            ParamID = int(ParamID)
        except ValueError as e:
            raise exceptions.InputError(f'ParamID parameter must be an integer, but "{ParamID}" was supplied.\n{e}')
        if ParamID < 0 or ParamID >= 2**8:
            raise exceptions.InputError(f'ParamID parameter must be 8-bit, but "{ParamID}" was supplied.')

        # Save the most recent Parameter retrieved, to be used by the System Parameter Request
        self.RetreivedSysParamId = ParamID

        data = [0x47, ParamID]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending GetSystemParameter command.\n{e}')     
            
    def RestoreSystemParameters(self):
        """
        Restore system parameters to factory defaults             
        """       
        data = [0x48]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending RestoreSystemParameters command.\n{e}')     
            
    def ClearMonitorCounters(self):
        """
        Clear the Processor Monitor Counters.
        """       
        data = [0x49]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending ClearMonitorCounters command.\n{e}')   

    def SetBadBlock(self, MagicNum, Block):
        """
        Marks a flash storage block as bad in the Bad Block Table. This block will not be allocated in future.
        
        Mandatory Arguments:
            MagicNum (uint8)  - The magic nubmer with the value 0x87 (135) must be provided.
            Block    (uint16) - The block number between 0 and 2015
        """
        try:
            MagicNum = int(MagicNum)
        except ValueError as e:
            raise exceptions.InputError(f'MagicNum parameter must be an integer, but "{MagicNum}" was supplied.\n{e}')
        if MagicNum != 0x87:
            raise exceptions.InputError(f'MagicNum must be equal to 0x87 or 135 decimal (to process the command), but "{MagicNum}" was supplied.')        
            
        try:
            Block = int(Block)
        except ValueError as e:
            raise exceptions.InputError(f'Block parameter must be an integer, but "{Block}" was supplied.\n{e}')
        if Block < 0 or Block > 2015:
            raise exceptions.InputError(f'Block parameter must be between 0 and 2015, but "{Block}" was supplied.')            
        
        byte0 = (Block>>0)%256
        byte1 = (Block>>8)%256
        
        data = [0x4A, MagicNum, byte0, byte1]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending SetBadBlock command.\n{e}')                  
            
    def ClearBadBlock(self, MagicNum, Block):
        """
        Unmarks a flash storage block as bad in the Bad Block Table. This block will be allocated in future.
        
        Mandatory Arguments:
            MagicNum (uint8)  - The magic nubmer with the value 0x87 (135) must be provided.
            Block    (uint16) - The block number between 0 and 2015
        """
        try:
            MagicNum = int(MagicNum)
        except ValueError as e:
            raise exceptions.InputError(f'MagicNum parameter must be an integer, but "{MagicNum}" was supplied.\n{e}')
        if MagicNum != 0x87:
            raise exceptions.InputError(f'MagicNum must be equal to 0x87 or 135 decimal (to process the command), but "{MagicNum}" was supplied.')        
            
        try:
            Block = int(Block)
        except ValueError as e:
            raise exceptions.InputError(f'Block parameter must be an integer, but "{Block}" was supplied.\n{e}')
        if Block < 0 or Block > 2015:
            raise exceptions.InputError(f'Block parameter must be between 0 and 2015, but "{Block}" was supplied.')            
        
        byte0 = (Block>>0)%256
        byte1 = (Block>>8)%256
        
        data = [0x4B, MagicNum, byte0, byte1]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending ClearBadBlock command.\n{e}')                
            
    # --- Parse the Imaging Parameters --- #

    def _parseImagingParameter_ThumbnailFactor(self, *Values):
        """
        Set thumbnail reduction factor, or disable thumbnail generation altogether.
    
        Mandatory Arguments:
            Value   - Reduction Factor (0 = disabled, 8, 16, 32, or 64)
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value not in IMAGING_PARAM_THUMBNAIL_FACTORS:
            raise exceptions.InputError(f'Value parameter must be one of {IMAGING_PARAM_THUMBNAIL_FACTORS}, but "{Value}" was supplied.')

        return [Value]

    def _parseImagingParameter_PlatformID(self, *Values):
        """
        Set the user defined platform ID
    
        Mandatory Arguments:
            Value   - User defined platform ID
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value >= 2**16:
            raise exceptions.InputError(f'Value parameter must be 16-bit, but "{Value}" was supplied.')

        byte0 = (Value>>0)%256
        byte1 = (Value>>8)%256
        
        return [byte0, byte1]

    def _parseImagingParameter_InstrumentID(self, *Values):
        """
        Set the user defined instrument ID
    
        Mandatory Arguments:
            Value   - User defined instrument ID
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value >= 2**16:
            raise exceptions.InputError(f'Value parameter must be 16-bit, but "{Value}" was supplied.')

        byte0 = (Value>>0)%256
        byte1 = (Value>>8)%256
        
        return [byte0, byte1]

    def _parseImagingParameter_BinningFactor(self, *Values):
        """
        Set binning reduction factor, or disable binning (bypass) generation altogether.
    
        Mandatory Arguments:
            Value   - Reduction Factor (0 = No binning (1x1), 2 = 2x2 binning, 4 = 4x4 binning)
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value not in IMAGING_PARAM_BINNING_FACTORS:
            raise exceptions.InputError(f'Value parameter must be one of {IMAGING_PARAM_BINNING_FACTORS}, but "{Value}" was supplied.')

        return [Value]             

    # --- Parse the System Parameters --- #                                     

    def _parseSystemParameter_FlashTargets(self, *Values):
        """
        Set the Flash Targets that should be enabled (normally all of them).
         - Note: Use this parameter with EXTREME CARE.
         - This parameter will typically never be changed from the factory value, unless there are problems with the flash memory.                  
         - This parameter is only loaded at startup.
    
        Mandatory Arguments:
            Value (uint16)  - Bit vector of the 16 targets that should be enabled.
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value >= 2**16:
            raise exceptions.InputError(f'Value parameter must be 16-bit, but "{Value}" was supplied.')

        byte0 = (Value>>0)%256
        byte1 = (Value>>8)%256
        
        return [byte0, byte1]
        
    def _parseSystemParameter_FlashLunsDisable(self, *Values):
        """
        Set the Flash LUNs that should be disabled (normally zero).
         - Note: Use this parameter with EXTREME CARE.
         - This parameter will typically never be changed from the factory value, unless there are problems with the flash memory.                  
         - This parameter is only loaded at startup.
    
        Mandatory Arguments:
            Value (uint16)  - Bit vector of the LUNs that should be disabled.
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value >= 2**16:
            raise exceptions.InputError(f'Value parameter must be 16-bit, but "{Value}" was supplied.')

        byte0 = (Value>>0)%256
        byte1 = (Value>>8)%256
        
        return [byte0, byte1]        

    def _parseSystemParameter_DataInterface(self, *Values):
        """
        Set the Data Interface to use.
         - Note: Use this parameter with EXTREME CARE.
         - This parameter will typically never be changed from the factory value, since most imagers only have one Data Interface.                  
    
        Mandatory Arguments:
            Value (uint8)  - Values are unique per imager.
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value >= 2**8:
            raise exceptions.InputError(f'Value parameter must be 8-bit, but "{Value}" was supplied.')      

        return [Value]   
        
    def _parseSystemParameter_SensorTempCalibrateFactorA(self, *Values):
        """
        Set the Sensor Temperature Calibration Factor A.
         - Note: Use this parameter with EXTREME CARE.
         - This parameter will typically never be changed from the factory value.                  
         - This parameter is only loaded at startup.
    
        Mandatory Arguments:
            Value (uint16)  - Factor A.
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value >= 2**16:
            raise exceptions.InputError(f'Value parameter must be 16-bit, but "{Value}" was supplied.')

        byte0 = (Value>>0)%256
        byte1 = (Value>>8)%256
        
        return [byte0, byte1]     

    def _parseSystemParameter_SensorTempCalibrateFactorB(self, *Values):
        """
        Set the Sensor Temperature Calibration Factor B.
         - Note: Use this parameter with EXTREME CARE.
         - This parameter will typically never be changed from the factory value.                  
         - This parameter is only loaded at startup.
    
        Mandatory Arguments:
            Value (uint16)  - Factor B.
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value >= 2**16:
            raise exceptions.InputError(f'Value parameter must be 16-bit, but "{Value}" was supplied.')

        byte0 = (Value>>0)%256
        byte1 = (Value>>8)%256
        
        return [byte0, byte1]         

    def _parseSystemParameter_LatchupChannelEnable(self, *Values):  
        """
        Enable the current channels to monitor for latch-up
         - Note: Use this parameter with EXTREME CARE.
         - This parameter will typically never be changed from the factory value, unless it is required to ignore specific latch-up channels.  
    
        Mandatory Arguments:
            Value (uint8)  - 8-bits, each enabling/disabling a channel (1 = enabled, 0 = disabled).
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value >= 2**8:
            raise exceptions.InputError(f'Value parameter must be 8-bit, but "{Value}" was supplied.')      

        return [Value]  
        
    def _parseSystemParameter_LatchupChannelLimits(self, *Values): # (Channel,  Limit)
        """
       Set current limits for the latch-up channels.
         - Note: Use this parameter with EXTREME CARE.
         - This parameter will typically never be changed from the factory value, unless it is required to ignore specific latch-up channels.  
    
        Mandatory Arguments:
            Channel (uint8)  - Channel nubmer (0 to 7).
            Limit   (uint8)  - Limit (upper 8-bit of the current 12-bit value)
        """
        try:
            Channel = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Channel parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Channel < 0 or Channel > 7:
            raise exceptions.InputError(f'Channel parameter must be between (0 and 7), but "{Band}" was supplied.')

        try:
            Limit = int(Values[1])
        except ValueError as e:
            raise exceptions.InputError(f'Limit parameter must be an integer, but "{Values[1]}" was supplied.\n{e}')
        if Limit < 0 or Limit >= 2**16:
            raise exceptions.InputError(f'Limit parameter must be unsigned 16-bit, but "{Limit}" was supplied.')
            
        byte0 = (Limit>>0)%256
        byte1 = (Limit>>8)%256    

        return [Channel, byte0, byte1]  

    def _parseSystemParameter_LatchupFilterCount(self, *Values):  
        """
        Set the number of over-current events that result in a latch-up.
         - Note: Use this parameter with EXTREME CARE.
         - This parameter will typically never be changed from the factory value.  
    
        Mandatory Arguments:
            Value (uint8)  - Decimal value 1 to 16.
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 1 or Value > 16:
            raise exceptions.InputError(f'Value parameter must be between 1 and 16, but "{Value}" was supplied.')      

        return [Value]  

    def _parseSystemParameter_MonitorEccSetup(self, *Values):  
        """
        Setup the ECC Reset Sources.
         - Note: Use this parameter with EXTREME CARE.
         - This parameter will typically never be changed from the factory value, unless it is required to ignore certain memory.  
    
        Mandatory Arguments:
            Value (uint4)  - 4-bits, each enabling/disabling an ECC reset source (1 = enabled, 0 = disabled).
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value >= 2**4:
            raise exceptions.InputError(f'Value parameter must be unsigned 4-bit, but "{Value}" was supplied.')      

        return [Value]   

    def _parseSystemParameter_MonitorWdtEnable(self, *Values):  
        """
        Enable or disable the Watchdog Timer.
         - Note: Use this parameter with EXTREME CARE.
         - This parameter will typically never be changed from the factory value, unless it is required to ignore watchdog resets.  
    
        Mandatory Arguments:
            Value (uint8)  - Enable = 1, Disable = 0
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value not in (0,1):
            raise exceptions.InputError(f'Value parameter must be 0 or 1, but "{Value}" was supplied.')      

        return [Value]           

    def _parseSystemParameter_MonitorWdtDivisor(self, *Values):  
        """
        Setup the Watchdog Divisor.
         - Note: Use this parameter with EXTREME CARE.
         - This parameter will typically never be changed from the factory value, unless it is required to change the watchdog timer interval.  
    
        Mandatory Arguments:
            Value (uint3)  - 3-bits indicating a divisor value.
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value >= 2**3:
            raise exceptions.InputError(f'Value parameter must be unsigned 3-bit (0 to 7), but "{Value}" was supplied.')      

        return [Value]

    def _parseSystemParameter_SpaceWireBaudRate(self, *Values):  
        """
        SpaceWire Baud Rate in megabits per second (Mbps).
         - Note: Use this parameter with CARE.
         - This parameter will typically never be changed from the factory value.  
    
        Mandatory Arguments:
            Value (uint8)  - 10, 20, 40, 50, 100 
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value not in (10,20,40,50,100):
            raise exceptions.InputError(f'Value parameter must be 10, 20, 40, 50 or 100, but "{Value}" was supplied.')      

        return [Value]

    def _parseSystemParameter_SpaceWireImagerLogAddr(self, *Values):  
        """
        SpaceWire Imager Logical Address.
         - Note: Use this parameter with CARE.
         - This parameter will typically never be changed from the factory value.  
    
        Mandatory Arguments:
            Value (uint8)  - Logical Address 
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value >= 2**8:
            raise exceptions.InputError(f'Value parameter must be unisgned 8-bit, but "{Value}" was supplied.')      

        return [Value]

    def _parseSystemParameter_SpaceWireControlHostLogAddr(self, *Values):  
        """
        SpaceWire Control Host Logical Address.
         - Note: Use this parameter with CARE.
         - This parameter will typically never be changed from the factory value.  
    
        Mandatory Arguments:
            Value (uint8)  - Logical Address 
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value >= 2**8:
            raise exceptions.InputError(f'Value parameter must be unisgned 8-bit, but "{Value}" was supplied.')      

        return [Value]
        
    def _parseSystemParameter_SpaceWireControlHostRoutingByte(self, *Values):  # Pos, Value
        """
        SpaceWire Control Host Routing Byte.
         - Note: Use this parameter with CARE.
         - This parameter will typically never be changed from the factory value.  
    
        Mandatory Arguments:
            Pos     (uint8) - Routing Byte Position (0 to 6 )
            Value   (uint8) - Routing Byte Value
        """
        try:
            Pos = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Pos parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Pos < 0 or Pos > 6:
            raise exceptions.InputError(f'Pos parameter must be betwwen 0 and 6, but "{Pos}" was supplied.')  
            
        try:
            Value = int(Values[1])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[1]}" was supplied.\n{e}')
        if Value < 0 or Value >= 2**8:
            raise exceptions.InputError(f'Value parameter must be unisgned 8-bit, but "{Value}" was supplied.')      

        return [Pos, Value]        
        
    def _parseSystemParameter_SpaceWireDataHostLogAddr(self, *Values):  
        """
        SpaceWire Data Host Logical Address.
         - Note: Use this parameter with CARE.
         - This parameter will typically never be changed from the factory value.  
    
        Mandatory Arguments:
            Value (uint8)  - Logical Address 
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value >= 2**8:
            raise exceptions.InputError(f'Value parameter must be unisgned 8-bit, but "{Value}" was supplied.')      

        return [Value]
        
    def _parseSystemParameter_SpaceWireDataHostRoutingByte(self, *Values):  # Pos, Value
        """
        SpaceWire Data Host Routing Byte.
         - Note: Use this parameter with CARE.
         - This parameter will typically never be changed from the factory value.  
    
        Mandatory Arguments:
            Pos     (uint8) - Routing Byte Position (0 to 6 )
            Value   (uint8) - Routing Byte Value
        """
        try:
            Pos = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Pos parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Pos < 0 or Pos > 6:
            raise exceptions.InputError(f'Pos parameter must be betwwen 0 and 6, but "{Pos}" was supplied.')  
            
        try:
            Value = int(Values[1])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[1]}" was supplied.\n{e}')
        if Value < 0 or Value >= 2**8:
            raise exceptions.InputError(f'Value parameter must be unisgned 8-bit, but "{Value}" was supplied.')      

        return [Pos, Value]      

    def _parseSystemParameter_SpaceWireDataProtocolSelect(self, *Values):  
        """
        SpaceWire Data CCSDS Protocol Select
         - Note: Use this parameter with CARE.
         - This parameter will typically never be changed from the factory value.  
    
        Mandatory Arguments:
            Value (uint8)  - 0 : Simera Sense Standard Protocol
                             1 : Custom Protocol
                             2 : CCSDS Packet Protocol, excluding Secondary Header
                             3 : CCSDS Packet Protocol, including Secondary Header
        """
        try:
            Value = int(Values[0])
        except ValueError as e:
            raise exceptions.InputError(f'Value parameter must be an integer, but "{Values[0]}" was supplied.\n{e}')
        if Value < 0 or Value > 3:
            raise exceptions.InputError(f'Value parameter must be 0 to 3, but "{Value}" was supplied.')      

        return [Value]

    def _parseSystemParameter_SpaceWireDataPayloadLimit(self, *Values):  
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
        if Value < 0 or Value >= 2**16:
            raise exceptions.InputError(f'Value parameter must be unsigned 16-bit, but "{Value}" was supplied.')             

        byte0 = (Value>>0)%256
        byte1 = (Value>>8)%256
        
        return [byte0, byte1]        
    
    # --- Bootloader Specifc Commands --- #    
    
    def EnterBootloader(self):
        """
        Enter and stay in the bootloader.
         - Note: This command will only be accepted immediately afeter power-up (within 500 ms).
         
         - This prevents the automatic booting of the default application.
         - This allows the other bootloader commands to be issued.
        """
        data = [0x70]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending EnterBootloader command.\n{e}')      

    def DisableProtection(self, Latchup, Ecc, Wdt):
        """
        Disable the Latch-up and Processor Monitoring protection temporarily.
         - Note: This command will only be accepted immediately after power-up (within 500 ms).         
         - Note: Use this parameter with EXTREME CARE for the diagnosis of failure conditions.
        
        Mandatory Arguments:
            Latchup (uint8) 0x94 to disable Latch-up Protection. Any other value has no effect.
            Ecc     (uint8) 0x68 to disable the ECC resets.
            Wdt     (uint8) 0x39 to disable the Watchdog Timer related resets.
        """
        try:
            Latchup = int(Latchup)
        except ValueError as e:
            raise exceptions.InputError(f'Latchup must be an integer, but "{Latchup}" was supplied.\n{e}')
        if Latchup < 0 or Latchup >= 2**8:
            raise exceptions.InputError(f'Latchup must be 8-bit, but "{Latchup}" was supplied.')
            
        try:
            Ecc = int(Ecc)
        except ValueError as e:
            raise exceptions.InputError(f'Ecc must be an integer, but "{Ecc}" was supplied.\n{e}')
        if Ecc < 0 or Ecc >= 2**8:
            raise exceptions.InputError(f'Ecc must be 8-bit, but "{Ecc}" was supplied.')            

        try:
            Wdt = int(Wdt)
        except ValueError as e:
            raise exceptions.InputError(f'Wdt must be an integer, but "{Wdt}" was supplied.\n{e}')
        if Wdt < 0 or Wdt >= 2**8:
            raise exceptions.InputError(f'Wdt must be 8-bit, but "{Wdt}" was supplied.') 
            
        data = [0x71, Latchup, Ecc, Wdt]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending DisableProtection command.\n{e}')             

    def ManualBootApp(self, AppNum):
        """
        Manually boot a specific (or default) application from the bootloader.
         - Note: This command will only be accepted by the bootloader.
        
        Mandatory Arguments:
            AppNum (uint8)  - 0 = Factory, 1 = User 1, 2 = User 2, any other value = Default Application
        """
        
        try:
            AppNum = int(AppNum)
        except ValueError as e:
            raise exceptions.InputError(f'AppNum must be an integer, but "{AppNum}" was supplied.\n{e}')
        if AppNum < 0 or AppNum >= 2**8:
            raise exceptions.InputError(f'AppNum must be 8-bit, but "{AppNum}" was supplied.')
            
        data = [0x72, AppNum]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending ManualBootApp command.\n{e}')   

    def SetDefaultApp(self, AppNum):
        """
        Set the default application to boot.
         - Note: This command will only be accepted by the bootloader.         
        
        Mandatory Arguments:
            AppNum (uint8)  - 0 = Factory, 1 = User 1, 2 = User 2
        """
        
        try:
            AppNum = int(AppNum)
        except ValueError as e:
            raise exceptions.InputError(f'AppNum must be an integer, but "{AppNum}" was supplied.\n{e}')
        if AppNum not in (0,1,2):
            raise exceptions.InputError(f'AppNum must be 0, 1 or 2, but "{AppNum}" was supplied.')
            
        data = [0x73, AppNum]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending SetDefaultApp command.\n{e}')     

    def ProgramSetup(self, AppNum, AppHeader):
        """
        Setup the Programming of a new application to a specific application area.
         - Note: This command will only be accepted by the bootloader.         
        
        Mandatory Arguments:
            AppNum  (uint8)     - 0 = Factory, 1 = User 1, 2 = User 2
            AppHdr  (32 bytes)  - List of 32 bytes. First 32 bytes of the application image (binary) file.
        """
        
        try:
            AppNum = int(AppNum)
        except ValueError as e:
            raise exceptions.InputError(f'AppNum must be an integer, but "{AppNum}" was supplied.\n{e}')
        if AppNum not in (0,1,2):
            raise exceptions.InputError(f'AppNum must be 0, 1 or 2, but "{AppNum}" was supplied.')
            
        if not isinstance(AppHeader, list) and not isinstance(AppHeader, numpy.ndarray): AppHeader = [ AppHeader ]

        if isinstance(AppHeader, list):
            data = [0x74, AppNum]
            data.extend(AppHeader)
        else:
            data = numpy.insert(AppHeader, 0, [0x74, AppNum])                           

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending ProgramSetup command.\n{e}')  

    def ProgramData(self, AppData):
        """
        Program Data for the new appliction, to the application area. 
         - Note: This command will only be accepted by the bootloader.         
         This commands should only be used after a ProgramSetup command.         
        
        Mandatory Arguments:
            AppData  (varies)  - List of up to 128 bytes. Binary data from the application image (binary) file, following the application header.
        """
            
        if not isinstance(AppData, list) and not isinstance(AppData, numpy.ndarray): AppData = [ AppData ]

        if isinstance(AppData, list):
            data = [0x75]
            data.extend(AppData)
        else:
            data = numpy.insert(AppData, 0, [0x75])                           

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending ProgramData command.\n{e}')    

    def ProgramDone(self):
        """
        Indicate that the programming of the application is done.
        - Note: This command will only be accepted by the bootloader.         
        """
        data = [0x76]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending ProgramDone command.\n{e}')     

    def GetAppHeader(self, AppNum):
        """
        Retrieve the header infomration of a specific application. The result is available via ReqAppHeader.
         - Note: This command will only be accepted by the bootloader.         
        
        Mandatory Arguments:
            AppNum (uint8)  - 0 = Factory, 1 = User 1, 2 = User 2
        """
        
        try:
            AppNum = int(AppNum)
        except ValueError as e:
            raise exceptions.InputError(f'AppNum must be an integer, but "{AppNum}" was supplied.\n{e}')
        if AppNum not in (0,1,2):
            raise exceptions.InputError(f'AppNum must be 0, 1 or 2, but "{AppNum}" was supplied.')
            
        data = [0x77, AppNum]

        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending GetAppHeader command.\n{e}')             

    ############################################################################
    ## REQUESTS ##
    ##############
    def ReqSubsystemStates(self):
        """
        Return the state of the imager subsystems
        
        raw, dictionary = ReqSubsystemStates()
    
        Returns the raw value read, as well as a Dictionary:
            ('Session', 'Cfg', 'Sen', 'Capture', 'Read')
        """
        req_id = 0x81
        req_length = 1
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSubsystemStates request.\n{e}')

        if isinstance(retval, list):
            retval = retval[0]

        # Extract bit mask
        Session = (retval & 0x0003)
        Cfg     = (retval & 0x0004)>>2
        Sen     = (retval & 0x0008)>>3
        Capture = (retval & 0x0030)>>4
        Read    = (retval & 0x0040)>>6

        return retval, {'Session': Session,
                        'Cfg'    : Cfg,
                        'Sen'    : Sen,
                        'Capture': Capture,
                        'Read'   : Read}
        
    def ReqCommandStatus(self):
        """
        Return the status of the most recent command
        
        status_id = ReqCommandStatus()
    
        Returns the raw status ID. Zero means no error.
        Error strings can be obtained by calling "GetCommandStatusString()"        
        """
        req_id = 0x82
        req_length = 1
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqCommandStatus request.\n{e}')
        
        if isinstance(retval, list):
            retval = retval[0]

        return retval
 
    def GetCommandStatusString(self, status):
        """
        Return the message string for provided command status
        
        string = GetCommandStatusString(status)
        """
        if status in COMMAND_STATUS_STRINGS:
            return COMMAND_STATUS_STRINGS[status]
        else:
            return f'Undefined Command Error'
        
    def ReqStartupStatus(self):
        """
        Return the status of the imager startup sequence
        
        raw, dictionary = ReqStartupStatus()
    
        Returns the raw value read, as well as a dictonary:
            ('Busy', 'Sys', 'Img', 'Sess','Flash')
        """
        req_id = 0x83
        req_length = 1
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqStartupStatus request.\n{e}')

        if isinstance(retval, list):
            retval = retval[0]

        # Extract bit mask
        Busy = (retval & 0x0001)
        Sys  = (retval & 0x0002)>>1
        Img  = (retval & 0x0004)>>2
        Sess = (retval & 0x0008)>>3
        Flash = (retval & 0x0010)>>4

        return retval, {'Busy' : Busy,
                        'Sys'  : Sys,
                        'Img'  : Img,
                        'Sess' : Sess,
                        'Flash': Flash}

    def ReqStorageStatus(self):
        """
        Return the status of the imager storage
        
        sessions, capacity = ReqStorageStatus()
    
        Returns the number of used sessions (out of 512) and used storage capacity (as a percentage).        
        """
        req_id = 0x84
        req_length = 3
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqStorageStatus request.\n{e}')

        if isinstance(retval, list):
            sessions = retval[0] + (retval[1]<<8)
            capacity = retval[2]

        return sessions, capacity

    def ReqSessionInformation(self):
        """
        Return the session information of a session previously specified by the GetSessionInformation command.
        
        status, size, used = ReqSessionInformation()
    
        Returns the session status, reserved session size (in bytes) and session space used (in bytes).        
        """
        req_id = 0x85
        req_length = 18
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSessionInformation request.\n{e}')

        if isinstance(retval, list):
            status = retval[0] + (retval[1]<<8)
            size   = retval[2] + (retval[3]<<8) + (retval[4]<<16) + (retval[5]<<24) + (retval[6]<<32) + (retval[7]<<40) + (retval[8]<<48) + (retval[9]<<56)
            used   = retval[10] + (retval[11]<<8) + (retval[12]<<16) + (retval[13]<<24) + (retval[14]<<32) + (retval[15]<<40) + (retval[16]<<48) + (retval[17]<<56)

        return status, size, used
        
    def ReqCurrentSessionId(self):
        """
        Return the session ID of the current session
        
        id = ReqCurrentSessionId()
    
        Returns the session ID.        
        """
        req_id = 0x86
        req_length = 4
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqCurrentSessionId request.\n{e}')

        if isinstance(retval, list):
            id = retval[0] + (retval[1]<<8) + (retval[2]<<16) + (retval[3]<<24)            

        return id
        
    def ReqCurrentSessionSize(self):
        """
        Return the session size of the current session
        
        size, used = ReqCurrentSessionSize()
    
        Returns the current session's reserved size (in bytes) and space used (in bytes).        
        """
        req_id = 0x87
        req_length = 16
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqCurrentSessionSize request.\n{e}')

        if isinstance(retval, list):
            size   = retval[0] + (retval[1]<<8) + (retval[2]<<16) + (retval[3]<<24) + (retval[4]<<32) + (retval[5]<<40) + (retval[6]<<48) + (retval[7]<<56)
            used   = retval[8] + (retval[9]<<8) + (retval[10]<<16) + (retval[11]<<24) + (retval[12]<<32) + (retval[13]<<40) + (retval[14]<<48) + (retval[15]<<56)

        return size, used        

    def ReqImagerTime(self):
        """
        Returns the imager time as a 64-bit microsecond value
        
        raw = ReqImagerTime()
    
        Returns the raw value        
        """
        req_id = 0x88
        req_length = 8
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqImagerTime request.\n{e}')
            
        if isinstance(retval, list):
            raw = retval[0] + (retval[1]<<8) + (retval[2]<<16) + (retval[3]<<24) + (retval[4]<<32) + (retval[5]<<40) + (retval[6]<<48) + (retval[7]<<56)

        return raw    

    def ReqImagingParameter(self):
        """
        Returns the imaging parameter previously specified using the GetImagingParameter command
        
        raw = ReqImagingParameter()
    
        Returns the raw value(s) as a list of bytes       
        """
        
        # Check if the GetImagingParameter command was already done
        if self.RetreivedImgParamId == None:
            raise exceptions.Error(f'No imaging parameter was retrieved. Use the GetImagingParameter command first, to retrieve an imaging parameter.')
        
        # Call the appropriate request handler, according ot the Retreived Img Parm ID
        retval = self.imaging_param_req_handlers[self.RetreivedImgParamId]()
               
        return retval 
        
    def ReqCeTelemetry(self):
        """
        Returns the Control Electronics Telemetry, previously retrieved using the GetCeTelemetry Command.
        
        tlm = ReqCeTelemetry()
    
        Returns the telemetry value(s) as a list
        The values can be printed as follow:
            for i in range(len(tlm)):
                tlmval = tlm[i]
                tlminfo = self.ce_tlm_info[i]
                print(f"{i:>2}  {tlminfo['Name']:12} : {tlmval:>4} {tlminfo['Unit']}")
        """
               
        req_id = 0x8A
        req_length = 59
        try:
            raw = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqCeTelemetry request.\n{e}')                   
        
        tlm = [
                raw[ 0] + raw[ 1]*256, # V_FeeSmps    ADC0,0 
                raw[ 2] + raw[ 3]*256, # C_FeeSmps    ADC0,1 
                raw[ 4] + raw[ 5]*256, # C_FeeLdo     ADC0,2 
                raw[ 6] + raw[ 7]*256, # V_FeeNegSmps ADC0,3 
                raw[ 8] + raw[ 9]*256, # C_Brd5V0     ADC0,4 
                raw[10] + raw[11]*256, # V_FeeOpAmp   ADC0,5 
                raw[12] + raw[13]*256, # V_SdramVtt   ADC0,6 
                raw[14] + raw[15]*256, # V_Brd3V3     ADC0,7 
                raw[16] + raw[17]*256, # V_Brd2V5     ADC0,8 
                raw[18] + raw[19]*256, # V_RefCal0    ADC0,9 
                raw[20] + raw[21]*256, # V_FeeLdo     ADC0,10
                raw[22] + raw[23]*256, # V_IntTst0    ADC0,11
                raw[24] + raw[25]*256, # V_REFM0      ADC0,12
                raw[26] + raw[27]*256, # V_REFP0      ADC0,13
                raw[28] + raw[29]*256, # C_BrdLdo     ADC1,0 
                raw[30] + raw[31]*256, # C_Smps3V3    ADC1,1 
                raw[32] + raw[33]*256, # V_Smps1V2    ADC1,3 
                raw[34] + raw[35]*256, # V_Smps1V0    ADC1,5 
                raw[36] + raw[37]*256, # C_Smps1V0    ADC1,6
                raw[38] + raw[39]*256, # C_Smps1V2    ADC1,7
                raw[40] + raw[41]*256, # V_Brd1V8     ADC1,8
                raw[42] + raw[43]*256, # C_SdramVtt   ADC1,9
                raw[44] + raw[45]*256, # V_RefCal1    ADC1,10
                raw[46] + raw[47]*256, # V_IntTst1    ADC1,11
                raw[48] + raw[49]*256, # V_REFM1      ADC1,12
                raw[50] + raw[51]*256, # V_REFP1      ADC1,13
                raw[52] + raw[53]*256, # V_Fpga1V0    
                raw[54] + raw[55]*256, # V_Fpga1V8    
                raw[56] + raw[57]*256, # V_Fpga2V5    
                raw[58]                # T_Fpga       
               ]
        
        # Adjust for 2's compliment (negative)
        # All values are int16, except last is int8
        for i in range(len(tlm)):
            # Last channel
            if (i == (len(tlm)-1)):
                # int8
                if tlm[i] >= 0x80:
                    tlm[i] -= 0x100            
            # All other channels
            else:
                # int16           
                if tlm[i] >= 0x8000:
                    tlm[i] -= 0x10000
        
        return tlm

    def ReqFeeTelemetry(self):
        """
        Returns the Front-End Elctronics Telemetry, previously retrieved using the GetFeeTelemetry Command. The FEE must also be enabled.

        tlm = ReqFeeTelemetry()

        Returns the telemetry value(s) as a list
        The values can be printed as follow:
            for i in range(len(tlm)):
                tlmval = tlm[i]
                tlminfo = self.fee_tlm_info[i]
                print(f"{i:>2}  {tlminfo['Name']:12} : {tlmval:>4} {tlminfo['Unit']}")
         """

        req_id = 0x8B
        req_length = 29
        try:
            raw = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqFeeTelemetry request.\n{e}')                   

        tlm = [
                raw[ 0] + raw[ 1]*256, # V_FeeSmps    ADC0,0 
                raw[ 2] + raw[ 3]*256, # V_FeeLdo     ADC0,1 
                raw[ 4] + raw[ 5]*256, # (unused)     ADC0,2 
                raw[ 6] + raw[ 7]*256, # V_TFLLow2    ADC0,3 
                raw[ 8] + raw[ 9]*256, # V_TFLLow3    ADC0,4 
                raw[10] + raw[11]*256, # V_Bandgap    ADC0,5 
                raw[12] + raw[13]*256, # V_ResetL     ADC0,6 
                raw[14] + raw[15]*256, # V_RefADC     ADC0,7 
                raw[16] + raw[17]*256, # V_CmvRef     ADC0,8 
                raw[18] + raw[19]*256, # V_Ramp2      ADC0,9 
                raw[20] + raw[21]*256, # V_Ramp1      ADC0,10
                raw[22] + raw[23]*256, # V_IntTst     ADC0,11
                raw[24] + raw[25]*256, # V_REFM       ADC0,12
                raw[26] + raw[27]*256, # V_REFP       ADC0,13
                raw[28]                # T_CMV      
               ]
               
        # Adjust for 2's compliment (negative)
        # All values are int16, except last is int8
        for i in range(len(tlm)):
            # Last channel
            if (i == (len(tlm)-1)):
                # int8
                if tlm[i] >= 0x80:
                    tlm[i] -= 0x100            
            # All other channels
            else:
                # int16           
                if tlm[i] >= 0x8000:
                    tlm[i] -= 0x10000
        
        return tlm       
        

    def ReqImagerInformation(self):
        """
        Returns the Imager Information        
        raw = ReqImagerInformation()
    
        Returns the raw value(s) as a list of bytes       
        """
               
        req_id = 0x8C
        req_length = 12
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqImagerInformation request.\n{e}')                   

        if isinstance(retval, list):
            productId = retval[0] + (retval[1]<<8) + (retval[2]<<16) + (retval[3]<<24)
            serialNum = retval[4] + (retval[5]<<8)
            firmwareMaj = retval[6]
            firmwareMin = retval[7]
            softwareMaj = retval[8]
            softwareMin = retval[9]
            baselineNum = retval[10] + (retval[11]<<8)

        return productId, serialNum, firmwareMaj, firmwareMin, softwareMaj, softwareMin, baselineNum       

    def ReqSessionListEntry(self):
        """
        Returns an Entry (Session ID) from the Seesion List
        
        SessionID = ReqSessionListEntry()
    
        Returns the Session ID as a 32-bit unsigned integer       
        """
               
        req_id = 0x8D
        req_length = 4
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSessionList request.\n{e}')                   

        if isinstance(retval, list):
            id = retval[0] + (retval[1]<<8) + (retval[2]<<16) + (retval[3]<<24)       

        return id    

    def ReqSystemParameter(self):
        """
        Returns the system parameter previously specified using the GetSystemParameter command
        
        raw = ReqSystemParameter()
    
        Returns the raw value(s) as a list of bytes       
        """
        # Check if the GetSystemParameter command was already done
        if self.RetreivedSysParamId == None:
            raise exceptions.Error(f'No system parameter was retrieved. Use the GetSystemParameter command first, to retrieve a system parameter.')
        
        # Call the appropriate request handler, according to the Retreived System Parameter ID
        retval = self.system_param_req_handlers[self.RetreivedSysParamId]()
               
        return retval

    def ReqResetStatus(self):
        """
        Returns the reset status of the imager.
        
        reset_reason, latchup_flags, app_number, run_time  = ReqResetStatus()
    
        Returns the reset reason, latch-up flags, running application number and run time.
        """
               
        req_id = 0x90
        req_length = 7
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqResetStatus request.\n{e}')                   

        if isinstance(retval, list):
            reset_reason  = retval[0]
            latchup_flags = retval[1]
            app_number    = retval[2]
            run_time      = retval[3] + (retval[4]<<8) + (retval[5]<<16) + (retval[6]<<24)       

        return reset_reason, latchup_flags, app_number, run_time     
        
    def GetResetReasonString(self, reason):
        """
        Return the message string for provided reset reason
        
        string = GetResetReasonString(reason)
        """
        if reason in RESET_REASON_STRINGS:
            return RESET_REASON_STRINGS[reason]
        else:
            return f'Undefined Reset Reason Error'        

    def GetLatchupFlagsString(self, flags):
        """
        Return the message string for provided latch-up flags

        string = GetLatchupFlagsString(flags)
        """
        flags = int(flags)
        ret_str = ""
        _first = True
        if flags >=0 and flags <= 2**7:
            for i in range(7):
                j = 2**i    
                if flags & j:
                    if _first:
                        _first = False
                        ret_str += f"{LATCH_UP_CHANNEL_STRINGS[i]}"
                    else:
                        ret_str += f", {LATCH_UP_CHANNEL_STRINGS[i]}"
            return ret_str
        else:
            return f'Undefined latch-up flags'

    def GetAppNumberString(self, app_number):

        app_str = f"Undefined (0x{app_number:02x})"
        if app_number == 0xBB: app_str = "Bootloader"
        if app_number == 0x00: app_str = "Factory"
        if app_number == 0x01: app_str = "User-1"
        if app_number == 0x02: app_str = "User-2"
        return app_str

    def ReqMonitorCounters(self):
        """
        Returns Processor Monitor Counters.
        
        IC_SEC, IC_DED, DC_SEC, DC_DED, MEM_BTL_SEC, MEM_BTL_DED, MEM_APP_SEC, MEM_APP_DED, WDT = ReqSystemParameter()
    
        Returns the ECC error counters and WDT counter values.
        """
               
        req_id = 0x91
        req_length = 17
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqMonitorCounters request.\n{e}')                   

        retdict = {}

        if isinstance(retval, list):
            IC_SEC = retval[0] + (retval[1]<<8)
            IC_DED = retval[2] + (retval[3]<<8)

            DC_SEC = retval[4] + (retval[5]<<8)
            DC_DED = retval[6] + (retval[7]<<8)
            
            MEM_BTL_SEC = retval[8] + (retval[9]<<8)
            MEM_BTL_DED = retval[10] + (retval[11]<<8)

            MEM_APP_SEC = retval[12] + (retval[13]<<8)
            MEM_APP_DED = retval[14] + (retval[15]<<8)
            
            WDT = retval[16]


            retdict['IC_SEC'] = IC_SEC
            retdict['IC_DED'] = IC_DED
            retdict['DC_SEC'] = DC_SEC
            retdict['DC_DED'] = DC_DED
            retdict['MEM_BTL_SEC'] = MEM_BTL_SEC
            retdict['MEM_BTL_DED'] = MEM_BTL_DED
            retdict['MEM_APP_SEC'] = MEM_APP_SEC
            retdict['MEM_APP_DED'] = MEM_APP_DED
            retdict['WDT'] = WDT

        return retdict
        
    def ReqFlashDiagnostics(self):
        """
        Returns the Flash Diagnostic Infomration.
        
        status, failed_targets = ReqFlashDiagnostics()
    
        Returns the status/error code and failed targets (as a 16-bit vector).
        """

        req_id = 0x92
        req_length = 3
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqFlashDiagnostics request.\n{e}')                   

        if isinstance(retval, list):
            status          = retval[0]                       
            failed_targets  = retval[1] + (retval[2]<<8)

        return status, failed_targets
        
    def ReqSessionDiagnostics(self):
        """
        Returns the Session Diagnostic Information after calling GetSessionInformation command.
        
        status, failed_targets = ReqSessionDiagnostics()
    
        Returns the session error flags, starting block and block length.
        """
               
        req_id = 0x93
        req_length = 5
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSessionDiagnostics request.\n{e}')                   

        if isinstance(retval, list):
            error_flags  = retval[0]                       
            start_block  = retval[1] + (retval[2]<<8)
            block_length = retval[3] + (retval[4]<<8)

        return error_flags, start_block, block_length 

    def GetSpaceWireLinkStateString(self, link_state):
        """
        Return the message string for provided spacewire lkink state
        
        string = GetSpaceWireLinkStateString(link_state)
        """
        link_str = f"Undefined (0x{link_state:02x})"
        if (link_state & 0x3) == 0x00: link_str = "Disabled"       # Disabled
        if (link_state & 0x3) == 0x01: link_str = "Disconnected"   # Enabled, but disconnected
        if (link_state & 0x3) == 0x02: link_str = "Connecting"     # Enabled, busy connceting
        if (link_state & 0x3) == 0x03: link_str = "Connected"      # Enabled, connected.
        return link_str
    
    def ReqSpaceWireLinkStatus(self):
        """
        Returns the SpaceWire Link status.
        
        status, error = ReqSpaceWireLinkStatus()
    
        Returns the status of the link and any error flags.
        """
               
        req_id = 0x95
        req_length = 2
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSpaceWireLinkStatus request.\n{e}')                   

        if isinstance(retval, list):
            status  = retval[0]
            error_flags  = retval[1]

        return status, error_flags
        
    def ReqSpaceWirePacketDiagnostics(self):
        """
        Returns the SpaceWire Control Interface Packet Diagnostics.
        
        status, error = ReqSpaceWirePacketDiagnostics()
    
        Returns the SpaceWire Packet counters and error flags.
        """
               
        req_id = 0x96
        req_length = 17
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSpaceWirePacketDiagnostics request.\n{e}')                   

        if isinstance(retval, list):
            packet_rx_cnt  = retval[0]  + (retval[1]<<8)  + (retval[2]<<16)  + (retval[3]<<24)
            packet_rx_fail = retval[4]  + (retval[5]<<8)  + (retval[6]<<16)  + (retval[7]<<24)
            packet_rx_ok   = retval[8]  + (retval[9]<<8)  + (retval[10]<<16) + (retval[11]<<24)
            packet_tx      = retval[12] + (retval[13]<<8) + (retval[14]<<16) + (retval[15]<<24)
            packet_error_flags = retval[16]

        return packet_rx_cnt, packet_rx_fail, packet_rx_ok, packet_tx, packet_error_flags

    def ReqRS422UartDiagnostics(self):
        """
        Returns the RS422 UART Diagnostics.
        
        status, error = ReqRS422UartDiagnostics()
    
        Returns the RS422 Packet counters and error flags.
        """
               
        req_id = 0x97
        req_length = 13
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqRS422UartDiagnostics request.\n{e}')                   

        if isinstance(retval, list):
            rx_byte_cnt      = retval[0]  + (retval[1]<<8)  + (retval[2]<<16)  + (retval[3]<<24)
            rx_byte_used_cnt = retval[4]  + (retval[5]<<8)  + (retval[6]<<16)  + (retval[7]<<24)
            rx_byte_dropped  = retval[8]  + (retval[9]<<8)  + (retval[10]<<16) + (retval[11]<<24)            
            rx_error_flags   = retval[12]

        return rx_byte_cnt, rx_byte_used_cnt, rx_byte_dropped, rx_error_flags
 
    def ReqRS422PacketDiagnostics(self):
        """
        Returns the RS422 (Packet Stream) Control Interface Diagnostics.
        
        status, error = ReqRS422PacketDiagnostics()
    
        Returns the RS422 Packet counters and error flags.
        """
               
        req_id = 0x98
        req_length = 17
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqRS422PacketDiagnostics request.\n{e}')                   

        if isinstance(retval, list):
            packet_rx_cnt  = retval[0]  + (retval[1]<<8)  + (retval[2]<<16)  + (retval[3]<<24)
            packet_rx_fail = retval[4]  + (retval[5]<<8)  + (retval[6]<<16)  + (retval[7]<<24)
            packet_rx_ok   = retval[8]  + (retval[9]<<8)  + (retval[10]<<16) + (retval[11]<<24)
            packet_tx      = retval[12] + (retval[13]<<8) + (retval[14]<<16) + (retval[15]<<24)
            packet_error_flags = retval[16]

        return packet_rx_cnt, packet_rx_fail, packet_rx_ok, packet_tx, packet_error_flags
        
    def ReqCompressSessionProgress(self):
        """
        Return the progress of the Compress Session task that is busy.
        
        progress = ReqCompressSessionProgress()

        """
        req_id = 0x99
        req_length = 11
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqCompressSessionProgress request.\n{e}')

        if isinstance(retval, list):
            busy = retval[0]
            band_lines_total = retval[1]  + (retval[2]<<8)  + (retval[3]<<16)  + (retval[4]<<24)
            band_lines_done  = retval[5]  + (retval[6]<<8)  + (retval[7]<<16)  + (retval[8]<<24)
            bands_total = retval[9]
            bands_done = retval[10]

        return busy, band_lines_total, band_lines_done, bands_total, bands_done    

    def ReqCompressSessionId(self):
        """
        Return the session ID of the compression session
        
        raw = ReqCompressSessionId()

        Returns the session ID.        
        """
        req_id = 0x9A
        req_length = 4
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqCompressSessionId request.\n{e}')

        if isinstance(retval, list):
            raw = retval[0] + (retval[1]<<8) + (retval[2]<<16) + (retval[3]<<24)     

        return raw
        
    def ReqSpiDiagnostics(self):
        """
        Returns the SPI Control Interface Diagnostics.
        
        trans_cnt = ReqSpiDiagnostics()
    
        Returns the SPI Transactoin count.
        """
               
        req_id = 0x9B
        req_length = 4
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSpiDiagnostics request.\n{e}')                   

        if isinstance(retval, list):
            trans_cnt  = retval[0]  + (retval[1]<<8)  + (retval[2]<<16)  + (retval[3]<<24)          

        return trans_cnt
                
    # --- Handle Imaging Parameter Requests --- //  
    
    def _handleImagingParameterReq_ThumbnailFactor(self):
        """
        Return the Thumbnail Factor
    
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
    
    def _handleImagingParameterReq_PlatformID(self):
        """
        Return the Platform ID
    
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

    def _handleImagingParameterReq_InstrumentID(self):
        """
        Return the Imager ID
    
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
        
    def _handleImagingParameterReq_BinningFactor(self):
        """
        Return the Binning Factor
    
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
        
    # --- Handle System Parameter Requests --- //     
                
    def _handleSystemParameterReq_FlashTargets(self):
        """
        Return the Flash Targets that are enabled, as a 16-bit vector.
    
        """       
        req_id = 0x8E
        req_length = 2

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSystemParameter request.\n{e}')               
                   
        if isinstance(retval, list):
            raw = retval[0] + (retval[1]<<8)
            
        return raw 
        
    def _handleSystemParameterReq_FlashLunsDisable(self):
        """
        Return the Flash LUNs that are disabled, as a 16-bit vector.
    
        """       
        req_id = 0x8E
        req_length = 2

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSystemParameter request.\n{e}')               
                   
        if isinstance(retval, list):
            raw = retval[0] + (retval[1]<<8)
            
        return raw     

    def _handleSystemParameterReq_DataInterface(self):
        """
        Return the Data Interface.
    
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
        
    def _handleSystemParameterReq_SensorTempCalibrateFactorA(self):
        """
        Return Sensor Temperature Calibration Factor A.
    
        """       
        req_id = 0x8E
        req_length = 2

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSystemParameter request.\n{e}')               
                   
        if isinstance(retval, list):
            raw = retval[0] + (retval[1]<<8)

        # int16           
        if raw >= 0x8000:
            raw -= 0x10000            

        return raw           

    def _handleSystemParameterReq_SensorTempCalibrateFactorB(self):
        """
        Return Sensor Temperature Calibration Factor B.
    
        """       
        req_id = 0x8E
        req_length = 2

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSystemParameter request.\n{e}')               
                   
        if isinstance(retval, list):
            raw = retval[0] + (retval[1]<<8)

        # int16           
        if raw >= 0x8000:
            raw -= 0x10000
            
        return raw                   
        
    def _handleSystemParameterReq_LatchupChannelEnable(self):
        """
        Return the Latch-up Enabled Channels.
    
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
                        
    def _handleSystemParameterReq_LatchupChannelLimits(self):
        """
        Return the Latch-up Channel Current Limits    
        """        
        req_id = 0x8E
        req_length = 16

        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSystemParameter request.\n{e}')                                          
      
        limit0 = retval[0] + (retval[1]<<8)
        limit1 = retval[2] + (retval[3]<<8)
        limit2 = retval[4] + (retval[5]<<8)
        limit3 = retval[6] + (retval[7]<<8)
        limit4 = retval[8] + (retval[9]<<8)
        limit5 = retval[10] + (retval[11]<<8)
        limit6 = retval[12] + (retval[13]<<8)
        limit7 = retval[14] + (retval[15]<<8)
      
        return [limit0, limit1, limit2, limit3, limit4, limit5, limit6, limit7] 
      
    def _handleSystemParameterReq_LatchupFilterCount(self):
        """
        Return the Latch-up filter count.
    
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

    def _handleSystemParameterReq_MonitorEccSetup(self):
        """
        Return the Setup of the ECC Reset Sources.
    
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

    def _handleSystemParameterReq_MonitorWdtEnable(self):
        """
        Return the Watchdog Timer Enable.
    
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

    def _handleSystemParameterReq_MonitorWdtDivisor(self):
        """
        Return the Watchdog Timer Divisor.
    
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

    def _handleSystemParameterReq_SpaceWireBaudRate(self):
        """
        Return the SpaceWire Baud Rate.
    
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

    def _handleSystemParameterReq_SpaceWireImagerLogAddr(self):
        """
        Return the SpaceWire Imager Logical Address.
    
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
        
    def _handleSystemParameterReq_SpaceWireControlHostLogAddr(self):
        """
        Return the SpaceWire Control Host Logical Address.
    
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

    def _handleSystemParameterReq_SpaceWireControlHostRoutingByte(self):
        """
        Return the SpaceWire Control Host Routing Bytes.
    
        """        
        req_id = 0x8E
        req_length = 7
        
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSystemParameter request.\n{e}')          
        
        return retval            
        
    def _handleSystemParameterReq_SpaceWireDataHostLogAddr(self):
        """
        Return the SpaceWire Data Host Logical Address.
    
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

    def _handleSystemParameterReq_SpaceWireDataHostRoutingByte(self):
        """
        Return the SpaceWire Data Host Routing Bytes.
    
        """        
        req_id = 0x8E
        req_length = 7
        
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSystemParameter request.\n{e}')
        
        return retval       

    def _handleSystemParameterReq_SpaceWireDataProtocolSelect(self):
        """
        Return the SpaceWire Data Protocol selected state.
    
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

    def _handleSystemParameterReq_SpaceWireDataPayloadLimit(self):
        """
        Return the SpaceWire Data Payload Limit.
    
        """        
        req_id = 0x8E
        req_length = 2
        
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqSystemParameter request.\n{e}')
            
        if isinstance(retval, list):
            raw = retval[0] + (retval[1]<<8)
            
        return raw               
    
    # --- Bootloader Specific Requests --- #
   
    def ReqDefaultApp(self):
        """
        Return the default appliction number that is automatically booted.
        
        defapp = ReqDefaultApp()
    
        Returns the default application number.
        
        """
        req_id = 0xF0
        req_length = 1
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqDefaultApp request.\n{e}')

        if isinstance(retval, list):
            retval = retval[0]

        return retval
                        
    def ReqAppHeader(self):
        """
        Return the appliction header information previously specified by the GetAppHeader command.
        
        valid, raw, dictionary = ReqAppHeader()
    
        Returns the valid/invalid status of the app header, raw values, as well as a dictionary:
        
        """
        req_id = 0xF1
        req_length = 15
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqAppHeader request.\n{e}')

        if isinstance(retval, list):
            valid       = retval[0]
            magic       = retval[1] + (retval[2]<<8) + (retval[3]<<16) + (retval[4]<<24)
            version_maj = retval[5]
            version_min = retval[6]
            data_len    = retval[7] + (retval[8]<<8) + (retval[9]<<16) + (retval[10]<<24)
            data_check  = retval[11] + (retval[12]<<8)
            hdr_check   = retval[13] + (retval[14]<<8)

        return valid, retval, { 'Magic'         : magic,
                                'VersionMajor'  : version_maj,
                                'VersionMinor'  : version_min,
                                'DataLength'    : data_len,
                                'DataChecksum'  : data_check,
                                'HeaderChecksum': hdr_check}     

    def ReqAutoBootError(self):
        """
        Return error code for a failed automatic boot.
        
        retval = ReqDefaultApp()
    
        Returns the error code (as per the standard error list).
        
        """
        req_id = 0xF2
        req_length = 1
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqAutoBootError request.\n{e}')

        if isinstance(retval, list):
            retval = retval[0]

        return retval                                

    ############################################################################
    ## DEBUG ##
    ###########
    def _apbWrite(self, Addr, Data):
        """ 
        Performs a low-level APB Bus write access.
        
        WARNING: Use this command with caution.
        
        Mandatory Arguments:
            Addr - 32-bit address for the bus access
            Data - 32-bit data value
        """        
        try:
            Addr = int(Addr)
        except ValueError as e:
            raise exceptions.InputError(f'Addr parameter must be an integer, but "{Addr}" was supplied.\n{e}')

        try:
            Data = int(Data)
        except ValueError as e:
            raise exceptions.InputError(f'Data parameter must be an integer, but "{Data}" was supplied.\n{e}')

        addr0 = (Addr >>  0) & 0xFF
        addr1 = (Addr >>  8) & 0xFF
        data0 = (Data >>  0) & 0xFF
        data1 = (Data >>  8) & 0xFF
        data2 = (Data >> 16) & 0xFF
        data3 = (Data >> 24) & 0xFF

        data = [0x60, addr0, addr1, data0, data1, data2, data3]
        
        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending _apbWrite command.\n{e}')
        
    def _apbRead(self, Addr):
        """ 
        Performs a low-level APB Bus read access
        
        WARNING: Use this command with caution.
        
        Mandatory Arguments:
            Addr - 32-bit address for the bus access
        """
        try:
            Addr = int(Addr)
        except ValueError as e:
            raise exceptions.InputError(f'Addr parameter must be an integer, but "{Addr}" was supplied.\n{e}')

        addr0 = (Addr >>  0) & 0xFF
        addr1 = (Addr >>  8) & 0xFF

        data = [0x61, addr0, addr1]
        
        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending _apbRead command.\n{e}')
            
    def _GetDataDump(self, Source, Length):
        """ 
        Performs a raw memory dump of a certain source.      
        
        Mandatory Arguments:
            Source (uint8) -    0 = Factory System Parameters
                                1 = Default System Parameters
                                2 = Factory Imaging Parameters
                                3 = Default Imaging Parameters
            Length (uint8) -   Number of bytes to dump (maximum of 255)
        """
        try:
            Source = int(Source)
        except ValueError as e:
            raise exceptions.InputError(f'Source parameter must be an integer, but "{Source}" was supplied.\n{e}')
        if Source < 0 or Source >= 4:
            raise exceptions.InputError(f'Source parameter must be 0, 1, 2 or 3 but "{Source}" was supplied.')            

        try:
            Length = int(Length)
        except ValueError as e:
            raise exceptions.InputError(f'Length parameter must be an integer, but "{Length}" was supplied.\n{e}')
        if Length < 0 or Length > 255:
            raise exceptions.InputError(f'Length parameter must be a maximum of 255, but "{Length}" was supplied.')
                    
        self.RetrievedDataDumpLength = Length

        data = [0x62, Source, Length]
        
        try:
            retval = self._CtrlIfWrite(data)
        except Exception as e:
            raise exceptions.Error(f'Error sending _DataDump command.\n{e}')            

    def _ReqApbData(self):
        """ 
        Returns the data retrieved from the previous APB Read command.            
        """
        req_id = 0xE0
        req_length = 4
        try:
            retval = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending ReqApbData request.\n{e}')

        if isinstance(retval, list):
            raw = retval[0] + (retval[1]<<8) + (retval[2]<<16) + (retval[3]<<24)

        return raw
        
    def _ReqBlockAllocationTable(self):
        """
        Returns the Block Allocation Table
        
        raw = ReqBlockAllocationTable()
    
        Returns the raw value(s) as a list of bytes. Each bit of each byte represents a Block in the flash memory. '0' - empty, '1' - used/allocated      
        """
               
        req_id = 0xE1
        req_length = 252
        try:
            raw = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending _ReqBlockAllocationTable request.\n{e}')                            

        return raw        

    def _ReqBadBlockTable(self):
        """
        Returns the Bad Block Table
        
        raw = ReqBadBlockTable()
    
        Returns the raw value(s) as a list of bytes. Each bit of each byte represents a Block in the flash memory. '0' - Good, '1' - Bad      
        """  
               
        req_id = 0xE2
        req_length = 252
        try:
            raw = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending _ReqBadBlockTable request.\n{e}')                            

        return raw  
        
    def _ReqDataDump(self):
        """
        Returns the Dumped Data.
        
        raw = ReqDataDump()
    
        Returns the raw value(s) as a list of bytes.     
        """
        
        # Check if the GetDataDump command was already done
        if self.RetrievedDataDumpLength == None:
            raise exceptions.Error(f'Use the GetDataDump command first, to retrieve data.')  
            
        req_id = 0xE3
        req_length = self.RetrievedDataDumpLength
        try:
            raw = self._CtrlIfRead(req_id, req_length)
        except Exception as e:
            raise exceptions.Error(f'Error sending _ReqDataDump request.\n{e}')                            

        return raw          
        
         
    # --- Internal Methods --- #

    def setEGSE(self, EGSE):
        """
        Set the EGSE instance to be used to interface to the xScape Imager
    
        Mandatory Argument:
            EGSE    - instance of simera.pylibEgseFx3.EGSE class
        """
        if not isinstance(EGSE, simera.pylibEgseFx3.EGSE):
            raise exceptions.InputError('EGSE parameter must be an instance of the simera.pylibEgseFx3.EGSE class')
        self.EGSE = EGSE

    def setI2Caddress(self, i2c_address):
        """
        Set the xScape Imager I2C address
        The control interface is not set to I2C automatically, use the "setControlInterface() method.
    
        Mandatory Argument:
            i2c_address - the I2C address
        """
        self.i2c_address = i2c_address

    def setPacketProtocol(self, protocol_module = None):
        """
         Set or add a non-standard (custom) Packet Protocol.       

        Optional Argument:
            protocol_module - the name of the python module defining the protocol.
                            - if not specified (None), the current protocol is removed and standard is used.
        """        
        self.PacketProtocol = protocol_module
        if (protocol_module != None):
            import importlib
            global protocol
            try:
                protocol = importlib.import_module(protocol_module)
            except Exception as e:
                raise exceptions.InputError(f'Could not find module {protocol_module}.\n{e}')
            
            # Save old (default) methods
            self.old_AddProtocol    = self._AddProtocol
            self.old_RemoveProtocol = self._RemoveProtocol
            self.old_ReadOverhead   = self._ReadOverhead            
            
            # Override local methods
            self._AddProtocol    = protocol.Add
            self._RemoveProtocol = protocol.Remove
            self._ReadOverhead   = protocol.ReadOverhead                        
            
        else:
            # Restore local methods
            print(f'Restore!')            
            self._AddProtocol    = self.old_AddProtocol
            self._RemoveProtocol = self.old_RemoveProtocol
            self._ReadOverhead   = self.old_ReadOverhead                        

    def setCcsdsControlProtocol(self, enable = True, sec_enable = False, apid = 0x000, ancillary = []):
        """
        Set the CCSDS Control Protocol Options.
        Nite: Only applicable for SpaceWire and UART Interfaces.
        """
        self.ccsds_enable = enable
        self.ccsds_sec_enable = sec_enable
        self.ccsds_apid = apid
        self.ccsds_ancillary = ancillary

    def setControlInterface(self, interface_type):
        """
        Specify which control interface to use for the imager.
        Can be I2C, SPI, RS4xx, SpaceWire, CAN

        Mandatory Argument:
            interface_type   - the enumerated value for the interface type to use.
                               Must be one of the simera.xscape module constants:
                                    CONTROL_INTERFACE_I2C
                                    CONTROL_INTERFACE_SPI
                                    CONTROL_INTERFACE_RS4xx
                                    CONTROL_INTERFACE_SpW
        """
        self.control_interface = interface_type

    def setControlInterfaceI2C(self):
        """
        Use I2C control interface for the imager
        """
        self.control_interface = CONTROL_INTERFACE_I2C

    def setControlInterfaceSPI(self):
        """
        Use SPI control interface for the imager
        """
        self.control_interface = CONTROL_INTERFACE_SPI

    def setControlInterfaceRS4xx(self, uart):
        """
        Use RS4xx Control Interface for the imager, using a COM port on the PC, not the EGSE.

        Mandatory Arguments:
            port   - text string of the COM port (e.g. 'COM2')
            baud   - baud rate in bits per second (e.g. 115200)
        """
        self.control_interface = CONTROL_INTERFACE_RS4xx
        self.uart = uart

    def setControlInterfaceSpW(self, LogicalAddrImager, RoutingBytes=[]):
        """
        Use SpW control interface for the imager
        Mandatory Arguments:
            AddrLocal  - Logical Address for the EGSE
            AddrImager - Logical Address of thge Imager
        """        
        self.control_interface = CONTROL_INTERFACE_SpW        
        self.SpwDestinationAddr = LogicalAddrImager;        
        self.SpwRoutingBytes = RoutingBytes;

    # --- Protocol Methods --- #
    def _AddCcsdsHeader(self, trans_bytes, sec_enable, apid, ancillary=[]):
        """
        Add the CCSDS header(s) to the suppleid Transaction Bytes.
        """
        ccsds_hdr_length = 6+(sec_enable*9)+len(ancillary)       
        packet = [0]*(ccsds_hdr_length+len(trans_bytes))
        length = len(trans_bytes) + (ccsds_hdr_length-6) - 1 # transaction length + Header - primary(6) - 1 for thie field
        
        # Packet Type field (All commands are type = 1, Requests are type = 0)
        if (trans_bytes[0] >= 0x80):
            type_field = 0x00 # 0
        else:
            type_field = 0x10 # 1
        
        # Populate Primary Header (6 bytes)
        packet[0] = type_field + (sec_enable << 3) + ((apid >> 8) & 0x07) # "000?1xxx" (Version = "000", Type = "?", SecFlag = "?", Upper 3-bit APID = xxx)
        packet[1] = (apid >> 0) & 0xFF # Lower 8-bit APID
        packet[2:4] = [0xC0,0x01] # "1100000000000001" (Flag = "11", Seqeunce = "00000000000001")
        packet[4] = (length >> 8) & 0xFF
        packet[5] = (length >> 0) & 0xFF
        
        # Polutate Secondary Header - Time Code field and Anvillary bytes are not used, so all zeros (9 bytes + ), already filled.
        
        # Populate (optional) Ancillary Bytes
        if ancillary:
            packet[(ccsds_hdr_length-len(ancillary)):ccsds_hdr_length] = ancillary
        
        # Populate the Data Field        
        packet[ccsds_hdr_length:] = trans_bytes
        
        return packet        
        
    def _RemoveCcsdsHeader(self, data, sec_enable, apid, ancillary=[]):
        """
        Strip the CCSDS header(s) and return the remaining data (excluding the request ID)
        """
        ccsds_hdr_length = 6+(sec_enable*9)+(sec_enable*len(ancillary))

        # Check Length Field
        if (len(data) < (ccsds_hdr_length+1)):
            print(f'Data Received is too short!')

        # Check CCSDS Primary Header APID
        packet_apid = (data[0] << 8) | data[1];
        if ( (packet_apid & 0x07FF)  != (apid & 0x07FF) ): # Check lower 11-bits only
            print(f'CCSDS Primary Header APID is incorrect! Received {(packet_apid & 0x07FF):#06x} but expected {(apid & 0x07FF):#06x}.')

        # Check CCSDS Length Field
        remaining_length = ((data[4] << 8) | data[5]) + 1;  
        if remaining_length != (len(data)-6):        
            print(f"CCSDS Primary Header Length Filed is incorrect! Field value indicates {remaining_length} but data length is {(len(data)-6)}")
            
        # Check CCSDS Secondary Time Code Bytes (all zero)
        if sec_enable:
            time_code_error = False            
            for i in range(9):
                if data[6+i] != 0:
                    time_code_error = True
            if time_code_error:
                print(f'CCSDS Secondary Header (Time Code) Bytes are incorrect! Received {data[6:15]} but expected {[0,0,0,0,0,0,0,0,0]}.')
                
        # Check CCSDS Secondary Header Ancillary Bytes
        if ( sec_enable and (len(ancillary)>0) ):
            ancillary_error = False
            for i in range(len(ancillary)):
                if data[15+i] != ancillary[i]:
                    ancillary_error = True
            if ancillary_error:
                print(f'CCSDS Secondary Header (Ancillary Bytes) are incorrect! Received {data[15:15+len(ancillary)]} but expected {ancillary}.')                    
        
        return data[(ccsds_hdr_length+1):]   # The first byte (Request ID) is also removed
        
    def _AddUartHeader(self, data, ccsds_enable):
        """
        Adds a UART Stream Header to a packet
        """
        header = [0]*(4+(not(ccsds_enable))*2) # 4 sync bytes + 2 length bytes (if there is not CCSDS)   
        data_len = len(data)
        header[0:4] = [0x35,0x2E,0xF8,0x53] # Sync    
        
        # Add length bytes, Little Endian (Length of remaining data)
        if not(ccsds_enable):            
            header[4] = (data_len >> 0) & 0xFF
            header[5] = (data_len >> 8) & 0xFF    
            
        header.extend(data)            
        return header    

    def _RemoveUartHeader(self, data, ccsds_enable):        
        
        # Check Sync Bytes
        if (data[0:4] != [0x35,0x2E,0xF8,0x53]):
            print(f'RS-4xx Header Sync bytes not found!')
            
        # Check Length field (non-CCSDS header)
        if not ccsds_enable:
            remaining_length = ((data[4]) | (data[5]) << 8) 
            if remaining_length != (len(data)-6):    
                print(f'RS-4xx Header Length is incorrect! Field value inidicates {remaining_length} but expected length of {(len(data)-6)}')
        
        if ccsds_enable:
            return data[4:]           
        else:
            return data[6:]
        
    '''
    Methods to Add the standard protocols to the xScape Control Interface Writes and Reads (CtrlIfWrite and CtrlIfRead)
     - AddProtocol      - This adds the protocol headers, using transaction bytes as input. Typically used when writing.
     - RemoveProtocol   - This removes the protocol headers, returning the original transaction bytes. Typically used with reading.
     - ReadOverhead     - Returns the number of overhead bytes that are added by the protocol for a read.
    '''

    def _AddProtocol(self, data):
        """
        Add Protocol Headers for SpaceWire or RS422 Interfaces
        """
        # Add CCSDS Header(s)
        if self.ccsds_enable:        
            msg_data = self._AddCcsdsHeader(data, sec_enable = self.ccsds_sec_enable, apid = self.ccsds_apid, ancillary = self.ccsds_ancillary)
        else:
            msg_data = data
        
        # Add RS422 Header
        if self.control_interface == CONTROL_INTERFACE_RS4xx:
            msg_data = self._AddUartHeader(msg_data, self.ccsds_enable)
        
        return msg_data
        
    def _RemoveProtocol(self, data):
    
        # Remove RS422 Header
        if self.control_interface == CONTROL_INTERFACE_RS4xx:
            msg_data = self._RemoveUartHeader(data, self.ccsds_enable)
        else:
            msg_data = data
            
        #print(f'{data:02x'))    
        #print([f'{b:02x}' for b in data])
            
        # Remove CCSDS Header(s)    
        if self.ccsds_enable:
            trans_bytes = self._RemoveCcsdsHeader(msg_data, sec_enable = self.ccsds_sec_enable, apid = self.ccsds_apid, ancillary = self.ccsds_ancillary)
        else:
            # Remove request ID Only
            trans_bytes = msg_data[1:]
        return trans_bytes;
        
    def _ReadOverhead(self):
        """
        Returns the overhead in bytes, which is the header(s) as well as the extra request ID byte.
        """
        
        overhead = (self.ccsds_enable*6) + (self.ccsds_sec_enable*9) + + (self.ccsds_sec_enable*len(self.ccsds_ancillary)) + 1
        if self.control_interface == CONTROL_INTERFACE_RS4xx:
            overhead += 4 # Extra 4 Sync Bytes
            if not(self.ccsds_enable):
                overhead += 2 # Extra 2 length bytes
                
        #print(f'Read Overhead = {overhead}')   
        
        return overhead

    # Perform a Control Interface Write, used for Commands
    def _CtrlIfWrite(self, data):        
        if not isinstance(data, list) and not isinstance(data, numpy.ndarray): data = [ data ]        
        # Select an Interface
        with self._threadLock:
            if self.control_interface == CONTROL_INTERFACE_I2C:           
                return self.EGSE.I2cWr(self.i2c_address, data)
            elif self.control_interface == CONTROL_INTERFACE_SPI:
                if not isinstance(data, list) and not isinstance(data, numpy.ndarray): data = [ data ]
                dataWr = [0]*(len(data) + 3)
                dataWr[0] = data[0]     # Command byte       
                dataWr[1] = 0           # Turn around byte (dummy)
                dataWr[2] = 0           # Turn around byte (dummy)
                dataWr[3] = 0           # Turn around byte (dummy)        
                dataWr[4:] = data[1:]   # Parameter bytes
                ret = self.EGSE.SpiTrans(dataWr)
                # Check for first 4 SPI bytes on MISO
                if ret[0:4] != [0x53, 0x53, 0x53, 0x53]:
                    raise exceptions.ControlInterfaceError(f'Invalid SPI data received. Expecting bytes [83, 83 ,83 ,83] but received {ret[0:4]}.')
            elif self.control_interface == CONTROL_INTERFACE_SpW:
                # Add Packet Protocol                
                data = self._AddProtocol(data)
                # Add Routig Bytes and Imager Logcial Addr
                self.EGSE.SpWWr(self.SpwRoutingBytes + [self.SpwDestinationAddr] + data)       
                # Debug
                if (self.debug):
                    print(f'CMD via SPW: Wrote {len(data)} bytes.')
                    print(data)
            elif self.control_interface == CONTROL_INTERFACE_CAN:
                raise exceptions.ControlInterfaceError(f'CAN control interface not implemented')
            elif self.control_interface == CONTROL_INTERFACE_RS4xx:                                                 
                # Add Packet Protocol                
                data = self._AddProtocol(data)                
                self.uart.Write(data)       
                if (self.debug):
                    print(f'CMD via UART: Wrote {len(data)} bytes.')
                    print('  Dec. Bytes: [{}]'.format(",".join("{:4}".format(x) for x in data)))
                    print('  Hex. Bytes: [{}]'.format(",".join("0x{:02X}".format(x) for x in data)))
            else:
                raise exceptions.ControlInterfaceError(f'Control Interface is not specified. Cannot send command.')

    # Perform a Control Interface Write/Read (Combination), used for Requests
    def _CtrlIfRead(self, data, rd_length):
        if not isinstance(data, list) and not isinstance(data, numpy.ndarray): data = [ data ]        
        # Select an Interface    
        with self._threadLock:
            if self.control_interface == CONTROL_INTERFACE_I2C:
                return self.EGSE.I2cCombo(self.i2c_address, data, rd_length)
            elif self.control_interface == CONTROL_INTERFACE_SPI:                
                dataWr = [0]*(len(data) + 3 + rd_length)
                dataWr[0] = data[0]     # Transaction ID byte       
                dataWr[1] = 0           # Turn around byte 1
                dataWr[2] = 0           # Turn around byte 2
                dataWr[3] = 0           # Turn around byte 3
                dataWr[4:] = data[1:]   # Parameter bytes  (not normally used)
                dataWr[(4+len(data)):] = [0]*rd_length # Add dummy bytes for read length               
                ret = self.EGSE.SpiTrans(dataWr)
                # Check for first 4 SPI bytes on MISO
                if ret[0:4] != [0x53, 0x53, 0x53, 0x53]:
                    raise exceptions.ControlInterfaceError(f'Invalid SPI data received. Expecting bytes [83, 83 ,83 ,83] but received {ret[0:4]}.')
                return ret[4:] # Skip the first 4 bytes (transaction ID and 3 turn around bytes)
            elif self.control_interface == CONTROL_INTERFACE_SpW:
                # Add Packet Protocol                
                data = self._AddProtocol(data)
                rd_length = rd_length + self._ReadOverhead()
                # Write Request Transfer to SpaceWire (add Routig Bytes and Imager Logcial Addr)
                self.EGSE.SpWWr(self.SpwRoutingBytes + [self.SpwDestinationAddr] + data)   
                # Debug
                if (self.debug):
                    print(f'REQ via SPW: Wrote {len(data)} bytes.')
                    print(data)
                # Read Request Response Tranfer from SpaceWire, returning a list of bytes                
                ret, error = self.EGSE.SpWRd()     
                # Debug
                if (self.debug):
                    print(f'RSP via SPW: Read {len(ret)} bytes.')
                    print(ret)                               
                if error == True:
                    raise exceptions.ControlInterfaceError(f'Control Interface error. Rx spacewire packet error.')
                # Remove Packet Protocol
                trans_bytes = self._RemoveProtocol(ret)                
                return trans_bytes
            elif self.control_interface == CONTROL_INTERFACE_CAN:
                raise exceptions.Error(f'CAN control interface not implemented')
            elif self.control_interface == CONTROL_INTERFACE_RS4xx:
                # Add Packet Protocol                
                data = self._AddProtocol(data)
                rd_length = rd_length + self._ReadOverhead() 
                # Write Request Transfer to UART
                self.uart.Write(data)
                # Debug
                if (self.debug):
                    print(f'REQ via UART: Wrote {len(data)} bytes.')                    
                    print('  Dec. Bytes: [{}]'.format(",".join("{:4}".format(x) for x in data)))
                    print('  Hex. Bytes: [{}]'.format(",".join("0x{:02X}".format(x) for x in data)))                    
                # Read Request Response Tranfer from UART, returning a list of bytes
                ret = self.uart.Read(rd_length)     
                # Debug
                if (self.debug):
                    print(f'RSP via UART: Read {len(ret)} bytes.')
                    print('  Dec. Bytes: [{}]'.format(",".join("{:4}".format(x) for x in ret)))
                    print('  Hex. Bytes: [{}]'.format(",".join("0x{:02X}".format(x) for x in ret)))
                # Remove Packet Protocol
                trans_bytes = self._RemoveProtocol(ret)
                return trans_bytes
            else:
                raise exceptions.Error(f'Control Interface is not specified. Cannot send command.')      



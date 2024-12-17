'''
Simera Sense EGSE module
Copyright (c) 2019-2020 Simera Sense (info@simerasense.com).
Released under the GNU GPLv3.0 License.
'''

import usb1
import numpy
import struct
import time

# Get _tread.allocate_lock() to make class thread-safe. Import _thread instead of threading to reduce startup cost
try:
    from _thread import allocate_lock as Lock
except ImportError: # should never happen - threading always included in Python 3.7+
    from _dummy_thread import allocate_lock as Lock


from . import exceptions



# 'public' module constants
HsdiMode_Rst = 0
HsdiMode_Tx  = 1
HsdiMode_Rx  = 2
GpioMode_In  = 0
GpioMode_Out = 1
IoConfig_Lvds = 1
IoConfig_Gpio = 0

DATA_INTERFACE_HSDIF = 0x01 #this numbering follows that used in SPI registers on waxwing.
DATA_INTERFACE_USART = 0x02
DATA_INTERFACE_SPW =  0x04
DATA_INTERFACE_SPW_REDUN =  0x05
DATA_INTERFACE_TPGEN = 0x08#Testpattern generator.
DICTIONARY_DATA_INTERFACE = {DATA_INTERFACE_HSDIF:'DATA_INTERFACE_HSDIF', DATA_INTERFACE_USART:'DATA_INTERFACE_USART', DATA_INTERFACE_SPW:'DATA_INTERFACE_SPW', DATA_INTERFACE_TPGEN: 'DATA_INTERFACE_TPGEN', DATA_INTERFACE_SPW_REDUN:'DATA_INTERFACE_SPW_REDUN'}#TODO: update

HS_MODE_RX = 0x01
HS_MODE_TX = 0x02#Not yet supported
DICTIONARY_HS_MODE = {HS_MODE_RX:'HS_MODE_RX', HS_MODE_TX:'HS_MODE_TX' }

USART_MAX_CLK_SPEED = 8 #In Mega Hertz @Niki, which are all reasonable frequencies?

SPW_DATA_MODE = 0x01 
SPW_TMTC_MODE = 0x02 
DICTIONARY_SPW_MODE = {SPW_DATA_MODE : 'SPW_DATA_MODE' , SPW_TMTC_MODE : 'SPW_TMTC_MODE'}

I2C_PORT_CE   = 0x00
I2C_PORT_ENV  = 0x01

# GPIOs used for PPS

PpsConfig = [{'Option':['PPS_LVCMOS_1', 'PPS_LVCMOS_ENC'],                 'EgseGpio':20},
             {'Option':['PPS_LVCMOS_2', 'PPS_LVCMOS_3'],                   'EgseGpio':19},                 
             {'Option':['PPS_LVDS_1','PPS_LVDS_2','PPS_LVDS_ENC'],         'EgseGpio': 0}
            ]

# 'private' module constants class
class _const():
    USB_VENDOR_ID  = 0x16D0
    USB_PRODUCT_ID = 0x0F49

    # USB bus type. Can be '2.0' or the default '3.0'
    usb_version    = 3.0

    usb_controlwrite_timeout_ms = 300
    usb_controlread_timeout_ms  = 900
    usb_bulkwrite_timeout_ms    = 700
    usb_bulkread_timeout_ms     = 2000
    usb_bulkread_timeout_overhead_ms = 750#Every bulk read will have at least this as a timout.
    usb_bulkread_timeout_ratio       = 1.5#1.5x calculated timeout is observed.


    supported_i2c_speeds = [100, 400, 1000, 10]
    supported_i2c_ports  = [I2C_PORT_CE, I2C_PORT_ENV]

    #Case statements on FX3
    version_request =         0xBF
    write_request =           0xC6
    read_setup_request =      0xC7
    read_request =            0xC8
    read_status_EGSE =        0xC9
    read_spi_reg_simple =     0xCA
    write_spi_reg_simple=     0xCB
    read_ww_flash_ID=         0xCC
    read_page_ww_flash=       0xCD
    erase_spi_flash_ww=       0xCE
    program_spi_flash_ww=     0xCF
    read_debug_registers_fx3= 0xD0
    debug_functionality=      0xD1
    toggle_led_via_gpio=      0xD2
    fpga_reg_rd=              0xD3
    fpga_reg_wr=              0xD4
    fpga_reboot=              0xD5
    reset_hsd_buffers=        0xD6
    eeprom_random_addr_read=  0xD7
    eeprom_sequential_random_read = 0xD8
    eeprom_random_write_byte= 0xD9
    eeprom_random_write_page= 0xDA
    misc_debugging=           0xDB
    reg_rd_wr_speed_test=     0xDC
    i2c_wr_trans=             0xDD
    i2c_combo_trans=          0xDE

    # Registers on the FPGA (WaxWing)
    reg_addr_global_control=  0x01
    reg_addr_core_selector=   0x02
    reg_addr_core_version=    0x03
    reg_addr_dbg_mux=         0x04
    reg_addr_dbg_reg=         0x05
    reg_build_info=           0x06
    reg_addr_scratchpad=      0x07
    reg_addr_version_0=       0x08#Kept for backwards compatibility
    reg_addr_version_1=       0x09#Kept for backwards compatibility
    reg_version_mux_sel=      0x08
    reg_version_mux=          0x09
    reg_scratch_serial=       0x0A#Is a constant for rev3 PCB
    

    #I2C Enviro Master
    reg_addr_i2c_env_config         =    0x0B
    reg_addr_i2c_env_control        =    0x0C
    reg_addr_i2c_env_status         =    0x0D 
    reg_addr_i2c_env_length_wr_lo   =    0x0E
    reg_addr_i2c_env_data           =    0x0F
    
    #for backwards compatibility - this is unfortunately left here.
    reg_addr_hsd_mode =       0x10 #These are read and writable.
    
    #I2C Enviro Master (contd)
    reg_addr_i2c_env_length_rd_lo  =     0x11
    reg_addr_i2c_env_length_wr_hi  =     0x12
    reg_addr_i2c_env_length_rd_hi  =     0x13
    
    reg_hsd_resid_data_0 =    0x14
    reg_hsd_resid_data_1 =    0x15
    
    # SpW registers
    reg_spw_ctrl =                  0x16
    reg_spw_stat =                  0x17
    reg_spw_tx_div_cnt =            0x18
    reg_spw_count_tout =            0x19
    
    reg_spw_data_la =               0x1A
    reg_spw_data_status =           0x1B
    reg_spw_data_ctrl =             0x1C

    reg_spw_tmtc_ctrl =             0x1E
    reg_spw_tc_len_lo =             0x1F
    reg_spw_tc_len_hi =             0x20
    reg_spw_tmtc_fifo =             0x21
    reg_spw_tc_status =             0x22
    reg_spw_tm_status =             0x23    
    reg_spw_rd_la =                 0x24
    reg_spw_rd_len_lo =             0x25
    reg_spw_rd_len_hi =             0x26

    # One Wire Enviro
    reg_addr_ow_ctrl =              0x27
    reg_addr_ow_sensor_id =         0x28
    reg_addr_ow_sensor_id_mux =     0x29
    reg_addr_ow_status =            0x2A
    reg_addr_ow_data_lsb =          0x2B
    reg_addr_ow_data_msb =          0x2C

    # High-Speed Data Interface
    reg_hsd_if_rst =                0x2D
    #reg_fif_rst =                   0x2E #not implemented...
    reg_hsd_if_status =             0x2F
    reg_gpif_conf =                 0x30
    reg_sync_byte =                 0x31
    reg_gpif_status =               0x32

    #Usart
    reg_usart_ctrl =                0x33
    reg_usart_sigs =                0x34
    reg_usart_status =              0x35
    reg_usart_wait_ass =            0x36
    reg_usart_wait_post_ass =       0x37
    reg_hs_mux =                    0x38
    reg_hs_mode =                   0x39

    #SERDES 
    reg_serdes_ctrl=                0x3E
    reg_serdes_status=              0x3F

    # I2C Master
    reg_addr_i2c_config =       0x40
    reg_addr_i2c_control =      0x41
    reg_addr_i2c_status =       0x42
    reg_addr_i2c_length_wr_lo = 0x43
    reg_addr_i2c_data =         0x44
    reg_addr_i2c_length_rd_lo = 0x45
    reg_addr_i2c_length_wr_hi = 0x46
    reg_addr_i2c_length_rd_hi = 0x47
    # SPI Master
    reg_addr_spi_config =       0x48
    reg_addr_spi_control =      0x49
    reg_addr_spi_status =       0x4A
    reg_addr_spi_length_lo =    0x4B
    reg_addr_spi_data =         0x4C
    reg_addr_spi_length_hi =    0x4D
    
    reg_pin_config_a =          0x4E
    reg_pin_config_b =          0x4F
    
    # GPIO registers
    reg_gpio_direction_0 =      0x50
    reg_gpio_direction_1 =      0x51
    reg_gpio_direction_2 =      0x52
    reg_gpio_data_out_0 =       0x53
    reg_gpio_data_out_1 =       0x54
    reg_gpio_data_out_2 =       0x55
    reg_gpio_data_in_0 =        0x56
    reg_gpio_data_in_1 =        0x57
    reg_gpio_data_in_2 =        0x58
    reg_gpio_config_0 =         0x59
    reg_gpio_config_1 =         0x5A
    reg_gpio_config_2 =         0x5B
    reg_gpio_pulse_clks_0 =     0x5C
    reg_gpio_pulse_clks_1 =     0x5D
    reg_gpio_pulse_clks_2 =     0x5E
    reg_gpio_pulse_clks_3 =     0x5F
    reg_gpio_pulse_pin =        0x60
    reg_gpio_pulse_trigger =    0x61
    # User LEDs
    reg_led_override =          0x63
    reg_usr_led =               0x64
    reg_addr_i2c_pull_up =      0x65
    # Power switch
    reg_measured_current_lsb =  0x66#TODO: update
    reg_measured_current_msb =  0x67#TODO: update, 0x67 and 0x67 repeat...
    reg_upper_msb =             0x66
    reg_upper_lsb =             0x67
    reg_lower_msb =             0x68
    reg_lower_lsb =             0x69
    
    reg_addr_ow_pwr =           0x6A

    reg_pwr_switch_status =     0x6C
    reg_pwr_switch_cmd    =     0x6D
    reg_chan_measure      =     0x6E
    reg_avg_current_lsb =       0x6F
    reg_avg_current_msb =       0x70
    reg_raw_val_vin_msb =       0x71
    reg_raw_val_vin_lsb =       0x72
    reg_avg_mux_lsb =           0x73
    reg_avg_mux_msb =           0x74
    reg_raw_val_vout_msb =      0x75
    reg_raw_val_vout_lsb =      0x76
    reg_serdes_dbg=             0x77

    #LED Brightness
    reg_usr_led_1_brtns =       0x78
    reg_usr_led_2_brtns =       0x79
    reg_status_led_brtns =      0x7A
    reg_data_led_brightness =   0x7B
    reg_ctrl_led_brightness =   0x7C
    
    #Spw info 
    reg_spw_enum_0 =            0x7D
    reg_spw_enum_1 =            0x7E
    reg_spw_enum_2 =            0x7F


    # USB Endpoints
    hsd_rd_endpoint=          0x81 #The endpoint from which we read the data (FPGA -> FX3 -> PC)

    #Status Codes
    EGSE_status_code = {
            0x00:'INITIAL_STATE',
            0x01:'WW_BUSY_RD_WR',
            0x02:'SUCCESSFUL_READ',
            0x03:'SUCCESSFUL_WRITE',
            0x04:'START_READ',
            0x05:'START_WRITE',
            0x06:'READ_TIMEOUT',
            0x07:'WRITE_TIMEOUT',
            0x08:'FLASH_ERASE_ERROR_WRITE_PROTECT',
            0x09:'FLASH_ERASE_ERROR',
            0x0A:'FLASH_ERASE_SUCCESS',
            0x0B:'FLASH_PROGRAM_SUCCESS',
            0x0C:'FLASH_PROGRAM_ERROR',
            0x0D:'FLASH_PROGRAM_WRITE_PROTECT_ERROR',
            0xF2:'TESTING'
    }
    
    #Firmware register blocks mux-values for version-readout. This macthes with EgseFx3_pkg.vhd 
    Fw_ver_offset_ctrl = 0
    Fw_ver_offset_hs   = 32
    Fw_ver_offset_p4   = 64
    Fw_ver_offset_j4   = 96
    Fw_ver_offset_j1   = 128
    Fw_ver_offset_misc = 160
    
    Fw_ver_reg_mux_val = {
            0 + Fw_ver_offset_ctrl : 'I2C',
            1 + Fw_ver_offset_ctrl : 'SPI',
            2 + Fw_ver_offset_ctrl : 'SpW',
            3 + Fw_ver_offset_ctrl : 'GPIO',
            
            0 + Fw_ver_offset_hs : 'LVDS Simera',
            1 + Fw_ver_offset_hs : 'LVDS USART',
            2 + Fw_ver_offset_hs : 'SpW',
            
            0 + Fw_ver_offset_p4 : 'One Wire',
            1 + Fw_ver_offset_p4 : 'I2C',
            2 + Fw_ver_offset_p4 : 'GPIO',
            
            0 + Fw_ver_offset_misc : 'SPI Slave regs',
            1 + Fw_ver_offset_misc : 'EgseFx3.vhd',
            2 + Fw_ver_offset_misc : 'Power Switch',
            3 + Fw_ver_offset_misc : 'ADC',
            4 + Fw_ver_offset_misc : 'Moving Avg',
            5 + Fw_ver_offset_misc : 'GPIF',
            6 + Fw_ver_offset_misc : 'LED Flash',
            7 + Fw_ver_offset_misc : 'LED PWM',
            8 + Fw_ver_offset_misc : 'Sys Clocks'
    }


#Number of bytes data within control transfer is allowed to be
if _const.usb_version == 3.0:
    _const.control_transfer_size = 512
elif _const.usb_version == 2.0:
    _const.control_transfer_size = 64


class EGSE:
    '''
    Simera Sense EGSE class

    Set the 'debug' instance variable to True to enable debug output
    '''

    def __init__ (self, SerialNumber = None):
        """
        SerialNumber (string) must be specified to bind to a specific EGSE connected to the computer
            Otherwise the firt available EGSE device is used
        """

        # Set a debug interface type (used to identify this interface as an EGSE)
        self.debug_interface_type = 'EGSE'

        # instance global var set True to enable debug output prints
        self.debug = False

        # USB transaction timeouts in milliseconds
        self.usb_controlwrite_timeout_ms        = _const.usb_controlwrite_timeout_ms
        self.usb_controlread_timeout_ms         = _const.usb_controlread_timeout_ms
        self.usb_bulkwrite_timeout_ms           = _const.usb_bulkwrite_timeout_ms
        self.usb_bulkread_timeout_ms            = _const.usb_bulkread_timeout_ms
        self.usb_bulkread_timeout_overhead_ms   = _const.usb_bulkread_timeout_overhead_ms
        self.usb_bulkread_timeout_ratio         = _const.usb_bulkread_timeout_ratio#Given the calculated timeout, what is the amount of grace given (e.g. 1.5 is 150% time)
        
        #These are here to easily determine what the module constant is, it doesn't get changed.
        self._i2c_port_ce  = I2C_PORT_CE
        self._i2c_port_env = I2C_PORT_ENV
        

        # true if command interface is configured and ready for use
        self.command_if_i2c_configured = False
        self.command_if_spi_configured = False

        self.i2c_transaction_timeout_s = 0.250 #timeout in seconds
        self.i2c_env_transaction_timeout_s = 0.250 #timeout in seconds for environmental I2C port
        
        #Dict which holds config of IO's
        self.gpio_config_dict = {}

        #Dictionary which ensures we only set the channel 1x.
        self.AdcCurrMeasChannel = []

        #EGSE Default start up with this type of HS link.
        self.HsDataIfType = DATA_INTERFACE_HSDIF
        self.HsMode = HS_MODE_RX #Default and only possible mode.
        self. HsDataLaneRate = 100 # default
        self.UsartClkFrq = 4#Default 4 MHz
        self.HsDebug = False#Set this to True to get some debug info (high level).
        
        #SpW admin 
        self.SpWMode = SPW_DATA_MODE#Default more (DATA and not TMTC)
        self.SpWDebug = False#Set this to True for high-level debug.
        self.SpWTcSendTimeout_s  = 0.25#time in seconds.
        self.SpWBitRate = 100#Default 100mbps, this is what the EGSE is setup to transmit and recieve at.
        self.SpWLaRd = None
        self.SpWLaData = None
        self.SpWTxMbaud = 0
        self.SpwDataOnly = False


        if SerialNumber is None:
            self.SerialNumber = None
        else:
            try:
                self.SerialNumber = str(SerialNumber)
            except Exception:
                raise exceptions.InputError('EGSE SerialNumber must be a string')

        self._threadLock = Lock()


        USBcontext = usb1.USBContext()
        if self.SerialNumber is None:
            # use the first available EGSE device
            handle = USBcontext.getByVendorIDAndProductID(
                    _const.USB_VENDOR_ID, _const.USB_PRODUCT_ID,
                    skip_on_error=True,skip_on_access_error=True)
        else:
            # use the specific EGSE device, specified by SerialNumber
            handle = None
            for device in USBcontext.getDeviceIterator(skip_on_error=True):
                try:
                    if device.getVendorID() == _const.USB_VENDOR_ID and \
                            device.getProductID() == _const.USB_PRODUCT_ID and \
                            device.getSerialNumber() == self.SerialNumber :
                        handle = device
                        break
                except:
                    """
                    USBcontext.getDeviceIterator iterates through EGSE serial numbers in ascending order.
                    If a device is open, the loop continues to the next device until the specified serial number is found.
                    """
                    pass
                    

        if not handle or handle is None:
            # The EGSE was not found on the USB bus
            if self.SerialNumber is None:
                raise exceptions.EgseNotFoundError()
            else:
                raise exceptions.EgseNotFoundError(f'EGSE with Serial Number {self.SerialNumber} was not found')

        try:
            DevHandle = handle.open()
        except Exception as e:
            raise exceptions.UsbOpenError(f'{e}')

        self.Dev_Handle = DevHandle
        self.Dev_Handle.claimInterface(0) #Claim device
        
        
		#Determine the speed that is negotiated between the device and host. Must be connected to USB3
		#4 -> USB3, 3 -> USB2, 2 -> USB1
        if handle.getDeviceSpeed() < 4:
            raise exceptions.USBError(f'EGSE is not plugged into a USB3 capable port. Also ensure that it is not connected via a USB hub, as this may also cause this error.')
        
        #Determine whether version 2 or 3 HW revision.
        self.HwRevision = int(self.getHwVersion())
        
        
        
        if self.HwRevision == 2:
            #Dictionary which ensures we only set the channel 1x.
            self.AdcCurrMeasChannel = []
            self.SpWMaxBitRate = 100
        
        else:
            #Value to indicate which channel is currently set. Set to 12, out of the actual range.
            self.AdcMeasChannel = 12
            self.SpWMaxBitRate = 200
        
        # The EGSE needs to be able to support various PPS selections.
        self.PpsPrimary   = None 
        self.PpsSecondary = None 
        self.PpsSel       = 'pri'
        
        # Call the setup methods for the HS Link
        self.setDataInterface(self.HsDataIfType)
        self.setHsMode(self.HsMode)
        
        if self.HwRevision == 2:
            #Grab various calibrated values for EGSE.
            self.CurrCirGain = 0
            self.CurrCirVref = 0
                #Current sensing circuit
            res = self._GetCalCurr()
            self.CurrCirGain = res[0]
            self.CurrCirVref = res[1]
        else:
            #Determine whether current has been calibrated.
            if self._IsCurrCal():
                #Grab current calibration 
                res = self._GetCurrCalCoeff()
                self.CurrCalCoeff_A = res[0]
                self.CurrCalCoeff_B = res[1]
                self.CurrCalCoeff_C = res[2]
                self._CurrCalibrated = True
            else:
                print(f'***Warning: current measurements are uncalibrated**')
                self._CurrCalibrated = False
            
            #Determine whether Vin has been calibrated.
            if self._IsVinCal():
                #Grab Vin calibration 
                res = self._GetVinCalCoeff()
                self.VinCalCoeff_A = res[0]
                self.VinCalCoeff_B = res[1]
                self.VinCalCoeff_C = res[2]
                self.VinFit =        res[3]
                self.GetAndSetPwrOutLimits()#Read default calibrated limits from EEPROM, and set in register.
                self._VinCalibrated = True
            else:
                print(f'***Warning: Vin measurements are uncalibrated. Power provided to Imager may damage the if correct voltage not provided.**')
                self._VinCalibrated = False
            
            
            #Determine whether Vout is calibrated.
            if self._IsVoutCal():
                #Grab Vout C-value 
                #Vout C-value
                VoutCLsb = self._EepromFx3RdBt(addr = 0x3FF7B)
                VoutCMsb = self._EepromFx3RdBt(addr = 0x3FF7C)
                raw_cal = ((VoutCMsb << 8) | VoutCLsb) 
                
                #16bit 2'x compliment, accomodate sign
                if raw_cal > 0x8000:
                    raw_cal = raw_cal - 0x10000
                ValDiv = raw_cal / 1000.0
                
                self.VoutCalCoeff_C = ValDiv
                self._VoutCalibrated = True
            else:
                print(f'***Warning: Vout measurements are uncalibrated.**')
                self._VoutCalibrated = False
            
            # By default set to 
            self.SetSpiGpioPinConfig(conf = 'gpio')
        
        # Remapping of method definitions.
        if self.HwRevision == 3:
            self.PwrOut    = self.PwrOut_v3
            self.PwrOutRst = self.PwrOutRst_v3
            self.CurrMeas  = self.CurrMeas_v3

    def __del__(self):
        # clean-up
        with self._threadLock:
            try:    del self.Dev_Handle
            except Exception: pass

    def CloseLink(self):
        if not self.Dev_Handle is None:
            with self._threadLock:
                self.Dev_Handle.releaseInterface(0)
                self.Dev_Handle.close()

    ##########_________________Versioning and Status_________________##########
    def getVersion(self, verbose = True):
        """Provide the version of the EGSE software and EGSE firmware.
            Returns:
                - ver (int) [major, minor] for each of EGSE software, and EGSE firmware
        """
        verinfo = {}
        verinfo['Software'] = self.getSwVersion()
        verinfo['Firmware'] = self.getFwVersion()
        if verbose:
            self.printCoreVersions(1)
        return verinfo

    def getFwVersion(self):
        """Determine the version of FW which the FPGA has on it.
        """
        if self.HwRevision == 2:
            try:
                retval = [self.FpgaRegRd(reg = _const.reg_addr_version_0), self.FpgaRegRd(reg = _const.reg_addr_version_1)]
            except Exception as e:
                raise exceptions.Error(f'Error reading EGSE version information.\n{e}')
        else:
            # Major version 
            self.FpgaRegWr(_const.reg_version_mux_sel, 5)
            val_lsb = self.FpgaRegRd(_const.reg_version_mux)
            maj = val_lsb
            
            # Minor version 
            self.FpgaRegWr(_const.reg_version_mux_sel, 6)
            val_lsb = self.FpgaRegRd(_const.reg_version_mux)
            min = val_lsb
            retval = [maj, min]
        return retval

    def getHwVersion(self):
        """
        Return the PCB revision number, aka HW version number.
        """
        val = self.FpgaRegRd(_const.reg_scratch_serial)
        if val == 0xD4:
            #Unique magic number which indicates this is not HW revision 2 or earlier. Can therefore read the following registers.
            self.FpgaRegWr(_const.reg_version_mux_sel, 1)
            val_msb = self.FpgaRegRd(_const.reg_version_mux)
            self.FpgaRegWr(_const.reg_version_mux_sel, 2)
            val_lsb = self.FpgaRegRd(_const.reg_version_mux)
            hw_ver = (val_msb<<8) + val_lsb            
            
            #Confirm that the EEPROM in FX3 confirms this.
            hw_ver_eeprom = self.GetHwRevisionEeprom()
            if hw_ver_eeprom != hw_ver:
                print(f'Reported PCB version {hw_ver_eeprom} does not line up with what the FW expects {hw_ver}. \nNOTE: exception not raised such that this can be rectified.')
        else:
            hw_ver = 2
        return hw_ver

    def getSerdes(self):
        """
        Determine whether this EGSE uses special serdes block for LVDS
        """
        if self.HwRevision == 2:
            raise exceptions.Error(f'Not supported for this version of EGSE.\n{e}')
        else:
            # Serdes info
            self.FpgaRegWr(_const.reg_version_mux_sel, 7)
            val = self.FpgaRegRd(_const.reg_version_mux)
            
        return val


    def GetHwRevisionEeprom(self):
        """
        Read back the HW revision of the PCB which is stored in EEPROM.
        """
        #LSB
        val_lsb = self._EepromFx3RdBt(addr = 0x3FF79)
        #MSB
        val_msb = self._EepromFx3RdBt(addr = 0x3FF7A)
        return val_lsb + (val_msb << 8)

    def getBuildVariant(self):
        """
        Determine build variant
            returns
                var (int): build variant 
        """
        if self.HwRevision == 3:
            # Build variant 
            self.FpgaRegWr(_const.reg_version_mux_sel, 3)
            val_msb = self.FpgaRegRd(_const.reg_version_mux)
            self.FpgaRegWr(_const.reg_version_mux_sel, 4)
            val_lsb = self.FpgaRegRd(_const.reg_version_mux)
            var = (val_msb<<8) + val_lsb
        else:
            #TODO: could perform checks which use 1.6 1.7 to determine SPW or not.
            var = 0
        return var

    def getEgseInfo(self, verbose=True):
        """Determine the HW PCB version, build variant, major version, minor version of FW, Serial number.
        returns:
            hw (int): HW PCB version
            var (int): build variant 
            maj (int): major version 
            min (int): minor version
            sn (str) : 3-character serial number
        """
        
        hw  = self.getHwVersion()
        var = self.getBuildVariant()
        if self.HwRevision == 2:
            var = 'n/a'
            serdes = False
        else:
            serdes = self.getSerdes()
        maj, min = self.getFwVersion()
        
        sn = self.getSerialNumber()
        
        if verbose:
            print(f'The EGSE has the following components and properties')
            print(f'\tHW (PCB): \t{hw}')
            print(f'\tVariant: \t{var}')
            print(f'\tVersion: \t{maj}.{min}')
            print(f'\tSERDES: \t{bool(serdes)}')
            print(f'\tSN:   \t\t{sn}')
            
            
        
        return hw, var, maj, min, sn
        
    def getSwVersion(self):
        """Determine the version of SW which the FX3 has on it.
        """
        request_type = 0x40
        request = _const.version_request
        value = 0x0000
        index = 0x0000
        length = 0x0004 #number of bytes
        with self._threadLock:
            rx_data = self.Dev_Handle.controlRead(request_type = request_type, request = request, value= value, index=index, length=length, timeout = self.usb_controlread_timeout_ms )

        lst_data = list(rx_data)

        Maj_ver = (lst_data[0] << 8) + lst_data[1]#First two bytes
        Min_ver = (lst_data[2] << 8) + lst_data[3]#Last two bytes

        return [Maj_ver, Min_ver]
        
    def getSerialNumber(self):
        """Return serial number of the EGSE in string format, 
        this is stored in the code of the FX3 for HwRevision==2, 
        stored in EEPROM and loaded at bootup for HwRevision==3 
        """
        serialNumber = self.Dev_Handle.getSerialNumber()
        return serialNumber

    def printCoreVersions(self, verbose = 1):
        """Print the versions of the various cores, backwards compatible with previous EGSE's.
        verbose (int): 1: all CE interfaces, 2: also debug interfaces, 3: internal mod
        """
        
        #Cycle through all 256 registers. V0.0 indicates that core not being present.
        for i in range(256):
            #Grab version number 
                #set version mux
            try:
                self.FpgaRegWr(reg = _const.reg_addr_core_selector, data=i)
            except Exception as e:
                raise exceptions.Error(f'Error writing value to version mux.\n{e}')            
                #read version 
            try:
                ver = self.FpgaRegRd(reg = _const.reg_addr_core_version, length = 1)
            except Exception as e:
                raise exceptions.Error(f'Error reading version register.\n{e}')    
                #split major and minor versions
            ver_maj = (ver & 0xF0)>>4
            ver_min = ver & 0x0F
            #If core is present, map to the correct core name, under the correct subgroup.
            if ver_maj == 3 and ver_min == 4:#the test value 0x34 was stored in old EGSE at this register location.
                if i == 0:
                    print(f'Old incompatible EGSE, where FW version reporting was not yet supported')
                else:
                    pass
            else:
                if verbose >= 1 and i < _const.Fw_ver_offset_p4:
                    if i == _const.Fw_ver_offset_ctrl :
                        print(f'CE Ctrl interfaces ')
                    if i == _const.Fw_ver_offset_hs:
                        print(f'CE High-speed Data interfaces ')
                    if (ver_maj != 0):#the core actually exists.
                        print(f'    {_const.Fw_ver_reg_mux_val[i]:15s}: v{ver_maj}.{ver_min}')                                            
                elif verbose >= 2 and i < _const.Fw_ver_offset_misc:
                    if i == _const.Fw_ver_offset_p4:
                        print(f'P4 connector IF')
                    if i == _const.Fw_ver_offset_j4:
                        print(f'J4 connector IF')
                    if i == _const.Fw_ver_offset_j1:
                        print(f'J1 connector IF')                
                    if (ver_maj != 0):#the core actually exists.
                        print(f'    {_const.Fw_ver_reg_mux_val[i]:15s}: v{ver_maj}.{ver_min}')                                                                    
                elif verbose == 3:
                    if i == _const.Fw_ver_offset_misc:
                        print(f'Internal modules')                                    
                    if (ver_maj != 0):#the core actually exists.
                        print(f'    {_const.Fw_ver_reg_mux_val[i]:15s}: v{ver_maj}.{ver_min}')                                                                                            
                

    def getClientPinConfig(self):
        """
        Determine which ctrl and data is placed where. Since we have only few Ctrl and Data interfaces combinations,
        simply return a number.
        
        Arguments return:
            config : (int), 0: old EGSE without config reporting 
                            1: LVDS (DiffPairs 0-4) + SPI (DiffPairs 5-7)  aka intial builds
                            2: SpW  (DiffPairs 5-8) + SPI (DiffPairs 0-2)         
        """
        
        #Determine if SPI is present 
        self.FpgaRegWr(reg = _const.reg_addr_core_selector, data= _const.Fw_ver_offset_ctrl + 1)#SPI 
        verSpi = self.FpgaRegRd(reg = _const.reg_addr_core_version, length = 1)
        
        #Determine if SpW is present 
        self.FpgaRegWr(reg = _const.reg_addr_core_selector, data= _const.Fw_ver_offset_ctrl + 2)#SpW
        verSpW = self.FpgaRegRd(reg = _const.reg_addr_core_version, length = 1)        
        
        #Determine if LVDS is present 
        self.FpgaRegWr(reg = _const.reg_addr_core_selector, data= _const.Fw_ver_offset_hs + 0)#LVDS
        verLvds = self.FpgaRegRd(reg = _const.reg_addr_core_version, length = 1)                
        
        if   (verSpi & 0xFF != 0x00) and (verSpW & 0xFF == 0x00) and (verLvds & 0xFF != 0x00):
            config = 1
        elif (verSpi & 0xFF != 0x00) and (verSpW & 0xFF != 0x00):
            config = 2
        else:
            config = 0
        return config
    
    def SetSpiGpioPinConfig(self, conf = 'spi'):
        """
        The Rev3 EGSE either supports SPI over LVDS17 and LVDS8,
        OR single ended PPS over LVDS17_P, and old CE_On (aka mutually exclusive).
        
        conf (string): either 'spi', 'SPI' or 'Spi' for SPI. 
                       OR     'gpio', 'GPIO' or 'Gpio' for single ended PPS on LVDS17_p and CE_On at LVDS17_n
        """
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return         
        
        spi_str  = ['spi',  'SPI',  'Spi']
        gpio_str = ['gpio', 'GPIO', 'Gpio']
        
        if conf in spi_str:
            self.FpgaRegRdModWr(reg = _const.reg_pin_config_a, val = '0', pos = 0)
            self.FpgaRegRdModWr(reg = _const.reg_pin_config_a, val = '0', pos = 1)
        elif conf in gpio_str:
            self.FpgaRegRdModWr(reg = _const.reg_pin_config_a, val = '1', pos = 0)
            self.FpgaRegRdModWr(reg = _const.reg_pin_config_a, val = '1', pos = 1)
        else:
            raise exceptions.InputError('Incorrect conf, set to {conf}, however need to select one of following: {spi_str}, {gpio_str}')

    def GetSpiGpioPinConfig(self):
        """
        Determine the config, see SetSpiGpioPinConfig for info.
        The Rev3 EGSE either supports SPI over LVDS17 and LVDS8,
        OR single ended PPS over LVDS17_P, and old CE_On (aka mutually exclusive).
        
        return
            conf (string): 'spi' or 'gpio'
        """
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return         
        
        val = self.FpgaRegRd(reg = _const.reg_pin_config_a)
        
        if val & 0x03 == 0x03:
            ret = 'gpio'
        elif val & 0x03 == 0x00:
            ret = 'spi'
        else:
            raise exceptions.HardwareError('Incorrect config detected')
        
        return ret
        
    def Fx3Status(self):
        """
        Read data from the FX3's 'status_reg_EGSE'

        Arguments in:
            - none
        Arguments return
            - string and integer equivalent values, see dictionary _const.EGSE_status_code
        """
        request_type = 0x40
        request = _const.read_status_EGSE
        value = 0x0000
        index = 0x0000
        length = 0x0001 #number of bytes, 1x 8bit register
        with self._threadLock:
            status_EGSE = self.Dev_Handle.controlRead(request_type = request_type, request = request, value= value, index=index, length=length, timeout = self.usb_controlread_timeout_ms )
        t = struct.unpack( 'B', status_EGSE)
        t = t[0]
        if self.debug:
            print('EGSE status:', _const.EGSE_status_code[t], '\t value:',hex(t))
        return _const.EGSE_status_code[t],t

    def EgseReadStatus(self):
        """
        Read data from the FX3's 'status_reg_EGSE'

        Arguments in:
            - none
        Arguments return
            - string and integer equivalent values, see dictionary _const.EGSE_status_code
        """
        request_type = 0x40
        request = _const.read_status_EGSE
        value = 0x0000
        index = 0x0000
        length = 0x0001 #number of bytes, 1x 8bit register
        with self._threadLock:
            status_EGSE = self.Dev_Handle.controlRead(request_type = request_type, request = request, value= value, index=index, length=length, timeout = self.usb_controlread_timeout_ms )
        t = struct.unpack( 'B', status_EGSE)
        t = t[0]
        if self.debug:
            print(f'EGSE status: "{hex(t)}", "{_const.EGSE_status_code[t]}"')
        return _const.EGSE_status_code[t],t


    ##########_________________FPGA Register bit-banging_________________##########
    def FpgaRegRd(self, reg, length = 1):
        """
        Read a certain register from FPGA (WaxWing module), default length is 1 data byte.
        This is the lowest level of abstraction

        Arguments In:
            - reg: (int) the waxwings 7bit register address in decimal, therefore the maximum value is 127.
            - length: (int) the number of data bytes we want to read, if not specified, default length of 1.

        Return:
            - data: (uint8 or list of uint8's). If in GUI mode, and an invalid value is given, will return a string, otherwise returns data.
        """
        #Check length
        try:
            length = int(length)
        except ValueError as e:
            raise exceptions.InputError(f'length parameter must be an integer, but {length} was supplied.\n{e}')
        #Check reg
        try: reg = int(reg)
        except Exception: raise exceptions.InputError(f'reg value must an integer, but {reg} was supplied.')
        if (reg > 127) or (reg < 0): raise exceptions.InputError(f'reg parameter must be between 0 and 127, but {reg} was supplied.')


        request_type = 0x40
        request = _const.fpga_reg_rd
        length = length#number of bytes, 16 byte array
        value = length#length of data which we want to read, default = 1.
        index = reg#address: 0 - 127

        if (reg > 127) or (reg < 0): raise exceptions.InputError(f'reg parameter must be between 0 and 127, but {reg} was supplied.')

        try:
            with self._threadLock:
                rx_data = self.Dev_Handle.controlRead(request_type = request_type, request = request, value= value, index=index, length=length, timeout = self.usb_controlread_timeout_ms)
        except Exception as e:
            raise exceptions.UsbControlTransferReadError(f'Error reading EGSE FPGA Register.\n{e}')

        data = list(rx_data)#convert from bytearray since it is a pain to work with
        if len(data) == 1:#If only one data point, return as a single value
            data = data[0]

        if self.debug:
            if length == 1:
                print("Register",hex(reg),"is:")
                print('\t Hex:', hex(data))
                print('\t Dec:', data)
            else:
                print("Register",hex(reg),"is:")
                print('\t Dec:', data)

        return data

    def FpgaRegWr(self, reg, data):
        """
        Write data to a register on FPGA (WaxWing module), default length is 1 data byte, this is determined by looking at 'data'.
        This is the lowest level of abstraction

        Arguments In:
            - reg: (int) the 7bit register value in decimal, therefore the maximum value is 127.
            - data: (uint8 or list of uint8's) the data we want to send, list cannot be longer than 255.

        Return:
            - message (str) an error message, this is only possible if self.GUI == True, otherwise will throw the same message as an exception.
        """

        #Paramater checking
        try: reg = int(reg)
        except Exception: raise exceptions.InputError(f'Register value must an integer, but {reg} was supplied.')
        if (reg > 127) or (reg < 0): raise exceptions.InputError(f'Register parameter must be between 0 and 127, but {reg} was supplied.')
        if not isinstance(data, list) and not isinstance(data, numpy.ndarray): data = [ data ]
        data_len = len(data)
        if data_len > 2048: raise exceptions.InputError(f'Data parameter may have up to 2048 elements, but {data_len} elements was supplied.')

        request_type = 0x40
        request = _const.fpga_reg_wr

        #Combine command and data
        #List version: send    [reg][data[0]]...[data[n-1]]
        value = data_len +1
        data_list = []
        data_list.append(reg)
        data_list.extend(data)
        index = 120#We need some default value for the transfer, currently the FX3 can react to this field, however it does not use this value.

        try:
            with self._threadLock:
                self.Dev_Handle.controlWrite(request_type = request_type, request = request, value= value, index=index, data = data_list, timeout = self.usb_controlwrite_timeout_ms) #The actual USB control transfer
        except Exception as e:
            raise exceptions.UsbControlTransferWriteError()

        if self.debug:
            print('Writing:',data,'to reg:', hex(reg))

    def FpgaRegRdModWr(self, reg, val, pos):
        """
        Read-Modify-Write data to a waxwing register. Currently functionality is such that only 1x8bit register may be operated on at a time.
        
        Arguments In:
            - reg: (int) the checking whether this register is within range happens in 'FpgaRegRd' method.
            - val: (uint8) '1' to set, '0' to clear. 
            - pos: (int) 0 to 7, where 0 is the LSB, and 7 is MSB. I.e.: which bit position is to be modified.
        
        Example: to set register 0x05 to modify position '2' with a '1'. 
            FpgaRegRdModWr(reg=x05, val=1, pos=2)
            If register x05 was x30, it will be modified to x34.
        
        """
        #Parameter checking 
        try: reg = int(reg)
        except Exception: raise exceptions.InputError(f'reg value must an integer, but {reg} was supplied.')
        if (reg > 127) or (reg < 0): raise exceptions.InputError(f'reg parameter must be between 0 and 127, but {reg} was supplied.')    
        
        try: pos = int(pos) 
        except Exception: raise exceptions.InputError(f'pos value must an integer, but {pos} was supplied.')
        if (pos > 7) or (pos < 0): raise exceptions.InputError(f'pos parameter must be between 0 and 7, but {pos} was supplied.')    
        
        try: val = int(val)
        except Exception: raise exceptions.InputError(f'val must an integer, but {val} was supplied.')
        if (val > 1) or (val < 0) : raise exceptions.InputError(f'val parameter must be an integer, either 0 or 1, but {val} was supplied.')    
        
        #Read 
        reg_val_initial = self.FpgaRegRd(reg = reg)
        
        #Modify             
        if val == 1:#Set value 
            reg_val_updated = reg_val_initial | (1 << pos)
        else:#If value is zero, therefore clear but at that position        
            reg_val_updated = reg_val_initial & (0xFF ^ (1 << pos) )
        
        #Write
        self.FpgaRegWr(reg = reg, data = reg_val_updated)
        
    def FpgaReset(self):
        """
        A system reset of the FPGA. 
        """
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 
        self.FpgaRegWr(_const.reg_addr_global_control, 0x01)


    ## ======================================================================= ##
    ##########_____________Reading from the WaxWing's flash____________##########
    def _FlashReadPage(self, address):
        """
        Read 1 full page from WW's SPI config flash.

        Arguments In:
            - address: 24 bit address, can be anywhere within sector or subsector. E.g.: 0x000100 will read from 0x000100 to 0x0001FF, aka 1 full page.

        Return:
            - data: numpy.array(), convert bytearray numpy.array, such that it is easier to work with. Will contain 0-255 range.
        """
        if self.HwRevision == 3:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 

        try: address = int(address)
        except Exception: raise exceptions.InputError(f'address value must an integer, but {address} was supplied.')
        if (address > 0xffffff) or (address < 0): raise exceptions.InputError(f'address parameter must be 24-bit unsigned, but {address} was supplied.')

        request_type = 0x40
        request = _const.read_page_ww_flash
        length = 0x0100 #number of bytes per page

        #For address: 0xABCDEF, addr_MSB = 0xABCD
            		#           addr_LSB = 0x00EF
        addr_MSB = (address & 0xFFFF00) >>8
        addr_LSB = (address & 0x0000FF)
        value = addr_MSB
        index = addr_LSB

        #Read the data
        try:
            with self._threadLock:
                rx_data = self.Dev_Handle.controlRead(request_type = request_type, request = request, value= value, index=index, length=length, timeout =400)#1ms seems fine enough, we add safety factor to 400ms
        except Exception as e:
            raise exceptions.UsbControlTransferReadError()


        rx_data_arr = numpy.asarray(rx_data)#convert from bytearray since it is a pain to work with
        if self.debug:
            print (rx_data_arr)
        return rx_data_arr
    #TODO: step b



    def FpgaReboot(self):
        """
        Re-load the config stored in the SPI flash into the FPGA's config.
        This is required after updating firmware if you do not want to power cycle the entire EGSE.
        """
        if self.HwRevision == 3:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 
        
        #Control Write
        request_type = 0x40
        request = _const.fpga_reboot
        length = 0x0002
        value = 0x0000
        index = 0x0000

        try:
            with self._threadLock:
                #Perform a read, where the FX3 sw waits for 3 seconds before 'returning' control to python, hence reading garbage data.
                if self.debug:
                    print('Re-booting EGSE FPGA by toggling IO via FX3... please wait 3 seconds')
                #The USB call lasts 3seconds (in the C-app), therefore add that plus normal delta for timeout.
                data = self.Dev_Handle.controlRead(request_type = request_type, request = request, value= value, index=index, length=length, timeout = 3000+_const.usb_controlread_timeout_ms)
        except Exception as e:
            raise exceptions.UsbControlTransferReadError()
        if self.debug:
            print('EGSE\'s FPGA rebooted.')


    ## ======================================================================= ##
    ############_________________Programming the FX3_________________############
    def _EepromFx3RdBt(self, addr):
        """
        Read one byte of FX3's M24M02-DR eeprom, 'eeprom random address read'.

        Arguments In:
            - addr (numpy.uint32) : an 18bit address.

        Return:
            - data (numpy.uint8): the byte which we want to read
        """

        try: addr = int(addr)
        except Exception: raise exceptions.InputError(f'addr value must an integer, but {addr} was supplied.')
        if (addr > 0x3ffff) or (addr < 0): raise exceptions.InputError(f'addr parameter must be 18-bit unsigned, but {addr} was supplied.')


        #Shift 15 bits (instead of 16) since the RnW bit is the LS-bit of the first byte (see pg 13 of EEPROM datasheet).
        addrMSB = (addr & 0x30000) >> 15#Grab the top two bits, shift right, result in 16 bit value
        addrMSB = addrMSB & 0x6
        addrLSB = (addr & 0x0FFFF)#Grab the bottom 16 bits, result in 16bit value

        request_type = 0x40
        request = _const.eeprom_random_addr_read
        value = addrMSB
        index = addrLSB
        length= 0x0001 #number of bytes, 1x 8bit register

        try:
            with self._threadLock:
                rx_data = self.Dev_Handle.controlRead(request_type = request_type, request = request, value= value, index=index, length=length, timeout = self.usb_controlread_timeout_ms)
        except Exception as e:
            raise exceptions.UsbControlTransferReadError()

        data = numpy.asarray(rx_data)#convert from bytearray since it is a pain to work with
        data = data[0]

        if self.debug:
            print('Data recieved from addr: ', addr ,  ':0x' , hex(data))

        return data


    def _EepromFx3RdPg_bytearr(self, addr):
        """
        Read one page (256 bytes) of data from the FX3's EEPROM. Data sheet not explicit if the address has to be on page boundaries, so user must manage that he sends addresses at page boundaries.

        Arguments In:
            - address (numpy.uint32) : an 18bit address.
        Return:
            - data (list containing uint8's): the data which was read from the FX3's EEPROM
        """
        try: addr = int(addr)
        except Exception: raise exceptions.InputError(f'addr value must an integer, but {addr} was supplied.')
        if (addr > 0x3ffff) or (addr < 0): raise exceptions.InputError(f'addr parameter must be 18-bit unsigned, but {addr} was supplied.')

        #Shift 15 bits (instead of 16) since the RnW bit is the LS-bit of the first byte (see pg 13 of EEPROM datasheet).
        addrMSB = (addr & 0x30000) >> 15#Grab the top two bits, shift right, result in 16 bit value
        addrMSB = addrMSB & 0x6#Now left with A17,A16
        addrLSB = (addr & 0x0FFFF)#Grab the bottom 16 bits, result in 16bit value

        request_type = 0x40
        request = _const.eeprom_sequential_random_read
        value = addrMSB
        index = addrLSB
        length = 0x100#Hardcoded to 256 bytes - the page size of the EEPROM, in theory could read smnaller chunks.

        try:
            with self._threadLock:
                rx_data = self.Dev_Handle.controlRead(request_type = request_type, request = request, value= value, index=index, length=length, timeout = self.usb_controlread_timeout_ms)
        except Exception as e:
            raise exceptions.UsbControlTransferReadError()

        data = list(rx_data)#convert from bytearray sinbce it is a pain to work with

        return data


    def _EepromFx3RdPg(self, addr):
        """
        Read one page (256 bytes) of data from the FX3's EEPROM. Data sheet not explicit if the address has to be on page boundaries, so user must manage that he sends addresses at page boundaries.

        Arguments In:
            - address (numpy.uint32) : an 18bit address.
        Return:
            - data (numpy.uint8 array, will be 256 deep): the data which was read from the FX3's EEPROM
        """

        try: addr = int(addr)
        except Exception: raise exceptions.InputError(f'addr value must an integer, but {addr} was supplied.')
        if (addr > 0x3ffff) or (addr < 0): raise exceptions.InputError(f'addr parameter must be 18-bit unsigned, but {addr} was supplied.')

        #Shift 15 bits (instead of 16) since the RnW bit is the LS-bit of the first byte (see pg 13 of EEPROM datasheet).
        addrMSB = (addr & 0x30000) >> 15#Grab the top two bits, shift right, result in 16 bit value
        addrMSB = addrMSB & 0x6#Now left with A17,A16
        addrLSB = (addr & 0x0FFFF)#Grab the bottom 16 bits, result in 16bit value

        if self.debug:
            print('addrMSB', addrMSB)

        request_type = 0x40
        request = _const.eeprom_sequential_random_read
        value = addrMSB
        index = addrLSB
        length = 0x100#Hardcoded to 256 bytes - the page size of the EEPROM, in theory could read smnaller chunks.

        try:
            with self._threadLock:
                rx_data = self.Dev_Handle.controlRead(request_type = request_type, request = request, value= value, index=index, length=length, timeout = self.usb_controlread_timeout_ms)
        except Exception as e:
            raise exceptions.UsbControlTransferReadError()

        data = numpy.asarray(rx_data)#convert from bytearray sinbce it is a pain to work with

        return data



    ## ========================================================================================= ##
    ##########_________________Comms: WaxWing to outside world (e.g. CE)_________________##########
    #_SPI comms_#
    def SpiInit(self, clk_freq_mhz):
        """
        Initialise the SPI Master channel, ie the frequency with which the SPI on the EGSE will comms with connected electronics on the appropriate link.
        There are default values in place (1MHz SCK), but if you want to change this, it is only required one time per EGSE SPI session.
        Please confirm wether your EGSE has this functionality in it's firmware.

        Arguments In:
            - clk_freq_mhz : desired clock frequency in MHz. Can be a float or an integer
        Return
            - float        : the actual frequency achieved on SPI's SCK line, in MHz
        """

        try: clk_freq_mhz = float(clk_freq_mhz)
        except Exception: raise exceptions.InputError(f'clk_freq_mhz value must be a number, but {clk_freq_mhz} was supplied.')
        if (clk_freq_mhz < 0): raise exceptions.InputError(f'clk_freq_mhz parameter must be a positive number, but {clk_freq_mhz} was supplied.')
        
        #Set pins up.
        if (self.HwRevision == 3):
            # Only variant 1 and 3 and 4 supports this,
            if (self.getBuildVariant() == 1) or (self.getBuildVariant() == 3) or (self.getBuildVariant() == 4):
                self.SetSpiGpioPinConfig(conf = 'spi')
            else:
                raise exceptions.InputError(f'This FW-variant for REV3 EGSE does not support SPI.')

        #calculate divisor
        divisor = round(100/(2*clk_freq_mhz))

        #Write this value to the register.
        try:
            self.FpgaRegWr(reg = _const.reg_addr_spi_config, data=divisor)
        except Exception as e:
            raise exceptions.SPIError(f'Error programming SPI clock divisor.\n{e}')

        true_freq = 100/(2*divisor)

        if self.debug:
            print(f'User desired {clk_freq_mhz:.3f} MHz however {true_freq:.3f} MHz was achieved.')

        return true_freq


    def SpiTrans(self, mosi):
        """
        Set up and trigger a full duplex SPI transaction on the SPI port (e.g. full duplex to whatever is directly connected to the EGSE's SPI port)
        Please confirm wether your EGSE has this functionality in it's firmware.

        Arguments In:
            - mosi: (uint8 or list of uint8's) the data which is streamed to the connected device (slave).  Master (m) out (o) slave (s) in (i) a.k.a. mosi).
              NOTE: the number of bytes in 'mosi' is equivalent to the number of bytes in 'miso'.

        Return
            - miso: (uint8 or list of uint8's) the data which is streamed from the connected device (slave).  Master (m) in (i) slave (s) out (i) a.k.a. miso) see mosi for more detail.
        """
        #First determine whether we have a list or single byte.
        if not isinstance(mosi, list) and not isinstance(mosi, numpy.ndarray): mosi = [ mosi ]
        mosi_len = len(mosi)

        if mosi_len > 2048 or mosi_len == 0:
            raise exceptions.InputError(f'A max data length of 2048 is allowed, but "{mosi_len}" was supplied.')

        #length register
        self.FpgaRegWr(reg = _const.reg_addr_spi_length_lo, data = (mosi_len % 256)) # Lower Byte
        self.FpgaRegWr(reg = _const.reg_addr_spi_length_hi, data = (mosi_len // 256)) # Upper Byte

        #Control register, note: write to data register AFTER control register, it is how the spec says.
        control = 0x80
        self.FpgaRegWr(reg = _const.reg_addr_spi_control, data = control)

        #Data register
        self.FpgaRegWr(reg = _const.reg_addr_spi_data, data = mosi)

        #Poll status till done
        stat = self.FpgaRegRd(reg = _const.reg_addr_spi_status)
        count_ms = 0
        while stat != 0x02:#While SPI transaction is busy and data is not available, wait. Ie only read once the full data is in and SPI transaction is finished
            time.sleep(0.0005)#wait 1ms
            count_ms = count_ms +1
            if count_ms == 500:
                raise exceptions.SPIError(f'Timed out after 500ms during SpiTransaction.')
            stat = self.FpgaRegRd(reg = _const.reg_addr_spi_status)
        #Grab miso data
        miso = self.FpgaRegRd(reg = _const.reg_addr_spi_data, length = mosi_len)

        return miso

    #_I2C comms_#
    def I2cConfig(self, speed_kbps=100, transaction_timeout_s=None, port = I2C_PORT_CE):
        """
        Configure the EGSE's I2C link to run at a certain rate. Valid options are: 100, 400, 1000, 10 Kbit/s, optionally provide it with
        a transaction timeout in seconds.

        Arguments in:
            - speed_kbps: (int): Rate at which the link is configured to run at. Valid options: 100, 400, 1000 or 10. Defaults to 100 kbps.
            - transaction_timeout_s: (float): timeout in seconds for each I2C transaction to complete
            - port: {int}: there are two I2C ports, the Control Electronics port "I2C_PORT_CE", and the Environmental Connector port "I2C_PORT_ENV".

        Return:
            BOOL    - True when successful
                    - False when not successful
        """

        #Paramater test
        if not speed_kbps in _const.supported_i2c_speeds:
            raise exceptions.InputError(f'{speed_kbps} is not a viable option for speed_kbps. Please choose one of {_const.supported_i2c_speeds}')
        if not port in _const.supported_i2c_ports:
            raise exceptions.InputError(f'{port} is not a viable option for port. Please choose one of {_const.supported_i2c_ports}')        
        if not transaction_timeout_s is None:
            try:
                if port == I2C_PORT_CE:
                    self.i2c_transaction_timeout_s = float(transaction_timeout_s)
                elif port == I2C_PORT_ENV:
                    self.i2c_env_transaction_timeout_s = float(transaction_timeout_s)
            except ValueError:
                raise exceptions.InputError(f'timeout parameter must be a number, but "{transaction_timeout_s}" was given')

        #Write new value
        if speed_kbps == 100:
            dataWr = 0x00
        elif speed_kbps == 400:
            dataWr = 0x01
        elif speed_kbps == 1000:
            dataWr = 0x02
        elif speed_kbps == 10:#Mainly used for really bad cable harnesses.
            dataWr = 0x03

        #Setup appropriate registers for requested port 
        if  port == I2C_PORT_CE:
            config_reg_addr = _const.reg_addr_i2c_config
        elif port == I2C_PORT_ENV:
            config_reg_addr = _const.reg_addr_i2c_env_config

        try:
            self.FpgaRegWr(reg = config_reg_addr , data = dataWr)
        except Exception as e:
            raise exceptions.I2CLinkConfigurationError(f'Error programming I2C Clock Rate\n{e}')

        #Read and confirm new value
        try:
            curr_speed = self.FpgaRegRd(reg = config_reg_addr, length = 1)
        except Exception as e:
            raise exceptions.I2CLinkConfigurationError(f'Error verifying I2C Clock Rate\n{e}')

        if self.debug:
            print(f'I2C link successfully configured to: {_const.supported_i2c_speeds[curr_speed]}')
        #Update status and return True.
        if port == I2C_PORT_CE:
            self.command_if_i2c_configured = True
            return True
        elif port == I2C_PORT_ENV: 
            return True

    def _isI2CBusBusy(self, port = I2C_PORT_CE):
        if port == I2C_PORT_CE:
            reg_addr_status = _const.reg_addr_i2c_status
        elif port == I2C_PORT_ENV:
            reg_addr_status = _const.reg_addr_i2c_env_status
        
        try:
            stat = self.FpgaRegRd(reg = reg_addr_status)
        except Exception as e:
            raise exceptions.Error(f'Error reading I2C status register.\n{e}')

        if stat & 0x01 == 0x00:#BusBusy not true anymore
            return False
        else:
            return True

    def _waitI2CBusNotBusy(self, waiting_period_s = 0.250, port = I2C_PORT_CE):
        """
        Check if I2C bus is busy, and keep checking for a specified period of time
        """
        if port == I2C_PORT_CE:
            reg_addr_status = _const.reg_addr_i2c_status
        elif port == I2C_PORT_ENV:
            reg_addr_status = _const.reg_addr_i2c_env_status

        timeout = time.time() + waiting_period_s
        stat = 0
        while time.time() < timeout:
            try:
                stat = self.FpgaRegRd(reg = reg_addr_status)
            except Exception as e:
                raise exceptions.Error(f'Error reading I2C status register.\n{e}')

            if stat & 0x01 == 0x00:#BusBusy not true anymore
                return True
            else:
                time.sleep(0.0001)

        if self.debug:
            print("I2C Bus is Busy. Status Register = 0x{:02X}".format(stat))

        return False

    def _waitI2CTransactionDone(self, port, waiting_period_s = 0.500):
        if port == I2C_PORT_CE:
            reg_addr_status = _const.reg_addr_i2c_status
        elif port == I2C_PORT_ENV:
            reg_addr_status = _const.reg_addr_i2c_env_status        
        
        timeout = time.time() + waiting_period_s
        stat = 0
        while time.time() < timeout:
            try:
                stat = self.FpgaRegRd(reg = reg_addr_status)
            except Exception as e:
                raise exceptions.Error(f'Error reading I2C status register.\n{e}')

            if stat & 0x02 == 0x00: # Transaction Done
                return True
            #else:
            #    time.sleep(0.0001)

        if self.debug:
            print("I2C Transaction Timed Out. Status Register = 0x{:02X}".format(stat))

        return False

    def I2cPullUp(self, val):
        """
        The EGSE has pull-ups which can be enabled/disabled by software for the 'I2C_PORT_CE' port. EGSE by default has the pullups enabled.

        Arguments In:
            - val (bool, '1' or '0'):   'True' or '1' enables EGSE's onboard pullup
                                        'False' or '0' disables EGSE's onboard pullup
        """
        #Parameter check
        try: #covers both a float and a bool option.
            val = int(val)
        except ValueError as e:
            raise exceptions.InputError(f'val parameter must be \'1\', \'0\', \'True\' or \'False\', instead \'{val}\' was supplied.\n{e}')

        if (val not in [0, 1]):
            raise exceptions.InputError(f'val parameter must be \'1\', \'0\', \'True\' or \'False\', instead "{val}" was supplied.')

        #Update the register on waxwing:
        try:
            if self.debug:
                print(val, ' is written to register' , _const.reg_addr_i2c_pull_up)
            self.FpgaRegWr(reg = _const.reg_addr_i2c_pull_up , data = val)
        except Exception as e:
            raise exceptions.Error(f'Could not set pullup register.\n{e}')

    def I2cWr(self, slaveAddress, data, port = I2C_PORT_CE):
        """
        Write data to a generic device, determined by the device address.

        Arguments IN:
            - slaveAddress: (8bit value, range from 0 to 127): device address (aka device ID) which we want to write to
            - data: (uint8 or list of uint8's), data which we want to write. Assume data already in correct order.
            - port: {int}: there are two I2C ports, the Control Electronics port "I2C_PORT_CE", and the Environmental Connector port "I2C_PORT_ENV".            

        Return:
            BOOL    - True when I2C Write was successful
                    - False when not successful
        """
        #1.) Check if bus busy
        #2.) Write length (write) - high and low bytes
        #3.) Write Data (consists of slave address then data)
        #4.) Write to control reg to start off transaction
        #5.) Poll till done.

        #Paramater check
        try:
            slaveAddress = int(slaveAddress)
        except ValueError as e:
            raise exceptions.InputError(f'slaveAddress parameter must be an integer, but "{slaveAddress}" was supplied.\n{e}')
        if (slaveAddress > 127) or (slaveAddress < 0):
            raise exceptions.InputError(f'slaveAddress parameter must be between 0 and 127 (inclusive), but "{slaveAddress}" was supplied.')
        if not port in _const.supported_i2c_ports:
            raise exceptions.InputError(f'{port} is not a viable option for port. Please choose one of {_const.supported_i2c_ports}')        

        #Select appropriate registers 
        if port == I2C_PORT_CE:
            #Write 
            reg_addr_length_wr_lo   = _const.reg_addr_i2c_length_wr_lo
            reg_addr_length_wr_hi   = _const.reg_addr_i2c_length_wr_hi
            reg_addr_data           = _const.reg_addr_i2c_data
            reg_addr_control        = _const.reg_addr_i2c_control
            #Read 
            reg_addr_status         = _const.reg_addr_i2c_status
        elif port == I2C_PORT_ENV:
            reg_addr_length_wr_lo   = _const.reg_addr_i2c_env_length_wr_lo
            reg_addr_length_wr_hi   = _const.reg_addr_i2c_env_length_wr_hi
            reg_addr_data           = _const.reg_addr_i2c_env_data
            reg_addr_control        = _const.reg_addr_i2c_env_control
            #Read 
            reg_addr_status         = _const.reg_addr_i2c_env_status        
        
        #If data = None, this means we ONLY write out the address, otherwise we write out the address combined with the data
        if data == None:
            data_len = 0
        else:
            # Check for maximum length (the FPGA supports up to 2048 byte transfers)
            if not isinstance(data, list) and not isinstance(data, numpy.ndarray): data = [ data ]
            data_len = len(data)
            if data_len > 2048: raise exceptions.InputError(f'Data parameter may have up to 2048 elements, but {data_len} elements was supplied.')

        #1.)
        if not self._waitI2CBusNotBusy(port = port):
            #bus is busy
            if self.debug:
                print('I2C bus is busy')
            raise exceptions.I2CBusBusyError()

        #2.)
        try:
            self.FpgaRegWr(reg = reg_addr_length_wr_lo , data = (data_len % 256) ) # Lower Byte
        except Exception as e:
            raise exceptions.I2CError(f'Error writing I2C transaction length to EGSE.\n{e}')
        try:
            self.FpgaRegWr(reg = reg_addr_length_wr_hi , data = (data_len // 256) ) # Upper Byte
        except Exception as e:
            raise exceptions.I2CError(f'Error writing I2C transaction length to EGSE.\n{e}')

        #3.)
        dataWr = [0]*(data_len + 1)
        dataWr[0] = slaveAddress
        if data != None:#Only populate this if we actually have data to send.
            dataWr[1:] = data

        try:
            self.FpgaRegWr(reg = reg_addr_data , data = dataWr)
        except Exception as e:
            raise exceptions.I2CError(f'Error writing I2C transaction data to EGSE.\n{e}')

        #4.)
        try:
            self.FpgaRegWr(reg = reg_addr_control , data = 0x01)
        except Exception as e:
            raise exceptions.I2CError(f'Error triggering I2C transaction.\n{e}')
        
        #5.)
        if not self._waitI2CTransactionDone(port = port):#, waiting_period_s = self.i2c_env_transaction_timeout_s):
            if self.debug:
                print(' - Transaction still busy')
            raise exceptions.I2CTransactionTimeoutError()

        try:
            stat = self.FpgaRegRd(reg = reg_addr_status)
        except Exception as e:
            raise exceptions.I2CError(f'Error reading I2C return data.\n{e}')
        if stat & 0x08 == 0x00:#Looking to see if there was an ack from the slave.
            if self.debug:
                print(" - No slave acknowledge for slaveAddress", slaveAddress)
                print(" - I2C Status Register = 0x{:02X}".format(stat))
            raise exceptions.I2CNoSlaveAckError(f'Slave address: \'{hex(slaveAddress)}\'. ')

        return True

    def I2cCombo(self, slaveAddress, wr_data, rd_length, port = I2C_PORT_CE):
        """
        This performs a Write-Read (Combination) on the I2C bus.

        Arguments In:
            - slaveAddress (8bit value, range from 0 to 127): device address (aka device ID) which we want to read from
            - wr_data (uint8 or list of uint8's), data which we want to write. Assume data already in correct order.
            - rd_length (8bit, range 1-255) how many bytes do we want to read. Generally this will be 4
                since we will read a 32bit value, but in some cases it will be a multiple of 4.
            - port: {int}: there are two I2C ports, the Control Electronics port "I2C_PORT_CE", and the Environmental Connector port "I2C_PORT_ENV".                            

        Return:
            - data (array of bytes), data just sent back as is, not re-orderd
        """

        #1.) Check status, wait till I2C bus not busy or timeout
        #2.) write length (read) and (write)
        #3.) write slaveAddress and wr_data
        #4.) iniitialise combo transaction
        #5.) check status, wait till done or timeout
        #6.) read data from DATA register

        #Input paramater checks
        try:
            slaveAddress = int(slaveAddress)
        except ValueError as e:
            raise exceptions.InputError(f'slaveAddress parameter must be an integer, but "{slaveAddress}" was supplied.\n{e}')
        if (slaveAddress > 127) or (slaveAddress < 0):
            raise exceptions.InputError(f'slaveAddress parameter must be between 0 and 127 (inclusive), but "{slaveAddress}" was supplied.')
        if not port in _const.supported_i2c_ports:
            raise exceptions.InputError(f'{port} is not a viable option for port. Please choose one of {_const.supported_i2c_ports}')                    

        if not isinstance(wr_data, list) and not isinstance(wr_data, numpy.ndarray): wr_data = [ wr_data ]
        wr_length = len(wr_data)
        if wr_length > 2048: raise exceptions.InputError(f'wr_data parameter may have up to 2048 elements, but {wr_length} elements was supplied.')

        try:
            rd_length = int(rd_length)
        except ValueError as e:
            raise exceptions.InputError(f'rd_length parameter must be an integer, but "{rd_length}" was supplied.\n{e}')
        if (rd_length > 2048) or (rd_length < 1):
            raise exceptions.InputError(f'rd_length parameter must be between 0 and 2048 (inclusive), but "{rd_length}" was supplied.')
        
        #Select appropriate registers 
        if port == I2C_PORT_CE:
            #Write 
            reg_addr_len_rd_lo    =  _const.reg_addr_i2c_length_rd_lo
            reg_addr_len_rd_hi    =  _const.reg_addr_i2c_length_rd_hi
            reg_addr_len_wr_lo    =  _const.reg_addr_i2c_length_wr_lo
            reg_addr_len_wr_hi    =  _const.reg_addr_i2c_length_wr_hi
            reg_addr_data         =  _const.reg_addr_i2c_data
            reg_addr_control      =  _const.reg_addr_i2c_control
            #read
            reg_addr_status       =  _const.reg_addr_i2c_status
        elif port == I2C_PORT_ENV:
            #Write 
            reg_addr_len_rd_lo    =  _const.reg_addr_i2c_env_length_rd_lo
            reg_addr_len_rd_hi    =  _const.reg_addr_i2c_env_length_rd_hi
            reg_addr_len_wr_lo    =  _const.reg_addr_i2c_env_length_wr_lo
            reg_addr_len_wr_hi    =  _const.reg_addr_i2c_env_length_wr_hi
            reg_addr_data         =  _const.reg_addr_i2c_env_data
            reg_addr_control      =  _const.reg_addr_i2c_env_control
            #read
            reg_addr_status       =  _const.reg_addr_i2c_env_status            

        #1.)
        if not self._waitI2CBusNotBusy(port = port):
            #bus is busy
            if self.debug:
                print('I2C bus is busy')
            raise exceptions.I2CBusBusyError()

        #2.)
        try:
            self.FpgaRegWr(reg = reg_addr_len_rd_lo , data = (rd_length % 256) )
        except Exception as e:
            raise exceptions.I2CError(f'Error writing I2C transaction length (read) to EGSE.\n{e}')
        try:
            self.FpgaRegWr(reg = reg_addr_len_rd_hi , data = (rd_length // 256) )
        except Exception as e:
            raise exceptions.I2CError(f'Error writing I2C transaction length (read) to EGSE.\n{e}')

        try:
            self.FpgaRegWr(reg = reg_addr_len_wr_lo , data = (wr_length % 256) )
        except Exception as e:
            raise exceptions.I2CError(f'Error writing I2C transaction length (write) to EGSE.\n{e}')
        try:
            self.FpgaRegWr(reg = reg_addr_len_wr_hi , data = (wr_length // 256) )
        except Exception as e:
            raise exceptions.I2CError(f'Error writing I2C transaction length (write) to EGSE.\n{e}')

        #3.)
        dataWr = [0]*(wr_length + 1)
        dataWr[0] = slaveAddress
        dataWr[1:] = wr_data

        try:
            self.FpgaRegWr(reg = reg_addr_data , data = dataWr)
        except Exception as e:
            raise exceptions.I2CError(f'Error writing I2C transaction write data bytes to EGSE.\n{e}')

        #4.)
        try:
            self.FpgaRegWr(reg = reg_addr_control , data = 0x04)
        except Exception as e:
            raise exceptions.I2CError(f'Error triggering I2C combo transaction.\n{e}')

        #5.)
        if not self._waitI2CTransactionDone(port = port):
            if self.debug:
                print(' - Transaction still busy')
            raise exceptions.I2CTransactionTimeoutError()

        try:
            stat = self.FpgaRegRd(reg = reg_addr_status)
        except Exception as e:
            raise exceptions.I2CError(f'Error reading I2C return data.\n{e}')
        if stat & 0x08 == 0x00:#Looking to see if there was an ack from the slave.
            if self.debug:
                print(" - No slave acknowledge for slaveAddress", slaveAddress)
                print(" - I2C Status Register = 0x{:02X}".format(stat))
            raise exceptions.I2CNoSlaveAckError()
        elif stat & 0x04 == 0x00:
            if self.debug:
                print(" - No data received from slave device")
            raise exceptions.I2CNoDataFromSlaveError()

        #6.)
        try:
            data = self.FpgaRegRd(reg = reg_addr_data, length = rd_length)
        except Exception as e:
            raise exceptions.I2CError(f'Error reading I2C transaction data from EGSE.\n{e}')

        return data

    def I2cRd(self, slaveAddress, length, port = I2C_PORT_ENV):
        """Setup a I2c read transaction. slaveAddress is 7bit. 

        Arguments In:
            - slaveAddress (8bit value, range from 0 to 127): device address which we want to read from.        
            - length (uint8): how many bytes of data to read. (1-2048)
        Return:    
            - data (array of bytes), data just sent back as is, not re-orderd
        
        """
        #TODO: still test on actual I2C bus...
        #1.) CHeck wether status is busy, else timeout
        #2.) Setup length field on I2C master
        #3.) Setup Data field on I2C master (Device slaveAddress)
        #4.) Initiate Rd
        #5.) Poll status register until I2C status indicates done.
        #6.) Now read data from Register.
        
        #Input paramater checks
        try:
            slaveAddress = int(slaveAddress)
        except ValueError as e:
            raise exceptions.InputError(f'slaveAddress parameter must be an integer, but "{slaveAddress}" was supplied.\n{e}')
        if (slaveAddress > 127) or (slaveAddress < 0):
            raise exceptions.InputError(f'slaveAddress parameter must be between 0 and 127 (inclusive), but "{slaveAddress}" was supplied.')
        if not port in _const.supported_i2c_ports:
            raise exceptions.InputError(f'{port} is not a viable option for port. Please choose one of {_const.supported_i2c_ports}')                    
        try:
            length = int(length)
        except ValueError as e:
            raise exceptions.InputError(f'length parameter must be an integer, but "{length}" was supplied.\n{e}')
        if (length > 2048) or (length < 1):
            raise exceptions.InputError(f'length parameter must be between 0 and 2048 (inclusive), but "{length}" was supplied.')
        
        #Select appropriate registers 
        if port == I2C_PORT_CE:
            #Write 
            reg_addr_len_rd_lo    =  _const.reg_addr_i2c_length_rd_lo
            reg_addr_len_rd_hi    =  _const.reg_addr_i2c_length_rd_hi
            reg_addr_len_wr_lo    =  _const.reg_addr_i2c_length_wr_lo
            reg_addr_len_wr_hi    =  _const.reg_addr_i2c_length_wr_hi
            reg_addr_data         =  _const.reg_addr_i2c_data
            reg_addr_control      =  _const.reg_addr_i2c_control
            #read
            reg_addr_status       =  _const.reg_addr_i2c_status
        elif port == I2C_PORT_ENV:
            #Write 
            reg_addr_len_rd_lo    =  _const.reg_addr_i2c_env_length_rd_lo
            reg_addr_len_rd_hi    =  _const.reg_addr_i2c_env_length_rd_hi
            reg_addr_len_wr_lo    =  _const.reg_addr_i2c_env_length_wr_lo
            reg_addr_len_wr_hi    =  _const.reg_addr_i2c_env_length_wr_hi
            reg_addr_data         =  _const.reg_addr_i2c_env_data
            reg_addr_control      =  _const.reg_addr_i2c_env_control
            #read
            reg_addr_status       =  _const.reg_addr_i2c_env_status                    
        
        
        #1.)
        if not self._waitI2CBusNotBusy(port = port):
            #bus is busy
            if self.debug:
                print('I2C bus is busy')
            raise exceptions.I2CBusBusyError()
        
        #2.) 
        try:
            self.FpgaRegWr(reg = reg_addr_len_rd_lo , data = (length % 256) )
        except Exception as e:
            raise exceptions.I2CError(f'Error writing I2C read length to EGSE.\n{e}')
        try:
            self.FpgaRegWr(reg = reg_addr_len_rd_hi , data = (length // 256) )
        except Exception as e:
            raise exceptions.I2CError(f'Error writing I2C read length to EGSE.\n{e}')        
        
        #3.) 
        try:
            self.FpgaRegWr(reg = reg_addr_data , data = slaveAddress)
        except Exception as e:
            raise exceptions.I2CError(f'Error setting slave address for reading I2C transaction.\n{e}')        
        
        #4.) 
        try:
            self.FpgaRegWr(reg = reg_addr_control , data = 0x02)
        except Exception as e:
            raise exceptions.I2CError(f'Error performing InitRd.\n{e}')        
        
        #5.) 
        if not self._waitI2CTransactionDone(port = port):
            if self.debug:
                print(' - Transaction still busy')
            raise exceptions.I2CTransactionTimeoutError()
                
        #6.)
        try:
            data = self.FpgaRegRd(reg = reg_addr_data, length = length)
        except Exception as e:
            raise exceptions.I2CError(f'Error reading I2C transaction data from EGSE.\n{e}')

        return data        

    ## ========================================================================================= ##
    ##########______________High Speed Interface to outside world (e.g. CE)______________##########

    def HsSetMode(self, mode):
        """
        Setup the specific High speed data interface (HsdIf) on the EGSE to either recieve (rx), transmit (tx), or reset (rst). 
        
        Arguments In:
            - mode (Module Constant : HsdiMode_Rst, HsdiMode_Tx, or HsdiMode_Rx)
        """


        #1. First put all HsdIf's in reset
        #2. determine what should be sent
        #3. send to HSD_MODE register

        #1.
        try:
            self.FpgaRegWr(reg = _const.reg_addr_hsd_mode, data = 0x00)
        except Exception as e:
            raise exceptions.HsdiError(f'Error resetting HSI IOs.\n{e}')

        #2.
        try:
            mode = int(mode)
        except ValueError as e:
            raise exceptions.InputError(f'Mode parameter must be an integer, but "{mode}" was supplied.\n{e}')
        if mode == HsdiMode_Rst:
            mode_data = 0x00
        elif mode == HsdiMode_Tx:
            mode_data = 0x01
        elif mode == HsdiMode_Rx:
            mode_data = 0x02
        else:
            raise exceptions.InputError(f'Invalid HSI Mode "{mode}" specified.')

        if self.debug:
            print('Writing:',hex(hsd_mode_data) ,' to ', 'reg:', _const.reg_addr_hsd_mode)

        #3.
        try:
            self.FpgaRegWr(reg = _const.reg_addr_hsd_mode, data = hsd_mode_data)
        except Exception as e:
            raise exceptions.HsdiError(f'Error setting HSI Mode.\n{e}')

    def HsStatus(self, hex_show = False):
        '''
        Returns Status about the High-Speed Interface
        '''
        try:
            GpifStatus = self.FpgaRegRd(reg = _const.reg_gpif_status)
            hsmux      = self.FpgaRegRd(reg = _const.reg_hs_mux)
            hsMode     = self.FpgaRegRd(reg = _const.reg_hs_mode)
            stat_hsdIf = self.FpgaRegRd(reg = _const.reg_hsd_if_status)
            if self.HwRevision == 3:
                stat_serdes= self.FpgaRegRd(reg = _const.reg_serdes_status)
                serdes_dbg = self.FpgaRegRd(reg = _const.reg_serdes_dbg)
            stat_usart = self.FpgaRegRd(reg = _const.reg_usart_status)
            usart_sigs = self.FpgaRegRd(reg = _const.reg_usart_sigs)
            spw_stat   = self.FpgaRegRd(reg = _const.reg_spw_stat) 
            spw_data_status   = self.FpgaRegRd(reg = _const.reg_spw_data_status) 
        except Exception as e:
            exceptions.HsdiError(f'Failed to put read status of Hs.\n{e}')
        
        if self.HsDebug:
            if hex_show == False:
                print(f'__Various Hs Status__')
    
                #GpifStatus
                dict_GpifStatus = {}
                dict_GpifStatus["FifoEmpty"] = (GpifStatus & 0x40) != 0
                dict_GpifStatus["DataAvail"] = (GpifStatus & 0x20) != 0
                dict_GpifStatus["GpifReady"] = (GpifStatus & 0x10) != 0        
                print(f'    GpifStatus:')
                print(dict_GpifStatus)
                
                #HsMux
                dict_HsMux = {}
                dict_HsMux["HsdIf"] = (hsmux & 0x01) != 0
                dict_HsMux["USART"] = (hsmux & 0x02) != 0
                dict_HsMux["SPW"] =   (hsmux & 0x04) != 0
                print(f'    HsMux:')
                print(dict_HsMux)
    
                #HsMode
                #stat_hsdIf
                #stat_usart
                #usart_sigs
                
                #spw_stat 
                dict_spw_stat = {}
                dict_spw_stat["DataDone"] = (spw_stat & 0x80 ) != 0
                dict_spw_stat["ErrEsc"] = (spw_stat & 0x40 ) != 0
                dict_spw_stat["ErrDisc"] = (spw_stat & 0x20 ) != 0
                dict_spw_stat["ErrPar"] = (spw_stat & 0x10 ) != 0
                dict_spw_stat["ErrCred"] = (spw_stat & 0x08 ) != 0
                dict_spw_stat["Running"] = (spw_stat & 0x04 ) != 0
                dict_spw_stat["Connecting"] = (spw_stat & 0x02 ) != 0
                dict_spw_stat["Started"] = (spw_stat & 0x01 ) != 0
                print(f'    spw_stat')
                print(dict_spw_stat)
                
                #spw_data_status
                dict_spw_data_status = {}
                dict_spw_data_status["Done"] = (spw_data_status & 0x04 ) != 0
                dict_spw_data_status["Busy"] = (spw_data_status & 0x02 ) != 0
                dict_spw_data_status["ToutMP"] = (spw_data_status & 0x01 ) != 0
                print(dict_spw_data_status)
            
                print(f'_____________________')
            else:        
                print(f'___HsStatus:___')
                print(f'    GpifStatus {hex(GpifStatus)}')
                print(f'    hsmux      {hex(hsmux     )}')
                print(f'    hsMode     {hex(hsMode    )}')
                print(f'    stat_hsdIf {hex(stat_hsdIf)}')
                if self.HwRevision == 3:
                    print(f'    stat_serdes{hex(stat_serdes)}')
                    print(f'    serdes_dbg {hex(serdes_dbg)}')
                print(f'    stat_usart {hex(stat_usart)}')
                print(f'    usart_sigs {hex(usart_sigs)}')
                print(f'    spw_stat   {hex(spw_stat)}')
                print(f'    spw_data   {hex(spw_data_status)}')


    def HsIfReset(self):
        """Place various FSM's into reset, to clear any dodgy data/state which it may be in due to Power Cycle of connected HW"""
        
        if self.HsDataIfType == DATA_INTERFACE_HSDIF:
            self.FpgaRegWr(reg = _const.reg_hsd_if_rst , data = 0x01)#reset    
            self.FpgaRegWr(reg = _const.reg_hsd_if_rst , data = 0x00)#take out of reset
                        
        elif self.HsDataIfType == DATA_INTERFACE_USART:
            #Not confirmed...
            #self.FpgaRegWr(reg = _const.reg_usart_ctrl , data = 0x01)#reset 
            #self.FpgaRegWr(reg = _const.reg_usart_ctrl , data = 0x00)#take out of reset
            if self.HwRevision == 3:
                self.FpgaRegWr(reg = _const.reg_usart_ctrl , data = 0x01)#reset 
                time.sleep(0.01)
                self.FpgaRegWr(reg = _const.reg_usart_ctrl , data = 0x00)#take out of reset
        elif (self.HsDataIfType == DATA_INTERFACE_SPW) or (self.HsDataIfType == DATA_INTERFACE_SPW_REDUN):
            #Not confirmed... still need to test, somehow clear data (not ctrl?) buffers?
            #self.SpWRstRxFifo()
            #print('This feature/requirement not yet investigated')
            pass

    def SerdesStatus(self):
        "Determine the status of the SERDES FSM"
        
        stat_serdes= self.FpgaRegRd(reg = _const.reg_serdes_dbg)
        val = stat_serdes & 0xF
        val_dict =  {1:"IDLE",
                    2 : "LINK_OFF",
                    3 : "LINK_TUNE_DELAY",
                    4 : "LINK_BIT_SLIPPING",
                    5 : "LINK_SYNCED",
                    6 : "LINK_ACTIVE",
                    7 : "LINK_BIT_SLIP_WAIT",
                    8 : "USART_CENTRE_ALIGN",
                    9 : "WAIT_DROP_CLOCK"
                    }
        print(f'SERDES link FSM is in following state...{val_dict[val]}')


    def HsIfInit(self):
        """
        Perform the appropriate clearing of buffers etc at the beginning of a data capture.
        """
        #  NOTE: this is broken into '#___GPIF actions___#' which are generic accross the various data interfaces,
        #  and '#___HS data actions___#' which will perform the appropriate interface specific actions.
        #  self.HsDataIfType is used to distinguish between which of the following to perform.

        #___GPIF actions___#
        #Put Gpif in reset
        try:
            self.FpgaRegWr(reg = _const.reg_gpif_conf , data = 0x00)
        except Exception as e:
            raise exceptions.HsdiError(f'Error resetting GPIF interface (on waxwing).\n{e}')
        if self.debug:
            GpifStatus = self.FpgaRegRd(reg = _const.reg_gpif_status)
            print('  Initial reset: Gpif : ', hex(GpifStatus))

        #Reset FX3 fifos properly
        try:
            self.Dev_Handle.resetDevice()
            self.Dev_Handle.resetDevice()
        except Exception as e:
            raise exceptions.HsdiError(f'Error clearing GPIF fifos (on FX3).\n{e}')


        #___HS data actions___#
        #Take Hs out of reset
        if self.HsDataIfType == DATA_INTERFACE_HSDIF:
            #Take HsdIfRx out of reset, this should assert RR

            #NOTE: technically this does nothing, since the HsdIf is already out of reset.

            #NOTE: why don't I reset HsdIfRx here? Because at this stage the link may already be in active mode.
            #HsdIf first needs to SYNC before it can go to active mode, putting reset here will simply put it back,
            #to try and SYNC, which it will do unsuccsessfully.
            
            #Take out of reset.
            try:
                self.FpgaRegWr(reg = _const.reg_hsd_if_rst , data = 0x00)
            except Exception as e:
                raise exceptions.HsdiError(f'Error taking HsdIf out of reset.\n{e}')
            if self.debug:
                HsdIfStatus = self.FpgaRegRd(reg = _const.reg_hsd_if_status)
                print('  HsdIf out of reset: ', hex(HsdIfStatus))


        if self.HsDataIfType == DATA_INTERFACE_USART:
            ##Put UsartRx out in reset.
            #try:
            #    self.FpgaRegWr(reg = _const.reg_usart_ctrl , data = 0x01)
            #except Exception as e:
            #    raise exceptions.HsdiError(f'Error putting Usart in reset.\n{e}')
            ##Take UsartRx out of reset.
            #try:
            #    self.FpgaRegWr(reg = _const.reg_usart_ctrl , data = 0x00)
            #except Exception as e:
            #    raise exceptions.HsdiError(f'Error taking Usart out of reset.\n{e}')
            #Enable UsartRx
            try:
                self.FpgaRegWr(reg = _const.reg_usart_ctrl , data = 0x02)
            except Exception as e:
                raise exceptions.HsdiError(f'Error setting Enable for Usart.\n{e}')

        if (self.HsDataIfType == DATA_INTERFACE_SPW) or (self.HsDataIfType == DATA_INTERFACE_SPW_REDUN):
            #Enable autostart of Spw core.
            try:
                self.FpgaRegWr(reg = _const.reg_spw_ctrl , data= 0x04)
            except Exception as e:
                raise exceptions.HsdiError(f'Error setting SpW.\n{e}')

        if (self.HsDataIfType == DATA_INTERFACE_SPW_REDUN):
            try:
                self.FpgaRegRdModWr(reg = _const.reg_spw_ctrl, val = 1, pos = 7)
            except Exception as e:
                raise exceptions.HsdiError(f'Error setting SpW.\n{e}')

        #___GPIF actions___#
        #Take Gpif out of reset, this is essentially what stalls the data link at this point.
        try:
            self.FpgaRegWr(reg = _const.reg_gpif_conf , data = 0x02)
        except Exception as e:
            raise exceptions.HsdiError(f'Error taking GPIF (on waxwing) out of reset, and into RX.\n{e}')
        if self.debug:
            GpifStatus = self.FpgaRegRd(reg = _const.reg_gpif_status)
            print('  Initial out of reset: Gpif : ', hex(GpifStatus))


    def HsIsDone(self):
        """
        Determine whether the data has finished sending. This responds differently for the various types of interaces.
        
        Return:
            done (bool): 'True' if link is finished sending data AND data has been read over USB, 'False' if not. 
        """
        #Determine status GPIF block on Waxwing 
        try:
            gpif_stat = self.FpgaRegRd(reg = _const.reg_gpif_status)
        except Exception as e:
            raise exceptions.HsdiError(f'Error determining the status if the GPIF block in Waxwing.\n{e}')           
        
        if (gpif_stat & 0x0F == 0x04):
            gpif_done = True
        else:
            gpif_done = False
        
        if self.HsDataIfType == DATA_INTERFACE_HSDIF:
            #Determine status HSDIF block on waxwing  
            try :
                hsdif_status = self.FpgaRegRd(reg = _const.reg_hsd_if_status)
                serdes_status = self.FpgaRegRd(reg = _const.reg_serdes_status)
            except Exception as e:
                raise exceptions.HsdiError(f'Error determining the HSDIF\'s status.\n{e}')
            
            if self.HwRevision == 2:
                serdes_status = 0x00
            
            #   HsdIf link done              and gpif is done sending last data.
            if (hsdif_status & 0x08 == 0x08) and (gpif_done == True) or  \
               (serdes_status & 0x4 == 0x4 ) and (gpif_done == True):
                return True
            else:
                return False
               
        if self.HsDataIfType == DATA_INTERFACE_USART:
            #Determine status usart block on Waxwing.
            try:
                usart_sigs = self.FpgaRegRd(reg = _const.reg_usart_sigs)
            except Exception as e:
                raise exceptions.HsdiError(f'Error determining the USART\'s status.\n{e}')
            
            #                Usart_Done    and   gpif is done sending last data  
            if (usart_sigs & 0x04 == 0x04) and (gpif_done == True):
                return True
            else:
                return False 

        if (self.HsDataIfType == DATA_INTERFACE_SPW) or (self.HsDataIfType == DATA_INTERFACE_SPW_REDUN):
            #We will have to communicate with the CE directly to determine this...
            #Thus, set the timeout to such a degree that it simply ends after timing out.
            return True

    def HsIfResetEnd(self):
        """
        Perform the appropriate clearing of buffers etc at the end of a data capture.
        """
        #  NOTE: this is broken into '#___GPIF actions___#' which are generic accross the various data interfaces,
        #  and '#___HS data actions___#' which will perform the appropriate interface specific actions.
        #  self.HsDataIfType is used to distinguish between which of the following to perform.

        #___GPIF actions___#
        #Put Gpif in reset
        try:
            self.FpgaRegWr(reg = _const.reg_gpif_conf , data = 0x00)
        except Exception as e:
            raise exceptions.HsdiError(f'Error resetting GPIF interface (on waxwing).\n{e}')

        #___HS data actions___#
        #Reset HS
        if self.HsDataIfType == DATA_INTERFACE_HSDIF:
            #Put HsdIfRx in reset, this should de-assert RR

            try:
                self.FpgaRegWr(reg = _const.reg_hsd_if_rst , data = 0x01)
            except Exception as e:
                raise exceptions.HsdiError(f'Error resetting HsdIf.\n{e}')

        if self.HsDataIfType == DATA_INTERFACE_USART:
            #Reset Usart, and disable.
            try:
                self.FpgaRegWr(reg = _const.reg_usart_ctrl , data = 0x01)
            except Exception as e:
                raise exceptions.HsdiError(f'Error putting Usart in reset.\n{e}')

        if (self.HsDataIfType == DATA_INTERFACE_SPW) or (self.HsDataIfType == DATA_INTERFACE_SPW_REDUN):
            #Reset the spw link. clear errors, reset and disable link
            try:
                self.FpgaRegWr(reg = _const.reg_spw_ctrl , data = 0x19)
            except Exception as e:
                raise exceptions.HsdiError(f'Error putting SpW in reset.\n{e}')   

        if (self.HsDataIfType == DATA_INTERFACE_SPW_REDUN):
            try:
                self.FpgaRegRdModWr(reg = _const.reg_spw_ctrl, val = 1, pos = 7)
            except Exception as e:
                raise exceptions.HsdiError(f'Error putting SpW in reset.\n{e}') 

        #___GPIF actions___#
        #Reset FX3 fifos again.
        try:
            self.Dev_Handle.resetDevice()
            self.Dev_Handle.resetDevice()
        except Exception as e:
            raise exceptions.HsdiError(f'Error clearing GPIF fifos (on FX3).\n{e}')

        #___HS data actions___#
        #Take HS out of reset.
        time.sleep(0.3)#Give some time for buffers to clear etc.

        if self.HsDataIfType == DATA_INTERFACE_HSDIF:
            #Take out of reset HsdIfRx
            try:
                self.FpgaRegWr(reg = _const.reg_hsd_if_rst , data = 0x00)
            except Exception as e:
                raise exceptions.HsdiError(f'Error taking HsdIf out of reset.\n{e}')
        
        if self.HsDataIfType == DATA_INTERFACE_USART:
            #Take out of reset
            try:
                self.FpgaRegWr(reg = _const.reg_usart_ctrl , data = 0x00)
            except Exception as e:
                raise exceptions.HsdiError(f'Error taking Usart out of  reset.\n{e}')
        
        if (self.HsDataIfType == DATA_INTERFACE_SPW) or (self.HsDataIfType == DATA_INTERFACE_SPW_REDUN):
            #Take out of reset, and disable 
            try:
                self.FpgaRegWr(reg = _const.reg_spw_ctrl , data = 0x01)
            except Exception as e:
                raise exceptions.HsdiError(f'Error taking SpW out of reset.\n{e}') 

        if (self.HsDataIfType == DATA_INTERFACE_SPW_REDUN):
            try:
                self.FpgaRegRdModWr(reg = _const.reg_spw_ctrl, val = 1, pos = 7)
            except Exception as e:
                raise exceptions.HsdiError(f'Error taking SpW out of reset.\n{e}') 

    def HsLinkRate(self):
        """
        Return the linkrate (i.e. bits per second which we expect coming accross the Harness from CE to EGSE). This returns the maximum
        """

        if self.HsDataIfType == DATA_INTERFACE_HSDIF:
            
            # Determine whether 1x or 2x Data lanes are being used.         
            try:
                mode = self.FpgaRegRd(reg = _const.reg_hs_mode)
            except Exception as e:
                raise exceptions.HsdiError(f'Error determining whether data interface single or double lane.\n{e}')            
            if mode & 0x4 == 0x4:#Single lane 
                ret_val = 1 * self.HsDataLaneRate * 1e6 # Single Data lane
            else:
                ret_val = 2 * self.HsDataLaneRate * 1e6 # Dual Data lanes

        if self.HsDataIfType == DATA_INTERFACE_USART:

            ret_val = 0.8 * self.UsartClkFrq * 1e6 # Singledata lane, control info encoded INTO data line, so link will be 80% effifcient (8 data bytes, 1start, 1stop bit)

        if (self.HsDataIfType == DATA_INTERFACE_SPW) or (self.HsDataIfType == DATA_INTERFACE_SPW_REDUN):            
            ret_val = self.SpWBitRate*1e6 #The max link rate possible for the spacewire (on the EGSE currently) is 100Mbps. This returns value as it is setup as. 
            #TODO: still better determine what the CE will be transmitting at.
        return ret_val

    def HsResid(self):
        """
        Read out the residual data register
        """
        #Residual/junk data
        add_val = 0#if we have recieved an odd number of data, there is 1 more byte of junk data

        #___GPIF actions___#
        #resid data is calculated by the GPIF block.
        try:
            resid_lsb = self.FpgaRegRd(reg = _const.reg_hsd_resid_data_0)
            resid_msb = self.FpgaRegRd(reg = _const.reg_hsd_resid_data_1)
        except Exception as e:
            raise exceptions.HsdiError(f'Error Determining the residual/junk data from residual data registers.\n{e}')

        #___HS data actions___#
        if self.HsDataIfType == DATA_INTERFACE_HSDIF:
            add_val = 0#Currentl we only subtract 0, since we have not incorporated the case where data may be odd.
        if self.HsDataIfType == DATA_INTERFACE_USART:
            #Read OddnEven value
            try:
                OddnEven = self.FpgaRegRd(reg = _const.reg_usart_sigs)
            except Exception as e:
                raise exceptions.HsdiError(f'Error determining the Usart sigs register value.\n{e}')
            OddnEven = OddnEven & 0x20
            add_val = OddnEven

        if (self.HsDataIfType == DATA_INTERFACE_SPW) or (self.HsDataIfType == DATA_INTERFACE_SPW_REDUN):
            add_val = 0#Likewise to HSDIF also assuming data will always be even number of bytes.

        resid = (resid_lsb + (resid_msb << 8) ) + add_val#Will either add 0 or 1.
        if self.debug:
            print('Resid_lsb: ', resid_lsb)
            print('Resid_msb: ', resid_msb)
            print('Resid total: ', resid  )
        return resid

    def setDataInterface(self, interface, UsartClk = 4):
        """ Select the type of data interface you want to use, make sure from your user manual that you indeed have access to that specific protocol.

        Arguments In:
            - interface (int): type of interface, options:
                                DATA_INTERFACE_HSDIF (Simera Sense's custom 100 / 200MBit downlink)
                                DATA_INTERFACE_USART (1xstart bit, 1x stop bit, no parity.)
                                DATA_INTERFACE_SPW   (SpaceWire)
								DATA_INTERFACE_SPW_REDUN   (Second SpaceWire)
            - UsartClk (int): frequencies (in MHz) which the Usart can be setup as. See USART_MAX_CLK_SPEED.
                              The HsdIf cannot change frequencies on the EGSE. It has a maximum frequency of 100MHz.
        """
        #Check parameters
        try:
            interface = int(interface)
        except ValueError as e:
            raise exceptions.InputError(f'interface parameter must be an integer, but {interface} was supplied.\n{e}')
        #Check that parameter
        list_HS_interfaces = [DATA_INTERFACE_HSDIF, DATA_INTERFACE_USART, DATA_INTERFACE_SPW, DATA_INTERFACE_SPW_REDUN]
        if self.HwRevision == 3:
            list_HS_interfaces = [DATA_INTERFACE_HSDIF, DATA_INTERFACE_USART, DATA_INTERFACE_SPW, DATA_INTERFACE_SPW_REDUN, DATA_INTERFACE_TPGEN]
        if interface not in list_HS_interfaces:
            raise exceptions.InputError(f'interface must be one of the following: DATA_INTERFACE_HSDIF, DATA_INTERFACE_USART, DATA_INTERFACE_SPW, DATA_INTERFACE_TPGEN (for HwRevision=3) which have integer values: {list_HS_interfaces}, instead {interface} was provided')

        if UsartClk > USART_MAX_CLK_SPEED:
            raise exceptions.InputError(f'UsartClk parameter must be less than or equal to {USART_MAX_CLK_SPEED}, instead {UsartClk} was supplied.\n{e}')


        #Update the mux on the EGSE.
        try:
            self.FpgaRegWr(_const.reg_hs_mux, interface)
        except Exception as e:
            raise exceptions.HsdiError(f'Could not set high speed data interface.\n{e}')

        #Update the object, this is what will be checked in other methods such as 'HsCapture'
        self.HsDataIfType = interface
    
        #For SpW we need to ensure that the RX is set, since this is not done elsewhere.
        if (interface == DATA_INTERFACE_SPW) or (interface == DATA_INTERFACE_SPW_REDUN):
            self.setHsMode(mode= HS_MODE_RX)

        #Update the Usart link speed, need this to calulate the timeouts required for bulk reads.
        if interface == DATA_INTERFACE_USART:
            self.UsartClkFrq = UsartClk

        #Perform the reset and out of reset required for the HsdIf due to sync requirement.
        if interface == DATA_INTERFACE_HSDIF:
            self.HsIfResetEnd()#TODO: can still refine this probably, will need to investigate.

        #Perform the resetting and out of reset action for Usart.
        if interface == DATA_INTERFACE_USART:
            self.HsIfResetEnd()

    def setHsMode(self, mode, single = False, polarity = 'rise', ddr=False, lane_rate=100):
        """
        Sets High-Speed Interface into either Transmit or Receive mode.
        Currently we can only recieve data over the EGSE (HS_MODE_RX)

        Arguments In:
            - mode (int)        : HS_MODE_RX, or HS_MODE_TX
            - single (bool)     : if True, Single Data Lane (D0) on LVDS
                                  if False (default), Dual Data lane (D0 and D1) on LVDS.                                     
            - polarity (string) : if sampling on rising edge 'rise', if sampling on falling edge 'fall' (for LVDS and USART)
            - ddr(bool)         : if True, set HSDIF into DDR mode (only applicable for SERDES implementation on HwRevision=3),
                                  if False, set HSDIF into SDR  mode (default)
            - rate (int)        : Rate of the LVDS Data Lane(s) in Mbps 
        """
        
        #Check parameters
        try:
            mode = int(mode)
        except ValueError as e:
            raise exceptions.InputError(f'mode parameter must be an integer, but {mode} was supplied.\n{e}')

        list_HS_modes = [HS_MODE_RX, HS_MODE_TX]

        if mode not in list_HS_modes:
            raise exceptions.InputError(f'mode must be one of the following: HS_MODE_RX, HS_MODE_TX, which corresponds to {list_HS_modes}, instead {mode} was supplied.')
        if (int(single) not in [0, 1]):
            raise exceptions.InputError(f'single parameter must be \'1\', \'0\', \'True\' or \'False\', instead "{single}" was supplied.')            

        #Currently always in RX mode, thus it is the only option which does't raise error.
        if mode == HS_MODE_TX:
            raise exceptions.InputError(f'The EGSE can only be used in HS_MODE_RX at the moment.')
        
        #Bit that indicates we will be using only 1x data lane.
        if single == True:
            mode = mode | 0x4

        #Bit which indicates whether sampling rising or falling edge of data
        if polarity == 'rise':
            #Clear
            mode = mode & (~0x08 & 0xFF) 
        elif polarity == 'fall':
            #Set 
            mode = mode | 0x8
        else:
            raise exceptions.InputError(f'polarity parameter must be an appropriate string.\n{e}')        
        
        if self.HwRevision == 3:
            if ddr:
                mode = mode | 0x80
            elif not ddr:
                mode = mode & (~0x80 & 0xFF)
            else:
                raise exceptions.InputError(f'Please provide boolean for ddr.\n{e}')
        
        #Write to a mode register on EGSE, not that it does not do anything at the time being.
        try:
            self.FpgaRegWr(_const.reg_hs_mode, mode)
        except Exception as e:
            raise exceptions.HsdiError(f'Could not set high speed data mode.\n{e}')

        # Update the objects
        #self.HsDataMode = mode
        self.HsDataLaneRate= lane_rate

    def HsHwSwCheck(self):
        """
        This function serves as a sanity check: is the EGSE FW in sync with the python sw.
        It checks the following:
            interface (HsdIf, Usart, SPWr)
            speed (if additional info is provided, do the speeds coincide?) #TODO: still implement this...
            mode (TX or RX)
        If this is incorrect, the setup functions were probably not performed before the HsCapture method.
        """
        #___Interface___#
        #___HsdIf___#
        if self.HsDataIfType == DATA_INTERFACE_HSDIF:

            #Check that the interfaces line up
            try:
                stat = self.FpgaRegRd(reg = _const.reg_hs_mux)
            except Exception as e:
                raise exceptions.HsdiError(f'Error determing HS MUX value status.\n{e}')
            if stat != 0x01:
                raise exceptions.HsdiError(f'Error, python object is setup for DATA_INTERFACE_HSDIF, aka {DATA_INTERFACE_HSDIF}, but physical EGSE FW is setup for interface {DICTIONARY_DATA_INTERFACE[stat]}.')

            #Check that the speeds line up
                #TODO, currently only supports 200Mbps

        #___Usart___#
        if self.HsDataIfType == DATA_INTERFACE_USART:
            #Check thta interface lines up
            try:
                stat = self.FpgaRegRd(reg = _const.reg_hs_mux)
            except Exception as e:
                raise exceptions.HsdiError(f'Error determing HS MUX value status.\n{e}')
            if stat != 0x02:
                raise exceptions.HsdiError(f'Error, python object is setup for DATA_INTERFACE_USART, aka {DATA_INTERFACE_USART}, but physical EGSE FW is setup for interface {DICTIONARY_DATA_INTERFACE[stat]}.')

            #Check speeds
                #No need, the speed cannot be changed on the EGSE FW, it is made for maximum 100MHz clk, as long as the SW has the right value, bulkread timeouts will be calculated correctly.

        #___SPWR___#
        if (self.HsDataIfType == DATA_INTERFACE_SPW) or (self.HsDataIfType == DATA_INTERFACE_SPW_REDUN):
            #Check thta interface lines up
            try:
                stat = self.FpgaRegRd(reg = _const.reg_hs_mux)
            except Exception as e:
                raise exceptions.HsdiError(f'Error determing HS MUX value status.\n{e}')
            if stat != 0x04:
                raise exceptions.HsdiError(f'Error, python object is setup for DATA_INTERFACE_USART, aka {DATA_INTERFACE_USART}, but physical EGSE FW is setup for interface {DICTIONARY_DATA_INTERFACE[stat]}.')

        #Check that the modes line up (Tx, or RX), this is generic and only needs to happen 1x
        try:
            stat = self.FpgaRegRd(reg = _const.reg_hs_mode)
        except Exception as e:
            raise exceptions.HsdiError(f'Error determing HS MODE value.\n{e}')
        if (stat&0x3) != self.HsMode:#And with 0x3 since the bottom 2 bits indicate TX vs RX, 3rd lowest bit indicates single data lane or not.
            raise exceptions.HsdiError(f'Error, python object is setup for {DICTIONARY_HS_MODE[self.HsMode]} , meanwhile EGSE FW is setup for {DICTIONARY_HS_MODE[stat]}.')


    def CalcHsTout(self, num_bytes_read):
        """
        Calculate the bulkread timout required for the specific link type.
        """
        bytes_per_sec = ((self.HsLinkRate()) / 8)
        tout_calc = int( ((num_bytes_read / bytes_per_sec) * self.usb_bulkread_timeout_ratio * 1000) + self.usb_bulkread_timeout_overhead_ms  ) # in milliseconds
        if self.debug:
            print(f'  USB Bulk Read timeout is {tout_calc} ms, for {int(num_bytes_read)} bytes to read at a linkrate of {bytes_per_sec} bytes per second.')
            print(f'  this value is valid for non-debug mode')#TODO: is this still the case???
        return tout_calc

    def GpifEgseTP(self, TestPattern = False):
        """
        Capture 1MB testpattern which is generated in the GPIF core.
        """
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 
        
        #Disable the GPIF (in reset)
        self.FpgaRegWr(reg = _const.reg_gpif_conf , data = 0x00)
        
            #Clear the GPIF Fifos (no fifos to clear)
        
        #Clear the FX3 Fifos.
        self.Dev_Handle.resetDevice()
        self.Dev_Handle.resetDevice()
        time.sleep(0.1)

        gpifStatus = self.FpgaRegRd(reg = _const.reg_gpif_status)
        print(f'GPIF status (during reset): {hex(gpifStatus)}')
        
        #Enable the GPIF Testpattern mode, set to RX mode.
        
        # TX or RX mode?
        
        self.setDataInterface(interface= DATA_INTERFACE_TPGEN)
        
        if TestPattern:
            self.FpgaRegWr(reg = _const.reg_gpif_conf , data = 0x0A)#Test pattern
        else:
            self.FpgaRegWr(reg = _const.reg_gpif_conf , data = 0x1A)#16 bit counter
        
        conf = self.FpgaRegRd(reg = _const.reg_gpif_conf)
        print(f'Gpif Config: {hex(conf)}')
        
        gpifStatus = self.FpgaRegRd(reg = _const.reg_gpif_status)
        print(f'GPIF status: {hex(gpifStatus)}')
        
        #Readout 16KB via USB call.
        try:
            data = self.Dev_Handle.bulkRead(0x81 , length = 16*1024, timeout = 1000)
            print(f'The data recieved is [first 64 bytes: {data[0:64]}')
        except usb1.USBErrorTimeout as e:
            data = e.received
            print(f'Number of bytes received: {len(data)}')
            print(f'Data: {data}')
            gpifStatus = self.FpgaRegRd(reg = _const.reg_gpif_status)
            print(f'GPIF status: {hex(gpifStatus)}')

    def HsCapture(self, length=None, filename=None, IterLength = 1024*1024, dbg = False, callback=None, callback_param=None,verbose=True):
        """
        Capture High-Speed Data to a file, or return data as a parameter.
        Provide a length if the transaction has a known length, otherwise do not provide a length.

        Arguments In:
            - length: number of bytes to capture. If left blank, an unknown amount is captured.
                     Capture stops when link goes from 'ACTIVE' to 'INACTIVE', i.e. when the transmitter has finished sending all its data.
            - filename: name of the capture file. If this is left blank, then no file is captured, instead variable is passed to user.
            - IterLength : when reading an unknown number of bytes, this will determine how many bytes we
                            read per iteration. The larger the number, the less responsive other commands (if we
                            have multiple threads), the smaller the number, the more responsive, yet less efficient the transfer rate.
                            Also note, the larger the value, the longer it will take to timeout on the LAST iteration. NOTE: IterLength must be divisible
                            by 16384.
            - dbg : boolean, if set True, will print out useful data for debugging data link.

        Return:
            - data : numpy.array.
        """
        #Parameter checking:
        #IterLength
        try:
            IterLength = int(IterLength)
        except ValueError as e:
            raise exceptions.InputError(f'IterLength parameter must be an integer, but {IterLength} was supplied.\n{e}')
        if (IterLength <= 0) or (IterLength % 16384 != 0):
            raise exceptions.InputError(f'IterLength parameter must be an integer, and a multiple of 16384, but {IterLength} was supplied.')
        #filename
        if not filename is None:
            try:
                newFile = open(filename,"wb")
            except Exception as e:
                raise exceptions.InputError(f'Cannot open file "{filename}" for writing\n{e}')

        # only do extra round when callback provided
        if callback:
            _done_final_round = False
        else:
            _done_final_round = True


        #Sanity check, that the physical EGSE and python code are in sync with what type of interface is being used.
        self.HsHwSwCheck()       
        

        #First perform the appropriate reset combination:
        self.HsIfInit()
        if dbg:
            print(' post enable')
            self.HsStatus()


        #Determine what a reasonable timeout is for this number of bytes:
        tout_calc = self.CalcHsTout(IterLength)

        #if self.debug:
        #    tout_calc = tout_calc * 2 # In Debug mode, increase the timeout
        #    print( 'HsCapture packet wise timeout ', tout_calc)

        #Determine whether link has synced or not, and whether it is active or not...
        serdes_stat = self.FpgaRegRd(reg = 0x3F)
        if dbg and self.HwRevision == 3:
        	print(f'Link active: {bool(0x2 & serdes_stat)}')
        	print(f'Link synced: {bool(0x1 & serdes_stat)}')
        
        #gpif_stat = self.FpgaRegRd(reg = _const.reg_gpif_status)
        #usart_sigs   = self.FpgaRegRd(reg = _const.reg_usart_sigs)
        #usart_status = self.FpgaRegRd(reg = _const.reg_usart_status)
        #print(f'GPIF status: {hex(gpif_stat)}')
        #print(f'USART sigs: {usart_sigs}')
        #print(f'USART status: {usart_status}')        


        #Now perform bulkreads:
        dataRx = True
        dataStitch = bytearray([])#Empty byte array
        loopCnt = 0
        while dataRx == True:
            loopCnt = loopCnt +1
            if dbg:
                print('Loop count ', loopCnt)
            try:
                with self._threadLock:
                    data = self.Dev_Handle.bulkRead(0x81 , length = IterLength, timeout = tout_calc)
            except usb1.USBErrorTimeout as e:
                #Either we have timed out (and are done recieving data) OR we have timed out because data flow is very slow in comparison to expected rate. This will be the 
                #case when a large amount of 'filtering' is applied to the data coming from the CE.
                if dbg:
                    print('  the status in last timeout')
                    self.HsStatus()
                    print('  is the link done?: ' , self.HsIsDone())
                if _done_final_round:
                    if callback or self.HsIsDone():
                        if dbg:
                            print('Bulk read timeout occurred')
                            print('Bulk read timeout time: ', tout_calc)
                            print('Data length received: ', len(e.received))
                            self.HsStatus()
                        d = e.received
                        #Now determine if there is any junk Data
                        junkData = self.HsResid()
                        if dbg:
                            print(' number junk data bytes: ', junkData)
                            print(' length timed out data is:', len(d))
                        data = d           
                        dataRx = False#Jump out of while loop
                    
                else:
                    #print("NOT  HsIsDone")
                    #stay within the loop, and if there was any data that did make it through, append it to data stitch
                    data = e.received
                    #Note, junk data should always be zero, good to check though
                    junkData = self.HsResid()
                    if dbg:
                        print(f'  timed out and continuing')

                    if callback:
                        callback(callback_param)
                        _done_final_round = True
                    else:
                        dataRx = False#Jump out of while loop


            except Exception as E:
                self.HsIfResetEnd()
                raise exceptions.HsdiError(f'Error in USB bulk read.\n{E}')

            # Check if data was received
            if 'data' not in locals():
                # No data received
                self.HsIfResetEnd()
                print(f"No Data Received.")
                return
            
            # Write to a file            
            if not filename is None:
                if dbg:
                    print("  __HsCapture: Writing to file:", filename)
                try:
                    newFile.write(data)
                except Exception as e:
                    self.HsIfResetEnd()
                    raise exceptions.HsdiError(f'Error writing to file {filename}.\n{e}')
                if verbose == True:
                    if length != None:
                        print(f"Read Out {newFile.tell():,}/{length:,} [{newFile.tell()/length*100:.1f}%]", end="\r")
                    else:
                        print(f"Read Out {newFile.tell() / (1024*1024)} MByte", end="\r")
                
            # OR just return the array
            else:
                dataStitch = dataStitch + data         
        
        #Perform appropriate trimming of junk data
        if junkData != 0:
            if not filename is None:
                sizeNewFile = newFile.tell()-junkData
                newFile.truncate(newFile.tell()-junkData)
                if verbose == True:
                    if length != None:
                        print(f"Final Percentage: [{sizeNewFile/length*100:.1f}%].                         ")
                    else:
                        print(f"File size: {sizeNewFile / (1024*1024)} MByte.                    ")
            else:
                dataStitch = dataStitch[:-junkData]

        #No need to trim data, but update the printout to accurately present the data
        else:
            if not filename is None:
                if verbose == True:
                    if length != None:
                        print('a')
                        print(f"Final Percentage: [{newFile.tell()/length*100:.1f}%].                        ")
                    else:
                        print(f"File size: {newFile.tell() / (1024*1024)} MByte.                    ")
            
        if dbg:
            print('Pre reset End')
            self.HsStatus()
            
        # Perform the post-capture resets
        self.HsIfResetEnd()

        # Close file ## ##
        if not filename is None:
            print()
            if self.SpWDebug:
                print("  __HsCapture: Closing file:", filename)
            newFile.close()
        # OR just return the array
        else:
            #Convert to numpy.array
            data_truncated_np_array = numpy.frombuffer(buffer = dataStitch, dtype = numpy.uint8)
            return data_truncated_np_array

    ## ========================================================================================= ##
    ##########______________ Space Wire DATA, Telecommands, Telemetry____________________##########
    ### A spacewire (SpW) core in instantiated on the EGSE. It allows us to download data at a highspeed 
    ### from the CE. This uses the following Logical Address: LA_DATA. Furthermore writes and reads 
    ### can be initiated. Read data coming in has logical address: LA_RD
    ### Error/Exception Classes:
    ###     SpWError(Error)
    ###         Specific SpW control to the core, i.e. establishing a link etc.
    ###     SpWDataError(DataInterfaceError)
    ###         any high speed data downlink errors.
    ###     SpWWrError(ControlInterfaceError)
    ###         any errors relating to writing 
    ###     SpWRdError  (ControlInterfaceError)
    ###         any errors relating to reading
    ###
    ###Some specific SpW helper methods, these methods are for the SpW core in general.
    def SpWReset(self):
        """
        Clear errors and reset SpW core
        """
        if (self.HsDataIfType == DATA_INTERFACE_SPW) or (self.HsDataIfType == DATA_INTERFACE_SPW_REDUN):
            try:
                self.FpgaRegWr(reg = _const.reg_spw_ctrl, data = 0x19)
            except Exception as e:
                raise exceptions.SpWResetError()
                
        if (self.HsDataIfType == DATA_INTERFACE_SPW_REDUN):
            try:
                self.FpgaRegRdModWr(reg = _const.reg_spw_ctrl, val = 1, pos = 7)
            except Exception as e:
                raise exceptions.SpWResetError()
        
    def SpWAutoStart(self, enable = 1):
        """
        Perform autostart , also enable by default, otherwise disable
        """
        if (self.HsDataIfType == DATA_INTERFACE_SPW):
            if enable not in [0,1]:
                raise exceptions.InputError(f'Must be either {1} or {0}.')                
            reg_val = 0x04 | int(not(enable))        
            #Take out of reset, autostart, and make enable/disable
            try:
                self.FpgaRegWr(_const.reg_spw_ctrl, reg_val)
            except Exception as e:
                raise exceptions.SpWAutoStartError()
                
        if (self.HsDataIfType == DATA_INTERFACE_SPW_REDUN):
            if enable not in [0,1]:
                raise exceptions.InputError(f'Must be either {1} or {0}.')                
            reg_val = 0x84 | int(not(enable))        
            #Take out of reset, autostart, and make enable/disable
            try:
                self.FpgaRegWr(_const.reg_spw_ctrl, reg_val)
            except Exception as e:
                raise exceptions.SpWAutoStartError()
    
    def SpWStatus(self, show=True):
        """
        Print status, either print to screen, or return (if show == False)
        """
        if show not in [True, False]:
            raise exceptions.InputError(f'Must be either True or False.')                
        
        try:               
            stat = self.FpgaRegRd(reg = _const.reg_spw_stat)
        except Exception as e:
            raise exceptions.SpWStatusError()
        
        if show == True:
            print(f'            SpW Status: {hex(stat)}, (Connected = {bool(stat&0x04)})')
            # Some logic to show which errors occured.
            if stat & 0x08 == 0x08:
                print(f'            CREDIT ERROR occured, triggers a link reset')
            if stat & 0x10 == 0x10:
                print(f'            PARITY ERROR occured, triggers a link reset')            
            if stat & 0x20 == 0x20:
                print(f'            DISCONNECTION occured, triggers a link reset')            
            if stat & 0x40 == 0x40:
                print(f'            ESCAPE ERROR occured, triggers a link reset')            
            
        else :
            return stat
    
    def SpWTxConfig200(self):
        """
        Determine whether the EGSE FW is setup to do max Tx Freq of 100, or 200 Mbps. 
        """
        try:
            stat = self.FpgaRegRd(reg = _const.reg_spw_stat)
        except Exception as e:
            raise exceptions.SpWError(f'Could not determine the maximum tx rate of SpW link.\n{e}')
        if (stat & 0x80) == 0x80:
            return True 
        else:
            return False 
    
    def SpWClrError(self):
        """
        Clear the errors which have been latched.
        """
        try:
            self.FpgaRegRdModWr(reg = _const.reg_spw_ctrl, val = 1, pos = 4)#Clear the errors
            self.FpgaRegRdModWr(reg = _const.reg_spw_ctrl, val = 0, pos = 4)#Take out of reset.
        except Exception as e:
            raise exceptions.SpWError(f'Could not set or clear the ClrError ctrl bit.\n{e}')        
        
    def SpWIsError(self):
        """
        Determine if there are any Errors, raise suitable exception for corresponding error.
        """
        #Determine status 
        statSpw = self.SpWStatus(False)
        
        #ErrEsc     ErrDisc     ErrPar     ErrCred
        
        #0001 : ErrCred 
        if (statSpw & 0x78) == 0x08:
            raise exceptions.SpWErrCredError()
        #0010 : ErrPar
        if (statSpw & 0x78) == 0x10:
            raise exceptions.SpWErrParError()
            
        #0011 : ErrPar ErrCred
        if (statSpw & 0x78) == 0x18:
            raise exceptions.SpWErrParCredError()                

        #0100 : ErrDisc
        if (statSpw & 0x78) == 0x20:
            raise exceptions.SpWErrDiscError()                    
            
        #0101 : ErrDisc ErrCred
        if (statSpw & 0x78) == 0x28:
            raise exceptions.SpWErrDiscCredError()                                
        
        #0110 : ErrDisc ErrPar
        if (statSpw & 0x78) == 0x30:
            raise exceptions.SpWErrDiscParError()                                        
        
        #0111 : ErrDisc ErrPar ErrCred
        if (statSpw & 0x78) == 0x38:
            raise exceptions.SpWErrDiscParCredError()                                                
            
        #1000 ErrEsc
        if (statSpw & 0x78) ==  0x40:
            raise exceptions.SpWErrEscError()
            
        #1001 ErrEsc ErrCred
        if (statSpw & 0x78) ==  0x48:
            raise exceptions.SpWErrEscCredError()
            
        #1010 ErrEsc ErrPar
        if (statSpw & 0x78) ==  0x50:
            raise exceptions.SpWErrEscParError()            
            
        #1011 ErrEsc ErrPar ErrCred
        if (statSpw & 0x78) == 0x58:
            raise exceptions.SpWErrEscParCredError()            
            
        #1100 ErrEsc ErrDisc 
        if (statSpw & 0x78) == 0x60:  
            raise exceptions.SpWErrEscDiscError()            
            
        #1101 ErrEsc ErrDisc ErrCred
        if (statSpw & 0x78) == 0x64:
            raise exceptions.SpWErrEscDiscCredError()            
            
        #1110 ErrEsc ErrDisc ErrPar
        if (statSpw & 0x78) ==  0x70:
            raise exceptions.SpWErrEscDiscParError()            
            
        #1111 ErrEsc ErrDisc ErrPar ErrCred
        if (statSpw & 0x78) ==  0x78:
            raise exceptions.SpWErrEscDiscParCredError()                        
        
    #### Helper methods -> resetting each sub-unit if FW, note all of these units are reset when SpWReset() is called.
    def SpWRstTcFifo(self):
        """
        Reset the TcFifo
        """
        try:
            self.FpgaRegRdModWr(reg = _const.reg_spw_tmtc_ctrl, val = 1, pos = 1)#Pulse reset
        except Exception as e:
            raise exceptions.SpWWrError(f'Could not reset TcFifo.\n{e}')                
            
    def SpWRstTmFifo(self):
        """
        Reset TmFifo
        """        
        try:
            self.FpgaRegRdModWr(reg = _const.reg_spw_tmtc_ctrl, val = 1, pos = 3)#Pulse reset
        except Exception as e:
            raise exceptions.SpWRdError(f'Could not reset TmFifo.\n{e}')                        
        
    def SpWRstTxFiller(self):
        """
        Reset TxFiller FSM, this handles the TC fifo to TxBuffer transactions.
        """
        self.SpWRstTcFifo()
        
    def SpWRstSpwFifoFiller(self):
        """
        Reset FifoFiller, the FSM which handles routing incoming data.
        """
        try:
            self.FpgaRegRdModWr(reg = _const.reg_spw_tmtc_ctrl, val = 1, pos = 5)#Pulse reset
        except Exception as e:
            raise exceptions.SpWDataError(f'Could not reset SpWFifoFiller.\n{e}')                                
        
    def SpWRstRxFifo(self):
        """
        Reset the RxFifo, the fifo which is connected to GPIF interface.
        """
        try:
            self.FpgaRegRdModWr(reg = _const.reg_spw_data_ctrl, val = 1, pos = 1)#Pulse reset
        except Exception as e:
            raise exceptions.SpWDataError(f'Could not reset RxFifo.\n{e}')                                        

        
    #### TC helper methods: 
    def SpWRdWrStatus(self):
        """
        Read and print out the status of TmTc of EGSE.
        """        
        stat = self.FpgaRegRd(reg = _const.reg_spw_tc_status)        
        
        print(f'  __SpW: TC (sending data from EGSE onto link')
        print(f'           TC_busy\t {stat & 0x01 == 0x01} ')
        print(f'           TC_done\t {stat & 0x02 == 0x02} ')
        print(f'           TcFifoEmpty\t {stat & 0x04 == 0x04} ')
        print(f'           TcFifoFull\t {stat & 0x08 == 0x08} ')
        
        stat = self.FpgaRegRd(reg = _const.reg_spw_tm_status)
        
        print(f'  __SpW: TM (reading data from link onto EGSE')
        print(f'           TM_busy\t {stat & 0x10 == 0x10} ')
        print(f'           TM_done\t {stat & 0x20 == 0x20} ')
        print(f'           TmFifoEmpty\t {stat & 0x40 == 0x40} ')
        print(f'           TmFifoFull\t {stat & 0x80 == 0x80} ')
        
    def SpWIsWrDone(self):
        """
        Determine if the Telecommand was indeed sent (out into the TxFifo)
        """
        try:
            stat = self.FpgaRegRd(reg = _const.reg_spw_tc_status)
        except Exception as e:
            raise exceptions.SpWWrError(f' Could not determine whether TC is done or not. \n {e}')        
        
        if stat & 0x02 == 0x02:
            return True 
        else:         
            return False 


    def SpWWr(self, data):
        """
        Send data across SpW link. 
        
        Arguments In:
            data (list of bytes): the data which is sent accross the SpW link. This does not have any intelligence,
            it simply forwards whatever it gets from the higher levels which call this function. Thus you will need to include
            Logical Adress, and routing bytes if required in the beginning of the list, followed by your actual data.
       
        """
        #Parameter checking 
        #Check if this is a list 
        if isinstance(data, list) == False: 
            raise exceptions.InputError(f'data must be a list of bytes.') 
        #Check length, is it larger than the fifo can handle:
        if len(data) > 2047:#Note, this is 2047 since the last byte (which is the EOP byte still needs to be written, and it can't if Txfifo (which is 2048 deep is full of data).
            raise exceptions.InputError(f'data is longer than 2047, which is the max that the SpW TxFifo can take at the moment.') 
        #Check size (0-255) and int.
        for i in range(len(data)):
            try:
                data[i] = int(data[i])
            except Exception: 
                raise exceptions.InputError(f'data must be a byte, but {data[i]} was supplied.')
            if (data[i] > 255) or (data[i] < 0):
                raise exceptions.InputError(f'data must be a byte, within range 0 to 255, however {data[i]} was supplied.')
        
        #Reset TxFiller and TcFifo
        try:
            self.FpgaRegRdModWr(reg = _const.reg_spw_tmtc_ctrl, pos = 1, val = 1)#Pulses the signal
        except Exception as e:
            raise exceptions.SpWWrError(f'Could not reset the TxFiller and TcFifo. \n {e}')
            
        
        len_data = len(data)
        len_lo = len_data & 0x00FF
        len_hi = (len_data & 0xFF00 ) >> 8
        if self.SpWDebug:
            print (f'  __SpW: Length written to register')
            print (f'           len_lo: {hex(len_lo)} ')
            print (f'           len_hi: {hex(len_hi)} ')
        
        #How many bytes to send 
        try:
            self.FpgaRegWr(reg = _const.reg_spw_tc_len_lo, data = len_lo )
            self.FpgaRegWr(reg = _const.reg_spw_tc_len_hi, data = len_hi )
        except Exception as e:
            raise exceptions.SpWWrError(f' Could not write number of bytes (length) that we want to send. \n {e}')                

        #Clear error flag and determine whether there was any error after data was sent.
        self.SpWClrError()
        if self.SpWDebug:
            print(f'  __SpW: Before sending data')
            self.SpWStatus()
        
        #Send data data to the TcFifo 
        try:
            self.FpgaRegWr(reg = _const.reg_spw_tmtc_fifo, data = data )
        except Exception as e:
            raise exceptions.SpWWrError(f' Could not send the data to the TcFifo. \n {e}')                
        
        #Kick off transaction.
        try:
            self.FpgaRegRdModWr(reg = _const.reg_spw_tmtc_ctrl, pos = 0, val = 1)#Pulses the signal
        except Exception as e:
            raise exceptions.SpWWrError(f' Could not kickoff write. \n {e}')   
        
        #Raise error if data is not sent within a certain amount of time, this will be because TxFifo is asserting full (if SpW is already setup coorectly.)
        flag = False
        t_curr = time.time()
        t_timeout = t_curr + self.SpWTcSendTimeout_s
        while flag == False:
            flag = self.SpWIsWrDone()            
            t_curr = time.time()
            if t_curr > t_timeout :
                raise exceptions.SpWWrTimeoutError(f'Either SpW is not initialised, or the TxFifo is full, or we are sending way to much data. Timeout val is: {self.SpWTcSendTimeout_s} seconds\n')
            #time.sleep(0.001)#Sleep for 1 ms

        if self.SpWDebug:
            print(f'  __SpW: after sending data')
            self.SpWStatus()
           
        #Check if any errors occurred... #TODO: do this cleaner perhaps
        #self.SpWIsError()
        
    
    ### Read SpW -> this is specifically the slow, packet based reading.
    def SpWRd(self, tout = 0.2):
        """
        Read data which arrived over the SpW link. This will read 1x packet at a time. Max packet length 2048 bytes.
        This max length determined by TmFifo in Waxwing which does burst reads via the FX3.
        
        Arguments In:
            - tout (float) the amount of time to wait before timing out in seconds. Therefore if we timeout,
                           either the first byte arrived has incorrect logical address, or no data arrived at all.
                           A reset of the SpW core is recommended (as data may be stuck in SpW core, or the data 
                           is partially read out, and thus also needs to be reset.
        
        Return
            - data (list of bytes), contains all the data which was read over SpW link. Note logical address and EEP/EOP are
                                    not present in this data.
            - EEP (boolean) True if last byte EEP (Error End of Packet), else False.
        """
        #Parameter checking
        try:
            tout = float(tout)
        except ValueError as e:
            raise exceptions.InputError(f'tout parameter must be a float, but {tout} was supplied.\n{e}')        
        
        #Polling loop -> check if any data arrives on RxBuffer within time, and read it out.
        flag = False
        t_curr = time.time()
        t_timeout = t_curr + tout
        while flag == False:
            #Pulse TmReadEn
            try:
                self.FpgaRegRdModWr(reg = _const.reg_spw_tmtc_ctrl , val =1, pos=4)            
            except Exception as e:
                raise exceptions.SpWRdError(f'Could not pulse the read enable to start the read for SpWRd().\n{e}')                        
            
            #Determine status
            try:            
                stat = self.FpgaRegRd(reg = _const.reg_spw_tm_status )
            except Exception as e:
                raise exceptions.SpWRdError(f'Could not determine the status of the SpWRd().\n{e}')                        
            
            if stat &  0x20 == 0x20:#Is the data done reading?
                flag = True 
                EEP = ( stat & 0x08 == 0x08)#Determine whether a EEP or a EOP occurred
            t_curr = time.time()
            if t_curr > t_timeout :
                raise exceptions.SpWRdTimeoutError(f'Read did not finish within {tout} seconds of initiating read.')
            #time.sleep(0.001)#Sleep for 1 ms
        
        #Determine the amount of bytes that were recieved.
        try:
            len_lo = self.FpgaRegRd(reg = _const.reg_spw_rd_len_lo )
            len_hi = self.FpgaRegRd(reg = _const.reg_spw_rd_len_hi )
        except Exception as e:
            raise exceptions.SpWRdError(f'Could not determine the number of bytes read in SpWRd().\n{e}')                        
        lenRd = len_lo + (len_hi << 8)
        if self.SpWDebug:
            print(f'  __SpW: num bytes to read over SpW is {lenRd} bytes..')
        
        #Perform readout of TmFifo, reading the correct amount of bytes.
        try:
            data = self.FpgaRegRd(reg = _const.reg_spw_tmtc_fifo, length = lenRd)
        except Exception as e:
            raise exceptions.SpWRdError(f'Could not read the {lenRd} bytes of data out of TmFifo in SpWRd().\n{e}')                        
                
        #Pulse Tm_RdOutDone flag 
        try:
            self.FpgaRegRdModWr(reg = _const.reg_spw_tmtc_ctrl, val = 1, pos=2)
        except Exception as e:
            raise exceptions.SpWRdError(f'Could not pulse the Tm_RdOutDone flag in SpWRd().\n{e}')                        
    
        if self.SpWDebug:            
            print(f'  __SpW: SpWRd Error End of Packet (EEP): {EEP}')
    
        #Check if any errors occurred... #TODO: do this cleaner perhaps
        self.SpWIsError()
    
        return data , EEP
    
    
    ### Data Helper functions
    def SpWIsCaptureDone(self):
        """
        Determine whether we are finished with recieveing data over SpW over the fast DATA link.
        """
        try:
            stat = self.FpgaRegRd(reg = _const.reg_spw_data_status)
        except Exception as e:
            raise exceptions.SpWDataError(f' Could not read the the SpW status register  \n {e}')        
        
        #Determine if a Timeout ocurred mid-packet, this will mean that mid-packet data simply stopped coming in.
        if (stat & 0x01) == 0x01:
            raise exceptions.SpWDataTimedOutMidPacket()
                
        if (stat & 0x04) == 0x04:
            return True
        else :
            return False

    def SpWIsCaptureOdd(self):
        """
        If an odd number of bytes is captured, we need to trim the last valid data byte (it is also junk).
        This is since the GPIF fifo is 8bit in 16bit out.
        """
        try:
            stat = self.FpgaRegRd(reg = _const.reg_spw_data_status)
        except Exception as e:
            raise exceptions.SpWDataError(f' Could not read the the SpW status register  \n {e}')                
        
        if (stat & 0x08) == 0x08:
            return True 
        else: 
            return False
        
    def SpWConfig(self, LaRd=None, LaData=None, TxBitRateMbps=None, DataOnly=None, Clear=False):
        """
        Configure the Spacewire settings, to be used by the SpWOpen function.
        Does not Establish a link.
        Only sets the parameters that are provided.
        """
        if Clear:
            # Clear all of the config fields
            self.SpWLaRd = None
            self.SpWLaData = None
            self.SpWTxMbaud = 0
            self.SpwDataOnly = False
        else:
            # Set the fields using the supplied parameters
            if LaRd != None:          self.SpWLaRd = LaRd
            if LaData != None:        self.SpWLaData = LaData
            if TxBitRateMbps != None: self.SpWTxMbaud = TxBitRateMbps
            if DataOnly != None:      self.SpwDataOnly = DataOnly
    
    def SpWOpen(self, LaRd=None, LaData=None, TxBitRateMbps=None, DataOnly=None):
        """
        The EGSE supports 3 types of operations on the SpW bus.
            -> high speed data reading via the USB bulk transfers, 
               this is referred to as 'Capture' or 'Data Capture' or 'DATA'
            -> lower speed data reading, one packet at a time, referred to 
               as 'SpwRd', 'Read' or 'TM'
            -> lower speed writing, this is 1x packet at a time, this is referred
               to as 'SpWWr', 'Write' or 'TC'
            -> data only mode will only allow the High speed data link, it therefore ignores both 
               LaRd and LaData, expects no LA byte to be sent, and routes everything through high-speed link
        
        Open the SpW link and prepare EGSE for Capture, Read and Write.
        
        Arguments in: 
            -LaRd   (int) logical address of this EGSE's Read node, 0 <= LaRd <= 255
            -LaData (int) logical address of this EGSE's High speed data Capture node, 0 <= LaData <= 255 
            -TxBitRateMbps (int) what speed will the reciever be recieving at. Max speed is 100Mbps. Valid options
                             are 100/n , where n >1. In turn the transmitter will also be setup to that speed.
                             It is assumed that the TxBitRate is the same as the RxBitRate.
        """
        # Override Parameters
        if LaRd == None:          LaRd = self.SpWLaRd
        if LaData == None:        LaData = self.SpWLaData
        if TxBitRateMbps == None: TxBitRateMbps = self.SpWTxMbaud
        if DataOnly == None:      DataOnly = self.SpwDataOnly
        
        #Basic Parameter check
        #LaRd
        if LaRd!= None:
            try:
                LaRd = int(LaRd)
            except ValueError as e:
                raise exceptions.InputError(f'LaRd parameter must be an integer, but {LaRd} was supplied.\n{e}')        
            if (LaRd > 255) or (LaRd < 0): 
                raise exceptions.InputError(f'0 <= LaRd <=255, but LaRd of {LaRd} was supplied.')                 
        #LaData
        if LaData != None:
            try:
                LaData = int(LaData)
            except ValueError as e:
                raise exceptions.InputError(f'LaData parameter must be an integer, but {LaData} was supplied.\n{e}')        
            if (LaData > 255) or (LaData < 0): 
                raise exceptions.InputError(f'0 <= LaData <=255, but LaData of {LaData} was supplied.')                         
        #TxBitRateMbps
        try:
            TxBitRateMbps = int(TxBitRateMbps)
        except ValueError as e:
            raise exceptions.InputError(f'TxBitRateMbps parameter must be an integer, but {TxBitRateMbps} was supplied.')                    
        if TxBitRateMbps > self.SpWMaxBitRate:
            raise exceptions.InputError(f'TxBitRateMbps parameter may not be larger than 200, instead {TxBitRateMbps} was supplied.')                    

        
        #________________Initialise the SPW link_________________#
        
        if self.SpWDebug:
            print (f'  __SpW: Status pre-reset')
            self.SpWStatus()        

        #perform initial system reset of SpW, leave in reset right till last step.
        try: 
            self.SpWReset()
        except Exception as e:
            raise exceptions.SpWResetError(f'\n{e}')

        #Set the tx speed                 
        txDivCnt = self.SpWMaxBitRate//TxBitRateMbps - 1                      
        TxBitRateMbps_set = self.SpWMaxBitRate/(txDivCnt + 1)
        if self.SpWDebug:
            print(f'  __SpW: the true TxBitRate: {TxBitRateMbps_set}, txDivCount: {txDivCnt}')
        try:
            self.FpgaRegWr(reg = _const.reg_spw_tx_div_cnt , data = txDivCnt)
        except Exception as e:
            raise exceptions.SpWTxLinkRateError()
            
        if self.SpWDebug:
            print (f'  __SpW: Status post-reset')
            self.SpWStatus()
        #______________________DATA________________________# 

        #Update the link rate (this is useed for calculating timeouts.
        self.SpWBitRate = TxBitRateMbps_set
            
        #Put GPIF in reset
        try:
            self.FpgaRegWr(reg = _const.reg_gpif_conf , data = 0x00)
        except Exception as e:
            raise exceptions.SpWDataError(f'Error resetting GPIF interface (on waxwing).\n{e}')        
        
        #Reset FX3 fifos properly
        try:
            self.Dev_Handle.resetDevice()
            self.Dev_Handle.resetDevice()
        except Exception as e:
            raise exceptions.SpWDataError(f'Error clearing GPIF fifos (on FX3).\n{e}')        

        #  Logical address Data logic  #
        #Data only, so we need to set to 0x00
        if DataOnly:
            LaData = 0x00#When set to zero, all data is read out via high-speed link, and we do not interpret LA byte,
                         #but rather consider it as data.
            self.SpWLaData = LaData#Update the class variable.
        #Not data only mode
        else:
            #We were provided with a valid logical address 
            if LaData != None:
                if LaData == 0x00:
                    raise exceptions.SpWDataError(f'You cannot set LaData = 0x00 when not in DataOnly mode. \n{e}')
            else: 
                LaData = 0xFF#logical address needs to be set to something that is NOT = 0x00, otherwise all packets will be forwarded to GPIF.
                self.SpWLaData = LaData#Update the class variable.
        #Perform actual setting on FPGA.       
        try:
            self.FpgaRegWr(reg = _const.reg_spw_data_la , data = LaData)
        except Exception as e:
            raise exceptions.SpWRdError(f'Error setting the Logical address of this node to {hex(LaData) }.\n{e}')                

        #______________________Ctrl________________________# 
        #  Logical address read  #
        #We have a valid logical address.
        if LaRd != None:
            if DataOnly == True:
                if self.SpWDebug:
                    print(f'It technically makes no sense setting LaRd to anything when DataOnly is True.\n')
        #Have no relevant logical address, set it to zero, since this register will be set to something, however it will have no impact.
        else:
            #Set the Logical Address of this node, even though it is not used.
            LaRd = 0x00
            self.SpWLaRd = LaRd#Update the class variable.
        #Perform actual setting on FPGA.
        try:
            self.FpgaRegWr(reg = _const.reg_spw_rd_la , data = LaRd)
        except Exception as e:
            raise exceptions.SpWRdError(f'Error setting the Logical address of this node to {hex(LaRd) }.\n{e}')                        
        
        #Reset the TmFifo 
        try:
            self.FpgaRegRdModWr(reg = _const.reg_spw_tmtc_ctrl , val = 1, pos = 3)
        except Exception as e:
            raise exceptions.SpWRdError(f'Error clearing the TmFifo (the fifo that accumulates all the data for logical address {hex(LaRd) }.\n{e}')                        
            
        #Reset the SpwFifoFiller FSM - this is the FSM that handles the arbitration between routing nodes TM and DATA
        try:
            self.FpgaRegRdModWr(reg = _const.reg_spw_tmtc_ctrl , val = 1, pos = 5)
        except Exception as e:
            raise exceptions.SpWRdError(f'Error reseting SpWFifoFiller.\n{e}')                                
        
        #________________AutoStart SPW link_________________#
        #Auto Enable SpW core (also take out of Reset)
        self.SpWAutoStart(enable = 1)
        
        time.sleep(0.3)
        #Check the status
        statSpW = self.SpWStatus(False)
        if (statSpW & 0x04) == 0x04:#Link is running       
            if self.SpWDebug:
                print(f'  __SpW: link is running!')
        
        #    print(f'    ______________status at opening______________')        
        #After opening the SpW link, were what is the status?        
        if self.SpWDebug:
            print(f'  __SpW: Status after Opening SpW link:')
            self.SpWStatus()
        #Check if any errors occured after setting up link, this should raise error if error is present in core.
        #self.SpWIsError()
        
        # Clear EGSE's RxNodeFifo
        self.SpWClrRxNodeFifo()
        
        # Drop any invalid received packets or packets with incorrect logical address.
        # Has no effect in Data Only mode.
        self.SpWAutoDropPkts()

    def SpWCapture(self, length=None, filename=None, IterLength = 1024*1024, TimeoutFw = 500):
        """
        Capture data over the DATA SpW link, either to a file, or return as a parameter.
        Do not provide a length, we read until timeout occurs.

        Arguments In:
            - filename: name of the capture file. If this is left blank, then no file is captured, instead variable is passed to user.
            - IterLength : when reading an unknown number of bytes, this will determine how many bytes of data we read over 1x USB Bulk transfer. 
                            The larger the number, the less responsive other commands (if we
                            have multiple threads), the smaller the number, the more responsive, yet less efficient the transfer rate.
                            Also note, the larger the value, the longer it will take to timeout on the LAST iteration. NOTE: IterLength must be divisible
                            by 16384.
            - TimeoutFw (int) number of milliseconds which the Waxwing (FPGA on EGSE) waits after receiving any data byte for this node before it times-out. This timeout will 
                            then indicate an end of data to be read out, and terminate this capture. 
                                    TODO: determine what are the max, min limits. TODO implement on FPGA...
                                    TODO: implement a done flag after timeout
                                    TODO: add this to HsIsDone()
                                                                                                                                                    

        Return:
            - data : numpy.array.
        """
        #Parameter checking:

        #IterLength
        try:
            IterLength = int(IterLength)
        except ValueError as e:
            raise exceptions.InputError(f'IterLength parameter must be an integer, but {IterLength} was supplied.\n{e}')
        if (IterLength <= 0) or (IterLength % 16384 != 0):
            raise exceptions.InputError(f'IterLength parameter must be an integer, and a multiple of 16384, but {IterLength} was supplied.')
        #filename
        if not filename is None:
            try:
                newFile = open(filename,"wb")
            except Exception as e:
                raise exceptions.InputError(f'Cannot open file "{filename}" for writing\n{e}')
        #timeout 
        try: 
            TimeoutFw  = int(TimeoutFw)
        except ValueError as e:
            raise exceptions.InputError(f'TimeoutFw parameter must be an integer, but {TimeoutFw} was supplied.\n{e}')            
        if TimeoutFw > ((255*0.00524)*1000) or TimeoutFw < (0.00525 * 1000):
            raise exceptions.InputError(f'TimeoutFw parameter must be larger than {0.00525 * 1000} and less than {(255*0.00524)*1000}, but {TimeoutFw} was supplied.\n{e}')        

        #______________Capture an unknown lenght of data._________________
        
        #Determine what a reasonable timeout is for this number of bytes:        
            #This is timeout if the link is running at full tilt, therefore an optimistic timeout.
            #This is what the python uses for it's bulkread iterations.
        timeout_usb = self.CalcHsTout(IterLength)

        # Ensure that the FW timeout is less than the USB timeout (with 300ms margin)
        if (TimeoutFw) > (timeout_usb-300):
            timeout_usb = timeout_usb + 301

        #Set the timout on the waxwing, a 8bit value between 1 and 255
            #This is the time we wait on waxwing, if no data arrives within 
            #this time, link is considered finished transmitting data to this node.
            #This value is written to the waxwing register.
        timeout_waxwing = int((TimeoutFw)/(1000*0.00524288))
        try:
            self.FpgaRegWr(reg = _const.reg_spw_count_tout , data = timeout_waxwing)
        except Exception as e:
            raise exceptions.SpWDataError(f'Could not set the data timeout in the firmware.\n{e}')        
       
        if self.SpWDebug:
            print(f'  __SpW Capture: the USB bulk read packet wise timeout {timeout_usb} ms')
            print(f'  __SpW Capture: the Waxwing bulkread packet timeout reg_write  {timeout_waxwing}')

        #Take GPIF out of reset, and enable it. Up till this point data may have filled up the SpW core fifos, but the FifoFiller will not start until GPIF is 'ready'
        try:
            self.FpgaRegWr(reg = _const.reg_gpif_conf , data = 0x02)
        except Exception as e:
            raise exceptions.SpWDataError(f'Error taking GPIF (on waxwing) out of reset, and into RX.\n{e}')
        if self.SpWDebug:
            GpifStatus = self.FpgaRegRd(reg = _const.reg_gpif_status)
            print('  __SpW Capture: Initial out of reset: Gpif : ', hex(GpifStatus))        

        ###############DEBGUG##############
        if self.SpWDebug:
            print('________________Pre read___________________')
            self.HsStatus(True)

        # Check if SpW Link is Established
        statSpW = self.SpWStatus(False)
        if (statSpW & 0x04) == 0x04: 
            # Link is running/established            
            self.SpWClrError() # Clear any old errors
        else:
            raise exceptions.SpWError('Cannot Capture, as SpaceWire Link is not Established')            

        #Now perform bulkreads:
        dataRx = True
        dataStitch = bytearray([])#Empty byte array
        loopCnt = 0
        while dataRx == True:
            loopCnt = loopCnt +1
            if self.SpWDebug:
                print('  __SpW Capture: Loop count ', loopCnt)
                print(f'Rsidual data: {self.HsResid()}')
                print(f'IS capture Done: {self.SpWIsCaptureDone()}')
            try:
                with self._threadLock:
                    data = self.Dev_Handle.bulkRead(0x81 , length = IterLength, timeout = timeout_usb)
            except usb1.USBErrorTimeout as e:
                # Either we have timed out (and are done recieving data) OR we have timed out because data flow is very slow in comparison to expected rate. This will be the 
                # case when a large amount of 'filtering' is applied to the data coming from the CE. 
                # Note, when a timeout on the Waxwing takes place, it asserts a done flag, and can be read via SpWIsCaptureDone(). The assumption is that the CE will have no more data left to send.                
                if self.SpWDebug:
                    print('  __SpW Capture: the status in last timeout')
                    self.HsStatus(True)
                    print('  __SpW Capture: is the link done?: ' , self.SpWIsCaptureDone())
                if self.SpWIsCaptureDone():
                    if self.SpWDebug:
                        print('  __SpW Capture: Bulk read timeout occurred')
                        print('  __SpW Capture: Bulk read timeout time: ', timeout_usb)
                        print('  __SpW Capture: FW timeout time: ', TimeoutFw)
                        print('  __SpW Capture: Data length received: ', len(e.received))
                        self.HsStatus(True)
                    d = e.received
                    # Now determine if there is any junk Data
                    junkData = self.HsResid()
                    if self.SpWDebug:
                        print('  __SpW Capture: number junk data bytes: ', junkData)
                        print('  __SpW Capture: length timed out data is:', len(d))
                    data = d           
                    dataRx = False # Jump out of while loop
                    
                else:
                    # Stay within the loop, and if there was any data that did make it through, append it to data stitch
                    # This is in the case where data is coming through slowly data 
                    data = e.received
                    # Note, junk data should always be zero, good to check though
                    junkData = self.HsResid()
                    if junkData != 0:
                        raise exceptions.SpWDataError(f'Error in USB bulk read - we get junkData value of {junkData} when we should get {0}.\n')
                    
                    if self.SpWDebug:
                        print(f'  __SpW Capture: timed out and continuing')
            
            # Any issue which the USB BULK read has.
            except Exception as E:
                raise exceptions.SpWDataError(f'Error in USB bulk read.\n{E}')
            
            # Write to a file
            if not filename is None:
                if self.SpWDebug:
                    print("  __SpW Capture: Writing to file:", filename)
                try:
                    newFile.write(data)
                except Exception as e:
                    raise exceptions.SpWDataError(f'Error writing to file {filename}.\n{e}')
                print(f"\rRead Out {newFile.tell():,}/{length:,} [{newFile.tell()/length*100:.1f}%]", end="")
            # OR just return the array
            else:
                dataStitch = dataStitch + data

        
        # Perform appropriate trimming of junk data
        if junkData != 0: # Perfect boudary, same as IterLength
            if not filename is None:                
                if self.SpWIsCaptureOdd():
                    # Account for odd/even number of bytes received.
                    newFile.truncate(newFile.tell()-junkData-1)
                else:
                    newFile.truncate(newFile.tell()-junkData)
                newFile.close()
            else:
                if self.SpWDebug:
                    print("Remove junk data bytes")
                if self.SpWIsCaptureOdd():
                    # Account for odd/even number of bytes received.
                    dataStitch = dataStitch[:-junkData-1]
                else:
                    dataStitch = dataStitch[:-junkData]

        ###############DEBGUG##############
        if self.SpWDebug:
            print('________________Post read PRE pulse rd done___________________')
            self.HsStatus(True)

        # Put GPIF in reset
        try:
            self.FpgaRegWr(reg = _const.reg_gpif_conf , data = 0x00)
        except Exception as e:
            raise exceptions.SpWDataError(f'Error resetting GPIF interface (on waxwing).\n{e}')        


        # Pulse pRdDone (aka sSpwDataRdDone) this lets SpWFifoFiller continue to see to which node the next data byte must go. Will only properly continue
        # when GPIF is let out of reset or if a TM data is in buffer.
        try:            
            self.FpgaRegRdModWr(reg = _const.reg_spw_data_ctrl , val = 1, pos  = 0)
        except Exception as e:
            raise exceptions.SpWDataError(f'Error pulsing pInitSpwFiller.\n{e}')

        ###############DEBGUG##############
        if self.SpWDebug:
            print('________________Post read POST pulse rd done___________________')
            self.HsStatus(True)

        # Check if any errors occurred during the capture (this will throw an exception)
        self.SpWIsError()

        #TODO: make the file append? This is useful for multiple reads...

        # Write to a file ## ##
        if not filename is None:
            print()
            if self.SpWDebug:
                print("  __SpW Capture: Closing file:", filename)
            newFile.close()
        # OR just return the array
        else:
            # Convert to numpy.array
            data_truncated_np_array = numpy.frombuffer(buffer = dataStitch, dtype = numpy.uint8)
            return data_truncated_np_array

    def SpWClose(self):
        """
        Perform the disabling and clearing of buffers etc.
        """
        #____________SpW admin_____________#        
        #Hold SpW core in reset, this also resets SpwFifoFiller, as well as the RxFifo
        try: 
            self.SpWReset()
        except Exception as e:
            raise exceptions.SpWResetError()        
        
        #______________ Capture _______________#
        #Put GPIF in reset
        try:
            self.FpgaRegWr(reg = _const.reg_gpif_conf , data = 0x00)
        except Exception as e:
            raise exceptions.SpWDataError(f'Error resetting GPIF interface (on waxwing).\n{e}')        
        
        #Reset FX3 FIfo
        try:
            self.Dev_Handle.resetDevice()
            self.Dev_Handle.resetDevice()
        except Exception as e:
            raise exceptions.SpWDataError(f'Error clearing GPIF fifos (on FX3).\n{e}')                

        #______________ Read _______________#
        #Reset SpWFifoFiller, already in reset if SpWReset().        
        #Reset TM fifo, already in reset if SpWReset().        

        #______________ Write ______________#
        #Put TxFiller into reset, already in reset if SpWReset().        
        #Reset TC Fifo, already in reset if SpWReset().        

    def SpWRxFsmInfo(self):
        """
        Shows which states the 'Router, TM, and Data' state machines are in.
        """
        
        stat = self.FpgaRegRd(reg = _const.reg_spw_enum_0)
        statRouter = stat>>4
        statTm = stat & 0xF
        
        stat = self.FpgaRegRd(reg = _const.reg_spw_enum_1)
        statData = stat & 0xF
        
        
        # dictionaries which hold various states.
        RouterDict = {1:"IDLE", 2:"ENABLE_RD_TM", 3:"ENABLE_RD_DATA", 4:"ENABLE_CLR_NODE_FIFO", 5:"ENABLE_DROP_PKT", 6:"INIT"}
        TmDict     = {1:"IDLE", 2:"PULL_DATA", 3:"WAIT_PULL", 4:"PKT_END_DETECTED", 5:"WAIT_PRE_DONE", 6:"DONE"}
        DataDict   = {1:"IDLE_D", 2:"WAIT_PULL_D", 3:"PULL_DATA_D", 4:"PKT_END_DETECTED_D", 5:"WAIT_PKT_ENDED_D",
                      6:"TOUT_MID_PACKET_D", 7:"PRE_DONE_D", 8:"DONE_D", 9:"WAIT_PRE_DONE_D", 10:"READ_OUT_LA_D",
                      11:"WAIT_READ_OUT_LA_D"}
        
        print(f' Router: {statRouter}, Tm: {statTm}, Data: {statData}')
        
        print(f'Router State: {RouterDict[statRouter]}')
        print(f'Tm State:     {TmDict[statTm]}')
        print(f'Data State:   {DataDict[statData]}')        

    def SpWDataWordDbg(self, verbose=False):
        """
        REad out the curent data word that is waiting in the RX FIFO of the EGSE's SpW node.
        Also determine whether or not it is valid, and whterh or not it is a EndOFPacket flag.
        """
        stat = self.FpgaRegRd(reg = _const.reg_spw_enum_1)
        ValidData            = (stat>>5) & 0x1
        ValidEndOfPacketFlag = (stat>>4) & 0x1
        stat = self.FpgaRegRd(reg = _const.reg_spw_enum_2)
        DataWord = stat
        if verbose:
            print(f'DataWord: {DataWord}')
            print(f'ValidData: {bool(ValidData)}')
            print(f'ValidEndOfPacketFlag: {bool(ValidEndOfPacketFlag)}')        
        return bool(ValidData)
        
    def SpWClrRxNodeFifo(self):
        """
        Clear the RxNode FIFO.
        """
        # Pulse the clear node fifo bit.
        self.FpgaRegRdModWr(reg = _const.reg_spw_ctrl, val = 1, pos = 5)
        

    def SpWAutoDropPkts(self, enable=True):
        """
        Setup the EGSE to automatically drop invalid SPW packets that are recieved (e.g. incorrect LA).
        Note: if in Data-only mode, no packets will be dropped, since the drop decision occurs on the first
        byte of every arriving packet.
        """
        self.FpgaRegRdModWr(reg = _const.reg_spw_ctrl, val = int(enable), pos = 6) #Set not pulse.
    
    def SpWLaError(self):
        """
        WHen the EGSE's SpW Node is setup in self.SpWAutoDropPkts, it drops any packets that are recieved
        which have an irrelevant LA, or if junk data is sitting in the SpW Node FIFO.
        Return Indicate whether or not a error occurred. This flag is cleared by calling
        self.SpWRstSpwFifoFiller()
        """
        stat = self.FpgaRegRd(reg = _const.reg_spw_data_status)
        LaError = (stat >> 4) & 0x01
        return bool(LaError)			

    def SpWInitialBytesHighSpeed(self):
        """
        Determine the first 2x bytes recieved which are marked as Highpeed data.
        """
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 
        
        #Data from node, should include junk or LA
        self.FpgaRegWr(_const.reg_addr_dbg_mux, 4)
        val = self.FpgaRegRd(reg = _const.reg_addr_dbg_reg)
        print(f'Node Byte 1: {hex(val)}')
        self.FpgaRegWr(_const.reg_addr_dbg_mux, 5)
        val = self.FpgaRegRd(reg = _const.reg_addr_dbg_reg)
        print(f'Node Byte 2: {hex(val)}')
        
        
        #Data being sent to 8-16 converter
        self.FpgaRegWr(_const.reg_addr_dbg_mux, 2)
        val = self.FpgaRegRd(reg = _const.reg_addr_dbg_reg)
        print(f'First  Byte 8-16: {hex(val)}')
        self.FpgaRegWr(_const.reg_addr_dbg_mux, 3)
        val = self.FpgaRegRd(reg = _const.reg_addr_dbg_reg)
        print(f'Second Byte 8-16: {hex(val)}')
        
        #   #Inside 8-16 converter
        #       #dodgy writes 
        #   self.FpgaRegWr(_const.reg_addr_dbg_mux, 6)
        #   val = self.FpgaRegRd(reg = _const.reg_addr_dbg_reg)
        #   print(f'First Byte Correct: {hex(val)}')                    
        #       #successful writes 
        #   self.FpgaRegWr(_const.reg_addr_dbg_mux, 7)
        #   val = self.FpgaRegRd(reg = _const.reg_addr_dbg_reg)
        #   print(f'First Byte Dodgy: {hex(val)}')                        
        
    def SpWNumPktsRx(self):
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 
        
        self.FpgaRegWr(_const.reg_addr_dbg_mux, 6)
        val_hi = self.FpgaRegRd(reg = _const.reg_addr_dbg_reg)

        self.FpgaRegWr(_const.reg_addr_dbg_mux, 7)
        val_lo = self.FpgaRegRd(reg = _const.reg_addr_dbg_reg)        
        
        return (val_hi << 8) + val_lo
        
    def SpWNumRdByte(self):
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 

        self.FpgaRegWr(_const.reg_addr_dbg_mux, 8)
        val_hi = self.FpgaRegRd(reg = _const.reg_addr_dbg_reg)

        self.FpgaRegWr(_const.reg_addr_dbg_mux, 9)
        val_mi = self.FpgaRegRd(reg = _const.reg_addr_dbg_reg)                

        self.FpgaRegWr(_const.reg_addr_dbg_mux, 10)
        val_lo = self.FpgaRegRd(reg = _const.reg_addr_dbg_reg)                        
        
        return (val_hi << 16) + (val_mi << 8) + val_lo
        

    ## ========================================================================================= ##
    ##########___________________ General Purpose IO's, and LEDs_________________________##########
    def IoGetConfig(self, IO):
        """
        This function returns the config of the IO in question.

        The EGSE has 21 IO's on the One-to-one connector. Some of these are configured to be high-speed capable differential IO's (LVDS),
        these cannot be used as GPIO's. The rest of the IO's can be used in GPIO fashion. The IO's config can only be changed after \
        a FPGA (Waxwing) FW update.

        Arguments In:
            - IO (int, 0 to 21) which IO we want to determine the configuration of.
        Return:
            - ioConfig (int)   '1' if setup as LVDS
                               '0' if setup as GPIO.
        """
        #Check parameters
        try:
            IO = int(IO)
        except ValueError as e:
            raise exceptions.InputError(f'IO parameter must be an integer, but "{IO}" was supplied.\n{e}')
        if (IO > 20) or (IO < 0):
            raise exceptions.InputError(f'IO parameter must be between 0 and 21 (inclusive), but "{IO}" was supplied.')

        #Setup some sort of dictionary if it has not already been setup
        if len(self.gpio_config_dict) == 0:#The dictionary is still empty

            #Read registers
            try:
                gpioConfig_0 = self.FpgaRegRd(reg = _const.reg_gpio_config_0)
                gpioConfig_1 = self.FpgaRegRd(reg = _const.reg_gpio_config_1)
                gpioConfig_2 = self.FpgaRegRd(reg = _const.reg_gpio_config_2)
            except Exception as e:
                raise exceptions.GpioError(f'Error reading configuration of IO\'s Direction register.\n{e}')

            gpioConfig_combined = gpioConfig_0 + (gpioConfig_1 <<8) + (gpioConfig_2 << 16)

            #Populate the dictionary
            for gpio_num in range(21):
                self.gpio_config_dict[str(gpio_num)] = (gpioConfig_combined >> gpio_num) & 0x01#This dict will contain '1' where IO is setup as LVDS, and '0' where setup as GPIO.

        #Return the config of the specific IO:
        return self.gpio_config_dict[str(IO)]

    def GpioGetMode(self, IO):
        """
        Get the mode of the specific IO, input or output.
        Arguments In:
            - IO (int, 0 to 20): which of the 21 pins do you want to determine mode of.

        Return:
            - mode (input '0' or output '1'): Is the EGSE's IO setup as an input '0' or output '1', if IO is setup as LVDS, will raise "exceptions.LvdsError"
        """

        try:
            IO = int(IO)
        except ValueError as e:
            raise exceptions.InputError(f'IO parameter must be an integer, but "{IO}" was supplied.\n{e}')
        if (IO > 20) or (IO < 0):
            raise exceptions.InputError(f'IO parameter must be between 0 and 21 (inclusive), but "{IO}" was supplied.')


        pinConfig = self.IoGetConfig(IO)
        if pinConfig == IoConfig_Lvds:
            raise exceptions.LvdsError(f'the IO is configured to be a LVDS capable IO, therefore it is not a GPIO.')

        #Read all 3 direction registers.
        try:
            directionStatus_0 = self.FpgaRegRd(reg = _const.reg_gpio_direction_0)
            directionStatus_1 = self.FpgaRegRd(reg = _const.reg_gpio_direction_1)
            directionStatus_2 = self.FpgaRegRd(reg = _const.reg_gpio_direction_2)
        except Exception as e:
            raise exceptions.GpioError(f'Error reading GPIO Direction register.\n{e}')

        for gpio_pins in range(21):
            if gpio_pins == IO:#This is the IO which we want to check mode of.
                direction_reg_combined = directionStatus_0 + (directionStatus_1 <<8) + (directionStatus_2 <<16)
                #Shift them all the way to the right, and only retrieve this last value.
                directionStatus = (direction_reg_combined >> IO) & 0x01

        return directionStatus

    def GpioSetMode(self, IO, mode):
        """
        Set a specific GPIO to either input or output. They startup as inputs.

        Arguments In:
            - IO (int, 0 to 20): which of the 21 IO mode do you want to set.
            - mode (input '0' or output '1'): Is the EGSE's IO setup as an input '0' or output '1' NOTE: we can always sample the value of the GPIO (even in output mode).
        """
        #check input values
        
        
        try:
            IO = int(IO)
        except ValueError as e:
            raise exceptions.InputError(f'IO parameter must be an integer, but "{IO}" was supplied.\n{e}')
        if (IO > 20) or (IO < 0):
            raise exceptions.InputError(f'IO parameter must be between 0 and 21 (inclusive), but "{IO}" was supplied.')

        try:
            mode = int(mode)
        except ValueError as e:
            raise exceptions.InputError(f'mode parameter must be an integer, but "{mode}" was supplied.\n{e}')
        if (mode > 1) or (mode < 0):
            raise exceptions.InputError(f'mode parameter must be between 0 and 1 (inclusive), but "{mode}" was supplied.')

        if self.HwRevision == 2:
            pinConfig = self.IoGetConfig(IO)
            if pinConfig == IoConfig_Lvds:
                raise exceptions.LvdsError(f'the IO is configured to be a LVDS capable IO, therefore it is not a GPIO.')
        
        #Setup mux which allows either SPI or GPIO functionality on pins 17_p, 17_n
        if self.HwRevision == 3:
            if ((IO == 19) or (IO == 18)) and ((self.getBuildVariant() == 1) or (self.getBuildVariant() == 3) or (self.getBuildVariant() == 4)):
                if self.GetSpiGpioPinConfig() == 'spi':
                    self.SetSpiGpioPinConfig(conf='gpio')
                    print(f'WARNING: setting the mode of IO {IO} has disabled SPI capability. Re-run EGSE.SpiInit(...) to retrieve SPI capability.')
                    
        #1.)
        #Read
        try:
            directionStatus_0 = self.FpgaRegRd(reg = _const.reg_gpio_direction_0)
            directionStatus_1 = self.FpgaRegRd(reg = _const.reg_gpio_direction_1)
            directionStatus_2 = self.FpgaRegRd(reg = _const.reg_gpio_direction_2)
        except Exception as e:
            raise GpioError(f'Error reading GPIO direction register.\n{e}')

        #Get current mode of that IO
        for gpio_pins in range(21):
            if gpio_pins == IO:#This is the IO which we want to modify
                direction_reg_combined = directionStatus_0 + (directionStatus_1 <<8) + (directionStatus_2 <<16)
                #directionStatus = (direction_reg_combined >> IO) & 0x01


                #Modify value of the IO to the required mode.
                if mode == 1:
                    #Create SET bistmask
                    direction_reg_combined_updated = direction_reg_combined | (1 << IO)
                    (1 << IO)
                if mode == 0:
                    #Create CLEAR bitmask
                    direction_reg_combined_updated = direction_reg_combined & (  (~ (1 << IO) ) & 0xFFFFFF)


        if self.debug:
            print('directionStatus_pos_to_regs', hex(direction_reg_combined_updated))

        #Write this value back to registers.
        try:
            self.FpgaRegWr(reg = _const.reg_gpio_direction_0, data =  (direction_reg_combined_updated       & 0x0000FF))
            self.FpgaRegWr(reg = _const.reg_gpio_direction_1, data = ((direction_reg_combined_updated >> 8 )& 0x0000FF))
            self.FpgaRegWr(reg = _const.reg_gpio_direction_2, data = ((direction_reg_combined_updated >> 16)& 0x0000FF))
        except Exception as e:
            raise exceptions.GpioError(f'Error setting GPIO direction register.\n{e}')

    def GpioSet(self, IO, val):
        """
        The EGSE has 21 IO's, 0 to 20. This function sets the a value on the GPIO.

        Arguments In:
            - IO (int, 0 to 20): which of the 21 IO's on the port do you want to use.
            - val (int, 0 or 1): the logic level you want on output.
        """
        #1.) First set direction bit as output (REad, modify, write), set the specific IO as output.
        #2.) Make the Gpio a certain value (read, modify, write)

        try:
            IO = int(IO)
        except ValueError as e:
            raise exceptions.InputError(f'IO parameter must be an integer, but "{IO}" was supplied.\n{e}')
        if (IO > 20) or (IO < 0):
            raise exceptions.InputError(f'IO parameter must be between 0 and 20 (inclusive), but "{IO}" was supplied.')

        pinConfig = self.IoGetConfig(IO)
        if self.HwRevision == 2:
            if pinConfig == IoConfig_Lvds:
                raise exceptions.LvdsError(f'the IO is configured to be a LVDS capable IO, therefore it is not a GPIO.')

        #1.)
        #Read
        try:
            self.GpioSetMode(IO, GpioMode_Out)
        except Exception as e:
            raise exceptions.GpioError(f'Error setting GPIO {IO} to output mode.\n{e}')

        #Read current values
        try:
            pinVal_0 = self.FpgaRegRd(reg = _const.reg_gpio_data_in_0)
            pinVal_1 = self.FpgaRegRd(reg = _const.reg_gpio_data_in_1)
            pinVal_2 = self.FpgaRegRd(reg = _const.reg_gpio_data_in_2)
        except Exception as e:
            raise GpioError(f'Error reading GPIO values.\n{e}')

        pinVal_combined = pinVal_0 + (pinVal_1 << 8) + (pinVal_2<<16)
        if self.debug:
            print('pinVal_combined',hex(pinVal_combined))

        #Modify value
        if val == 1:
            #create SET bitmask
            pinVal_updated = pinVal_combined | (1 << IO)
        if val == 0:
            #Create CLEAR bitmask
            pinVal_updated = pinVal_combined &  ( (~( 1 << IO))  & 0xFFFFFF )
        if self.debug:
            print('pinVal_updated', hex(pinVal_updated))

        #Write this value to regisers.
        try:
            self.FpgaRegWr(reg = _const.reg_gpio_data_out_0, data =  (pinVal_updated & 0x0000FF))
            self.FpgaRegWr(reg = _const.reg_gpio_data_out_1, data = ((pinVal_updated >> 8 )& 0x0000FF))
            self.FpgaRegWr(reg = _const.reg_gpio_data_out_2, data = ((pinVal_updated >> 16)& 0x0000FF))

            if self.debug:
                print('data_reg_0', hex(pinVal_updated & 0x0000FF))
                print('data_reg_1', hex ((pinVal_updated >> 8 )& 0x0000FF))
                print('data_reg_2', hex ((pinVal_updated >> 16)& 0x0000FF))

        except Exception as e:
            raise exceptions.GpioError(f'Error writing GPIO value to register.\n{e}')

    def GpioGet(self,IO = None):
        """
        Determine the current value of the respective GPIO's. Note, IO does not have to be set as an input in order to read the value.

        Arguments In:
            - IO (int, 0 to 20): which IO do we want to read

        Return:
            - val (int, '0' or '1'), logic value of the GPIO
        """
        #1.) Read the relevant reg values
        #2.) package and forward

        try:
            IO = int(IO)
        except ValueError as e:
            raise exceptions.InputError(f'IO parameter must be an integer, but "{IO}" was supplied.\n{e}')
        if (IO > 20) or (IO < 0):
            raise exceptions.InputError(f'IO parameter must be between 0 and 20 (inclusive), but "{IO}" was supplied.')

        pinConfig = self.IoGetConfig(IO)
        if pinConfig == IoConfig_Lvds:
            raise exceptions.LvdsError(f'the IO is configured to be a LVDS capable IO, therefore it is not a GPIO.')

        #1.)
        #Read the registers
        try:
            pinState_0 = self.FpgaRegRd(reg = _const.reg_gpio_data_in_0)
            pinState_1 = self.FpgaRegRd(reg = _const.reg_gpio_data_in_1)
            pinState_2 = self.FpgaRegRd(reg = _const.reg_gpio_data_in_2)
        except Exception as e:
            raise GpioError(f'Error reading GPIO values.\n{e}')

        #Determine individual states:
        for gpio_pins in range(21):
            if gpio_pins == IO:#This is the IO which we want to determine value of...
                pinState_combined = pinState_0 + (pinState_1 << 8) + (pinState_2 << 16)
                val = (pinState_combined >> IO ) & 0x01

        return val

    def GpioPulse(self, IO, tpulse):
        """
        Pulse a GPIO to it's inverse value for a certain time (tpulse). Note only one IO can be 'pulsed' at any given time.

        Arguments In:
            - IO (int, 0 to 20): which of the 21 IO do you want to use.
            - tpulse (float, seconds) range is between 10ns and 42.94s. Why? a 32bit value (the registers which
                                      hold the value on FPGA) has range from 1 to 4 294 967 295, that is the amount
                                      of clock cycles that we can toggle for, at 100MHz (10ns period), get this time range.
        """
        #1.) set the IO as an output (read, modify, write)
        #2.) write the pulse clocks to register
        #3.) update the pulse IO (the port and IO which we want to pulse)
        #4.) trigger the pulse functionality

        #Check input values
        try:
            IO = int(IO)
        except ValueError as e:
            raise exceptions.InputError(f'IO parameter must be an integer, but "{IO}" was supplied.\n{e}')
        if (IO > 20) or (IO < 0):
            raise exceptions.InputError(f'IO parameter must be between 0 and 20 (inclusive), but "{IO}" was supplied.')

        if (tpulse < 10e-9) or (tpulse > 42.94):
            raise exceptions.InputError(f'tpulse parameter must be between 10e-9 and 42.94 (inclusive), but "{tpulse}" was supplied.')

        pinConfig = self.IoGetConfig(IO)
        if pinConfig == IoConfig_Lvds:
            raise exceptions.LvdsError(f'the IO is configured to be a LVDS capable IO, therefore it is not a GPIO.')

        #1.)
        #Get the appropriate direction
        try:
            self.GpioSetMode(IO, GpioMode_Out)
        except Exception as e:
            raise exceptions.GpioError(f'Error setting GPIO {IO} to output mode.\n{e}')

        #2.)
        #Determine the correct value to be written
        SysClkWaxWing = 100e6#100MHz
        period = 1/SysClkWaxWing
        cycles = tpulse/period
        cycles = int(cycles)

        if self.debug:
            print('tpulse', tpulse)
            print('cycles', cycles)


        #Do bit-masking to write the correct full 32bit value to the 4 registers
        cycles_reg0 =  cycles & 0x000000FF
        cycles_reg1 = (cycles & 0x0000FF00) >> 8
        cycles_reg2 = (cycles & 0x00FF0000) >> 16
        cycles_reg3 = (cycles & 0xFF000000) >> 24

        if self.debug:
            print('Cycles reg', hex(cycles))

        try:
            self.FpgaRegWr(reg = _const.reg_gpio_pulse_clks_0, data = cycles_reg0)
            self.FpgaRegWr(reg = _const.reg_gpio_pulse_clks_1, data = cycles_reg1)
            self.FpgaRegWr(reg = _const.reg_gpio_pulse_clks_2, data = cycles_reg2)
            self.FpgaRegWr(reg = _const.reg_gpio_pulse_clks_3, data = cycles_reg3)
        except Exception as e:
            raise exceptions.GpioError(f'Error setting GPIO pulse length.\n{e}')

        #3.)
        pulsePin = IO
        try:
            self.FpgaRegWr(reg = _const.reg_gpio_pulse_pin, data = pulsePin)#No need to preserve state, simply write full value to register
        except Exception as e:
            raise exceptions.GpioError(f'Error setting GPIO pulse IO.\n{e}')

        #4.)
        try:
            self.FpgaRegWr(reg = _const.reg_gpio_pulse_trigger, data = 0x01)#No need to preserve state, simply write full value to register
        except Exception as e:
            raise exceptions.GpioError(f'Error triggering GPIO pulse.\n{e}')

    def InitPps(self, pri = None, sec = None, polarity = 1):
        """
        Initialise the EGSE with a certain set of PPS Options. 
        
        Argument In:
            - pri (string), which location of primary PPS.
            - sec (string), which location of secondary PPS.
            - polarity (int: 1, 0), 1 -> we must generate 'rising' pulses (default low), 0 -> we must generate falling pulses (default high).
        """

        # Check if pri and sec parameter are valid (in the PpsConfig Dictionary)
        if pri != None:
            if not any(pri in key['Option'] for key in PpsConfig):
                raise exceptions.InputError(f'Please apply appropriate value for PPS pri.\n{e}')
        if sec != None:
            if not any(sec in key['Option'] for key in PpsConfig):
                raise exceptions.InputError(f'Please apply appropriate value for PPS sec.\n{e}')
            
        # Check polarity parameter
        if polarity not in [0,1]:
            raise exceptions.InputError(f'Polarity parameter must be 0 or 1, but {polarity} was supplied.\n{e}')
        
        # Check for EGSE Revision 2 - PPS_LVDS options are not supported
        if (self.HwRevision == 2) and ((pri in PpsConfig[2]['Option']) or (sec == PpsConfig[2]['Option'])):            
            raise exceptions.InitialisationError(f'HW revision 2 does not support differential PPS.\n{e}')
        
        # Setup the EGSE PPS GPIOs
        for key in PpsConfig:
            if (pri in key['Option']) or (sec in key['Option']):
                # Option Found for a specific EGSE GPIO
                # Check/Handle PPS_LVCMOS_2 overlap with SPI Control Interface (for EGSE Revision 3)
                if (pri == 'PPS_LVCMOS_2') or (sec == 'PPS_LVCMOS_2'):
                    # Check for overlap
                    if (self.HwRevision == 3):
                        if (self.GetSpiGpioPinConfig() == 'spi'):
                            raise exceptions.InitialisationError(f'Cannot initialise PPS_LVCMOS_2 as the SPI Control Interface is already initialised.\n{e}')
                    
                        # Configure the pin as a GPIO for use as PPS
                        self.SetSpiGpioPinConfig(conf='gpio')                        
                
                # Set the GPIO as an output
                self.GpioSetMode(key['EgseGpio'], GpioMode_Out)
                
                # Set the GPIO default output value (based on PPS polarity)
                if polarity == 1:
                    self.GpioSet(key['EgseGpio'], 0)
                else:
                    self.GpioSet(key['EgseGpio'], 1)  
            else:
                # Set all other unselected PPS options to inputs, except for PPS_LVCMOS_2 if SPI is used, and except for all the pin 0 options if HwRevision 2 is used
                set_unselected_to_input = True
                
                # Don't set the PPS_LVCMOS_2 pin to an input if Spi is selected, because Spi uses that pin
                if (self.HwRevision == 3) and ('PPS_LVCMOS_2' in key['Option']) and (self.GetSpiGpioPinConfig() == 'spi') :
                    set_unselected_to_input = False
                
                # Don't set pin 0 to an input, because it's not set up as a GPIO
                if (self.HwRevision == 2) and (key['EgseGpio'] == 0):
                    set_unselected_to_input = False
                
                if set_unselected_to_input:
                    self.GpioSetMode(key['EgseGpio'], GpioMode_In)
                            
        # Save to the instance variable
        self.PpsPrimary = pri
        self.PpsSecondary = sec
        
        # Save Let it default to primary PPS.
        self.SelPps('pri')
    
    def SelPps(self, sel):
        """
        Define which PPS will be used, stored in a member variable.
        
        Arguments In:
            - sel (str), 'pri' or 'Primary' to use primary PPS, 'sec' or 'Secondary' to use secondary PPS.
        """
        if sel not in ['pri', 'sec', 'Primary', 'Secondary']:
            raise exceptions.InputError(f'Please apply appropriate value for sel.\n{e}')
        if sel == 'Primary':
            self.PpsSel = 'pri'
        elif sel == 'Secondary':
            self.PpsSel = 'sec'
        else:
            self.PpsSel = sel
        
    def SetPps(self, val):
        """
        PPS gets driven like an output, set it to high or low. This method abstracts which 
        interface should be used. The member variable PPS gets used, and can only be changed
		with SelPps().
        
        Argument In:
            - val (int, 1 or 0), 1 if setting to 'high', 0 if setting 'low'.
        """

        # Check val Parameter
        if val not in [0, 1, True, False]:
            raise exceptions.InputError(f'val parameter must be 1, 0, True or False, but {val} was supplied.\n{e}')
        
        # Determine which PPS option is to be accessed
        if self.PpsSel   == 'pri':
            pps_sel = self.PpsPrimary
        if self.PpsSel == 'sec':
            pps_sel = self.PpsSecondary
        
        # Look up the correct GPIO, and set the output value
        for key in PpsConfig:
            if pps_sel in key['Option']:
                self.GpioSet(key['EgseGpio'], val)
                #print(f"EGSE GPIO {key['EgseGpio']} set to {val} to driving {key['Option']}")
        
    def GetPps(self):
        """
        Returns which state the PPS is being driven to. 
        
        Return:
            - val (boolean) True if logical high, False for logical low.
        """
        
        # Determine which PPS option is to be accessed
        if self.PpsSel   == 'pri':
            pps_sel = self.PpsPrimary
        if self.PpsSel == 'sec':
            pps_sel = self.PpsSecondary        
        
        # Look up the correct GPIO, and set the output value
        for key in PpsConfig:
            if pps_sel in key['Option']:
                val = self.GpioGet(key['EgseGpio'])
        
        return val

    def SetUsrLed(self, led, val):
        """
        The EGSE has 2 User LEDs. We can set and read them.

        Arguments In:
            - led (int, '1' or '2'), which User LED do we want to set, '1' or '2'
            - val (bool (True, False), or int (1,0), what value do we want LED to have:
                                                'True' or '1' is on
                                                'False' or '0' is off.
        """
        if led != 1 and led != 2:
            raise exceptions.InputError(f'led must either be {1} or {2}, instead {led} was provided.')
        try: #covers both a float and a bool option.
            val = int(val)
        except ValueError as e:
            raise exceptions.InputError(f'val parameter must be \'1\', \'0\', \'True\' or \'False\', instead \'{val}\' was supplied.\n{e}')
        if (val not in [0, 1]):
            raise exceptions.InputError(f'val parameter must be \'1\', \'0\', \'True\' or \'False\', instead "{val}" was supplied.')

        #1.Read current value
        try:
            curr_led = self.FpgaRegRd(reg = _const.reg_usr_led)#Remember, '0' is on at this level
        except Exception as e:
            raise exceptions.UsrLedError(f'Error reading current value of User LED.\n{e}')

        #2. Modify data
        #Various cases
        if led == 2:
            curr_val = curr_led & 0x01#Preserve LSB
            if val == 1:
                val_mod = 0x00
            else:
                val_mod = 0x02
        elif led == 1:
            curr_val = curr_led & 0x02#Preserve MSB (aka second bit from right)
            if val == 1:
                val_mod = 0x00
            else:
                val_mod = 0x01

        new_reg_val = curr_val + val_mod

        if self.debug:
            print('curr_val', curr_val)
            print('val_mod', val_mod )
            print('new_reg_val', new_reg_val)

        #3.Write data
        try:
            self.FpgaRegWr(reg = _const.reg_usr_led, data = new_reg_val)
        except Exception as e:
            raise exceptions.UsrLedError(f'Error setting User LED register.\n{e}')

    def SetLedBrightness(self, led, per ):
        """Set the brightness of the relevant LED, do this via PWM on FPGA pin.

        Arguments In:
            - led (string) which LED to set. Valid options: 'UsrLed1',
            - perc (int) value between 0 and 100, percentage of brightness to enable.
        """
        #Parameter checking
        try:
            per = int(per)
        except ValueError as e:
            raise exceptions.InputError(f'per parameter must be a value between \'0\' and \'100\', instead \'{per}\' was supplied.\n{e}')

        if (per < 0) or (per > 100):
            raise exceptions.InputError(f'per parameter must be a value between \'0\' and \'100\', instead \'{per}\' was supplied.')

        valid_leds = ['UsrLed1', 'UsrLed2', 'StatusLed', 'DataLed', 'CtrlLed' ]
        if led not in valid_leds:
            raise exceptions.InputError(f'led parameter must be one of the following \'{valid_leds}\', instead \'{led}\' was supplied.')

        if led == 'UsrLed1':
            reg_write = _const.reg_usr_led_1_brtns
        if led == 'UsrLed2':
            reg_write = _const.reg_usr_led_2_brtns
        if led == 'StatusLed':
            reg_write = _const.reg_status_led_brtns
        if led == 'DataLed':
            reg_write = _const.reg_data_led_brightness
        if led == 'CtrlLed':
            reg_write = _const.reg_ctrl_led_brightness


        if self.debug:
            print('Setting brightness of: ', led)

        try:
            self.FpgaRegWr(reg = reg_write, data = per)
        except Exception as e:
            raise exceptions.LedError(f'Error setting brightness of \'{led}\' .\n{e}')

        if self.debug:
            print('Done setting brightness')

    ## ========================================================================================= ##
    ##########_________________________________ Power ___________________________________##########
    #___Power Switch___#
    def PwrOut(self, val):
        """
        The EGSE has a output power switch, which controls whether power is porovided across the one-to-one connector or not.

        Arguments In:
            - val (bool), 'True' will enable power to One-to-one connector, 'False' will disable the output to one-to-one connector.
        """
        try: #covers both a float and a bool option.
            val = int(val)
        except ValueError as e:
            raise exceptions.InputError(f'val parameter must be \'1\', \'0\', \'True\' or \'False\', instead \'{val}\' was supplied.\n{e}')
        if (val not in [0, 1]):
            raise exceptions.InputError(f'val parameter must be \'1\', \'0\', \'True\' or \'False\', instead "{val}" was supplied.')


        if val == 1:
            val_set = 0x01
        if val == 0:
            val_set = 0x02

        try:
            self.FpgaRegWr(reg = _const.reg_pwr_switch_cmd, data = val_set )
        except Exception as e:
            raise exceptions.PwrSwitchError(f'Error setting power switch register.\n{e}')

    def PwrOut_v3(self, val, verbose=False):
        """
        The EGSE has a output power switch, which controls whether power is provided across the one-to-one connector or not.
        When calling PwrOut(1), it will attempt to switch on the switch, however it will not be successful if the Vin is out 
        of range. See self.PwrOutLimits() on how to adjust these limits, however should only be adjusted with caution.
        Arguments In:
            - val (bool), 'True' will enable power to One-to-one connector, 'False' will disable the output to one-to-one connector.
        """
        try: #covers both a float and a bool option.
            val = int(val)
        except ValueError as e:
            raise exceptions.InputError(f'val parameter must be \'1\', \'0\', \'True\' or \'False\', instead \'{val}\' was supplied.\n{e}')
        if (val not in [0, 1]):
            raise exceptions.InputError(f'val parameter must be \'1\', \'0\', \'True\' or \'False\', instead "{val}" was supplied.')

        if val == 1:
            val_set = 0x01
        if val == 0:
            val_set = 0x02
            
        

        try:
            self.FpgaRegWr(reg = _const.reg_pwr_switch_cmd, data = val_set )
        except Exception as e:
            raise exceptions.PwrSwitchError(f'Error setting power switch register.\n{e}')
        round_to = 2
        lower, upper = self.PwrOutLimitsVal()
        lower = round(lower, round_to)
        upper = round(upper, round_to)
        vin = round(self.GetVin(), round_to)
        #Give time for switch output voltage to get to appropriate level (and averaging value to catch up)
        time.sleep(0.05)
        vout = round(self.GetVout(), round_to)
        str_msg_fail = f'If using external 5V input, ensure voltage is between: {lower} V - {upper} V, currently: {vin} V'
        str_msg_success = f'PWR OUT = {vout} V'
        str_msg_no_conn = f'Please ensure EGSE power supply is connected.'
        
        # Only report errors if trying to switch on switch.
        if val_set == 0x01:
            # Confirm switch is on
            if self.PwrOutStat() == 0x01:
                if verbose:
                    print(f'{str_msg_success}')
            else:
                # switch not on, some problem, print useful info by default.
                if vin < 0.5:# PS probably not connected.
                    print(f'{str_msg_no_conn}')
                else:
                    print(f'{str_msg_fail}')
        else:
            if verbose:
                print(f'{str_msg_success}')
                
    def PwrOutRst(self):
        """
        Place Power switch FW in reset, will also put ADC in reset.
        """
        try:
            self.FpgaRegWr(reg = _const.reg_pwr_switch_cmd, data = 4)
        except Exception as e:
            raise exceptions.PwrSwitchError(f'Error setting power switch register.\n{e}')

    def PwrOutRst_v3(self):
        """
        Clear the flags of PwrOut switch.
        """
        try:
            self.FpgaRegWr(reg = _const.reg_pwr_switch_cmd, data = 4)
        except Exception as e:
            raise exceptions.PwrSwitchError(f'Error setting power switch register.\n{e}')

    def PwrOutRaw(self):
        """
        Determine the raw value that is interpretd by the PwrSwitch comparator (value BEFORE the switch, aka Vin)
        """
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 
        
        try:
            val_msb = self.FpgaRegRd(reg = _const.reg_raw_val_vin_msb)
            val_lsb = self.FpgaRegRd(reg = _const.reg_raw_val_vin_lsb)
            val_cmp = (val_msb << 8) + val_lsb
        except Exception as e:
            raise exceptions.PwrSwitchError(f'Error getting power switch status.\n{e}')
        
        return val_cmp

    def PwrOutStat(self, verbose=False):
        """
        Determine the status of the power out switch. For HwRevision = 3, determine whether over/under voltage event occurred.

        Return
            - stat (int), '1' -> switch is on, '2' -> switch is off, '4' -> switch is in reset.
        """
        try:
            stat = self.FpgaRegRd(reg = _const.reg_pwr_switch_status)
        except Exception as e:
            raise exceptions.PwrSwitchError(f'Error getting power switch status.\n{e}')
        
        if self.HwRevision == 3:
            val_cmp = self.PwrOutRaw() 
        
        if verbose:
            if stat & 0x01 == 0x01:
                stat_string = 'ON'
            if stat & 0x02 == 0x02:
                stat_string = 'OFF'
            if stat & 0x04 == 0x04:
                stat_string = 'RESET'
            print('output switch is in ', stat_string, ' state')
            if self.HwRevision == 3:
                if stat & 0x08 == 0x08:
                    print(f'Currently Vin is BELOW the lower threshold.')
                if stat & 0x10 == 0x10:
                    print(f'Currently Vin is ABOVE the upper threshold.')
                if stat & 0x20 == 0x20:
                    print(f'UNDER-voltage Event occured.')
                if stat & 0x40 == 0x40:
                    print(f'OVER-voltage Event occured.')
                
                Vin = self.GetVin(verbose=True)
                print(f'Vin : {round(Vin, 3)}')
                
        return stat & 0x7F# To mask ADC busy bit.


    
    def GetVoutUncal(self, verbose=False):
        """
        Determine the theoretical voltage AFTER the switch, based on voltage divider circuit.

        """
        ratio = 2200 / (2200 + 3900)
        
        lsb = self.FpgaRegRd(_const.reg_raw_val_vout_lsb)
        msb = self.FpgaRegRd(_const.reg_raw_val_vout_msb)
        DN = (msb << 8) + lsb
        if verbose:
            print(f'DN: {DN}')
        VMeas = DN * 0.0005#12bit ADC, ref voltage 2.048V
        VoutUncal = VMeas / ratio
        
        return VoutUncal

    def GetVoutCal(self, verbose=False):
        """
        Use C-value to determine calibrated value.
        """
        ratio = (2.2 / (2.2+3.9))#Voltage divider ratio
        lsb = self.FpgaRegRd(_const.reg_raw_val_vout_lsb)
        msb = self.FpgaRegRd(_const.reg_raw_val_vout_msb)
        DN = (msb << 8) + lsb
        if verbose:
            print(f'DN: {DN}')
        y = (DN * 0.0005 * (1/ratio)) + self.VoutCalCoeff_C
        
        return y
    
    def GetVout(self, verbose=False):
        """
        Simply return the most accurate voltage reading for Vout.
        """
        if self._VoutCalibrated:
            vout = self.GetVoutCal()
            if verbose:
                print(f'Vout is Calibrated')
        else:
            vout = self.GetVoutUncal()
            if verbose:
                print(f'Vout Uncalibrated')
        return vout
    
    
    
    def _IsVoutCal(self):
        """
        Determine whether EGSE Vout reading has been calibrated.
        """
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 
        
        magNum = self._EepromFx3RdBt(addr=0x3FF7D)
        
        if (magNum == 0xAB):
            return True
        else:
            return False

    def _GetVinCalNumEntries(self):
        """
        Determine how many calibration points were used. Must be 3.
        """
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 
        
        val = self._EepromFx3RdBt(0x3FF50 + 40)
        return val

    def GetAndSetPwrOutLimits(self, dbg=False):
        """
        Determine the allowable range of what the output voltage may be. Write it to Firmware.
        """
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 

        addr_cal_offs = 0x3ff80
        
        # Upper 
        upper_dn = self._EepromFx3RdBt(addr_cal_offs + 1) << 8
        upper_dn = upper_dn + self._EepromFx3RdBt(addr_cal_offs + 0)
        
        self.FpgaRegWr(_const.reg_upper_msb, upper_dn>>8)
        self.FpgaRegWr(_const.reg_upper_lsb, upper_dn&0xFF)
        
        # Lower
        lower_dn = self._EepromFx3RdBt(addr_cal_offs + 3) << 8
        lower_dn = lower_dn + self._EepromFx3RdBt(addr_cal_offs + 2)
        
        self.FpgaRegWr(_const.reg_lower_msb, lower_dn>>8)
        self.FpgaRegWr(_const.reg_lower_lsb, lower_dn&0xFF)
        
        if dbg:
            print(f'upper_dn: {upper_dn}')
            print(f'lower_dn: {lower_dn}')
        
        
    def PwrOutLimitsVal(self):
        """
        Determine what the power switch registers are set to, and find the equivalent floating point representation 
        due to calibration.
        """
        
        upper_dn = ((self.FpgaRegRd(_const.reg_upper_msb)) << 8) + self.FpgaRegRd(_const.reg_upper_lsb)
        lower_dn = ((self.FpgaRegRd(_const.reg_lower_msb)) << 8) + self.FpgaRegRd(_const.reg_lower_lsb)
        
        # Using linear approximation: y = ax + b
        upper = self.VinCalCoeff_A * upper_dn + self.VinCalCoeff_B
        lower = self.VinCalCoeff_A * lower_dn + self.VinCalCoeff_B
        
        return lower, upper

    def _IsVinCal(self):
        """
        Determine whether EGSE Vin reading has been calibrated.
        """
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 
        
        cal_points = self._GetVinCalNumEntries()
        if (cal_points == 255) or (cal_points == 0):
            return False 
        else:
            return True

    def _GetVinCalCoeff(self, dbg=False):
        """
        We map the Vin readings to polynomial's coefficients. This function returns the a, b, c coefficients for the polynomial.
        """
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return         
        
        # Determine number of entries 
        num_entries = self._GetVinCalNumEntries()#Must be 3.
        
        if (num_entries < 3):
            raise ValueError("Need 3x entries to properly fit parabola - calibration was not performed correctly.")
        
        # Get all entries' x (DN's) and y (voltage) values.
        x = numpy.zeros(num_entries)
        y = numpy.zeros(num_entries)
        for i in range(num_entries):
            addr_offset = 0x3FF50 + (i*4)
            #Grab X-val 
            dn0 = self._EepromFx3RdBt(addr_offset + 0)
            dn1 = self._EepromFx3RdBt(addr_offset + 1)
            x[i] = (dn1 << 8) + dn0
            
            #Grab Y-val 
            load0 = self._EepromFx3RdBt(addr_offset + 2)
            load1 = self._EepromFx3RdBt(addr_offset + 3)            
            y[i] = ((load1 <<8) + load0) / 1000.0#Divide by 1000, since it is stored x1000
        
        if dbg:
            print(f'X and Y values')
            for i in range(num_entries):
                print(f'x: {x[i]}, y: {y[i]}')
        
        #Fit to a polynomial of order 1, aka straight line.
        fit = numpy.polyfit(x, y, 1)
        a = fit[0]
        b = fit[1]
        #c = fit[2]
        c=0
        
        return a, b, c, fit

    def GetVinCal(self):
        """
        The Vin readings are calibrated using parabola, determine the appropriate x-value for the given y-value.
        """
        if self._IsVinCal:
            #y = a x + b 
            x = self.PwrOutRaw()
            y = (self.VinCalCoeff_A * x ) + self.VinCalCoeff_B
            return y
        else:
            raise exceptions.PwrSwitchError(f'Trying to read calibrated value, when this EGSEs Vin has not been calibrated.\n{e}')

    def GetVinUncal(self, verbose=False):
        """
        Determine the theoretical voltage BEFORE the switch, based on voltage divider circuit.

        """
        ratio = 2200 / (2200 + 39000)
        DN = self.PwrOutRaw()
        if verbose:
            print(f'Here is DN: {DN}')
        VMeas = DN * 0.0005#12bit ADC, ref voltage 2.048V
        VinUncal = VMeas / ratio
        
        return VinUncal
    
    def GetVin(self, verbose=False):
        """
        Simply return the most accurate voltage reading for Vin.
        """
        if self._VinCalibrated:
            vin = self.GetVinCal()
            if verbose:
                print(f'Vin is Calibrated')
        else:
            vin = self.GetVinUncal()
            if verbose:
                print(f'Vin Uncalibrated')
        return vin

    ## ========================================================================================= ##
    ##########_____________________ ADC and Current measurements ________________________##########

    def _ReadADC(self, chan=0, dbg=False):
        """
        The EGSE has a 11 channel, 12bit ADC. 
        This function allows us to read the various channel values.

        Arguments In:
            - chan (integer, 0 to 11) which channel are we reading from?
            

        Return:
            - val (12-bit value as int.) Digital number read at ADC. 
        """
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 
        
        #The ADC has 11 channels, up till now only channel zero is used, do this only once:
        if self.AdcMeasChannel != chan:
            try:
                self.FpgaRegWr(reg = _const.reg_chan_measure, data = chan)
                self.AdcMeasChannel = chan
            except Exception as e:
                raise exceptions.PwrSwitchError(f'Error setting which ADC channel to read from.\n{e}')


        reg_lsb =  _const.reg_avg_mux_lsb
        reg_msb =  _const.reg_avg_mux_msb
        
        # Wait time for value to settle, since this goes through moving average. This is conservatively sufficiently long.
        time.sleep(0.3)
        
        #Determine register values of ADC read. The ADC constantly reads the values.
        try:
            lsb = self.FpgaRegRd(reg = reg_lsb)
        except Exception as e:
            raise exceptions.PwrSwitchError(f'Error retrieving lsb data from ADC.\n{e}')
        try:
            msb = self.FpgaRegRd(reg = reg_msb)
        except Exception as e:
            raise exceptions.PwrSwitchError(f'Error retrieving msb data from ADC.\n{e}')

        #Tally up the values from 2 8bit registers.
        val = (msb<<8) + lsb
        if dbg:
            print('Raw reg val:', val)
        
        return int(val)

    def _GetCurrCalNumEntries(self):
        """
        Determine how many calibration points were used.
        """
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 
        
        val = self._EepromFx3RdBt(0x3FF00 + 40)
        return val
        
    def _IsCurrCal(self):
        """
        Determine whether EGSE current reading has been calibrated.
        """
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 

        cal_points = self._GetCurrCalNumEntries()
        if (cal_points == 255) or (cal_points == 0):
            return False 
        else:
            return True
    
    def _GetCurrCalCoeff(self, dbg=False):
        """
        We map the current readings to polynomial's coefficients. This function returns the a, b, c coefficients for the polynomial.
        """
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 

        # Determine number of entries 
        num_entries = self._GetCurrCalNumEntries()        
        if (num_entries < 3):
            raise ValueError("Need at least 3x entries to properly fit parabola - calibration was not performed correctly.")
        
        # Get all entries' x (DN's) and y (load) values.
        x = numpy.zeros(num_entries)
        y = numpy.zeros(num_entries)
        for i in range(num_entries):
            addr_offset = 0x3FF00 + (i*4)
            #Grab X-val 
            dn0 = self._EepromFx3RdBt(addr_offset + 0)
            dn1 = self._EepromFx3RdBt(addr_offset + 1)
            x[i] = (dn1 << 8) + dn0
            
            #Grab Y-val 
            load0 = self._EepromFx3RdBt(addr_offset + 2)
            load1 = self._EepromFx3RdBt(addr_offset + 3)            
            y[i] = ((load1 <<8) + load0) / 1000.0#Divide by 1000, since it is stored x1000
        
        if dbg:
            print(f'X and Y values')
            for i in range(num_entries):
                print(f'x: {x[i]}, y: {y[i]}')
        
        #Fit to a polynomial 
        fit = numpy.polyfit(x, y, 2)
        a = fit[0]
        b = fit[1]
        c = fit[2]
        
        return a, b, c

    def _GetCalCurr(self):
        """
        Grab and return the values for the current calibration.
        If memory is either 0x00, or 0xFF, then assume it has not been calibrated (backwards compatibility)
        """
        if self.HwRevision == 3:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 
        
        #Read from page 0 of sub-sector 4079.
        res = self._FlashReadPage(address = 0xFEF000)
        
        if ((res[0]==0x00) and (res[1]==0x00) and (res[2]==0x00) and (res[3]==0x00)) or \
           ((res[0]==0xFF) and (res[1]==0xFF) and (res[2]==0xFF) and (res[3]==0xFF)):
            Gain = 0#If this is true, it is uncalibrated.
            Vref = 0#If this is true, it is uncalibrated.
        else:
            Gain = res[0] + res[1]*256
            Vref = (res[2] + (res[3]*256) ) / 1000                    
        
        return Gain, Vref

    def CurrMeas(self, chan = 0, avg = True):
        """
        The power provided by the EGSE to the output over the one-to-one harness has a current reading mechanism (12bit).
        We can determine the current being drawn.
        The reference voltage is 2.048V, the sense resistor is 5 milli Ohm

        Argguments In:
            - chan (integer, 0 to 11) which channel are we reading from?
            - avg (bool), if true (default), we get the average of the last 16 samples, if false, we get the latest instantaneous value.

        Return:
            - I_measured (float), the current flowing through the sense resistor in [A].
        """
        if self.HwRevision == 3:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 
        
        #The ADC has 12 channels, up till now only channel zero is used, do this only once:
        if len(self.AdcCurrMeasChannel) == 0:
            #  if self.debug:
            #      print('Setting the channel up')
            #  self.AdcCurrMeasChannel.append('Channel Set')
            try:
                self.FpgaRegWr(reg = _const.reg_chan_measure, data = chan)
            except Exception as e:
                raise exceptions.PwrSwitchError(f'Error setting which ADC channel to read from.\n{e}')
            

        #Determine whether we want instantaneous current, or average of last 16 samples.
        if avg == True:
            reg_lsb = _const.reg_avg_current_lsb
            reg_msb = _const.reg_avg_current_msb
        else:
            reg_lsb = _const.reg_measured_current_lsb
            reg_msb = _const.reg_measured_current_msb

        #Determine register values of ADC read. The ADC constantly reads the values.
        try:
            lsb = self.FpgaRegRd(reg = reg_lsb)
        except Exception as e:
            raise exceptions.PwrSwitchError(f'Error retrieving lsb data from ADC.\n{e}')

        try:
            msb = self.FpgaRegRd(reg = reg_msb)
        except Exception as e:
            raise exceptions.PwrSwitchError(f'Error retrieving msb data from ADC.\n{e}')

        #Tally up the values from 2 8bit registers.
        val = (msb<<8) + lsb

        if self.debug:
            print('val', val)

        V_per_quant_step = 0.0005
        Vout = val * V_per_quant_step

        if self.debug:
            print('Vout: ', Vout , ' [V]')
    
        #Uncalibrated
        if (self.CurrCirVref == 0) and (self.CurrCirGain == 0) or ():
            I_load = (Vout - 2.048) / (0.005 * 200)
        else:
        #Using Calibrated values
            I_load = (Vout - self.CurrCirVref) / (0.005 * self.CurrCirGain)
        
        #But since this is the reverse current (since we are measuring backwards), we multiply with -1.
        I_measured = I_load *-1
        

        #Determine resolution (between bits, what is the change in current)
        I_load_a = (Vout - 2.048) / (0.005 * 200)
        I_load_b = ((Vout + V_per_quant_step) - 2.048) / (0.005 * 200) #If it is one quantisation step lower.
        if self.debug:#self.debug:
            print('    Variation due to Quantisation/resolution :',  abs (I_load_a - I_load_b) , '[A]')
            print('I_load: ', I_load, ' [A]')
            print('I_measured: ', I_measured, ' [A]')
            print('lsb', lsb)
            print('msb', msb)
            print('I_measured', I_measured)

        return I_measured

    def CurrMeas_v3(self, chan = 0, avg = True, dbg = False):
        """
        The power provided by the EGSE to the load (CE), has a current reading mechanism (12bit).
        We can determine the current being drawn.
        The reference voltage is 2.048V, the sense resistor is 2 milli Ohm, current sense gain is 200x

        Argguments In:
            - chan (integer, 0 to 11) which channel are we reading from?
            - avg (bool), if true (default), we get the average of the last 64 samples, if false, we get the latest instantaneous value.

        Return:
            - I_measured (float), the current flowing through the sense resistor in [A].
        """
        if self.HwRevision == 2:
            print(f'WARNING: accessing functionality which is not supported by HwRevision {self.HwRevision}')
            return 
        
        #Determine whether we want instantaneous current, or average of last 64 samples.
        #if avg == True:
        reg_lsb = self.FpgaRegRd(reg = _const.reg_avg_current_lsb)
        reg_msb = self.FpgaRegRd(reg = _const.reg_avg_current_msb)
        
        val = reg_lsb + (reg_msb << 8)
        
        #Subtract from 4095, since the range is inverted
        val_post_inv = 4095 - val
        if dbg:
            print(f'raw Val is: {val}')
            print(f'val_post_inv is: {val_post_inv}')
            
        
        
        #The current through 2mOhm is the same as current through load.
        if self._CurrCalibrated:
            x = val_post_inv
            # y = ax^2 + bx + c
            I_Load_Calibrated = self.CurrCalCoeff_A * x**2 + self.CurrCalCoeff_B * x + self.CurrCalCoeff_C        
            
            I_Load = I_Load_Calibrated 
        else:
        
            V_per_quant_step = 0.0005#12 bit, 2.048 range, 2.048/2^12 = 0.0005
            V_amp = val_post_inv * V_per_quant_step#This is the Voltage Accros the 2mOhm resistor AFTER the 200x amplification.
            if dbg:
                print(f'V_amp is: {V_amp}')
            
            #The voltage accross the 2mOhm resistor, undo the effect of 200x gain.
            V_2mOhm = V_amp / 200
            if dbg:
                print(f'V_2mOhm is: {V_2mOhm}')
            
            #The current through 2 mOhm resistor, due to the voltage. I = V/R 
            I_2mOhm = V_2mOhm / 0.002
            if dbg:
                print(f'I_2mOhm: {I_2mOhm}')        
        
            #This takes the above calculations and brings it all into 1 equation it.
            I_Load_simple = (-0.00125 * val) + 5.11875
            
            I_Load = I_Load_simple
        
        #Incase the result is negative, it is simply close to zero. Current flowing in opposite direction is not possible by design.
        if I_Load < 0.0:
            I_Load = 0.0
        
        return I_Load

'''
Simera Sense EGSE Exception Class Definitions
Copyright (c) 2019-2020 Simera Sense (info@simerasense.com).
Released under the GNU GPLv3.0 License.

Exceptions can be raised with an optional argument that is added to __str__ output

Usage example:
    import simera.pylibEgseFx3 as egse
    try:
        raise egse.HardwareError('hw err')
    except (egse.HardwareError) as e:
        print(e) # to print the error message

        #or don't print/handle the exception here, but raise it again with a better message
        #raise egse.HardwareError('a new message') # if you want to push it higher
'''


class Error (Exception):
    def __init__ (self, msg=''): self.msg = msg
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'

class InputError (ValueError):
    def __init__ (self, msg=''): self.msg = msg#JL added this, now the exception messages print to screen.
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'

class HardwareError (Error):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'

class EgseNotFoundError (HardwareError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Cannot find the EGSE\nPlease make sure it is plugged into a USB 3.0 port on the computer. {self.msg}'

class USBError (HardwareError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'

class UsbOpenError (USBError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Cannot open the EGSE device\nMake sure all python sessions are closed, and that you have waited at least 4 seconds after plugging in the EGSE before trying to access it. {self.msg}'

class UsbControlTransferWriteError (USBError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. USB control transfer (write) failed. {self.msg}'

class UsbControlTransferReadError (USBError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. USB control transfer (read) failed. {self.msg}'

class InitialisationError (Error):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'

class CalibrationError (Error):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'

class ControlInterfaceError (Error):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'

class DataInterfaceError (Error):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'

class GpioError (Error):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'
    
class LvdsError (GpioError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'    

class UsrLedError(Error):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'

class LedError(Error):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'    

class PwrSwitchError(Error):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'
    
class CEPowerError(Error):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'
    
class SPIError (ControlInterfaceError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'

class OneWireError(Error):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'


class I2CError (ControlInterfaceError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'

class I2CNoSlaveAckError (I2CError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. No I2C slave acknowledge. {self.msg}'
    def __int__ (self): return 0x01

class I2CNoDataFromSlaveError (I2CError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. No data from I2C slave. {self.msg}'
    def __int__ (self): return 0x02

class I2CBusBusyError (I2CError):
    def __str__ (self): return f'EGSE I2C {self.__class__.__name__}. I2C bus is busy. {self.msg}'
    def __int__ (self): return 0x04

class I2CIncompleteTransactionError (I2CError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Incomplete I2C transaction. {self.msg}'
    def __int__ (self): return 0x05
class I2CIncompleteTransactionNoDataError (I2CIncompleteTransactionError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Incomplete I2C transaction with no data transferred. {self.msg}'
    def __int__ (self): return 0x06
class I2CIncompleteTransactionWithDataError (I2CIncompleteTransactionError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Incomplete I2C transaction with partial data transferred. {self.msg}'
    def __int__ (self): return 0x07
class I2CTransactionCompleteNoDataError (I2CIncompleteTransactionError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. I2C transaction completed with no data transferred. {self.msg}'
    def __int__ (self): return 0x08

class I2CLinkConfigurationError (I2CError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. I2C link configuration failed. {self.msg}'
    def __int__ (self): return 0x09

class I2CTransactionTimeoutError (I2CError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. I2C transaction timed out. {self.msg}'
    def __int__ (self): return 0x0A

class I2CAddressOutOfBoundsError (I2CError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. I2C address is out of bounds. {self.msg}'
    def __int__ (self): return 0x10

class I2CRegisterOutOfRangeError (I2CError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. I2C register out of range. {self.msg}'
    def __int__ (self): return 0x11

class I2CTransactionLengthError (I2CError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. I2C length is out of range. {self.msg}'
    def __int__ (self): return 0x12

class I2CTooManyDataIndicesError (InputError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. I2C data parameter contains too many indices. {self.msg}'
    def __int__ (self): return 0x13

class EgseSoftwareUpdateError (Error):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'

class EgseFirmwareUpdateError (Error):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'

class EgseFirmwareReadError (Error):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'


class SpWError(Error):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'
    
class SpWConfigClkError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Could not set up the clock appropriately for the SpW. {self.msg}'

class SpWResetError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Could not reset SpW core. {self.msg}'

class SpWAutoStartError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Could not Autostart SpW core. {self.msg}'

class SpWStatusError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Could not determine status of SpW core. {self.msg}'

class SpWTxLinkRateError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Could not set the Tx Link Rate. {self.msg}'


class SpWErrCredError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Credit error detected. {self.msg}'

class SpWErrParError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Parity error detected in the Run state. {self.msg}'
    
class SpWErrParCredError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Parity error detected in the Run state. ALSO Credit error detected. {self.msg}'

class SpWErrDiscError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}.Disconnection detected in the Run state. {self.msg}'

class SpWErrDiscCredError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}.Disconnection detected in the Run state. ALSO Credit error detected. {self.msg}'

class SpWErrDiscParError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Disconnection detected in the Run state. ALSO Parity error detected in the Run state. {self.msg}'

class SpWErrDiscParCredError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Disconnection detected in the Run state ALSO Parity error detected in the Run state. ALSO Credit error detected. {self.msg}'

class SpWErrEscError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Invalid escape sequence detected in the Run state. {self.msg}'

class SpWErrEscCredError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Invalid escape sequence detected in the Run state. ALSO Credit error detected. {self.msg}' 

class SpWErrEscParError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Invalid escape sequence detected in the Run state. ALSO Parity error detected in the Run state. {self.msg}' 

class SpWErrEscParCredError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Invalid escape sequence detected in the Run state. ALSO Parity error detected in the Run state. ALSO Credit error detected.{self.msg}' 

class SpWErrEscDiscError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Invalid escape sequence detected in the Run state. ALSO Disconnection detected in the Run state.{self.msg}' 
    
class SpWErrEscDiscCredError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Invalid escape sequence detected in the Run state. ALSO Disconnection detected in the Run state. ALSO Credit error detected. {self.msg}'     

class SpWErrEscDiscParError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Invalid escape sequence detected in the Run state. ALSO Disconnection detected in the Run state. ALSO Parity error detected in the Run state. {self.msg}'     

class SpWErrEscDiscParCredError(SpWError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Invalid escape sequence detected in the Run state. ALSO Disconnection detected in the Run state. ALSO Parity error detected in the Run state. ALSO Credit error detected. {self.msg}'     



    
    
class SpWWrError  (ControlInterfaceError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'
    
class SpWWrTimeoutError  (SpWWrError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. Could not send the TC data within time to the TxFifo (the Fifo on the SpW core). {self.msg}'    
    
class SpWRdError  (ControlInterfaceError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'    
    
class SpWRdTimeoutError (SpWRdError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'    
    
class SpWDataError(DataInterfaceError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'

class SpWDataTimedOutMidPacket(SpWDataError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. A timeout occurred mid-packet, i.e. a packet couldn\'t finish being sent/read out via the High Speed data readout, or no data was sent at all.{self.msg}'


class HsdiError (DataInterfaceError):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'

class InputParameterError (Error):
    def __str__ (self): return f'EGSE {self.__class__.__name__}. {self.msg}'


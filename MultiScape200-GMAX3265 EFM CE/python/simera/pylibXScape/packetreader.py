'''
Simera Sense xScape Packet Reader
Copyright (c) 2019-2020 Simera Sense (info@simerasense.com)
Released under MIT License.

The PacketReader extracts Image Data packets from a downloaded file

Usage example:
    import simera.pylibXScape

    pp = simera.pylibXScape.PacketParser()
    pr = simera.pylibXScape.PacketReader('download_file.bin')
    pr.setCryptoParameters(key=TheKEY, iv=TheIV) # if encryption was enabled during readout
    for p in pr:
        pp.parsePacket(p)

    # grab the handle to the ImageData object
    image_data = pp.ImageData()
    # print a summary of the ImageData contents
    print(image_data)
    # export all images and thumbnails to PNG files
    image_data.toPng()
'''

import zlib
import numpy
from . import exceptions


class PacketReader:

    cHDR_Sync           = [b'S', b'S']  #0x5353 / 'SS'

    def __init__(self, input=None, debug=False):
        self._debug = debug
        self.inputFile = None
        self.input = None
        self.inputPtr = 0
        ##self.inputLength = 0
        ##self.inputMaxIndex = 0
        self.packet = None
        self.crypto_key = None
        self.crypto_iv  = None

        if not input is None:
            self.setInput(input)

    def __iter__(self):
        return self

    def __next__(self):
        #while True:
        #    packet = self.nextPacket()
        #    if packet:
        #        return packet
        #    elif packet == -1:
        #        # CRC error. Ignore and continue to get next packet
        #        continue
        #    else:
        #        raise StopIteration
        sp_last_count = 0
        sp_payload = bytearray()

        while True:
            packet = self.nextPacket()
            if not packet:
                break;
            if packet['Subpacket'] != 0:
                # this is a sub-packet
                temp = packet['Subpacket']
                packet['SubpacketEnd']   = (temp & 0x80) != 0
                packet['SubpacketStart'] = (temp & 0x40) != 0
                packet['SubpacketCount'] = (temp & 0x3f)
                if packet['SubpacketStart']:
                    sp_payload = bytearray(packet['raw'][:7:1])
                    sp_payload.append(0)    # set sub-packet flags to zero
                    sp_last_count = 0
                    #if self._debug:
                    #    print("Subpacket START")
                else:
                    sp_last_count+=1
                if sp_last_count != packet['SubpacketCount']:
                    #sub-packet sequence is not correct
                    if self._debug:
                        print(f"Sub-packet sequence count error. Expected count value of {sp_last_count} but got {packet['SubpacketCount']}")
                    #raise StopIteration
                else:
                    if self._debug:
                        print(f"Subpacket APPEND, lenth field is {packet['Length']}")
                    sp_payload.extend(bytearray(packet['raw'][8::1]))
                if packet['SubpacketEnd']:
                    packet['Length'] = len(sp_payload)-8
                    length_bytes = packet['Length'].to_bytes(length=3, byteorder='little', signed=False)
                    sp_payload[4] = length_bytes[0]
                    sp_payload[5] = length_bytes[1]
                    sp_payload[6] = length_bytes[2]
                    packet['raw'] = bytes(sp_payload)

                    #if self._debug:
                    #    print(f"Subpacket END, raw length = {len(sp_payload)} bytes")
                    if packet['CRC-En']:
                        packet['CRC'] = self.calcCRC(packet['raw'])
                        if self._debug:
                            print(f"Subpacket END, length = {len(sp_payload)}+4 bytes")
                    else:
                        if self._debug:
                            print(f"Subpacket END, length = {len(sp_payload)} bytes")
                    return packet
            else:
                return packet
        raise StopIteration

    def enableDebug(self):
        """
        Enable debug output to console
        """
        self._debug = True

    def disableDebug(self):
        """
        Disable the debug output to console
        """
        self._debug = False

    def setCryptoParameters(self, key, iv):
        self.crypto_key = bytes(key)
        self.crypto_iv  = bytes(iv)

    def setInput(self, input):
        self.closeInput()
        if isinstance(input, str):
            try:
                self.input = numpy.memmap(input, dtype='uint8', mode='r')
                if self._debug:
                    print(f"Processing file '{input}'")
            except:
                if self._debug:
                    print(f"Error opening file '{input}'")
                raise
        else:
            if not isinstance(input, (numpy.memmap, numpy.ndarray, bytearray)):
                raise exceptions.InputError("Input must be a filename, or bytearray, or numpy.ndarray with dtype=uint8")
            else:
                self.input = input
                if self._debug:
                    print(f"Processing buffer'")
        ##self.inputLength = len(input)
        ##self.inputMaxIndex = self.inputLength - 1
        ##if self._debug:
        ##    print(f"size = {self.inputLength} bytes, max index = {self.inputMaxIndex}")

    def closeInput(self):
        if self.input and type(self.input) == 'numpy.memmap':
            try:
                del self.input
            except:
                print('Error closing file')
                raise
            else:
                self.input = None

    def calcCRC(self, rawPacket=None):
        if rawPacket is None:
            if self.packet is None:
                return False
            rawPacket = self.packet['raw']
        c = zlib.crc32(rawPacket)
        return c & 0xffffffff

    def inputRead(self, n):
        temp = self.input[self.inputPtr:self.inputPtr+n:1];
        self.inputPtr += n

        return temp.tobytes()

    def findNextPacket(self):
        search_length = 0

        sync = [0, 0]
        sync[1] = self.inputRead(1)
        sync[0] = self.inputRead(1)
        while sync != self.cHDR_Sync:
            temp = self.inputRead(1)
            if len(temp) == 0:
                return False
            sync[1] = sync[0]
            sync[0] = temp
            search_length += 1

        if search_length > 0:
            print(f"Warning: Skipped {search_length} bytes to start of next packet")

        # shift pointer 2 bytes back from current position
        self.inputPtr -= 2
        #--- we are now at the start of the packet sync
        # and return.
        return True

    def nextPacket(self):
        while self.findNextPacket():
            self.packet = None
            packet={}

            #no checks, we know there are at least 2 bytes here
            packet['Sync'] = self.inputRead(2)

            temp = self.inputRead(1)

            if len(temp) == 0:
                if self._debug:
                    print('EOF')
                return False
            temp = int.from_bytes(temp, byteorder="little", signed=False)
            notflags = temp >> 4
            flags = temp & 0x0f
            if (flags != (0xf - notflags)):
                if self._debug:
                    print(f"Error in Packet Header at position {self.inputPtr} - Flags({flags:04b}) and its complement({notflags:04b}) do not match")
            packet['Flags'] = flags
            packet['CRC-En'] = False
            if flags & 0x01 == 1:
                packet['CRC-En'] = True
            packet['Encrypt-En'] = False
            if flags & 0x02 == 2:
                packet['Encrypt-En'] = True

            temp = self.inputRead(1)
            if len(temp) == 0:
                if self._debug:
                    print('EOF')
                return False
            packet['PID'] = int.from_bytes(temp, byteorder="little", signed=False)

            temp = self.inputRead(3)
            if len(temp) < 3:
                if self._debug:
                    print('EOF')
                return False
            packet['Length'] = int.from_bytes(temp, byteorder="little", signed=False)

            temp = self.inputRead(1)
            if len(temp) == 0:
                if self._debug:
                    print('EOF')
                return False
            packet['ReservedByte'] = int.from_bytes(temp, byteorder="little", signed=False)
            packet['Subpacket'] = int.from_bytes(temp, byteorder="little", signed=False)

            # shift pointer to start of packet header and save packet start position
            self.inputPtr -= 8
            packet['position'] = self.inputPtr
            packetlen = packet['Length'] + 8

            temp = self.inputRead(packetlen) # (packet['Length']+8)
            if len(temp) < packetlen:
                if self._debug:
                    print('EOF')
                return False
            packet['raw'] = temp
            packet['payload'] = temp[8:]

            if self._debug:
                print(f"found packet @ {packet['position']:4}: PID=0x{packet['PID']:02x}, Len={packet['Length']:3}, Flags=0x{packet['Flags']:02x}, Sub-packet=0x{packet['Subpacket']:02x}")

            if packet['CRC-En']:
                temp = self.inputRead(4)
                if len(temp) < 4:
                    if self._debug:
                        print('EOF')
                    return False
                packet['CRC'] = int.from_bytes(temp, byteorder="little", signed=False)
                crc = self.calcCRC(packet['raw'])
                if not crc:
                    if self._debug:
                        print('error calculating CRC')
                    return False
                #print(f"Calculated CRC = 0x{packet['CRC']:08x}  |  CRC from input = 0x{crc:08x}")
                if crc != packet['CRC']:
                    print(f"Warning: Packet @ {packet['position']:4} has CRC ERROR.  Calculated CRC = 0x{crc:08x}  |  CRC from input = 0x{packet['CRC']:08x}")
                    # Uncomment to Quit if CRC mismatch.
                    #return -1

                    # Continue searching for next sync and continue to process the file
                    self.inputPtr = packet['position'] + 2
                    continue

                #else:
                #    print(f"CRC_OK          Calculated CRC = 0x{packet['CRC']:08x}  |  CRC from input = 0x{crc:08x}")

            # if encrypted, decrypt the payload
            if packet['Encrypt-En']:
                if self.crypto_iv is None or self.crypto_key is None:
                    print("Encrypted packet detected, but Key and IV not set. Please set key,iv using method 'setCryptoParameters(key, iv)'")
                    return False
                try:                    
                    # use pyaes library
                    import pyaes
                except ImportError:                                                            
                    raise exceptions.ImportError("Please install the python 'pyaes' library by running the following command:\n     > pip install pyaes")                    
 
                # perform decrypt
                print(f"Decrypting packets... please wait.")
                _aes = pyaes.AESModeOfOperationCTR(self.crypto_key, pyaes.Counter(int.from_bytes(self.crypto_iv, "big")))
                temp = _aes.decrypt(packet['payload'])

                packet['payload'] = temp
                packet['raw'] = packet['raw'][:8] + temp # replace 'raw' payload with decrypted payload
                if self._debug:
                    print(f"__decrypted packet : PID=0x{packet['PID']:02x},Len={packet['Length']:3},Flags=0x{packet['Flags']:02x} : {packet['payload']}")

            self.packet = packet
            return packet
        return False


class CcsdsPacketReader:

    cHDR_CCSDS              = [b'\x00', b'\x00']
    cHDR_CCSDS_Primary      = [b'\x12', b'\x0d']
    cHDR_CCSDS_Primary_Only = [b'\x12', b'\x05']
    cHDR_Sync               = [b'S', b'S']  #0x5353 / 'SS'

    #cHDR_Sync offset in bytes for proto:  0   1   2   3
    cHDR_Sync_Offset        =            [ 0, 15,  4, 13]


    def __init__(self, input=None, debug=False, proto=1, apid=0x000): #filename=None, buffer=None):
        self._debug = debug
        self.inputFile = None
        self.input = None
        self.inputPtr = 0
        self.inputLength = 0
        self.inputMaxIndex = 0
        self.packet = None
        self.crypto_key = None
        self.crypto_iv  = None

        if not input is None:
            self.setInput(input)

        self._protocol = proto  
        self._ccsds_apid = apid
        self.setCcsdsHeader()

    def __iter__(self):
        return self

    def __next__(self):
        #packet = self.nextPacket()
        #if packet:
        #    return packet
        sp_last_count = 0
        sp_payload = bytearray()

        while True:
            packet = self.nextPacket()
            if not packet:
                break;
            if packet['Subpacket'] != 0:
                # this is a sub-packet
                temp = packet['Subpacket']
                packet['SubpacketEnd']   = (temp & 0x80) != 0
                packet['SubpacketStart'] = (temp & 0x40) != 0
                packet['SubpacketCount'] = (temp & 0x3f)
                if packet['SubpacketStart']:
                    sp_payload = bytearray(packet['raw'][:7:1])
                    sp_payload.append(0)    # set sub-packet flags to zero
                    sp_last_count = 0
                    if self._debug:
                        print("Subpacket START")
                else:
                    sp_last_count+=1
                if sp_last_count != packet['SubpacketCount']:
                    #sub-packet sequence is not correct
                    if self._debug:
                        print(f"Sub-packet sequence count error. Expected count value of {sp_last_count} but got {packet['SubpacketCount']}")
                    #raise StopIteration
                else:
                    if self._debug:
                        print(f"Subpacket APPEND, length field is {packet['Length']}")
                    sp_payload.extend(bytearray(packet['raw'][8::1]))
                if packet['SubpacketEnd']:
                    packet['raw'] = bytes(sp_payload)
                    packet['Length'] = len(sp_payload)
                    if self._debug:
                        print(f"Subpacket END, raw length = {len(sp_payload)} bytes")
                    return packet
                
            else:
                return packet
        raise StopIteration

    def enableDebug(self):
        """
        Enable debug output to console
        """
        self._debug = True

    def disableDebug(self):
        """
        Disable the debug output to console
        """
        self._debug = False

    def setCryptoParameters(self, key, iv):
        self.crypto_key = bytes(key)
        self.crypto_iv  = bytes(iv)

    def setDataPacketProtocol(self, proto):
        """
        Set the Data Packet Protocol.
        0 = None
        1 = Custom (CCSDS with DSID)
        2 = CCSDS Basic (no Secondary)
        3 = CCSDS Full
        """
        self._protocol = proto
        self.setCcsdsHeader()

    def setCcsdsApid(self, apid=0x000):
        """
        Set 11-bit APID
        """        
        self._ccsds_apid = apid
        self.setCcsdsHeader()
        
    def setCcsdsHeader(self):   
        """
        Generate the expected fuirst 2 CCSDS Header Bytes
        """
        temp = self._ccsds_apid & 0x7FF        
        # Set Secondary Flag        
        if self._protocol in(1,3):
            temp |= 0x800         
        self.cHDR_CCSDS[0] = ((temp >> 0) & 0xFF).to_bytes(1,'little')
        self.cHDR_CCSDS[1] = ((temp >> 8) & 0xFF).to_bytes(1,'little')                

    def setInput(self, input):
        self.closeInput()
        if isinstance(input, str):
            try:
                self.input = numpy.memmap(input, dtype='uint8', mode='r')
                if self._debug:
                    print(f"Processing file '{input}'")
            except:
                if self._debug:
                    print(f"Error opening file '{input}'")
                raise
        else:
            if not isinstance(input, (numpy.memmap, numpy.ndarray, bytearray)):
                raise exceptions.InputError("Input must be a filename, or bytearray, or numpy.ndarray with dtype=uint8")
            else:
                self.input = input
                if self._debug:
                    print(f"Processing buffer'")
        self.inputLength = len(input)
        self.inputMaxIndex = self.inputLength - 1
        if self._debug:
            print(f"size = {self.inputLength} bytes, max index = {self.inputMaxIndex}")

    def closeInput(self):
        if self.input and type(self.input) == 'numpy.memmap':
            try:
                del self.input
            except:
                print('Error closing file')
                raise
            else:
                self.input = None

    def calcCRC(self, rawPacket=None):
        if rawPacket is None:
            if self.packet is None:
                return False
            rawPacket = self.packet['raw']
        c = zlib.crc32(rawPacket)
        return c & 0xffffffff

    def inputRead(self, n):
        temp = self.input[self.inputPtr:self.inputPtr+n:1];
        self.inputPtr += n

        return temp.tobytes()

    def findNextPacket(self):
        search_length = 0
        startPtr = self.inputPtr

        while True:
            sync = [0, 0]
            sync[1] = self.inputRead(1)
            sync[0] = self.inputRead(1)        
            
            # Look for first 2 CCSDS bytes (APID and Secondary Header Flag)        
            while sync != self.cHDR_CCSDS:
                temp = self.inputRead(1)
                if len(temp) == 0:
                    return False
                sync[1] = sync[0]
                sync[0] = temp
                search_length += 1

            if search_length > 0:
                print(f"Warning: Skipped {search_length} bytes to start of next CCSDS packet")

            # shift pointer forward from current position, to start of CCSDS Packet Payload Field, based on protocol
            #if self._protocol == 1:
            #    self.inputPtr += 15
            #elif  self._protocol == 2:
            #    self.inputPtr += 4
            #elif  self._protocol == 3:
            #    self.inputPtr += 13
            self.inputPtr += self.cHDR_Sync_Offset[self._protocol]

            sync = [0, 0]
            sync[1] = self.inputRead(1)
            if len(sync[1]) == 0:
                return False
            sync[0] = self.inputRead(1)
            if len(sync[0]) == 0:
                return False
            if sync != self.cHDR_Sync:
                print("Warning: CCSDS Header found without Image Data Header. Maybe the wrong Data Packet Protocol was selected?")
                search_length += 2
                self.inputPtr = startPtr + 2
                startPtr += 2
                continue
            else:
                break

        # shift pointer 2 bytes back from current position
        self.inputPtr -= 2
        #--- we are now at the start of the packet sync
        # and return.
        return True

    def nextPacket(self, input=None):
        while self.findNextPacket():
            self.packet = None
            packet={}

            #no checks, we know there are at least 2 bytes here
            packet['Sync'] = self.inputRead(2)

            temp = self.inputRead(1)

            if len(temp) == 0:
                if self._debug:
                    print('EOF')
                return False
            temp = int.from_bytes(temp, byteorder="little", signed=False)
            notflags = temp >> 4
            flags = temp & 0x0f
            if (flags != (0xf - notflags)):
                if self._debug:
                    print(f"Error in Packet Header at position {self.inputPtr} - Flags({flags:04b}) and its complement({notflags:04b}) do not match")
            packet['Flags'] = flags
            packet['CRC-En'] = False
            if flags & 0x01 == 1:
                packet['CRC-En'] = True
            packet['Encrypt-En'] = False
            if flags & 0x02 == 2:
                packet['Encrypt-En'] = True

            temp = self.inputRead(1)
            if len(temp) == 0:
                if self._debug:
                    print('EOF')
                return False
            packet['PID'] = int.from_bytes(temp, byteorder="little", signed=False)

            temp = self.inputRead(3)
            if len(temp) < 3:
                if self._debug:
                    print('EOF')
                return False
            packet['Length'] = int.from_bytes(temp, byteorder="little", signed=False)


            temp = self.inputRead(1)
            if len(temp) == 0:
                if self._debug:
                    print('EOF')
                return False
            packet['ReservedByte'] = int.from_bytes(temp, byteorder="little", signed=False)
            packet['Subpacket'] = int.from_bytes(temp, byteorder="little", signed=False)

            # shift pointer to start of packet header and save packet start position
            self.inputPtr -= 8
            packet['position'] = self.inputPtr
            packetlen = packet['Length'] + 8

            temp = self.inputRead(packetlen) # (packet['Length']+8)
            if len(temp) < packetlen:
                if self._debug:
                    print('EOF')
                return False
            packet['raw'] = temp
            packet['payload'] = temp[8:]

            if self._debug:
                print(f"found packet @ {packet['position']:4}: PID=0x{packet['PID']:02x}, Len={packet['Length']:3}, Flags=0x{packet['Flags']:02x}, Sub-packet=0x{packet['Subpacket']:02x}")

            if packet['CRC-En']:
                temp = self.inputRead(4)
                if len(temp) < 4:
                    if self._debug:
                        print('EOF')
                    return False
                packet['CRC'] = int.from_bytes(temp, byteorder="little", signed=False)
                crc = self.calcCRC(packet['raw'])
                if not crc:
                    if self._debug:
                        print('error calculating CRC')
                    return False
                #print(f"Calculated CRC = 0x{packet['CRC']:08x}  |  CRC from input = 0x{crc:08x}")
                if crc != packet['CRC']:
                    print(f"WARNING: Packet @ {packet['position']:4} has CRC ERROR.  Calculated CRC = 0x{packet['CRC']:08x}  |  CRC from input = 0x{crc:08x}")
                    # Uncomment to Quit if CRC mismatch.
                    #return -1

                    # Continue searching for next sync and continue to process the file
                    self.inputPtr = packet['position'] + 2
                    continue

                #else:
                #    print(f"CRC_OK          Calculated CRC = 0x{packet['CRC']:08x}  |  CRC from input = 0x{crc:08x}")

            # if encrypted, decrypt the payload
            if packet['Encrypt-En']:
                if self.crypto_iv is None or self.crypto_key is None:
                    print("Encrypted packet detected, but Key and IV not set. Please set key,iv using method 'setCryptoParameters(key, iv)'")
                    return False
                try:                    
                    # use pyaes library
                    import pyaes
                except ImportError:                                                            
                    raise exceptions.ImportError("Please install the python 'pyaes' library by running the following command:\n     > pip install pyaes")                    
 
                # perform decrypt
                print(f"Decrypting packets... please wait.")
                _aes = pyaes.AESModeOfOperationCTR(self.crypto_key, pyaes.Counter(int.from_bytes(self.crypto_iv, "big")))
                temp = _aes.decrypt(packet['payload'])

                packet['payload'] = temp
                packet['raw'] = packet['raw'][:8] + temp # replace 'raw' payload with decrypted payload
                if self._debug:
                    print(f"__decrypted packet : PID=0x{packet['PID']:02x},Len={packet['Length']:3},Flags=0x{packet['Flags']:02x} : {packet['payload']}")

            self.packet = packet
            return packet
        return False


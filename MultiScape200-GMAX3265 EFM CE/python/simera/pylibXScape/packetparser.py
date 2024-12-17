'''
Simera Sense xScape Packet Parser
Copyright (c) 2019-2020 Simera Sense (info@simerasense.com)
Released under MIT License.

The Packet Parser parses image data packets into an ImageData instance

Usage example:
    import simera.pylibXScape

    pp = simera.pylibXScape.PacketParser()

    for p in simera.pylibXScape.PacketReader('download_part_1.bin'):
        pp.parsePacket(p)

    # Run a for loop for each file if download was split
    for p in simera.pylibXScape.PacketReader('download_part_2.bin'):
        pp.parsePacket(p)

    # grab the handle to the ImageData object
    image_data = pp.ImageData()

    # print a summary of the ImageData contents
    print(image_data)

    # export all raw images, thumbnails, and compressed segments to PNG files
    image_data.toPng()
'''

import array
from . import exceptions
from . import imagedata
from ctypes import cdll, POINTER, c_uint8, c_uint16, c_int, cast, c_char
import numpy as np


PRODUCT_ID_MONOSCAPE50                       = 52197
PRODUCT_ID_MONOSCAPE50_ENCLOSURE             = 55407
PRODUCT_ID_MONOSCAPE100                      = 55309
PRODUCT_ID_MONOSCAPE100_ENCLOSURE            = 55410
PRODUCT_ID_MONOSCAPE_CMV12000_EFM_IE         = 55418
PRODUCT_ID_MONOSCAPE_CMV12000_EFM_CE         = 55419
PRODUCT_ID_MONOSCAPE200                      = 55414
PRODUCT_ID_MONOSCAPE200_ENCLOSURE            = 55415
PRODUCT_ID_MONOSCAPE_GMAX3265_EFM_IE         = 55428
PRODUCT_ID_MONOSCAPE_GMAX3265_EFM_CE         = 55429
PRODUCT_ID_TRISCAPE50                        = 46448
PRODUCT_ID_TRISCAPE50_ENCLOSURE              = 55408
PRODUCT_ID_TRISCAPE100                       = 34293
PRODUCT_ID_TRISCAPE100_ENCLOSURE             = 55411
PRODUCT_ID_TRISCAPE_CMV12000_EFM_IE          = 55420
PRODUCT_ID_TRISCAPE_CMV12000_EFM_CE          = 55421
PRODUCT_ID_TRISCAPE200                       = 34755
PRODUCT_ID_TRISCAPE200_ENCLOSURE             = 55416
PRODUCT_ID_TRISCAPE_GMAX3265_EFM_IE          = 55430
PRODUCT_ID_TRISCAPE_GMAX3265_EFM_CE          = 55431
PRODUCT_ID_MULTISCAPE50CIS                   = 46444
PRODUCT_ID_MULTISCAPE50CIS_ENCLOSURE         = 52912
PRODUCT_ID_MULTISCAPE100CIS                  = 36173
PRODUCT_ID_MULTISCAPE100CIS_ENCLOSURE        = 55412
PRODUCT_ID_MULTISCAPE_CMV12000_EFM_IE        = 55425
PRODUCT_ID_MULTISCAPE_CMV12000_EFM_IE_FILTER = 55426
PRODUCT_ID_MULTISCAPE_CMV12000_EFM_CE        = 55427
PRODUCT_ID_MULTISCAPE200CIS                  = 34756
PRODUCT_ID_MULTISCAPE200CIS_ENCLOSURE        = 55417
PRODUCT_ID_MULTISCAPE_GMAX3265_EFM_IE        = 55432
PRODUCT_ID_MULTISCAPE_GMAX3265_EFM_IE_FILTER = 55433
PRODUCT_ID_MULTISCAPE_GMAX3265_EFM_CE        = 55434
PRODUCT_ID_HYPERSCAPE50                      = 44550
PRODUCT_ID_HYPERSCAPE50_ENCLOSURE            = 55409
PRODUCT_ID_HYPERSCAPE100                     = 34647
PRODUCT_ID_HYPERSCAPE100_ENCLOSURE           = 55413
PRODUCT_ID_HYPERSCAPE_CMV12000_EFM_IE        = 55422
PRODUCT_ID_HYPERSCAPE_CMV12000_EFM_IE_FILTER = 55423
PRODUCT_ID_HYPERSCAPE_CMV12000_EFM_CE        = 55424

PACKETID_SESSIONSTART                    = 0x00
PACKETID_SESSIONEND                      = 0x01
PACKETID_SCENESTART                      = 0x02
PACKETID_EXPOSURESTART                   = 0x03
PACKETID_LINEDATA                        = 0x04
PACKETID_THUMBLINEDATA                   = 0x05
PACKETID_SEGMENTDATA                     = 0x06
PACKETID_TIMESYNC                        = 0x07
PACKETID_TIMESYNCPPS                     = 0x08
PACKETID_VIDEODATA                       = 0x0A
PACKETID_CCSDS122DATA                    = 0x0B
PACKETID_USERANCILLARY                   = 0x80
PACKETID_IMAGERANCILLARY_IMAGERINFO      = 0xA0
PACKETID_IMAGERANCILLARY_IMAGERCONFIG_LINESCAN = 0xA1
PACKETID_IMAGERANCILLARY_IMAGERCONFIG_SNAPSHOT = 0xA4
PACKETID_IMAGERANCILLARY_SENSORCONFIG    = 0xA2
PACKETID_IMAGERANCILLARY_IMAGERTELEMETRY = 0xA3
PACKETID_IMAGERANCILLARY_COMPRESSIONINFO = 0xA6
PACKETID_IMAGERANCILLARY_OFETELEMETRY    = 0xA7

PIXEL_ENCODING_8B8B     = 0x00
PIXEL_ENCODING_10B10B   = 0x01
PIXEL_ENCODING_10B16B   = 0x02
PIXEL_ENCODING_12B12B   = 0x03
PIXEL_ENCODING_12B16B   = 0x04

PIXEL_FORMAT_MONO       = 0
PIXEL_FORMAT_BAYER_RG   = 1
PIXEL_FORMAT_BAYER_GR   = 2
PIXEL_FORMAT_BAYER_GB   = 3
PIXEL_FORMAT_BAYER_BG   = 4
PIXEL_FORMAT_BAYER_R_COMP = 5
PIXEL_FORMAT_BAYER_G_COMP = 6
PIXEL_FORMAT_BAYER_B_COMP = 7



class PacketParser:
    '''
    Image Data Parser for xScape Imagers
    '''

    def __init__(self):

        self._debug = False
        self.PacketVersion = 0
        self._ImageData = None
        self.SessionID = None
        self.SceneNumber = None
        self.ExposureTimestamp = None

        self.PID_Switcher = {
                        PACKETID_SESSIONSTART                          : lambda x,y : self._parsePacket_SessionStart(x,y),
                        PACKETID_SESSIONEND                            : lambda x,y : self._parsePacket_SessionEnd(x,y),
                        PACKETID_SCENESTART                            : lambda x,y : self._parsePacket_SceneStart(x,y),
                        PACKETID_EXPOSURESTART                         : lambda x,y : self._parsePacket_ExposureStart(x,y),
                        PACKETID_LINEDATA                              : lambda x,y : self._parsePacket_LineData(x,y),
                        PACKETID_THUMBLINEDATA                         : lambda x,y : self._parsePacket_ThumbLineData(x,y),
                        PACKETID_SEGMENTDATA                           : lambda x,y : self._parsePacket_SegmentData(x,y),
                        PACKETID_TIMESYNC                              : lambda x,y : self._parsePacket_TimeSync(x,y),
                        PACKETID_TIMESYNCPPS                           : lambda x,y : self._parsePacket_TimeSyncPPS(x,y),
                        PACKETID_VIDEODATA                             : lambda x,y : self._parsePacket_VideoData(x,y),
                        PACKETID_CCSDS122DATA                          : lambda x,y : self._parsePacket_CCSDS122Data(x,y),
                        PACKETID_USERANCILLARY                         : lambda x,y : self._parsePacket_UserAncillary(x,y),
                        PACKETID_IMAGERANCILLARY_IMAGERINFO            : lambda x,y : self._parsePacket_ImagerAncillary_ImagerInfo(x,y),
                        PACKETID_IMAGERANCILLARY_IMAGERCONFIG_LINESCAN : lambda x,y : self._parsePacket_ImagerAncillary_ImagerConfig_Linescan(x,y),
                        PACKETID_IMAGERANCILLARY_IMAGERCONFIG_SNAPSHOT : lambda x,y : self._parsePacket_ImagerAncillary_ImagerConfig_Snapshot(x,y),
                        PACKETID_IMAGERANCILLARY_SENSORCONFIG          : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig(x,y),
                        PACKETID_IMAGERANCILLARY_IMAGERTELEMETRY       : lambda x,y : self._parsePacket_ImagerAncillary_ImagerTelemetry(x,y),
                        PACKETID_IMAGERANCILLARY_COMPRESSIONINFO       : lambda x,y : self._parsePacket_ImagerAncillary_CompressionInfo(x,y),
                        PACKETID_IMAGERANCILLARY_OFETELEMETRY          : lambda x,y : self._parsePacket_ImagerAncillary_OfeTelemetry(x,y)
                        }

        self.ImagerAncillary_SensorConfig_Switcher = {
                        PRODUCT_ID_MONOSCAPE50                       : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_MONOSCAPE50_ENCLOSURE             : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_MONOSCAPE100                      : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_MONOSCAPE100_ENCLOSURE            : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_MONOSCAPE_CMV12000_EFM_IE         : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_MONOSCAPE_CMV12000_EFM_CE         : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_MONOSCAPE200                      : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_GMAX3265(x,y),
                        PRODUCT_ID_MONOSCAPE200_ENCLOSURE            : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_GMAX3265(x,y),
                        PRODUCT_ID_MONOSCAPE_GMAX3265_EFM_IE         : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_GMAX3265(x,y),
                        PRODUCT_ID_MONOSCAPE_GMAX3265_EFM_CE         : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_GMAX3265(x,y),
                        PRODUCT_ID_TRISCAPE50                        : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_TRISCAPE50_ENCLOSURE              : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_TRISCAPE100                       : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_TRISCAPE100_ENCLOSURE             : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_TRISCAPE_CMV12000_EFM_IE          : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_TRISCAPE_CMV12000_EFM_CE          : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_TRISCAPE200                       : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_GMAX3265(x,y),
                        PRODUCT_ID_TRISCAPE200_ENCLOSURE             : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_GMAX3265(x,y),
                        PRODUCT_ID_TRISCAPE_GMAX3265_EFM_IE          : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_GMAX3265(x,y),
                        PRODUCT_ID_TRISCAPE_GMAX3265_EFM_CE          : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_GMAX3265(x,y),
                        PRODUCT_ID_MULTISCAPE50CIS                   : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_MULTISCAPE50CIS_ENCLOSURE         : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_MULTISCAPE100CIS                  : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_MULTISCAPE100CIS_ENCLOSURE        : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_MULTISCAPE_CMV12000_EFM_IE        : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_MULTISCAPE_CMV12000_EFM_IE_FILTER : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_MULTISCAPE_CMV12000_EFM_CE        : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_MULTISCAPE200CIS                  : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_GMAX3265(x,y),
                        PRODUCT_ID_MULTISCAPE200CIS_ENCLOSURE        : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_GMAX3265(x,y),
                        PRODUCT_ID_MULTISCAPE_GMAX3265_EFM_IE        : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_GMAX3265(x,y),
                        PRODUCT_ID_MULTISCAPE_GMAX3265_EFM_IE_FILTER : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_GMAX3265(x,y),
                        PRODUCT_ID_MULTISCAPE_GMAX3265_EFM_CE        : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_GMAX3265(x,y),
                        PRODUCT_ID_HYPERSCAPE50                      : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_HYPERSCAPE50_ENCLOSURE            : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_HYPERSCAPE100                     : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_HYPERSCAPE100_ENCLOSURE           : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_HYPERSCAPE_CMV12000_EFM_IE        : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_HYPERSCAPE_CMV12000_EFM_IE_FILTER : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y),
                        PRODUCT_ID_HYPERSCAPE_CMV12000_EFM_CE        : lambda x,y : self._parsePacket_ImagerAncillary_SensorConfig_CMV12000(x,y)
                        }

        self.PixelDecoder_Switcher = {
                        PIXEL_ENCODING_8B8B   : lambda x,y : self._pixelDecoder_8b8b(x,y),   # 8bit pixels mapped to 8bit symbols
                        PIXEL_ENCODING_10B10B : lambda x,y : self._pixelDecoder_10b10b(x,y), # 10bit pixels mapped to 10bit symbols, tightly packed
                        PIXEL_ENCODING_10B16B : lambda x,y : self._pixelDecoder_10b16b(x,y), # 10bit pixels mapped to 16bit symbols, into lower 10 bits of a 16bit word
                        PIXEL_ENCODING_12B12B : lambda x,y : self._pixelDecoder_12b12b(x,y), # 12bit pixels mapped to 12bit symbols, tightly packed
                        PIXEL_ENCODING_12B16B : lambda x,y : self._pixelDecoder_12b16b(x,y)  # 12bit pixels mapped to 16bit symbols, into lower 12 bits of a 16bit word
                        }

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

    def ImageData(self):
        return self._ImageData

    def parsePacket(self, packet, imageData=None):
        '''
        If imageData parameter is not provided, the instance's ImageData variable is used
        '''
        if imageData is None:
            if self._ImageData is None:
                self._ImageData = imagedata.ImageData()
            imageData = self._ImageData # Dicts are immutable, so the var is not copied, but the pointer is

        # Get the function from switcher dictionary
        if packet['PID'] in self.PID_Switcher:
            self.PID_Switcher[packet['PID']](packet, imageData)
        else:
            if self._debug:
                print(f"Invalid Packet ID 0x{packet['PID']:02x}({packet['PID']}) found at position {packet['position']}")
            return False

    def _parsePacket_SessionStart(self, packet, imageData=None):
        if self._debug:
            print('SessionStart')

        if packet['Length'] != 12:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            return False

        PacketVersion   = [packet['raw'][8+0], packet['raw'][8+1]]
        PlatformID      = packet['raw'][8+2] + (256*packet['raw'][8+3])
        InstrumentID    = packet['raw'][8+4] + (256*packet['raw'][8+5])
        #reserved       = packet['raw'][8+6] + (256*packet['raw'][8+7])
        SessionID       = packet['raw'][8+ 8] + \
                         (packet['raw'][8+ 9]<<8) + \
                         (packet['raw'][8+10]<<16) + \
                         (packet['raw'][8+11]<<24)

        if self._debug:
            print(f"\tPacketVersion = {PacketVersion}")
            print(f"\tPlatformID    = {PlatformID}")
            print(f"\tInstrumentID  = {InstrumentID}")
            print(f"\tSessionID     = {SessionID}")

        self.SessionID = SessionID
        self.SceneNumber = None
        self.PacketVersion = PacketVersion

        if not imageData is None:
            if not 'Sessions' in imageData:
                imageData['Sessions'] = {}
            if SessionID in imageData['Sessions']:
                if self._debug:
                    print(f"Warning - Received SessionStart for existing session ID 0x{SessionID:04x}")
            else:
                imageData['Sessions'][SessionID] = {}
            imageData['Sessions'][SessionID]['Closed'] = False
            imageData['Sessions'][SessionID]['PacketVersion'] = PacketVersion
            imageData['Sessions'][SessionID]['PlatformID'] = PlatformID
            imageData['Sessions'][SessionID]['InstrumentID'] = InstrumentID
            return True
        else:
            #not saving sessions info, so return the info
            retval = {}
            retval['PacketVersion'] = PacketVersion
            retval['PlatformID'] = PlatformID
            retval['InstrumentID'] = InstrumentID
            retval['SessionID'] = SessionID
            return retval

    def _parsePacket_SessionEnd(self, packet, imageData=None):
        if self._debug:
            print('SessionEnd')
        if packet['Length'] != 4:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False
        SessionID = packet['raw'][8+0] + (256*packet['raw'][8+1])
        if SessionID != self.SessionID:
            if self._debug:
                print(f"Warning - Received CloseSession for Session ID 0x{SessionID:04x}, while current Session ID is 0x{self.SessionID:04x}")
            return False
        else:
            imageData['Sessions'][SessionID]['Closed'] = True
            self.SessionID = None
            return True

    def _parsePacket_SceneStart(self, packet, imageData=None):
        if self._debug:
            print('SceneStart')
            #print(packet)

        if packet['Length'] != 12:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False

        SceneNumber = packet['raw'][8+0] + (256*packet['raw'][8+1])
        SceneType   = packet['raw'][8+2]
        SceneHeight = packet['raw'][8+4] + (packet['raw'][8+5]<<8) + (packet['raw'][8+6]<<16)
        SceneWidth  = packet['raw'][8+8] + (packet['raw'][8+9]<<8)

        if self._debug:
            print(f"\tSceneNumber    = {SceneNumber}")
            print(f"\tSceneType      = {SceneType}")
            print(f"\tSceneHeight    = {SceneHeight}")
            print(f"\tSceneWidth     = {SceneWidth}")

        if not imageData is None:
            if not self.SessionID is None:
                if not 'Scenes' in imageData['Sessions'][self.SessionID]:
                    imageData['Sessions'][self.SessionID]['Scenes'] = {}
                if SceneNumber in imageData['Sessions'][self.SessionID]['Scenes']:
                    if self._debug:
                        print(f"ERROR - Received SceneStart for existing Scene Number 0x{SceneNumber:04x} in Session ID 0x{currentSessionID:04x}")
                else:
                    imageData['Sessions'][self.SessionID]['Scenes'][SceneNumber] = {}
                    imageData['Sessions'][self.SessionID]['Scenes'][SceneNumber]['Type'] = SceneType
                    imageData['Sessions'][self.SessionID]['Scenes'][SceneNumber]['Width'] = SceneWidth
                    imageData['Sessions'][self.SessionID]['Scenes'][SceneNumber]['Height'] = SceneHeight

                self.SceneNumber = SceneNumber
                return True

            return False
        else:
            retval = {}
            retval['Description'] = 'SceneStart'
            retval['SceneNumber'] = SceneNumber
            retval['SceneType']   = SceneType
            retval['SceneHeight'] = SceneHeight
            retval['SceneWidth']  = SceneWidth
            return retval

    def _parsePacket_ExposureStart(self, packet, imageData=None):
        if self._debug:
            print("ExposureStart", end="")

        if packet['Length'] != 8:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False

        Timestamp = packet['raw'][8+0] + \
                   (packet['raw'][8+1]<<8) + \
                   (packet['raw'][8+2]<<16) + \
                   (packet['raw'][8+3]<<24) + \
                   (packet['raw'][8+4]<<32) + \
                   (packet['raw'][8+5]<<40) + \
                   (packet['raw'][8+6]<<48) + \
                   (packet['raw'][8+7]<<56)

        if self._debug:
            print(f"\tTimestamp = {Timestamp}", end="")

        if not imageData is None:
            if self._debug:
                if self.ExposureTimestamp:
                    print(f"\tDelta = {Timestamp - self.ExposureTimestamp}")
                else:
                    print()
            self.ExposureTimestamp = Timestamp
            return True
        else:
            if self._debug:
                print()
            return Timestamp

    def _pixelDecoder_8b8b(self, input_line, line_length):
        # 8bit pixels mapped to 8bit symbols, ie packed
        #if self._debug:
        #    print("8b8b")

        num_pixels = len(input_line) # maximum number of pixels in Pixel Data field
        
        if line_length <= num_pixels:
            num_pixels = line_length # use the correct line length
        else:
            if self._debug:
                print(f"ERROR - Not enough pixel data. Expected {line_length} pixels, but pixel data filed only has {num_pixels} pixels.")
            #raise
                
        output_line = array.array('B', [0]*num_pixels)

        for column in range(num_pixels):
            output_line[column] = input_line[column]

        return output_line

    def _pixelDecoder_10b10b(self, input_line, line_length):
        # 10bit pixels mapped to 10bit symbols, ie packed
        #if self._debug:
        #    print("10b10b")

        num_pixels = len(input_line) * 8 // 10  # maximum number of pixels in Pixel Data field

        if line_length <= num_pixels:
            num_pixels = line_length # use the correct line length
        else:
            if self._debug:
                print(f"ERROR - Not enough pixel data. Expected {line_length} pixels, but pixel data filed only has {num_pixels} pixels.")
            #raise
            
        output_line = array.array('H', [0]*num_pixels)

        i = 0
        bit_offset = 0
        for column in range(num_pixels):
            tmp = input_line[i] + input_line[i+1] * 256
            tmp >>= bit_offset
            tmp &= 0x3ff # AND with 10bit bitmask

            if self._debug:
                if (row == 0) and (column < 4):
                    print(f"\tpixel 0,{column} = 0x{tmp:02x}")

            output_line[column] = tmp

            i += 1
            bit_offset += 2
            if bit_offset == 8:
                bit_offset = 0
                i += 1

        return output_line

    def _pixelDecoder_10b16b(self, input_line, line_length):
        # 10bit pixels mapped to 16bit symbols, packed into lower 10 bits of a 16bit word
        #if self._debug:
        #    print("10b16b")

        # 10bit pixels mapped to 16bit symbols, ie packed
        num_pixels = len(input_line) // 2   # maximum number of pixels in Pixel Data field
        
        if line_length <= num_pixels:
            num_pixels = line_length # use the correct line length
        else:
            if self._debug:
                print(f"ERROR - Not enough pixel data. Expected {line_length} pixels, but pixel data filed only has {num_pixels} pixels.")
            #raise        

        output_line = array.array('H', [0]*num_pixels)

        i = 0
        for column in range(num_pixels):
            tmp = input_line[i] + input_line[i+1] * 256

            if self._debug:
                if (row == 0) and (column < 4):
                    print(f"\tpixel 0,{column} = 0x{tmp:02x}")

            output_line[column] = tmp
            i += 2

        return output_line

    def _pixelDecoder_12b12b(self, input_line, line_length):
        # 12bit pixels mapped to 12bit symbols, ie packed
        #if self._debug:
        #    print("12b12b")

        # 12bit pixels mapped to 12bit symbols, ie packed
        num_pixels = len(input_line) * 8 // 12  # maximum number of pixels in Pixel Data field

        if line_length <= num_pixels:
            num_pixels = line_length # use the correct line length
        else:
            if self._debug:
                print(f"ERROR - Not enough pixel data. Expected {line_length} pixels, but pixel data filed only has {num_pixels} pixels.")
            #raise   

        output_line = array.array('H', [0]*num_pixels)

        i = 0
        bit_offset = 0
        for column in range(num_pixels):
            tmp = input_line[i] + input_line[i+1] * 256
            tmp >>= bit_offset
            tmp &= 0xfff # AND with 12bit bitmask

            output_line[column] = tmp
            i += 1
            bit_offset += 4
            if bit_offset == 8:
                bit_offset = 0
                i += 1

        if self._debug:
            print(f"\tFirst 4 pixels of line = 0x{output_line[0]:04x} 0x{output_line[1]:04x} 0x{output_line[2]:04x} 0x{output_line[3]:04x}")

        return output_line

    def _pixelDecoder_12b16b(self, input_line, line_length):
        # 12bit pixels mapped to 16bit symbols, packed into lower 12 bits of a 16bit word
        #if self._debug:
        #    print("12b16b")

        # 12bit pixels mapped to 16bit symbols, ie packed
        num_pixels = len(input_line) // 2  # maximum number of pixels in Pixel Data field

        if line_length <= num_pixels:
            num_pixels = line_length # use the correct line length
        else:
            if self._debug:
                print(f"ERROR - Not enough pixel data. Expected {line_length} pixels, but pixel data filed only has {num_pixels} pixels.")
            #raise   

        output_line = array.array('H', [0]*num_pixels)

        i = 0
        for column in range(num_pixels):
            tmp = input_line[i] + input_line[i+1] * 256

            output_line[column] = tmp
            i += 2

        if self._debug:
            print(f"\tFirst 4 pixels of line = 0x{output_line[0]:04x} 0x{output_line[1]:04x} 0x{output_line[2]:04x} 0x{output_line[3]:04x}")

        return output_line

    def _parsePacket_LineData(self, packet, imageData=None):
        if self._debug:
            print(f"LineData", end="")

        if packet['Length'] <= 8:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False

        SpectralBand = packet['raw'][8+0]
        LineNumber   = packet['raw'][8+4] + (packet['raw'][8+5]<<8) + (packet['raw'][8+6]<<16)
        LineLength   = packet['raw'][8+8] + (packet['raw'][8+9]<<8)
        Format       = packet['raw'][8+10]
        Encoding     = packet['raw'][8+11]
        RawLine      = packet['raw'][8+12:(8+packet['Length'])]

        # use encoding to extract pixels
        # Get the function from switcher dictionary
        if not Encoding in self.PixelDecoder_Switcher:
            if self._debug:
                print(f"Invalid pixel encoding (0x{Encoding:02x}) for packet found at file position {packet['filepos']} in file '{packet['filename']}'")
            PixelData = False
        else:
            PixelData = self.PixelDecoder_Switcher[Encoding](RawLine, LineLength)


        if self._debug:
            print(f"\tSpectralBand = {SpectralBand}", end="")
            print(f"\tLineNumber = {LineNumber:8,}", end="")
            print(f"\tLineLength = {LineLength}", end="")
            print(f"\tFormat = {Format}", end="")
            print(f"\tEncoding = {Encoding}", end="")
            if PixelData is False:
                print(f"\tPixelData = none")
            else:
                print(f"\tPixelData = {len(PixelData)} pixels")

        if not imageData is None:
            if not 'Sessions' in imageData:
                imageData['Sessions'] = {}
            if not self.SessionID in imageData['Sessions']:
                imageData['Sessions'][self.SessionID] = {}
            if not 'Scenes' in imageData['Sessions'][self.SessionID]:
                imageData['Sessions'][self.SessionID]['Scenes'] = {}
            if not self.SceneNumber in imageData['Sessions'][self.SessionID]['Scenes']:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber] = {}
            if not 'RawBands' in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['RawBands'] = {}
            if not SpectralBand in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['RawBands']:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['RawBands'][SpectralBand] = {}
            imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['RawBands'][SpectralBand]['Format'] = Format
            imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['RawBands'][SpectralBand]['Encoding'] = Encoding
            imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['RawBands'][SpectralBand]['LineLength'] = LineLength
            if not 'Lines' in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['RawBands'][SpectralBand]:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['RawBands'][SpectralBand]['Lines'] = {}
            temp = {}
            temp['ExposureTimestamp'] = self.ExposureTimestamp
            temp['PixelData'] = PixelData
            imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['RawBands'][SpectralBand]['Lines'][LineNumber] = temp
            return True
        else:
            #not saving sessions info, so return the info
            retval = {}
            retval['SpectralBand'] = SpectralBand
            retval['LineNumber'] = LineNumber
            retval['LineLength'] = LineLength
            retval['Format'] = Format
            retval['Encoding'] = Encoding
            retval['PixelData'] = PixelData
            return retval

    def _parsePacket_ThumbLineData(self, packet, imageData=None):
        if self._debug:
            print("ThumbLineData", end="")
        if packet['Length'] <= 8:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False

        SpectralBand = packet['raw'][8+0]
        LineNumber   = packet['raw'][8+4] + (packet['raw'][8+5]<<8) + (packet['raw'][8+6]<<16)
        LineLength   = packet['raw'][8+8] + (packet['raw'][8+9]<<8)
        Format       = packet['raw'][8+10]
        Encoding     = packet['raw'][8+11]
        RawLine      = packet['raw'][8+12:(8+packet['Length'])]

        # use encoding to extract pixels
        # Get the function from switcher dictionary
        PixelData = self._pixelDecoder_8b8b(RawLine,LineLength)

        if self._debug:
            print(f"\tSpectralBand = {SpectralBand}", end="")
            print(f"\tLineNumber = {LineNumber:8,}", end="")
            print(f"\tLineLength = {LineLength}", end="")
            print(f"\tFormat = {Format}", end="")
            print(f"\tEncoding = {Encoding}", end="")
            if PixelData is False:
                print(f"\tPixelData = none")
            else:
                print(f"\tPixelData = {len(PixelData)} pixels")

        if not imageData is None:
            if not 'Sessions' in imageData:
                imageData['Sessions'] = {}
            if not self.SessionID in imageData['Sessions']:
                imageData['Sessions'][self.SessionID] = {}
            if not 'Scenes' in imageData['Sessions'][self.SessionID]:
                imageData['Sessions'][self.SessionID]['Scenes'] = {}
            if not self.SceneNumber in imageData['Sessions'][self.SessionID]['Scenes']:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber] = {}
            if not 'ThumbnailBands' in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['ThumbnailBands'] = {}
            if not SpectralBand in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['ThumbnailBands']:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['ThumbnailBands'][SpectralBand] = {}
            imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['ThumbnailBands'][SpectralBand]['Format'] = Format
            imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['ThumbnailBands'][SpectralBand]['Encoding'] = Encoding
            imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['ThumbnailBands'][SpectralBand]['LineLength'] = LineLength
            if not 'Lines' in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['ThumbnailBands'][SpectralBand]:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['ThumbnailBands'][SpectralBand]['Lines'] = {}
            temp = {}
            temp['ExposureTimestamp'] = self.ExposureTimestamp
            temp['PixelData'] = PixelData
            imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['ThumbnailBands'][SpectralBand]['Lines'][LineNumber] = temp
            return True
        else:
            #not saving sessions info, so return the info
            retval = {}
            retval['SpectralBand'] = SpectralBand
            retval['LineNumber'] = LineNumber
            retval['LineLength'] = LineLength
            retval['Format'] = Format
            retval['Encoding'] = Encoding
            retval['PixelData'] = PixelData
            return retval

    def _parsePacket_SegmentData(self, packet, imageData=None):
        if self._debug:
            print("SegmentData", end="")

        if packet['Length'] < 20:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False

        SpectralBand    = packet['raw'][8+0]
        LineNumber      = packet['raw'][8+4] + \
                         (packet['raw'][8+5]<<8) + \
                         (packet['raw'][8+6]<<16)
        LineLength      = packet['raw'][8+8] + \
                         (packet['raw'][8+9]<<8)
        Format          = packet['raw'][8+10]
        Encoding        = packet['raw'][8+11]
        SegmentInfo     = packet['raw'][8+12] + \
                         (packet['raw'][8+13]<<8) + \
                         (packet['raw'][8+14]<<16) + \
                         (packet['raw'][8+15]<<24)
        SegmentLength   = packet['raw'][8+16] + \
                         (packet['raw'][8+17]<<8) + \
                         (packet['raw'][8+18]<<16) + \
                         (packet['raw'][8+19]<<24)

        DataLength = packet['Length'] - 20
        Data = packet['raw'][8+20:(8+20+DataLength)]
        if SegmentLength <= DataLength:
            Data = Data[0:SegmentLength] # truncate to 'SegmentLength' bytes
        else:
            if self._debug:
                print(f"ERROR - Not enough data. Expected {SegmentLength} bytes, but packet only has {DataLength} bytes.")
            #raise
            return False

        if self._debug:
            print(f"  SpectralBand = {SpectralBand}", end="")
            print(f"  LineNumber = {LineNumber:8}", end="")
            print(f"  LineLength = {LineLength}", end="")
            print(f"  Format = {Format}", end="")
            print(f"  Encoding = {Encoding:}", end="")
            print(f"  SegmentInfo = 0x{SegmentInfo:08x}", end="")
            print(f"  SegmentLength = {SegmentLength:6,}", end="")
            print(f"  Data = {len(Data):,} bytes")


        if not imageData is None:
            if not 'Sessions' in imageData:
                imageData['Sessions'] = {}
            if not self.SessionID in imageData['Sessions']:
                imageData['Sessions'][self.SessionID] = {}
            if not 'Scenes' in imageData['Sessions'][self.SessionID]:
                imageData['Sessions'][self.SessionID]['Scenes'] = {}
            if not self.SceneNumber in imageData['Sessions'][self.SessionID]['Scenes']:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber] = {}
            if not 'SegmentBands' in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['SegmentBands'] = {}
            if not SpectralBand in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['SegmentBands']:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['SegmentBands'][SpectralBand] = {}
            imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['SegmentBands'][SpectralBand]['Format'] = Format
            imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['SegmentBands'][SpectralBand]['Encoding'] = Encoding
            imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['SegmentBands'][SpectralBand]['LineLength'] = LineLength
            if not 'Segments' in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['SegmentBands'][SpectralBand]:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['SegmentBands'][SpectralBand]['Segments'] = {}

            temp = {}
            temp['SegmentInfo'] = SegmentInfo
            temp['SegmentData'] = Data
            imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['SegmentBands'][SpectralBand]['Segments'][LineNumber] = temp
            return True
        else:
            #not saving sessions info, so return the info
            retval = {}
            retval['SpectralBand'] = SpectralBand
            retval['LineNumber'] = LineNumber
            retval['LineLength'] = LineLength
            retval['Format'] = Format
            retval['Encoding'] = Encoding
            retval['SegmentInfo'] = SegmentInfo
            retval['SegmentData'] = Data
            return retval


    def _parsePacket_TimeSync(self, packet, imageData=None):
        if self._debug:
            print('TimeSync')

        if packet['Length'] != 20:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False


        ImagerTime = packet['raw'][8+0] + \
                    (packet['raw'][8+1]<<8) + \
                    (packet['raw'][8+2]<<16) + \
                    (packet['raw'][8+3]<<24) + \
                    (packet['raw'][8+4]<<32) + \
                    (packet['raw'][8+5]<<40) + \
                    (packet['raw'][8+6]<<48) + \
                    (packet['raw'][8+7]<<56)
        TimeFormat = packet['raw'][8+8]
        PlatformTime = packet['raw'][8+12] + \
                      (packet['raw'][8+13]<<8) + \
                      (packet['raw'][8+14]<<16) + \
                      (packet['raw'][8+15]<<24) + \
                      (packet['raw'][8+16]<<32) + \
                      (packet['raw'][8+17]<<40) + \
                      (packet['raw'][8+18]<<48) + \
                      (packet['raw'][8+19]<<56)

        temp = {}
        temp['ImagerTime'] = ImagerTime
        temp['TimeFormat'] = TimeFormat
        temp['PlatformTime'] = PlatformTime

        if not imageData is None:
            if not 'TimeSync' in imageData['Sessions'][self.SessionID]:
                imageData['Sessions'][self.SessionID]['TimeSync'] = []
            imageData['Sessions'][self.SessionID]['TimeSync'].append(temp)
        else:
            #not saving sessions info, so return the info
            return temp

    def _parsePacket_TimeSyncPPS(self, packet, imageData=None):
        if self._debug:
            print('TimeSyncPPS')

        if packet['Length'] != 8:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False


        ImagerTime = packet['raw'][8+0] + \
                    (packet['raw'][8+1]<<8) + \
                    (packet['raw'][8+2]<<16) + \
                    (packet['raw'][8+3]<<24) + \
                    (packet['raw'][8+4]<<32) + \
                    (packet['raw'][8+5]<<40) + \
                    (packet['raw'][8+6]<<48) + \
                    (packet['raw'][8+7]<<56)


        temp = {}
        temp['ImagerTime'] = ImagerTime
        temp['PPS'] = True

        if not imageData is None:
            if not 'TimeSync' in imageData['Sessions'][self.SessionID]:
                imageData['Sessions'][self.SessionID]['TimeSync'] = []
            imageData['Sessions'][self.SessionID]['TimeSync'].append(temp)
        else:
            #not saving sessions info, so return the info
            return temp

    def _parsePacket_VideoData(self, packet, imageData=None):
        if self._debug:
            print('VideoData', end="")

        if packet['Length'] < 4:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False

        VideoStandard = packet['raw'][8+0]
        VideoFormat = packet['raw'][8+1]
        FrameNumber = packet['raw'][8+2] + (packet['raw'][8+3]<<8)
        DataLength = packet['Length'] - 4
        Data = packet['raw'][8+4:(8+4+DataLength)]

        if self._debug:
            print(f"\tVideoStandard = {VideoStandard}", end="")
            print(f"\tVideoFormat = {VideoFormat}", end="")
            print(f"\tFrameNumber = {FrameNumber:4}", end="")
            print(f"\tData = {len(Data):,} bytes")

        retval = {}
        retval['VideoStandard'] = VideoStandard
        retval['VideoFormat'] = VideoFormat
        retval['FrameNumber'] = FrameNumber
        retval['Data'] = Data

        if not imageData is None:
            if not 'Sessions' in imageData:
                imageData['Sessions'] = {}
            if not self.SessionID in imageData['Sessions']:
                imageData['Sessions'][self.SessionID] = {}
            if not 'Scenes' in imageData['Sessions'][self.SessionID]:
                imageData['Sessions'][self.SessionID]['Scenes'] = {}
            if not self.SceneNumber in imageData['Sessions'][self.SessionID]['Scenes']:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber] = {}
            if not 'Video' in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['Video'] = []
            imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['Video'].append(retval)
            return True
        else:
            #not saving sessions info, so return the info
            return retval

    def _parsePacket_CCSDS122Data(self, packet, imageData=None):
        if self._debug:
            print("CCSDS122Data", end="")

        if packet['Length'] < 16:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False

        SpectralBand = packet['raw'][8+0]
        LineLength = packet['raw'][8+4] + \
                    (packet['raw'][8+5]<<8)
        Format = packet['raw'][8+6]
        Encoding = packet['raw'][8+7]
        StreamInfo = packet['raw'][8+8] + \
                    (packet['raw'][8+9]<<8) + \
                    (packet['raw'][8+10]<<16) + \
                    (packet['raw'][8+11]<<24)
        SegmentNumber = packet['raw'][8+8] + \
                    (packet['raw'][8+9]<<8) + \
                    (packet['raw'][8+10]<<16)
        SubsegmentNumber = packet['raw'][8+11]
        StreamLength = packet['raw'][8+12] + (packet['raw'][8+13]<<8) + (packet['raw'][8+14]<<16) + (packet['raw'][8+15]<<24)

        DataLength = packet['Length'] - 16
        Data = packet['raw'][8+16:(8+16+StreamLength)]
        if StreamLength <= DataLength:
            Data = Data[0:StreamLength] # truncate to 'StreamLength' bytes
        else:
            if self._debug:
                print(f"ERROR - Not enough data. Expected {StreamLength} bytes, but packet only has {DataLength} bytes.")
            #raise
            return False

        if self._debug:
            print(f"  SpectralBand = {SpectralBand}", end="")
            print(f"  LineLength = {LineLength}", end="")
            print(f"  Format = {Format}", end="")
            print(f"  Encoding = {Encoding}", end="")
            print(f"  SegmentNum = {SegmentNumber:3}.{SubsegmentNumber:02}", end="")
            print(f"  StreamLength = {StreamLength:6,}", end="")
            print(f"  Data = {len(Data):,} bytes")
        
        if self._debug and SubsegmentNumber == 0:#The header of segment stream in first subsegment 
            Part1BFlag = (Data[0] & 0x40)>>6
            Part2Flag  = (Data[2] & 0x4)>>2
            Part3Flag  = (Data[2] & 0x2)>>1
            Part4Flag  = (Data[2] & 0x1)

            HeaderLen = 3#will always have at least header Part 1A

            Part1AHeader = Data[:3]
            Part1BHeader = False
            Part2Header  = False
            Part3Header  = False
            Part4Header  = False

            StartImgFlag   = (Part1AHeader[0] & 0x80)>>7
            EndImgFlag     = (Part1AHeader[0] & 0x40)>>6
            SegmentCount   = ((Part1AHeader[0] & 0x3F) <<2) + ((Part1AHeader[1] & 0xC0)>>6)        
            BitDepthDC     =  (Part1AHeader[1] & 0x3E) >>1
            BitDepthAC     = ((Part1AHeader[1] & 0x01 )<<4)   + ((Part1AHeader[2] & 0xF0) >> 4)
            
            if Part1BFlag == True:
                HeaderLen = HeaderLen + 1
                Part1BHeader = Data[HeaderLen-1 : HeaderLen]
                PadRows        = (Part1BHeader[0] & 0xE0)>>5
                ReservedP1B    = Part1BHeader[0] & 0x1F
            if Part2Flag == True:
                HeaderLen = HeaderLen + 5
                Part2Header = Data[HeaderLen-5 : HeaderLen]
                SegByteLimit   = (Part2Header[0]<< (8+8+3) ) + (Part2Header[1]<< (8+3) ) + (Part2Header[2]<<3) + ((Part2Header[3] & 0xE0)>>5)
                DCStop         = (Part2Header[3] & 0x10)>>4
                BitPlaneStop   = ((Part2Header[3] & 0x0F)<<1) + ((Part2Header[4] & 0x80)>>7)
                StageStop      = (Part2Header[4] & 0x60)>>5
                UseFill        = (Part2Header[4] & 0x10)>>4
                ReservedP2     = (Part2Header[4] & 0x0F)
            if Part3Flag == True:
                HeaderLen = HeaderLen + 3
                Part3Header = Data[HeaderLen-3 : HeaderLen]
                S              =  (Part3Header[0]<< (8+4) ) + (Part3Header[1]<<4) + ((Part3Header[2] & 0xF0)>>4)
                OptDCSelect    = (Part3Header[2] & 0x08 ) >> 3
                OptACSelect    = (Part3Header[2] & 0x04 ) >> 2
                ReservedP3     = (Part3Header[2] & 0x03 )
            if Part4Flag == True:
                HeaderLen = HeaderLen + 8            
                Part4Header = Data[HeaderLen-8 : HeaderLen]
                DWTtype        = (Part4Header[0] & 0x80)>>7
                ReservedP4a    = (Part4Header[0] & 0x40)>>6
                SignedPixels   = (Part4Header[0] & 0x10)>>4
                PixelBitDepth  = ((Part4Header[0] & 0x0F) % 16) + (((Part4Header[0] & 0x20 ) >> 5) *16) #TODO: check that this is correct
                ImageWidth     = (Part4Header[1] << (8+4)) + (Part4Header[2] << 4) + ((Part4Header[3] & 0xF0)>>4)
                TransposeImg   = (Part4Header[3] & 0x08)>>3
                temp_CWL       = Part4Header[3] & 0x07
                CustomWtFlag   = (Part4Header[4]&0x80)>>7
                CustomWtHH1    = (Part4Header[4]&0x60)>>5
                CustomWtHL1    = (Part4Header[4]&0x18)>>3
                CustomWtLH1    = (Part4Header[4]&0x06)>>1
                CustomWtHH2    = ((Part4Header[4]&0x01)<<1) + ((Part4Header[5]&0x80)>>7)
                CustomWtHL2    = (Part4Header[5]&0x60)>>5
                CustomWtLH2    = (Part4Header[5]&0x18)>>3
                CustomWtHH3    = (Part4Header[5]&0x06)>>1
                CustomWtHL3    = ((Part4Header[5]&0x01)<<1) + ((Part4Header[6]&0x80)>>7)
                CustomWtLH3    = (Part4Header[6]&0x60)>>5
                CustomWtLL3    = (Part4Header[6]&0x18)>>3
                ReservedP4b    = Part4Header[7] + ((Part4Header[6]&0x07) <<3)
                
                if temp_CWL == 0:
                    CodeWordLength = 8
                else:
                    CodeWordLength = "ERROR: Unsupported CodeWordLengh, the CCSDS FW does not support this yet."

            print(f"\tCCSDS Segment Info", end="")
            print(f"\n\t    ____Part1A", end="")
            print(f"\n\t    StartImgFlag  : {StartImgFlag}", end="")
            print(f"\n\t    EndImgFlag    : {EndImgFlag}", end="")
            print(f"\n\t    SegmentCount  : {SegmentCount}", end="")
            print(f"\n\t    BitDepthDC    : {BitDepthDC}", end="")
            print(f"\n\t    BitDepthAC    : {BitDepthAC}")
            
            if Part1BFlag:
                print(f"\t    ____Part1B", end="")
                print(f"\n\t    PadRows       : {PadRows}", end="")
                print(f"\n\t    ReservedP1B   : {ReservedP1B}")
            if Part2Flag:
                print(f"\t    ____Part2", end="")
                print(f"\n\t    SegByteLimit  : {SegByteLimit}, {SegByteLimit/1024} kByte", end="")
                print(f"\n\t    DCStop        : {DCStop}", end="")
                print(f"\n\t    BitPlaneStop  : {BitPlaneStop}", end="")
                print(f"\n\t    StageStop     : {StageStop}", end="")
                print(f"\n\t    UseFill       : {UseFill}", end="")
                print(f"\n\t    ReservedP2    : {ReservedP2}")
            if Part3Flag:
                print(f"\t    ____Part3", end="")
                print(f"\n\t    S             : {S}", end="")
                print(f"\n\t    OptDCSelect   : {OptDCSelect}", end="")
                print(f"\n\t    OptACSelect   : {OptACSelect}", end="")
                print(f"\n\t    ReservedP3    : {ReservedP3}")
            if Part4Flag:
                print(f"\t    ____Part4", end="")
                print(f"\n\t    DWTtype       : {DWTtype      }", end="")
                print(f"\n\t    ReservedP4a   : {ReservedP4a  }", end="")
                print(f"\n\t    SignedPixels  : {SignedPixels }", end="")
                print(f"\n\t    PixelBitDepth : {PixelBitDepth}", end="")
                print(f"\n\t    ImageWidth    : {ImageWidth   }", end="")
                print(f"\n\t    TransposeImg  : {TransposeImg }", end="")
                print(f"\n\t    CodeWordLength: {CodeWordLength}", end="")
                print(f"\n\t    CustomWtFlag  : {CustomWtFlag }", end="")
                print(f"\n\t    CustomWtHH1   : {CustomWtHH1  }", end="")
                print(f"\n\t    CustomWtHL1   : {CustomWtHL1  }", end="")
                print(f"\n\t    CustomWtLH1   : {CustomWtLH1  }", end="")
                print(f"\n\t    CustomWtHH2   : {CustomWtHH2  }", end="")
                print(f"\n\t    CustomWtHL2   : {CustomWtHL2  }", end="")
                print(f"\n\t    CustomWtLH2   : {CustomWtLH2  }", end="")
                print(f"\n\t    CustomWtHH3   : {CustomWtHH3  }", end="")
                print(f"\n\t    CustomWtHL3   : {CustomWtHL3  }", end="")
                print(f"\n\t    CustomWtLH3   : {CustomWtLH3  }", end="")
                print(f"\n\t    CustomWtLL3   : {CustomWtLL3  }", end="")
                print(f"\n\t    ReservedP4b   : {ReservedP4b  }")
                    
                #print(f"\n____________________", end="")

        if not imageData is None:
            if not 'Sessions' in imageData:
                imageData['Sessions'] = {}
            if not self.SessionID in imageData['Sessions']:
                imageData['Sessions'][self.SessionID] = {}
            if not 'Scenes' in imageData['Sessions'][self.SessionID]:
                imageData['Sessions'][self.SessionID]['Scenes'] = {}
            if not self.SceneNumber in imageData['Sessions'][self.SessionID]['Scenes']:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber] = {}
            if not 'CCSDS122Bands' in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['CCSDS122Bands'] = {}
            if not SpectralBand in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['CCSDS122Bands']:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['CCSDS122Bands'][SpectralBand] = {}

            if not 'Formats' in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['CCSDS122Bands'][SpectralBand]:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['CCSDS122Bands'][SpectralBand]['Formats'] = {}
            if not Format in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['CCSDS122Bands'][SpectralBand]['Formats']:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['CCSDS122Bands'][SpectralBand]['Formats'][Format] = {}

            if not 'Segments' in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['CCSDS122Bands'][SpectralBand]['Formats'][Format]:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['CCSDS122Bands'][SpectralBand]['Formats'][Format]['Segments'] = {}
            if not SegmentNumber in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['CCSDS122Bands'][SpectralBand]['Formats'][Format]['Segments']:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['CCSDS122Bands'][SpectralBand]['Formats'][Format]['Segments'][SegmentNumber] = {}

            imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['CCSDS122Bands'][SpectralBand]['Formats'][Format]['Segments'][SegmentNumber]['LineLength'] = LineLength
            imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['CCSDS122Bands'][SpectralBand]['Formats'][Format]['Segments'][SegmentNumber]['Encoding'] = Encoding
            if not 'Data' in imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['CCSDS122Bands'][SpectralBand]['Formats'][Format]['Segments'][SegmentNumber]:
                imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['CCSDS122Bands'][SpectralBand]['Formats'][Format]['Segments'][SegmentNumber]['Data'] = []
            imageData['Sessions'][self.SessionID]['Scenes'][self.SceneNumber]['CCSDS122Bands'][SpectralBand]['Formats'][Format]['Segments'][SegmentNumber]['Data'].extend(Data)
            return True

        else:
            #not saving sessions info, so return the info
            retval = {}
            retval['SpectralBand'] = SpectralBand
            retval['LineLength'] = LineLength
            retval['Format'] = Format
            retval['Encoding'] = Encoding
            retval['StreamInfo'] = StreamInfo
            retval['SegmentNumber'] = SegmentNumber
            retval['SubsegmentNumber'] = SubsegmentNumber
            retval['StreamLength'] = StreamLength
            retval['Data'] = Data
            return retval

    def _parsePacket_UserAncillary(self, packet, imageData=None):
        if self._debug:
            print('UserAncillary')

        if packet['Length'] < 4:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False

        DataID = packet['raw'][8+0]
        DataLength = packet['raw'][8+2] + (packet['raw'][8+3]<<8)
        Data = packet['raw'][8+4:(8+4+DataLength)]

        temp = {}
        temp['ExposureTimestamp'] = self.ExposureTimestamp
        temp['Data'] = Data

        if not imageData is None:
            if not 'UserData' in imageData['Sessions'][self.SessionID]:
                imageData['Sessions'][self.SessionID]['UserData'] = {}
            if not DataID in imageData['Sessions'][self.SessionID]['UserData']:
                imageData['Sessions'][self.SessionID]['UserData'][DataID] = []
            imageData['Sessions'][self.SessionID]['UserData'][DataID].append(temp)
        else:
            #not saving sessions info, so return the info
            return temp

    def _parsePacket_ImagerAncillary_ImagerInfo(self, packet, imageData=None):
        if self._debug:
            print('ImagerAncillary_Information')

        if packet['Length'] != 12:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False

        ProductID = packet['raw'][8+0] + \
                   (packet['raw'][8+1]<<8) + \
                   (packet['raw'][8+2]<<16)
        SerialNumber = packet['raw'][8+4] + \
                      (packet['raw'][8+5]<<8)
        FirmwareVersion = [packet['raw'][8+6], packet['raw'][8+7]]
        SoftwareVersion = [packet['raw'][8+8], packet['raw'][8+9]]
        BaselineNumber = [packet['raw'][8+10], packet['raw'][8+11]]

        temp = {}
        temp['ProductID'] = ProductID
        temp['SerialNumber'] = SerialNumber
        temp['FirmwareVersion'] = FirmwareVersion
        temp['SoftwareVersion'] = SoftwareVersion
        temp['BaselineNumber'] = BaselineNumber

        if self._debug:
            print(f"\t{temp}")

        if not imageData is None:
            if not 'Sessions' in imageData:
                imageData['Sessions'] = {}
            if not 'ImagerInformation' in imageData['Sessions'][self.SessionID]:
                imageData['Sessions'][self.SessionID]['ImagerInformation'] = {}
            imageData['Sessions'][self.SessionID]['ImagerInformation'] = temp
            self.ImagerProductID = ProductID
            self.ImagerSerialNumber = SerialNumber
        else:
            return temp

    def _parsePacket_ImagerAncillary_ImagerConfig_Linescan(self, packet, imageData=None):
        if self._debug:
            print('ImagerAncillary_ImagerConfig_Linescan')

        #smallest packet size for 1 band
        if packet['Length'] < 12:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False

        LinePeriod = packet['raw'][8+0] + \
                    (packet['raw'][8+1]<<8) + \
                    (packet['raw'][8+2]<<16)+ \
                    (packet['raw'][8+3]<<24)
        SpectralBands = packet['raw'][8+4]

        #calculate length and deduce API ver
        LengthAPI5 = SpectralBands*3 + 8
        if LengthAPI5%4 != 0:
            LengthAPI5 = LengthAPI5 + (4 - LengthAPI5%4) # pad to 4 byte boundary
        LengthAPI6 = SpectralBands*5 + 8
        if LengthAPI6%4 != 0:
            LengthAPI6 = LengthAPI6 + (4 - LengthAPI6%4) # pad to 4 byte boundary
        LengthAPI12 = SpectralBands*5 + 12
        if LengthAPI12%4 != 0:
            LengthAPI12 = LengthAPI12 + (4 - LengthAPI12%4) # pad to 4 byte boundary        
        
        if packet['Length'] == LengthAPI5:
            #API <= 5
            #e.g. for 7-Band MultiScape the packet length = 32.
            BandSetup = []
            for i in range(SpectralBands):
                BandSetup.append(packet['raw'][8+5+i])
            BinningFactor = packet['raw'][8+5+SpectralBands]
            ThumbnailFactor = packet['raw'][8+5+SpectralBands+1]
            BandStartRow=[]
            for i in range(SpectralBands):
                BandStartRow.append(packet['raw'][8+5+SpectralBands+2+(2*i)] + (packet['raw'][8+5+SpectralBands+3+(2*i)]<<8))
            ScanDirection = packet['raw'][8+5+SpectralBands+2+(2*SpectralBands)]

            if self._debug:
                print(f"\tLinePeriod\t\t{LinePeriod}")
                print(f"\tSpectralBands\t\t{SpectralBands}")
                print(f"\tBandSetup\t\t{BandSetup}")
                print(f"\tBinningFactor\t\t{BinningFactor}")
                print(f"\tThumbnailFactor\t\t{ThumbnailFactor}")
                print(f"\tBandStartRow\t\t{BandStartRow}")
                print(f"\tScanDirection\t\t{ScanDirection}")

            temp = {}
            temp['LinePeriod'] = LinePeriod
            temp['SpectralBands'] = SpectralBands
            temp['BandSetup'] = BandSetup
            temp['BinningFactor'] = BinningFactor
            temp['ThumbnailFactor'] = ThumbnailFactor
            temp['BandStartRow'] = BandStartRow
            temp['ScanDirection'] = ScanDirection
        elif packet['Length'] == LengthAPI6:
            #API 6+
            #e.g. for 7-Band MultiScape the packet length = 44.
            BandSetup = []
            for i in range(SpectralBands):
                BandSetup.append(packet['raw'][8+5+i])
            BinningFactor = packet['raw'][8+5+SpectralBands]
            ThumbnailFactor = packet['raw'][8+5+SpectralBands+1]
            BandStartRow=[]
            for i in range(SpectralBands):
                BandStartRow.append(packet['raw'][8+5+SpectralBands+2+(2*i)] + (packet['raw'][8+5+SpectralBands+3+(2*i)]<<8))
            BandCWL=[]
            for i in range(SpectralBands):
                BandCWL.append(packet['raw'][8+5+SpectralBands+2+(2*SpectralBands)+(2*i)] + (packet['raw'][8+5+SpectralBands+3+(2*SpectralBands)+(2*i)]<<8))
            ScanDirection = packet['raw'][8+5+SpectralBands+2+(2*SpectralBands)+(2*SpectralBands)]

            if self._debug:
                print(f"\tLinePeriod\t\t{LinePeriod}")
                print(f"\tSpectralBands\t\t{SpectralBands}")
                print(f"\tBandSetup\t\t{BandSetup}")
                print(f"\tBinningFactor\t\t{BinningFactor}")
                print(f"\tThumbnailFactor\t\t{ThumbnailFactor}")
                print(f"\tBandStartRow\t\t{BandStartRow}")
                print(f"\BandCWL\t\t{BandCWL}")
                print(f"\tScanDirection\t\t{ScanDirection}")

            temp = {}
            temp['LinePeriod'] = LinePeriod
            temp['SpectralBands'] = SpectralBands
            temp['BandSetup'] = BandSetup
            temp['BinningFactor'] = BinningFactor
            temp['ThumbnailFactor'] = ThumbnailFactor
            temp['BandStartRow'] = BandStartRow
            temp['BandCWL'] = BandCWL
            temp['ScanDirection'] = ScanDirection
        elif packet['Length'] == LengthAPI12:
            #API 12+
            #e.g. 7-Band MultiScape. Packet Length = 48.
            ExposureTime = packet['raw'][8+5] + \
                        (packet['raw'][8+6]<<8) + \
                        (packet['raw'][8+7]<<16)+ \
                        (packet['raw'][8+8]<<24)            
            BandSetup = []
            for i in range(SpectralBands):
                BandSetup.append(packet['raw'][8+9+i])
            BinningFactor = packet['raw'][8+9+SpectralBands]
            ThumbnailFactor = packet['raw'][8+9+SpectralBands+1]
            BandStartRow=[]
            for i in range(SpectralBands):
                BandStartRow.append(packet['raw'][8+9+SpectralBands+2+(2*i)] + (packet['raw'][8+9+SpectralBands+3+(2*i)]<<8))
            BandCWL=[]
            for i in range(SpectralBands):
                BandCWL.append(packet['raw'][8+9+SpectralBands+2+(2*SpectralBands)+(2*i)] + (packet['raw'][8+9+SpectralBands+3+(2*SpectralBands)+(2*i)]<<8))
            ScanDirection = packet['raw'][8+9+SpectralBands+2+(2*SpectralBands)+(2*SpectralBands)]

            if self._debug:
                print(f"\tLinePeriod\t\t{LinePeriod}")
                print(f"\tSpectralBands\t\t{SpectralBands}")
                print(f"\tExposureTime\t\t{ExposureTime}")
                print(f"\tBandSetup\t\t{BandSetup}")
                print(f"\tBinningFactor\t\t{BinningFactor}")
                print(f"\tThumbnailFactor\t\t{ThumbnailFactor}")
                print(f"\tBandStartRow\t\t{BandStartRow}")
                print(f"\BandCWL\t\t{BandCWL}")
                print(f"\tScanDirection\t\t{ScanDirection}")

            temp = {}
            temp['LinePeriod'] = LinePeriod
            temp['SpectralBands'] = SpectralBands
            temp['ExposureTime'] = ExposureTime
            temp['BandSetup'] = BandSetup
            temp['BinningFactor'] = BinningFactor
            temp['ThumbnailFactor'] = ThumbnailFactor
            temp['BandStartRow'] = BandStartRow
            temp['BandCWL'] = BandCWL
            temp['ScanDirection'] = ScanDirection
        else:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False

        if not imageData is None:
            if not 'ImagerConfiguration' in imageData['Sessions'][self.SessionID]:
                imageData['Sessions'][self.SessionID]['ImagerConfiguration'] = temp
                return True
            else:
                if self._debug:
                    print('WARNING - Discarded redundant ImagerConfiguration packet')
                return False
        else:
            return temp

    def _parsePacket_ImagerAncillary_ImagerConfig_Snapshot(self, packet, imageData=None):
        if self._debug:
            print('ImagerAncillary_ImagerConfig_Snapshot')

        if packet['Length'] != 12:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False

        FrameInterval = packet['raw'][8+0] + \
                       (packet['raw'][8+1]<<8) + \
                       (packet['raw'][8+2]<<16)+ \
                       (packet['raw'][8+3]<<24)
        ExposureTime = packet['raw'][8+4] + \
                      (packet['raw'][8+5]<<8) + \
                      (packet['raw'][8+6]<<16)+ \
                      (packet['raw'][8+7]<<24)
        BinningFactor = packet['raw'][8+8]
        ThumbnailFactor = packet['raw'][8+9]

        if self._debug:
            print(f"\FrameInterval\t\t{FrameInterval}")
            print(f"\ExposureTime\t\t{ExposureTime}")
            print(f"\tBinningFactor\t\t{BinningFactor}")
            print(f"\tThumbnailFactor\t\t{ThumbnailFactor}")

        temp = {}
        temp['FrameInterval'] = FrameInterval
        temp['ExposureTime'] = ExposureTime
        temp['BinningFactor'] = BinningFactor
        temp['ThumbnailFactor'] = ThumbnailFactor

        if not imageData is None:
            if not 'ImagerConfiguration' in imageData['Sessions'][self.SessionID]:
                imageData['Sessions'][self.SessionID]['ImagerConfiguration'] = temp
                return True
            else:
                if self._debug:
                    print('WARNING - Discarded redundant ImagerConfiguration packet')
                return False
        else:
            return temp

    # this method is deprecated
    #def _parsePacket_ImagerAncillary_ImagerConfig(self, packet, imageData=None):
    #    if self._debug:
    #        print('ImagerAncillary_ImagerConfig')
    #
    #    if self.ImagerProductID in self.ImagerAncillary_ImagerConfig_Switcher:
    #        return self.ImagerAncillary_ImagerConfig_Switcher[self.ImagerProductID](packet, imageData)
    #    else:
    #        if self._debug:
    #            print(f"ERROR - unsupported product id ({self.ImagerProductID})")
    #        return False

    def _parsePacket_ImagerAncillary_SensorConfig_CMV12000(self, packet, imageData=None):
        if self._debug:
            print('ImagerAncillary_SensorConfig_CMV12000')

        if packet['Length'] != 8:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False

        ADCRange = packet['raw'][8+0] + (packet['raw'][8+1]<<8)
        BottomOffset = packet['raw'][8+2] + (packet['raw'][8+3]<<8)
        TopOffset = packet['raw'][8+4] + (packet['raw'][8+5]<<8)
        Gain = packet['raw'][8+6]
        EBlackEnable = packet['raw'][8+7]

        if self._debug:
            print(f"\tADCRange\t\t{ADCRange}")
            print(f"\tBottomOffset\t\t{BottomOffset}")
            print(f"\tTopOffset\t\t{TopOffset}")
            print(f"\tGain\t\t\t{Gain}")
            print(f"\tEBlackEnable\t\t{EBlackEnable}")

        temp = {}
        temp['ADCRange'] = ADCRange
        temp['BottomOffset'] = BottomOffset
        temp['TopOffset'] = TopOffset
        temp['Gain'] = Gain
        temp['EBlackEnable'] = EBlackEnable

        if not imageData is None:
            if not 'SensorConfiguration' in imageData['Sessions'][self.SessionID]:
                imageData['Sessions'][self.SessionID]['SensorConfiguration'] = temp
                return True
            else:
                if self._debug:
                    print('WARNING - Discarded redundant SensorConfiguration packet')
                return False
        else:
            return temp
            
    def _parsePacket_ImagerAncillary_SensorConfig_GMAX3265(self, packet, imageData=None):
        if self._debug:
            print('ImagerAncillary_SensorConfig_GMAX3265')

        if packet['Length'] != 4:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False

        PGAGain = packet['raw'][8+0]
        ADCGain = packet['raw'][8+1]
        DarkOffset = packet['raw'][8+2] + (packet['raw'][8+3]<<8)
        #convert to signed, based on int16 (16-bit 2's complement)
        if DarkOffset >= 0x8000:
            DarkOffset -= 0x10000

        if self._debug:
            print(f"\tPGAGain\t\t{PGAGain}")
            print(f"\tADCGain\t\t{ADCGain}")
            print(f"\tDarkOffset\t\t{DarkOffset}")

        temp = {}
        temp['PGAGain'] = PGAGain
        temp['ADCGain'] = ADCGain
        temp['DarkOffset'] = DarkOffset

        if not imageData is None:
            if not 'SensorConfiguration' in imageData['Sessions'][self.SessionID]:
                imageData['Sessions'][self.SessionID]['SensorConfiguration'] = temp
                return True
            else:
                if self._debug:
                    print('WARNING - Discarded redundant SensorConfiguration packet')
                return False
        else:
            return temp            

    def _parsePacket_ImagerAncillary_SensorConfig(self, packet, imageData=None):
        if self._debug:
            print('ImagerAncillary_SensorConfig', end='')

        if self.ImagerProductID in self.ImagerAncillary_SensorConfig_Switcher:
            return self.ImagerAncillary_SensorConfig_Switcher[self.ImagerProductID](packet, imageData)
        else:
            if self._debug:
                print(f"ERROR - unsupported product id ({self.ImagerProductID})")
            return False

    def _parsePacket_ImagerAncillary_ImagerTelemetry(self, packet, imageData=None):
        if self._debug:
            print('ImagerAncillary_ImagerTelemetry', end='')

        if packet['Length'] == 4:
            SensorTemperature = packet['raw'][8+0]

            #convert to signed
            if SensorTemperature >= 0x80:
                SensorTemperature -= 0x100

            if self._debug:
                print(f"\tSensorTemperature = {SensorTemperature} degC")

            temp = {}
            temp['ImagerTime'] = self.ExposureTimestamp     #take last exposure time to tag this temperature. only really has significance during imaging anyway
            temp['SensorTemperature'] = SensorTemperature

        elif packet['Length'] == 12:
            ImagerTime = packet['raw'][8+0] + \
                        (packet['raw'][8+1]<<8) + \
                        (packet['raw'][8+2]<<16) + \
                        (packet['raw'][8+3]<<24) + \
                        (packet['raw'][8+4]<<32) + \
                        (packet['raw'][8+5]<<40) + \
                        (packet['raw'][8+6]<<48) + \
                        (packet['raw'][8+7]<<56)
            SensorTemperature = packet['raw'][8+8]

            #convert to signed
            if SensorTemperature >= 0x80:
                SensorTemperature -= 0x100

            if self._debug:
                print(f"\tTimestamp = {ImagerTime}", end="")
                print(f"\tSensorTemperature = {SensorTemperature} degC")

            temp = {}
            temp['ImagerTime'] = ImagerTime
            temp['SensorTemperature'] = SensorTemperature

        else:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            #RAISE HERE
            return False

        if not imageData is None:
            if not 'ImagerTelemetry' in imageData['Sessions'][self.SessionID]:
                imageData['Sessions'][self.SessionID]['ImagerTelemetry'] = []
            imageData['Sessions'][self.SessionID]['ImagerTelemetry'].append(temp)
        else:
            #not saving sessions info, so return the info
            return temp

    def _parsePacket_ImagerAncillary_CompressionInfo(self, packet, imageData=None):
        if self._debug:
            print('ImagerAncillary_CompressionInfo', end='')

        if packet['Length'] != 12:
            if self._debug:
                print('ERROR - Incorrect Payload Length field')
            return False

        OriginalSessionID = packet['raw'][8+0] + \
                           (packet['raw'][8+1]<<8) + \
                           (packet['raw'][8+2]<<16) + \
                           (packet['raw'][8+3]<<24)
        BandMask          = packet['raw'][8+4] + \
                           (packet['raw'][8+5]<<8) + \
                           (packet['raw'][8+6]<<16) + \
                           (packet['raw'][8+7]<<24)
        CompressionRatio  = packet['raw'][8+8]
        #reserved       = packet['raw'][8+9] + (packet['raw'][8+10]<<8) + (packet['raw'][8+10]<<16)

        # convert Compression Ratio to a meaningfull value
        if CompressionRatio >= 10:
            CompressionRatio = CompressionRatio/10
        elif CompressionRatio == 1:
            CompressionRatio = "Lossless"
        else:
            CompressionRatio = 0  # invalid compression ratio setting

        # save the values for later
        self.CompressionInfo = {}
        self.CompressionInfo['OriginalSessionID'] = OriginalSessionID
        self.CompressionInfo['BandMask'] = BandMask
        self.CompressionInfo['CompressionRatio'] = CompressionRatio

        if self._debug:
            print(f"\tOriginalSessionID = {OriginalSessionID}", end="")
            print(f"\tBandMask = {BandMask:032b}", end="")
            print(f"\tCompressionRatio = {CompressionRatio}")

        temp = {}
        temp['OriginalSessionID'] = OriginalSessionID
        temp['BandMask'] = BandMask
        temp['CompressionRatio'] = CompressionRatio

        if not imageData is None:
            if not 'CompressionInfo' in imageData['Sessions'][self.SessionID]:
                imageData['Sessions'][self.SessionID]['CompressionInfo'] = []
            imageData['Sessions'][self.SessionID]['CompressionInfo'].append(temp)
        else:
            #not saving sessions info, so return the info
            return temp

    def _parsePacket_ImagerAncillary_OfeTelemetry(self, packet, imageData=None):
        if self._debug:
            print('ImagerAncillary_OfeTelemetry', end='')
        
        ImagerTime = packet['raw'][8+0] + \
                    (packet['raw'][8+1]<<8) + \
                    (packet['raw'][8+2]<<16) + \
                    (packet['raw'][8+3]<<24) + \
                    (packet['raw'][8+4]<<32) + \
                    (packet['raw'][8+5]<<40) + \
                    (packet['raw'][8+6]<<48) + \
                    (packet['raw'][8+7]<<56)
        
        SensorTemps = []
        NumSensors = packet['raw'][8+8]
        for i in range(NumSensors): # 0 to (NumSensors-1)
            val = packet['raw'][8+9+(i*2)] + (packet['raw'][8+9+(i*2)+1]*256)
            # int16 (2's compliment)
            if val >= 0x8000: val -= 0x10000
            # store in degrees C (not 0.1 degrees C)
            SensorTemps.append(val/10)
        
        SensorPositionsRaw = []
        for i in range(NumSensors*7): # 0 to (NumSensors-1)
            SensorPositionsRaw.append(chr(packet['raw'][8+9+(NumSensors*2)+i]))
            
        SensorPositions = []
        for i in range(NumSensors): # 0 to (NumSensors-1)
            strPosition = ''
            for j in range(7):
                strPosition += SensorPositionsRaw[(i*7)+j]
            SensorPositions.append(strPosition)
            
        if self._debug:
            print(f"\tTimestamp = {ImagerTime}", end="")
            print(f"\tOfeSensorTemps = {SensorTemps} degC")
            print(f"\tOfeSensorPositions = {SensorPositions}")

        temp = {}
        temp['ImagerTime'] = ImagerTime
        temp['OfeSensorTemps'] = SensorTemps
        temp['OfeSensorPositions'] = SensorPositions

        if not imageData is None:
            if not 'OfeTelemetry' in imageData['Sessions'][self.SessionID]:
                imageData['Sessions'][self.SessionID]['OfeTelemetry'] = []
            imageData['Sessions'][self.SessionID]['OfeTelemetry'].append(temp)
        else:
            # not saving sessions info, so return the info
            return temp

class PacketParserC(PacketParser):

    '''
    Image Data Parser for xScape Imagers
    '''

    def __init__(self):
        super().__init__()

        import os.path
        dll_name = "libpacket_clib"
        dllabspath = os.path.dirname(os.path.abspath(__file__)) + os.path.sep + dll_name
        c_lib = cdll.LoadLibrary(dllabspath)

        self.decode_8b8b = c_lib.pixelDecoder_8b8b
        self.decode_8b8b.restype = None
        self.decode_8b8b.argtypes = [POINTER(c_uint8), POINTER(c_char), c_int]

        self.decode_10b10b = c_lib.pixelDecoder_10b10b
        self.decode_10b10b.restype = None
        self.decode_10b10b.argtypes = [POINTER(c_uint16), POINTER(c_char), c_int]

        self.decode_10b16b = c_lib.pixelDecoder_10b16b
        self.decode_10b16b.restype = None
        self.decode_10b16b.argtypes = [POINTER(c_uint16), POINTER(c_char), c_int]

        self.decode_12b12b = c_lib.pixelDecoder_12b12b
        self.decode_12b12b.restype = None
        self.decode_12b12b.argtypes = [POINTER(c_uint16), POINTER(c_char), c_int]

        self.decode_12b16b = c_lib.pixelDecoder_12b16b
        self.decode_12b16b.restype = None
        self.decode_12b16b.argtypes = [POINTER(c_uint16), POINTER(c_char), c_int]

        self.PixelDecoder_Switcher = {
            PIXEL_ENCODING_8B8B   : lambda x, y : self._pixelDecoder_8b8b(x, y),   # 8bit pixels mapped to 8bit symbols
            PIXEL_ENCODING_10B10B : lambda x, y : self._pixelDecoder_10b10b(x, y), # 10bit pixels mapped to 10bit symbols, tightly packed
            PIXEL_ENCODING_10B16B : lambda x, y : self._pixelDecoder_10b16b(x, y), # 10bit pixels mapped to 16bit symbols, into lower 10 bits of a 16bit word
            PIXEL_ENCODING_12B12B : lambda x, y : self._pixelDecoder_12b12b(x, y), # 12bit pixels mapped to 12bit symbols, tightly packed
            PIXEL_ENCODING_12B16B : lambda x, y : self._pixelDecoder_12b16b(x, y)  # 12bit pixels mapped to 16bit symbols, into lower 12 bits of a 16bit word
        }

    def _pixelDecoder_8b8b(self, input_line, line_length):
        # 8bit pixels mapped to 8bit symbols, ie packed
        num_pixels = min(len(input_line), line_length)
        output_line = array.array('B', [0]*num_pixels)
        out_addr = output_line.buffer_info()[0]
        out_ptr = cast(out_addr, POINTER(c_uint8))
        self.decode_8b8b(out_ptr, input_line, num_pixels)
        return output_line

    def _pixelDecoder_10b10b(self, input_line, line_length):
        # 10bit pixels mapped to 10bit symbols, ie packed
        num_pixels = min(len(input_line) * 8 // 10, line_length)
        output_line = array.array('H', [0]*num_pixels)
        out_addr = output_line.buffer_info()[0]
        out_ptr = cast(out_addr, POINTER(c_uint16))
        self.decode_10b10b(out_ptr, input_line, num_pixels)
        return output_line

    def _pixelDecoder_10b16b(self, input_line, line_length):
        # 10bit pixels mapped to 16bit symbols, ie packed
        num_pixels = min(len(input_line) // 2, line_length)
        output_line = array.array('H', [0]*num_pixels)
        out_addr = output_line.buffer_info()[0]
        out_ptr = cast(out_addr, POINTER(c_uint16))
        self.decode_10b16b(cast(out_ptr, POINTER(c_uint16)), input_line, num_pixels)
        return output_line

    def _pixelDecoder_12b12b(self, input_line, line_length):
        # 12bit pixels mapped to 12bit symbols, ie packed
        num_pixels = min(len(input_line) * 8 // 12, line_length)
        output_line = array.array('H', [0]*num_pixels)
        out_addr = output_line.buffer_info()[0]
        out_ptr = cast(out_addr, POINTER(c_uint16))
        self.decode_12b12b(cast(out_ptr, POINTER(c_uint16)), input_line, num_pixels)
        return output_line

    def _pixelDecoder_12b16b(self, input_line, line_length):
        # 12bit pixels mapped to 16bit symbols, packed into lower 12 bits of a 16bit word
        num_pixels = min(len(input_line) // 2, line_length)
        output_line = array.array('H', [0]*num_pixels)
        out_addr = output_line.buffer_info()[0]
        out_ptr = cast(out_addr, POINTER(c_uint16))
        self.decode_12b16b(cast(out_ptr, POINTER(c_uint16)), input_line, num_pixels)
        return output_line


class PacketParserCNP(PacketParser):

    '''
    Image Data Parser for xScape Imagers
    '''

    def __init__(self):
        super().__init__()

        import os.path
        dll_name = "libpacket_clib"
        dllabspath = os.path.dirname(os.path.abspath(__file__)) + os.path.sep + dll_name
        c_lib = cdll.LoadLibrary(dllabspath)

        NP_POINTER_1D_u16 = np.ctypeslib.ndpointer(dtype=np.ushort, ndim=1, flags="C")
        NP_POINTER_1D_u8 = np.ctypeslib.ndpointer(dtype=np.ubyte, ndim=1, flags="C")

        self.decode_8b8b = c_lib.pixelDecoder_8b8b
        self.decode_8b8b.restype = None
        self.decode_8b8b.argtypes = [NP_POINTER_1D_u8, POINTER(c_char), c_int]

        self.decode_10b10b = c_lib.pixelDecoder_10b10b
        self.decode_10b10b.restype = None
        self.decode_10b10b.argtypes = [NP_POINTER_1D_u16, POINTER(c_char), c_int]

        self.decode_10b16b = c_lib.pixelDecoder_10b16b
        self.decode_10b16b.restype = None
        self.decode_10b16b.argtypes = [POINTER(c_uint16), POINTER(c_char), c_int]

        self.decode_12b12b = c_lib.pixelDecoder_12b12b
        self.decode_12b12b.restype = None
        self.decode_12b12b.argtypes = [NP_POINTER_1D_u16, POINTER(c_char), c_int]

        self.decode_12b16b = c_lib.pixelDecoder_12b16b
        self.decode_12b16b.restype = None
        self.decode_12b16b.argtypes = [POINTER(c_uint16), POINTER(c_char), c_int]

        self.PixelDecoder_Switcher = {
            PIXEL_ENCODING_8B8B   : lambda x, y : self._pixelDecoder_8b8b(x, y),   # 8bit pixels mapped to 8bit symbols
            PIXEL_ENCODING_10B10B : lambda x, y : self._pixelDecoder_10b10b(x, y), # 10bit pixels mapped to 10bit symbols, tightly packed
            PIXEL_ENCODING_10B16B : lambda x, y : self._pixelDecoder_10b16b(x, y), # 10bit pixels mapped to 16bit symbols, into lower 10 bits of a 16bit word
            PIXEL_ENCODING_12B12B : lambda x, y : self._pixelDecoder_12b12b(x, y), # 12bit pixels mapped to 12bit symbols, tightly packed
            PIXEL_ENCODING_12B16B : lambda x, y : self._pixelDecoder_12b16b(x, y)  # 12bit pixels mapped to 16bit symbols, into lower 12 bits of a 16bit word
        }


    def parsePacket(self, packet, imageData=None):
        '''
        If imageData parameter is not provided, the instance's ImageData variable is used
        '''
        if imageData is None:
            if self._ImageData is None:
                self._ImageData = imagedata.ImageDataCNP()
            imageData = self._ImageData # Dicts are immutable, so the var is not copied, but the pointer is

        # Get the function from switcher dictionary
        if packet['PID'] in self.PID_Switcher:
            self.PID_Switcher[packet['PID']](packet, imageData)
        else:
            if self._debug:
                print(f"Invalid Packet ID 0x{packet['PID']:02x}({packet['PID']}) found at position {packet['position']}")
            return False



    def _pixelDecoder_8b8b(self, input_line, line_length):
        # 8bit pixels mapped to 8bit symbols, ie packed
        num_pixels = min(len(input_line), line_length)
        output_line = np.empty(num_pixels, dtype=np.ubyte, order='C')
        self.decode_8b8b(output_line, input_line, num_pixels)
        return output_line

    def _pixelDecoder_10b10b(self, input_line, line_length):
        # 10bit pixels mapped to 10bit symbols, ie packed
        num_pixels = min(len(input_line) * 8 // 10, line_length)
        output_line = np.empty(num_pixels, dtype=np.ushort, order='C')
        self.decode_10b10b(output_line, input_line, num_pixels)
        return output_line

    def _pixelDecoder_10b16b(self, input_line, line_length):
        # 10bit pixels mapped to 16bit symbols, ie packed
        num_pixels = min(len(input_line) // 2, line_length)
        output_line = np.empty(num_pixels, dtype=np.ushort, order='C')
        self.decode_10b16b(output_line, input_line, num_pixels)
        return output_line

    def _pixelDecoder_12b12b(self, input_line, line_length):
        # 12bit pixels mapped to 12bit symbols, ie packed
        num_pixels = min(len(input_line) * 8 // 12, line_length)
        output_line = np.empty(num_pixels, dtype=np.ushort, order='C')
        self.decode_12b12b(output_line, input_line, num_pixels)
        return output_line

    def _pixelDecoder_12b16b(self, input_line, line_length):
        # 12bit pixels mapped to 16bit symbols, packed into lower 12 bits of a 16bit word
        num_pixels = min(len(input_line) // 2, line_length)
        output_line = np.empty(num_pixels, dtype=np.ushort, order='C')
        self.decode_12b16b(output_line, input_line, num_pixels)
        return output_line


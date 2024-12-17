'''
Simera Sense xScape Image Data Container
Copyright (c) 2019-2020 Simera Sense (info@simerasense.com)
Released under MIT License.

The ImageData class extends the built-in Dictionary type and provides methods to write to image file

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

    # export all images and thumbnails to PNG files
    image_data.toPng()
    
    # export all images and thumbnails to PNG, and override the pixel format
    # usefull when RGB sensor fitted to a linescan imager, an colour snapshots are desired.
    image_data.toPng(PixelFormat=simera.pylibXScape.PIXEL_FORMAT_BAYER_RG, FilenamePrefix='RGB')

'''

import array
import datetime
import math
import time

import png
import numpy
import json
from . import exceptions

PIXEL_FORMAT_MONO     = 0
PIXEL_FORMAT_BAYER_RG = 1
PIXEL_FORMAT_BAYER_GR = 2
PIXEL_FORMAT_BAYER_GB = 3
PIXEL_FORMAT_BAYER_BG = 4
PIXEL_FORMAT_BAYER_R_COMP = 5
PIXEL_FORMAT_BAYER_G_COMP = 6
PIXEL_FORMAT_BAYER_B_COMP = 7

PIXEL_ENCODING_8B8B   = 0x00
PIXEL_ENCODING_10B10B = 0x01
PIXEL_ENCODING_10B16B = 0x02
PIXEL_ENCODING_12B12B = 0x03
PIXEL_ENCODING_12B16B = 0x04

CCSDS_PIXEL_ENCODING_8B  = 0x00
CCSDS_PIXEL_ENCODING_10B = 0x01
CCSDS_PIXEL_ENCODING_12B = 0x02

IMAGE_SCENE_TYPES = [0,1,2,3,5]
VIDEO_SCENE_TYPES = [4]



class ImageData(dict):
    """
    Structure for image data
    """
    def __init__(self, *arg,**kw):
        super().__init__(*arg, **kw)
        self._debug = True
        self.printCcsdsCopyright = True

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

    def __str__(self):
        str = "xScape Image Data"
        if 'Sessions' in self:
            str += f"\n\t{len(self['Sessions'])} Sessions:"
            for sessionid in self['Sessions']:
                str += f"\n\t\tSessionID\t= {sessionid}"
                if 'Closed' in self['Sessions'][sessionid]: str += f"\n\t\tClosed\t\t= {self['Sessions'][sessionid]['Closed']}"
                if 'tPacketVersion' in self['Sessions'][sessionid]: str += f"\n\t\tPacketVersion\t{self['Sessions'][sessionid]['tPacketVersion']}"
                if 'tPlatformID' in self['Sessions'][sessionid]: str += f"\n\t\tPlatformID\t{self['Sessions'][sessionid]['tPlatformID']}"
                if 'tInstrumentID' in self['Sessions'][sessionid]: str += f"\n\t\tInstrumentID\t{self['Sessions'][sessionid]['tInstrumentID']}"
                if 'ImagerInformation' in self['Sessions'][sessionid]:
                    str += "\n\t\tImagerInformation"
                    for x in self['Sessions'][sessionid]['ImagerInformation']:
                        str+= f"\n\t\t\t{x}\t= {self['Sessions'][sessionid]['ImagerInformation'][x]}"
                if 'ImagerConfiguration' in self['Sessions'][sessionid]:
                    str += "\n\t\tImagerConfiguration"
                    for x in self['Sessions'][sessionid]['ImagerConfiguration']:
                        str+= f"\n\t\t\t{x}\t= {self['Sessions'][sessionid]['ImagerConfiguration'][x]}"
                if 'SensorConfiguration' in self['Sessions'][sessionid]:
                    str += "\n\t\tSensorConfiguration"
                    for x in self['Sessions'][sessionid]['SensorConfiguration']:
                        str+= f"\n\t\t\t{x}\t= {self['Sessions'][sessionid]['SensorConfiguration'][x]}"
                if 'ImagerTelemetry' in self['Sessions'][sessionid]:
                    str += "\n\t\tImagerTelemetry"
                    for x in self['Sessions'][sessionid]['ImagerTelemetry']:
                        str += f"\n\t\t\t{x}"
                if 'OfeTelemetry' in self['Sessions'][sessionid]:
                    str += "\n\t\tOfeTelemetry"
                    for x in self['Sessions'][sessionid]['OfeTelemetry']:
                        str += f"\n\t\t\t{x}"
                if 'TimeSync' in self['Sessions'][sessionid]:
                    str += "\n\t\tTimeSync"
                    for x in self['Sessions'][sessionid]['TimeSync']:
                        str += f"\n\t\t\t{x}"
                if 'UserData' in self['Sessions'][sessionid]:
                    str += "\n\t\tUserData"
                    for x in self['Sessions'][sessionid]['UserData']:
                        numbytes = 0
                        str += f"\n\t\t\tUser Data ID {x}:"
                        for packet in self['Sessions'][sessionid]['UserData'][x]:
                            str += f"\n\t\t\t\t\t{packet}"
                if 'Scenes' in self['Sessions'][sessionid]:
                    str += f"\n\t\t{len(self['Sessions'][sessionid]['Scenes'])} Scenes:"
                    for scenenumber in self['Sessions'][sessionid]['Scenes']:
                        str += f"\n\t\t\tSceneNumber = {scenenumber}"
                        if scenenumber != None:
                            if 'Type' in self['Sessions'][sessionid]['Scenes'][scenenumber]:
                                str += f"\n\t\t\tType\t= {self['Sessions'][sessionid]['Scenes'][scenenumber]['Type']}"
                            if 'Width' in self['Sessions'][sessionid]['Scenes'][scenenumber]:
                                str += f"\n\t\t\tWidth\t= {self['Sessions'][sessionid]['Scenes'][scenenumber]['Width']}"
                            if 'Height' in self['Sessions'][sessionid]['Scenes'][scenenumber]:
                                str += f"\n\t\t\tHeight\t= {self['Sessions'][sessionid]['Scenes'][scenenumber]['Height']}"

                        if not 'Type' in self['Sessions'][sessionid]['Scenes'][scenenumber] or self['Sessions'][sessionid]['Scenes'][scenenumber]['Type'] in IMAGE_SCENE_TYPES:
                            if 'RawBands' in self['Sessions'][sessionid]['Scenes'][scenenumber]:
                                str += f"\n\t\t\t{len(self['Sessions'][sessionid]['Scenes'][scenenumber]['RawBands'])} RawBands:"
                                for band in self['Sessions'][sessionid]['Scenes'][scenenumber]['RawBands']:
                                    str += f"\n\t\t\t\tBand {band}\t= "
                                    format = self['Sessions'][sessionid]['Scenes'][scenenumber]['RawBands'][band]['Format']
                                    if format == PIXEL_FORMAT_MONO:
                                        str += "Single Band, "
                                    elif format == PIXEL_FORMAT_BAYER_RG:
                                        str += "Bayer RG, "
                                    elif format == PIXEL_FORMAT_BAYER_GR:
                                        str += "Bayer GR, "
                                    elif format == PIXEL_FORMAT_BAYER_GB:
                                        str += "Bayer GB, "
                                    elif format == PIXEL_FORMAT_BAYER_BG:
                                        str += "Bayer BG, "
                                    else:
                                        str += "Unknown, "
                                    encoding = self['Sessions'][sessionid]['Scenes'][scenenumber]['RawBands'][band]['Encoding']
                                    if encoding == PIXEL_ENCODING_8B8B:
                                        str += f"8-bit pixel depth"
                                    elif encoding == PIXEL_ENCODING_10B10B:
                                        str += f"10-bit pixel depth"
                                    elif encoding == PIXEL_ENCODING_10B16B:
                                        str += f"10-bit pixel depth in 16-bit words"
                                    elif encoding == PIXEL_ENCODING_12B12B:
                                        str += f"12-bit pixel depth"
                                    elif encoding == PIXEL_ENCODING_12B16B:
                                        str += f"12-bit pixel depth in 16-bit words"
                                    else:
                                        str += f"unsupported pixel encoding"
                            else:
                                str += "\n\t\t\t0 RawBands"
                            if 'ThumbnailBands' in self['Sessions'][sessionid]['Scenes'][scenenumber]:
                                str += f"\n\t\t\t{len(self['Sessions'][sessionid]['Scenes'][scenenumber]['ThumbnailBands'])} ThumbnailBands:"
                                for band in self['Sessions'][sessionid]['Scenes'][scenenumber]['ThumbnailBands']:
                                    str += f"\n\t\t\t\tBand {band}\t= "
                                    format = self['Sessions'][sessionid]['Scenes'][scenenumber]['ThumbnailBands'][band]['Format']
                                    if format == PIXEL_FORMAT_MONO:
                                        str += "Single Band, "
                                    elif format == PIXEL_FORMAT_BAYER_RG:
                                        str += "Bayer RG, "
                                    elif format == PIXEL_FORMAT_BAYER_GR:
                                        str += "Bayer GR, "
                                    elif format == PIXEL_FORMAT_BAYER_GB:
                                        str += "Bayer GB, "
                                    elif format == PIXEL_FORMAT_BAYER_BG:
                                        str += "Bayer BG, "
                                    else:
                                        str += "Unknown, "
                                    str += f"{self['Sessions'][sessionid]['Scenes'][scenenumber]['ThumbnailBands'][band]['LineLength']} pixels per line"
                                    encoding = self['Sessions'][sessionid]['Scenes'][scenenumber]['ThumbnailBands'][band]['Encoding']
                                    if encoding == PIXEL_ENCODING_8B8B:
                                        str += f" @ 8-bit pixel depth"
                                    elif encoding == PIXEL_ENCODING_10B10B:
                                        str += f" @ 10-bit pixel depth"
                                    elif encoding == PIXEL_ENCODING_10B16B:
                                        str += f" @ 10-bit pixel depth in 16-bit words"
                                    elif encoding == PIXEL_ENCODING_12B12B:
                                        str += f" @ 12-bit pixel depth"
                                    elif encoding == PIXEL_ENCODING_12B16B:
                                        str += f" @ 12-bit pixel depth in 16-bit words"
                                    else:
                                        str += f" @ unsupported pixel encoding"
                            else:
                                str += "\n\t\t\t0 ThumbnailBands"
                            if 'SegmentBands' in self['Sessions'][sessionid]['Scenes'][scenenumber]:
                                str += f"\n\t\t\t{len(self['Sessions'][sessionid]['Scenes'][scenenumber]['SegmentBands'])} SegmentBands:"
                                for band in self['Sessions'][sessionid]['Scenes'][scenenumber]['SegmentBands']:
                                    str += f"\n\t\t\t\tBand {band}\t= {len(self['Sessions'][sessionid]['Scenes'][scenenumber]['SegmentBands'][band]['Segments'])} segments"
                            else:
                                str += "\n\t\t\t0 SegmentBands"
                            if 'CCSDS122Bands' in self['Sessions'][sessionid]['Scenes'][scenenumber]:
                                str += f"\n\t\t\t{len(self['Sessions'][sessionid]['Scenes'][scenenumber]['CCSDS122Bands'])} CCSDS122Bands"
                                for band in self['Sessions'][sessionid]['Scenes'][scenenumber]['CCSDS122Bands']:
                                    for format in self['Sessions'][sessionid]['Scenes'][scenenumber]['CCSDS122Bands'][band]['Formats']:
                                        str += f"\n\t\t\t\tBand {band:2}, Format {format:2}, {len(self['Sessions'][sessionid]['Scenes'][scenenumber]['CCSDS122Bands'][band]['Formats'][format]['Segments'])} segments"
                            else:
                                str += "\n\t\t\t0 CCSDS122 Packets"

                        if not 'Type' in self['Sessions'][sessionid]['Scenes'][scenenumber] or self['Sessions'][sessionid]['Scenes'][scenenumber]['Type'] in VIDEO_SCENE_TYPES:
                            if 'Video' in self['Sessions'][sessionid]['Scenes'][scenenumber]:
                                str += f"\n\t\t\t{len(self['Sessions'][sessionid]['Scenes'][scenenumber]['Video'])} Video Packets"
                            else:
                                str += "\n\t\t\t0 Video Packets"

                else:
                    str += "\n\t0 Scenes"
        else:
            str += "\n\t0 Sessions"

        return str

    def rawImages(self, ImageData=None):
        """
        return raw images, just the images, with no metadata

        returns a list of arrays, one array for each scene and for each band in each scene.
            - array(s) of uint8 for 8-bit images
            - array(s) of uint16 for 10-bit and 12-bit images
        """

        if ImageData is None:
            sessions = self['Sessions']
        else:
            sessions = ImageData['Sessions']

        rawimages = []

        for SessionID in sessions:
            for SceneNumber in sessions[SessionID]['Scenes']:
                scene = sessions[SessionID]['Scenes'][SceneNumber]
                if 'RawBands' in scene:
                    for Band in scene['RawBands']:
                        _lines = scene['RawBands'][Band]['Lines']
                        _encoding = scene['RawBands'][Band]['Encoding']
                        if _encoding == PIXEL_ENCODING_8B8B:
                            img = numpy.zeros((len(_lines), len(_lines[0]['PixelData'])), dtype=numpy.uint8)
                        else:
                            img = numpy.zeros((len(_lines), len(_lines[0]['PixelData'])), dtype=numpy.uint16)
                        for i in _lines:
                            img[i] = _lines[i]['PixelData']
                        rawimages.append(img)

        return rawimages

    def rawCcsds(self, ImageData=None):
        """
        return raw ccsds image(s), containing only pixels, after decompression
        """

        if ImageData is None:
            sessions = self['Sessions']
        else:
            sessions = ImageData['Sessions']

        ccsdsimages = []

        for SessionID in sessions:
            for SceneNumber in sessions[SessionID]['Scenes']:
                scene = sessions[SessionID]['Scenes'][SceneNumber]
                if 'CCSDS122Bands' in scene:
                    import subprocess
                    for Band in scene['CCSDS122Bands']:
                        _format=0
                        _encoding=0

                        for _format in scene['CCSDS122Bands'][Band]['Formats']:
                            _codes = bytearray()
                            _segments = scene['CCSDS122Bands'][Band]['Formats'][_format]['Segments']

                            for segment in _segments:
                                _encoding=_segments[segment]['Encoding']
                                _codes.extend(_segments[segment]['Data'])

                            if len(_codes) > 0:
                                with open('codes.bin','wb') as fout:
                                    fout.write(_codes)

                                if self.printCcsdsCopyright:
                                    print("CCSDS 122.0-B-1 decompression performed using source code of which all copyright is owned by the Board of Regents of the University of Nebraska. (http://hyperspectral.unl.edu/licenseSource.htm)")
                                    self.printCcsdsCopyright = False
                                cmdline = ['bpe.exe', '-d', 'codes.bin', '-o', 'decompressed.raw']
                                try:
                                    subprocess.call(cmdline, stdin=None, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)                
                                except Exception as e:
                                    print(f"\nFailed to run 'bpe.exe'. Please ensure 'bpe.exe' is located in the folder containing your python script.")
                                    #raise(e)
                                    return

                                #Read in file that was written by C-application, and append the bytearray to the appropriate list.
                                with open("decompressed.raw", 'rb') as f:
                                    ccsds122Raw = f.read()
                                ccsdsimages.append(ccsds122Raw)

        return ccsdsimages

    def toRaw(self, FilenamePrefix=None, ImageData=None):
        '''
        Writes all image scene(s) to RAW binary file(s)
        
        Filenames are generated as follow: "<FilenamePrefix>_<type of image>_<image number>"

        If no parameter is specified,
            - FilenamePrefix is auto-generated using current system time
            - The instance member variable is used for ImageData
        '''
        if FilenamePrefix is None:
            FilenamePrefix = datetime.datetime.now().strftime("%y%m%d_%H%M%S.%f")

        FilenameSuffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")

        rawimages = self.rawImages(ImageData)
        i=0
        for im in rawimages:
            with open (f"{FilenamePrefix}Raw_{i}_{FilenameSuffix}.raw", 'wb') as outfile:
                outfile.write(im)
            i = i + 1

        ccsdsimages = self.rawCcsds(ImageData)
        i=0
        for im in ccsdsimages:
            with open (f"{FilenamePrefix}_Ccsds122_{i}.raw", 'wb') as outfile:
                outfile.write(im)
            i = i + 1


    def toJson(self, FilenamePrefix="", ImageData=None):
        '''
        Write all session ancillary data to JSON file

        '''

        if FilenamePrefix is None:
            FilenamePrefix = ""

        FilenameSuffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")

        if ImageData is None:
            sessions = self['Sessions']
        else:
            sessions = ImageData['Sessions']

        for SessionID in sessions:
            _filename = f"{FilenamePrefix}Session{SessionID}_{FilenameSuffix}.json"
            Session = sessions[SessionID]

            jsonout = {}
            if 'PlatformID' in Session:          jsonout['PlatformID'] = Session['PlatformID']
            if 'PlatformID' in Session:          jsonout['InstrumentID'] = Session['InstrumentID']
            if 'PacketVersion' in Session:       jsonout['PacketVersion'] = Session['PacketVersion']
            if 'Closed' in Session:              jsonout['SessionClosed'] = Session['Closed']

            if 'ImagerInformation' in Session:   jsonout['ImagerInformation'] = Session['ImagerInformation']
            if 'ImagerConfiguration' in Session: jsonout['ImagerConfiguration'] = Session['ImagerConfiguration']
            if 'SensorConfiguration' in Session: jsonout['SensorConfiguration'] = Session['SensorConfiguration']
            if 'ImagerTelemetry' in Session:     jsonout['ImagerTelemetry'] = Session['ImagerTelemetry']
            if 'OfeTelemetry' in Session:        jsonout['OfeTelemetry'] = Session['OfeTelemetry']
            if 'CompressionInfo' in Session:     jsonout['CompressionInfo'] = Session['CompressionInfo']

            if 'Scenes' in Session:
                jsonout['Scenes'] = []
                for SceneNumber in Session['Scenes']:
                    temp={}
                    temp['Number'] = SceneNumber
                    temp['Type'] = Session['Scenes'][SceneNumber]['Type']
                    temp['Width'] = Session['Scenes'][SceneNumber]['Width']
                    temp['Height'] = Session['Scenes'][SceneNumber]['Height']
                    jsonout['Scenes'].append(temp)

            if 'TimeSync' in Session:            jsonout['Timesync'] = Session['TimeSync']
            if 'UserData' in Session:
                jsonout['UserData'] = {}
                for DataID in Session['UserData']:
                    jsonout['UserData'][DataID] = []
                    for entry in Session['UserData'][DataID]:
                        temp = {}
                        temp['LastExposureTimestamp'] = entry['ExposureTimestamp']
                        temp['Data'] = entry['Data'].decode('utf8').replace("'", '"')
                        jsonout['UserData'][DataID].append(temp)

            with open(_filename, 'w') as json_file:
                json.dump(jsonout, json_file, indent=4)
            print(f"Wrote '{_filename}'")


    def toPng(self, FilenamePrefix="", ImageData=None, PixelFormat=None, EnhanceContrast=False):
        '''
        Writes all image scene(s) to PNG file(s)
        
        PNG filenames are generated as follow: "<FilenamePrefix>_<SessionID>_<SceneNumber>_["Raw"]/["TN"]_<Band>"

        If no parameter is specified,
            - FilenamePrefix is auto-generated using current system time
            - The instance member variable is used for ImageData

        If EnhanceContrast is True the output PNG will have histogram-stretch applied to enhance image contrast.
            Usefull to display full image contrast for images with pixel depth greater than 8-bit.

        '''

        if FilenamePrefix is None:
            FilenamePrefix = ""

        FilenameSuffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")

        if ImageData is None:
            sessions = self['Sessions']
        else:
            sessions = ImageData['Sessions']

        for SessionID in sessions:
            for SceneNumber in sessions[SessionID]['Scenes']:
                scene = sessions[SessionID]['Scenes'][SceneNumber]
                if 'RawBands' in scene:
                    for Band in scene['RawBands']:

                        _lines = []
                        for i, L in scene['RawBands'][Band]['Lines'].items():
                            _lines.append(L['PixelData'])

                        _filename = f"{FilenamePrefix}Session{SessionID}_Scene{SceneNumber}_Raw_Band{Band}_{FilenameSuffix}.png"
                        if PixelFormat is None:
                            _format = scene['RawBands'][Band]['Format']
                        else:
                            _format = PixelFormat
                        _encoding = scene['RawBands'][Band]['Encoding']
                        if _format == PIXEL_FORMAT_MONO:
                            if SceneNumber != None:
                                self._Lines2Png(_filename, scene['Width'], _encoding, _format, _lines, EnhanceContrast)
                            else:
                                self._Lines2Png(_filename,              0, _encoding, _format, _lines, EnhanceContrast)
                        elif _format in [PIXEL_FORMAT_BAYER_BG, PIXEL_FORMAT_BAYER_GB, PIXEL_FORMAT_BAYER_GR, PIXEL_FORMAT_BAYER_RG]:
                            #debayer
                            deb_lines = self._demosaic(scene['Width'], _encoding, _format, _lines)
                            self._Lines2Png(_filename, scene['Width'], PIXEL_ENCODING_8B8B, _format, deb_lines, EnhanceContrast)
                        else:
                            print("unsupported pixel format")

                if 'ThumbnailBands' in scene:
                    for Band in scene['ThumbnailBands']:

                        _lines = []
                        for i, L in scene['ThumbnailBands'][Band]['Lines'].items():
                            _lines.append(L['PixelData'])

                        _width = len(_lines[0])
                        _filename = f"{FilenamePrefix}Session{SessionID}_Scene{SceneNumber}_TN_Band{Band}_{FilenameSuffix}.png"
                        if PixelFormat is None:
                            _format = scene['ThumbnailBands'][Band]['Format']
                        else:
                            _format = PixelFormat
                        if _format == PIXEL_FORMAT_MONO:
                            if SceneNumber != None:
                                self._Lines2Png(_filename,         _width, PIXEL_ENCODING_8B8B, _format, _lines, EnhanceContrast)
                            else:
                                self._Lines2Png(_filename,              0, PIXEL_ENCODING_8B8B, _format, _lines, EnhanceContrast)
                        elif _format in [PIXEL_FORMAT_BAYER_BG, PIXEL_FORMAT_BAYER_GB, PIXEL_FORMAT_BAYER_GR, PIXEL_FORMAT_BAYER_RG]:
                            #debayer
                            deb_lines = self._demosaic(_width, PIXEL_ENCODING_8B8B, _format, _lines)
                            self._Lines2Png(_filename, _width, PIXEL_ENCODING_8B8B, _format, deb_lines, EnhanceContrast)

                if 'SegmentBands' in scene:
                    import io
                    try:
                        import PIL.Image
                    except ImportError:
                        raise ImportError('Please install the Pillow library:  pip install Pillow')
                    for Band in scene['SegmentBands']:
                        _filename = f"{FilenamePrefix}Session{SessionID}_Scene{SceneNumber}_Seg_Band{Band}_{FilenameSuffix}.png"
                        _rawsegmentpixels=[]
                        _lines=[]
                        _width=scene['SegmentBands'][Band]['LineLength']
                        _encoding=scene['SegmentBands'][Band]['Encoding']
                        for line_number, segment in scene['SegmentBands'][Band]['Segments'].items():
                            fseg = io.BytesIO(segment['SegmentData'])
                            with PIL.Image.open(fseg) as im:
                                _rawsegmentpixels = list(im.getdata())
                                width, height = im.size
                                _rawsegmentpixels = [_rawsegmentpixels[i * width:(i + 1) * width] for i in range(height)]
                            _lines.extend(_rawsegmentpixels[:])
                        self._Lines2Png(_filename,         _width, _encoding, PIXEL_FORMAT_MONO, _lines, EnhanceContrast)

                if 'CCSDS122Bands' in scene:
                    import subprocess
                    for Band in scene['CCSDS122Bands']:
                        _decompimages = {}
                        _filename = f""
                        _encoding=0
                        _linelength=0
                        for _format in scene['CCSDS122Bands'][Band]['Formats']:
                            _filename = f"{FilenamePrefix}Session{SessionID}_Scene{SceneNumber}_Ccsds122_Band{Band}_Format{_format}_{FilenameSuffix}.png"
                            _segments = scene['CCSDS122Bands'][Band]['Formats'][_format]['Segments']
                            _codes = bytearray()
                            for segment in _segments:
                                _encoding=_segments[segment]['Encoding']
                                _linelength=_segments[segment]['LineLength']
                                _codes.extend(_segments[segment]['Data'])

                            if len(_codes) > 0:
                                with open('codes.bin','wb') as fout:
                                    fout.write(_codes)
                                if self.printCcsdsCopyright:
                                    print("CCSDS 122.0-B-1 decompression performed using source code of which all copyright is owned by the Board of Regents of the University of Nebraska. (http://hyperspectral.unl.edu/licenseSource.htm)")
                                    self.printCcsdsCopyright = False
                                cmdline = ['bpe.exe', '-d', 'codes.bin', '-o', 'decompressed.raw']
                                try:
                                    subprocess.call(cmdline, stdin=None, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
                                except Exception as e:
                                    print(f"\nFailed to run 'bpe.exe'. Please ensure 'bpe.exe' is located in the folder containing your python script.")
                                    #raise(e)
                                    return

                            _decomplines = []
                            with open('decompressed.raw', "rb") as fin:
                                if _encoding == CCSDS_PIXEL_ENCODING_8B:
                                    while True:
                                        _line = fin.read(_linelength)
                                        if len(_line) < _linelength:
                                            break
                                        _decomplines.append(_line)
                                    # override encoding for _Lines2Png()
                                    _encoding = PIXEL_ENCODING_8B8B
                                elif _encoding == CCSDS_PIXEL_ENCODING_10B or _encoding == CCSDS_PIXEL_ENCODING_12B:
                                    _bytesperline = _linelength * 2
                                    while True:
                                        _input_line = fin.read(_bytesperline) # 16-bit words, with lower 10bit containing pixel value
                                        _output_line = array.array('H', [0]*_linelength)
                                        if len(_input_line) < _bytesperline:
                                            break
                                        i=0
                                        for column in range(_linelength):
                                            tmp = _input_line[i] + _input_line[i+1] * 256
                                            _output_line[column] = tmp
                                            i += 2
                                        _decomplines.append(_output_line)
                                    # override encoding for _Lines2Png()
                                    if _encoding == CCSDS_PIXEL_ENCODING_10B:
                                        _encoding = PIXEL_ENCODING_10B16B
                                    else:
                                        _encoding = PIXEL_ENCODING_12B16B
                                else:
                                    print("unsupported CCSDS stream data pixel encoding")
                            _decompimages[_format] = _decomplines
                        
                        if PIXEL_FORMAT_BAYER_R_COMP in _decompimages and PIXEL_FORMAT_BAYER_G_COMP in _decompimages and PIXEL_FORMAT_BAYER_B_COMP in _decompimages:
                            #combine R,G,B color components, demosaic, and generate PNG
                            _imwidth = len(_decompimages[PIXEL_FORMAT_BAYER_G_COMP][0])*2
                            _imheight = len(_decompimages[PIXEL_FORMAT_BAYER_G_COMP])
                            if _encoding == PIXEL_ENCODING_8B8B:
                                img = numpy.zeros((_imheight, _imwidth), dtype=numpy.uint8)
                            else:
                                img = numpy.zeros((_imheight, _imwidth), dtype=numpy.uint16)
                            for i in range(_imheight//2):
                                #even rows, RGRGRG
                                m = i * 2
                                for j in range(_imwidth//2):
                                    n = j * 2
                                    img[m,n]    = _decompimages[PIXEL_FORMAT_BAYER_R_COMP][i][j]
                                    img[m,n+1]  = _decompimages[PIXEL_FORMAT_BAYER_G_COMP][m][j]
                                #odd rows, GBGBGB
                                for j in range(_imwidth//2):
                                    n = j * 2
                                    img[m+1,n]   = _decompimages[PIXEL_FORMAT_BAYER_G_COMP][m+1][j]
                                    img[m+1,n+1] = _decompimages[PIXEL_FORMAT_BAYER_B_COMP][i][j]

                            deb_lines = self._demosaic(_imwidth, _encoding, PIXEL_FORMAT_BAYER_RG, img)
                            _filename = f"{FilenamePrefix}_Session{SessionID}_Scene{SceneNumber}_Ccsds122_Band{Band}_RGB_{FilenameSuffix}.png"
                            self._Lines2Png(_filename, _imwidth, PIXEL_ENCODING_8B8B, PIXEL_FORMAT_BAYER_RG, deb_lines, EnhanceContrast)

                        else:
                            for i in _decompimages:
                                self._Lines2Png(_filename, _linelength, _encoding, _format, _decompimages[i], EnhanceContrast)

    def _Lines2Png(self, Filename, Width, Encoding, Format, Lines, EnhanceContrast=False):
        '''
        Writes ImageData lines to PNG file
        '''

        _linewidth = len(Lines[0])
        if Width != _linewidth:
            print(f"Warning: Width Mismatch. Scene Width = {Width}, but image lines have {_linewidth} pixels")
            Width = _linewidth

        img = []

        # convert pixels to 8-bit for PNG
        if Format == PIXEL_FORMAT_MONO:
            if EnhanceContrast:
                minbrightness = min(min(Lines))
                maxbrightness = numpy.percentile(Lines, 99.9)
                _contrastfactor = 256/(maxbrightness-minbrightness)
                for line in Lines:
                    outline=[]
                    for pix in line:
                        pix_adjusted = int((pix-minbrightness) * _contrastfactor)
                        if (pix_adjusted > 255): pix_adjusted = 255
                        if (pix_adjusted < 0): pix_adjusted = 0
                        outline.append(pix_adjusted)
                    img.append(outline)
            else:
                if Encoding == PIXEL_ENCODING_8B8B:
                    for line in Lines:
                        img.append(line)
                elif Encoding == PIXEL_ENCODING_10B10B or Encoding == PIXEL_ENCODING_10B16B:
                    import time
                    for line in Lines:
                        line = array.array('H', line)
                        outline = array.array('B', [0]*Width)
                        for j in range(Width):
                            tmp = line[j]
                            tmp >>= 2
                            if tmp > 0xff:
                                tmp = 0xff
                            else:
                                tmp &= 0xff
                            outline[j] = tmp
                        img.append(outline)
                elif Encoding == PIXEL_ENCODING_12B12B or Encoding == PIXEL_ENCODING_12B16B:
                    for line in Lines:
                        line = array.array('H', line)
                        outline = array.array('B', [0]*Width)
                        for j in range(Width):
                            tmp = line[j]
                            tmp >>= 4
                            if tmp > 0xff:
                                tmp = 0xff
                            else:
                                tmp &= 0xff
                            outline[j] = tmp
                        img.append(outline)

        if Format == PIXEL_FORMAT_MONO:
            w = png.Writer(Width, len(img), greyscale=True)
            with open(Filename, 'wb') as f:
                w.write(f, img)
            if self._debug:
                print(f"Wrote {len(img)} image lines to '{Filename}'")
                if EnhanceContrast:
                    print(f"\tContrast Enhancement enabled. Raw image pixel range {minbrightness}-{maxbrightness} adjusted to 0-255")

        elif Format in [PIXEL_FORMAT_BAYER_BG, PIXEL_FORMAT_BAYER_GB, PIXEL_FORMAT_BAYER_GR, PIXEL_FORMAT_BAYER_RG]:
            try:
                import colour
            except ImportError:
                raise ImportError('Please install the colour-demosaicing library:  pip install colour-demosaicing')
            colour.utilities.suppress_warnings(colour_warnings=True, colour_runtime_warnings=True, colour_usage_warnings=True, python_warnings=True)
            Linesf = numpy.array(Lines)
            Linesf /= numpy.max(Linesf)
            Lines8 = (numpy.clip(Linesf, 0, 1) * 255).astype(numpy.uint8)
            colour.write_image(Lines8, Filename)

            if self._debug:
                print(f"Wrote {len(Lines8)} image lines to '{Filename}'")

        else:
            print("png format not supported")

    def _demosaic(self, Width, Encoding, Format, Lines):
        '''
        Debayer the raw input image lines
        Returns debayer'ed image lines
        '''

        try:
            import colour
            import colour_demosaicing
        except ImportError:
            raise ImportError('Please install the colour-demosaicing library:  pip install colour-demosaicing')
        colour.utilities.suppress_warnings(colour_warnings=True, colour_runtime_warnings=True, colour_usage_warnings=True, python_warnings=True)

        img = []

        # convert pixels to 8-bit for PNG
        if Encoding == PIXEL_ENCODING_8B8B:
            for line in Lines:
                img.append([x/255 for x in line])
        elif Encoding == PIXEL_ENCODING_10B10B:
            for line in Lines:
                outline = array.array('B', [0]*Width)
                for j in range(Width):
                    tmp = line[j]
                    tmp >>= 2
                    if tmp > 0xff:
                        tmp = 0xff
                    else:
                        tmp &= 0xff
                    outline[j] = tmp
                img.append(outline)
        elif Encoding == PIXEL_ENCODING_10B16B:
            for line in Lines:
                img.append([x/1023 for x in line])
        elif Encoding == PIXEL_ENCODING_12B12B:
            for line in Lines:
                outline = array.array('B', [0]*Width)
                for j in range(Width):
                    tmp = line[j]
                    tmp >>= 4
                    if tmp > 0xff:
                        tmp = 0xff
                    else:
                        tmp &= 0xff
                    outline[j] = tmp
                img.append(outline)
        elif Encoding == PIXEL_ENCODING_12B16B:
            for line in Lines:
                img.append([x/4095 for x in line])


        CFA_STRING = ""
        if Format == PIXEL_FORMAT_BAYER_RG:
            CFA_STRING = 'RGGB'
        elif Format == PIXEL_FORMAT_BAYER_GR:
            CFA_STRING = 'GRBG'
        elif Format == PIXEL_FORMAT_BAYER_GB:
            CFA_STRING = 'GBRG'
        elif Format == PIXEL_FORMAT_BAYER_BG:
            CFA_STRING = 'BGGR'
        else:
            return
        # Uncomment line for the demosaic algorithm preferred
        return colour_demosaicing.demosaicing_CFA_Bayer_bilinear(img, CFA_STRING)
        #return colour_demosaicing.demosaicing_CFA_Bayer_bilinear(img, 'BGGR')        
        #return colour_demosaicing.demosaicing_CFA_Bayer_Malvar2004(img, 'BGGR')
        #return colour.cctf_encoding(colour_demosaicing.demosaicing_CFA_Bayer_Menon2007(img, CFA_STRING))

    def toMp4(self, FilenamePrefix=None, ImageData=None):
        '''
        Writes the video scene to MP4 file(s)
        
        MP4 filenames are generated as follow: "<FilenamePrefix>_<SessionID>_<SceneNumber>_["Raw"]/["TN"]_<Band>"

        If no parameters are specified,
            - FilenamePrefix is auto-generated using current system time
            - The instance member variable is used for ImageData
        '''

        if FilenamePrefix is None:
            FilenamePrefix = datetime.datetime.now().strftime("%y%m%d_%H%M%S.%f")

        if ImageData is None:
            sessions = self['Sessions']
        else:
            sessions = ImageData['Sessions']

        for SessionID in sessions:
            for SceneNumber in sessions[SessionID]['Scenes']:
                if 'Video' in sessions[SessionID]['Scenes'][SceneNumber]:

                    try:
                        import ffmpeg
                    except ImportError:
                        raise ImportError('Please install the ffmpeg library:  pip install ffmpeg-python')
                    
                    _filename = f"{FilenamePrefix}Session{SessionID}_Scene{SceneNumber}_Video"

                    try:
                        mp4_file_pipe = (
                            ffmpeg
                            .input('pipe:', framerate=30)
                            .output(_filename+'.mp4', vcodec='copy')
                            .overwrite_output()
                            .run_async(pipe_stdin=True, quiet=True)
                        )
                    except:
                        raise FileNotFoundError('Please ensure that  ffmpeg.exe is present in your working directory')

                    for video_packet in sessions[SessionID]['Scenes'][SceneNumber]['Video']:
                        mp4_file_pipe.stdin.write(video_packet['Data'])

                    mp4_file_pipe.stdin.close()
                    mp4_file_pipe.wait()


class ImageDataCNP(ImageData):

    def __init__(self):
        super().__init__()

        from ctypes import cdll, c_int, c_char_p, c_float
        NP_POINTER_2D_u16 = numpy.ctypeslib.ndpointer(dtype=numpy.ushort, ndim=2, flags="C")
        NP_POINTER_3D_u16 = numpy.ctypeslib.ndpointer(dtype=numpy.ushort, ndim=3, flags="C")
        NP_POINTER_2D_u8 = numpy.ctypeslib.ndpointer(dtype=numpy.ubyte, ndim=2, flags="C")
        NP_POINTER_3D_f = numpy.ctypeslib.ndpointer(dtype=numpy.float, ndim=3, flags="C")

        import os.path
        dll_name = "png_lib"
        dllabspath = os.path.dirname(os.path.abspath(__file__)) + os.path.sep + dll_name
        c_lib = cdll.LoadLibrary(dllabspath)

        self.to_png16 = c_lib.to_png16
        self.to_png16.restype = c_int
        self.to_png16.argtypes = [c_char_p,  NP_POINTER_2D_u16, c_int, c_int, c_int, c_int, c_float, c_int]

        self.to_png8 = c_lib.to_png8
        self.to_png8.restype = c_int
        self.to_png8.argtypes = [c_char_p,  NP_POINTER_2D_u8, c_int, c_int, c_int, c_int, c_float, c_int]

        self.to_pngcolour_f = c_lib.to_png_colour
        self.to_pngcolour_f.restype = c_int
        self.to_pngcolour_f.argtypes = [c_char_p,  NP_POINTER_3D_f, c_int, c_int, c_int]


    def toPng(self, FilenamePrefix="", ImageData=None, PixelFormat=None, EnhanceContrast=False, Compression=3):
        '''
        Writes all image scene(s) to PNG file(s)

        PNG filenames are generated as follow: "<FilenamePrefix>_<SessionID>_<SceneNumber>_["Raw"]/["TN"]_<Band>"

        If no parameter is specified,
            - FilenamePrefix is auto-generated using current system time
            - The instance member variable is used for ImageData

        If EnhanceContrast is True the output PNG will have histogram-stretch applied to enhance image contrast.
            Usefull to display full image contrast for images with pixel depth greater than 8-bit.

        '''

        if FilenamePrefix is None:
            FilenamePrefix = ""

        FilenameSuffix = datetime.datetime.now().strftime("%y%m%d_%H%M%S")

        if ImageData is None:
            sessions = self['Sessions']
        else:
            sessions = ImageData['Sessions']

        for SessionID in sessions:
            for SceneNumber in sessions[SessionID]['Scenes']:
                scene = sessions[SessionID]['Scenes'][SceneNumber]
                if 'RawBands' in scene:
                    for Band in scene['RawBands']:

                        _lines = []
                        for i, L in scene['RawBands'][Band]['Lines'].items():
                            _lines.append(L['PixelData'])

                        _filename = f"{FilenamePrefix}Session{SessionID}_Scene{SceneNumber}_Raw_Band{Band}_{FilenameSuffix}.png"
                        if PixelFormat is None:
                            _format = scene['RawBands'][Band]['Format']
                        else:
                            _format = PixelFormat
                        _encoding = scene['RawBands'][Band]['Encoding']
                        if _format == PIXEL_FORMAT_MONO:
                            if SceneNumber != None:
                                self._Lines2PngMono(_filename, scene['Width'], _encoding, _lines, EnhanceContrast, Compression)
                            else:
                                self._Lines2PngMono(_filename,              0, _encoding, _lines, EnhanceContrast, Compression)
                        elif _format in [PIXEL_FORMAT_BAYER_BG, PIXEL_FORMAT_BAYER_GB, PIXEL_FORMAT_BAYER_GR, PIXEL_FORMAT_BAYER_RG]:
                            # debayer
                            if SceneNumber != None:
                                width = scene['Width']
                            else:
                                width = 0
                            deb_lines = self._demosaic(_encoding, _format, _lines)
                            self._Lines2PngColour(_filename, width, deb_lines, _encoding, Compression)
                        else:
                            print("unsupported pixel format")

                if 'ThumbnailBands' in scene:
                    for Band in scene['ThumbnailBands']:

                        _lines = []
                        for i, L in scene['ThumbnailBands'][Band]['Lines'].items():
                            _lines.append(L['PixelData'])

                        _width = len(_lines[0])
                        _filename = f"{FilenamePrefix}Session{SessionID}_Scene{SceneNumber}_TN_Band{Band}_{FilenameSuffix}.png"
                        if PixelFormat is None:
                            _format = scene['ThumbnailBands'][Band]['Format']
                        else:
                            _format = PixelFormat
                        if _format == PIXEL_FORMAT_MONO:
                            if SceneNumber != None:
                                self._Lines2PngMono(_filename,         _width, PIXEL_ENCODING_8B8B, _lines, EnhanceContrast, Compression)
                            else:
                                self._Lines2PngMono(_filename,              0, PIXEL_ENCODING_8B8B, _lines, EnhanceContrast, Compression)
                        elif _format in [PIXEL_FORMAT_BAYER_BG, PIXEL_FORMAT_BAYER_GB, PIXEL_FORMAT_BAYER_GR, PIXEL_FORMAT_BAYER_RG]:
                            #debayer
                            deb_lines = self._demosaic(PIXEL_ENCODING_8B8B, _format, _lines)
                            if SceneNumber != None:
                                self._Lines2PngColour(_filename, _width, deb_lines, PIXEL_ENCODING_8B8B, Compression)
                            else:
                                self._Lines2PngColour(_filename, 0, deb_lines, PIXEL_ENCODING_8B8B, Compression)

                if 'SegmentBands' in scene:
                    import io
                    try:
                        import PIL.Image
                    except ImportError:
                        raise ImportError('Please install the Pillow library:  pip install Pillow')
                    for Band in scene['SegmentBands']:
                        _filename = f"{FilenamePrefix}Session{SessionID}_Scene{SceneNumber}_Seg_Band{Band}_{FilenameSuffix}.png"
                        _rawsegmentpixels=[]
                        _lines=[]
                        _width=scene['SegmentBands'][Band]['LineLength']
                        _encoding=scene['SegmentBands'][Band]['Encoding']
                        for line_number, segment in scene['SegmentBands'][Band]['Segments'].items():
                            fseg = io.BytesIO(segment['SegmentData'])
                            with PIL.Image.open(fseg) as im:
                                _rawsegmentpixels = list(im.getdata())
                                width, height = im.size
                                _rawsegmentpixels = [_rawsegmentpixels[i * width:(i + 1) * width] for i in range(height)]
                            _lines.extend(_rawsegmentpixels[:])
                        self._Lines2PngMono(_filename,         _width, _encoding, PIXEL_FORMAT_MONO, _lines, EnhanceContrast, Compression)

                if 'CCSDS122Bands' in scene:
                    import subprocess
                    for Band in scene['CCSDS122Bands']:
                        _decompimages = {}
                        _filename = f""
                        _encoding=0
                        _linelength=0
                        for _format in scene['CCSDS122Bands'][Band]['Formats']:
                            _filename = f"{FilenamePrefix}Session{SessionID}_Scene{SceneNumber}_Ccsds122_Band{Band}_Format{_format}_{FilenameSuffix}.png"
                            _segments = scene['CCSDS122Bands'][Band]['Formats'][_format]['Segments']
                            _codes = bytearray()
                            for segment in _segments:
                                _encoding=_segments[segment]['Encoding']
                                _linelength=_segments[segment]['LineLength']
                                _codes.extend(_segments[segment]['Data'])

                            if len(_codes) > 0:
                                with open('codes.bin','wb') as fout:
                                    fout.write(_codes)
                                if self.printCcsdsCopyright:
                                    print("CCSDS 122.0-B-1 decompression performed using source code of which all copyright is owned by the Board of Regents of the University of Nebraska. (http://hyperspectral.unl.edu/licenseSource.htm)")
                                    self.printCcsdsCopyright = False
                                cmdline = ['bpe.exe', '-d', 'codes.bin', '-o', 'decompressed.raw']
                                try:
                                    subprocess.call(cmdline, stdin=None, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
                                except Exception as e:
                                    print(f"\nFailed to run 'bpe.exe'. Please ensure 'bpe.exe' is located in the folder containing your python script.")
                                    #raise(e)
                                    return

                            _decomplines = []
                            with open('decompressed.raw', "rb") as fin:
                                if _encoding == CCSDS_PIXEL_ENCODING_8B:
                                    while True:
                                        _line = fin.read(_linelength)
                                        if len(_line) < _linelength:
                                            break
                                        _decomplines.append(_line)
                                    # override encoding for _Lines2Png()
                                    _encoding = PIXEL_ENCODING_8B8B
                                elif _encoding == CCSDS_PIXEL_ENCODING_10B or _encoding == CCSDS_PIXEL_ENCODING_12B:
                                    _bytesperline = _linelength * 2
                                    while True:
                                        _input_line = fin.read(_bytesperline) # 16-bit words, with lower 10bit containing pixel value
                                        _output_line = array.array('H', [0]*_linelength)
                                        if len(_input_line) < _bytesperline:
                                            break
                                        i=0
                                        for column in range(_linelength):
                                            tmp = _input_line[i] + _input_line[i+1] * 256
                                            _output_line[column] = tmp
                                            i += 2
                                        _decomplines.append(_output_line)
                                    # override encoding for _Lines2Png()
                                    if _encoding == CCSDS_PIXEL_ENCODING_10B:
                                        _encoding = PIXEL_ENCODING_10B16B
                                    else:
                                        _encoding = PIXEL_ENCODING_12B16B
                                else:
                                    print("unsupported CCSDS stream data pixel encoding")
                            _decompimages[_format] = _decomplines

                        if PIXEL_FORMAT_BAYER_R_COMP in _decompimages and PIXEL_FORMAT_BAYER_G_COMP in _decompimages and PIXEL_FORMAT_BAYER_B_COMP in _decompimages:
                            #combine R,G,B color components, demosaic, and generate PNG
                            _imwidth = len(_decompimages[PIXEL_FORMAT_BAYER_G_COMP][0])*2
                            _imheight = len(_decompimages[PIXEL_FORMAT_BAYER_G_COMP])
                            if _encoding == PIXEL_ENCODING_8B8B:
                                img = numpy.zeros((_imheight, _imwidth), dtype=numpy.uint8)
                            else:
                                img = numpy.zeros((_imheight, _imwidth), dtype=numpy.uint16)
                           
							# RG-bayer (CMV12000)
                            if _linelength == 4096 or _linelength == 2048 or _linelength == 1024:
                                for i in range(_imheight//2):
                                    #even rows, RGRGRG
                                    m = i * 2
                                    for j in range(_imwidth//2):
                                        n = j * 2
                                        img[m,n]    = _decompimages[PIXEL_FORMAT_BAYER_R_COMP][i][j]
                                        img[m,n+1]  = _decompimages[PIXEL_FORMAT_BAYER_G_COMP][m][j]
                                    #odd rows, GBGBGB
                                    for j in range(_imwidth//2):
                                        n = j * 2
                                        img[m+1,n]   = _decompimages[PIXEL_FORMAT_BAYER_G_COMP][m+1][j]
                                        img[m+1,n+1] = _decompimages[PIXEL_FORMAT_BAYER_B_COMP][i][j]

                                _filename = f"{FilenamePrefix}_Session{SessionID}_Scene{SceneNumber}_Ccsds122_Band{Band}_RGB_{FilenameSuffix}.png"
                                if PixelFormat is None:
                                    deb_lines = self._demosaic(_imwidth, _encoding, PIXEL_FORMAT_BAYER_RG, img)
                                    self._Lines2PngColour(_filename, _imwidth, deb_lines, PIXEL_ENCODING_8B8B, Compression)
                                else:
                                    self._Lines2PngMono(_filename, _imwidth, _encoding, img,  EnhanceContrast, Compression)
                            
                            # GB-bayer (GMAX3265)
                            else:
                                for i in range(_imheight//2):
                                    #even rows, GBGB  
                                    m = i * 2
                                    for j in range(_imwidth//2):
                                        n = j * 2
                                        img[m,n]    = _decompimages[PIXEL_FORMAT_BAYER_G_COMP][m][j]
                                        img[m,n+1]  = _decompimages[PIXEL_FORMAT_BAYER_B_COMP][i][j]
                                    #odd rows, RGRG
                                    for j in range(_imwidth//2):
                                        n = j * 2
                                        img[m+1,n]   = _decompimages[PIXEL_FORMAT_BAYER_R_COMP][i][j]
                                        img[m+1,n+1] = _decompimages[PIXEL_FORMAT_BAYER_G_COMP][m+1][j]

                                _filename = f"{FilenamePrefix}_Session{SessionID}_Scene{SceneNumber}_Ccsds122_Band{Band}_RGB_{FilenameSuffix}.png"
                                if PixelFormat is None:
                                    deb_lines = self._demosaic(_encoding, PIXEL_FORMAT_BAYER_GB, img)
                                    self._Lines2PngColour(_filename, _imwidth, deb_lines, PIXEL_ENCODING_8B8B, Compression)
                                else:
                                    self._Lines2PngMono(_filename, _imwidth, _encoding, img,  EnhanceContrast, Compression)

                        else:
                            for i in _decompimages:
                                self._Lines2PngMono(_filename, _linelength, _encoding, _decompimages[i],  EnhanceContrast, Compression)

    def _Lines2PngMono(self, Filename, Width, Encoding, Lines, EnhanceContrast, Compression):
        '''
        Writes ImageData lines to PNG file
        '''

        _linewidth = len(Lines[0])
        if Width != _linewidth:
            print(f"Warning: Width Mismatch. Scene Width = {Width}, but image lines have {_linewidth} pixels")
            Width = _linewidth

        Height = len(Lines)

        # convert pixels to 8-bit for PNG
        img = numpy.vstack(Lines)

        if EnhanceContrast:
            minbrightness = int(img.min())
            maxbrightness = numpy.percentile(img, 99.9)
            contrastfactor = 1.0/(maxbrightness-minbrightness)
        else:
            minbrightness = -1
            contrastfactor = 0.0

        if Encoding == PIXEL_ENCODING_8B8B:
            contrastfactor *= 256
            self.to_png8(Filename.encode(), img, Height, Width, 0, minbrightness, contrastfactor, Compression)
        elif Encoding == PIXEL_ENCODING_10B10B or Encoding == PIXEL_ENCODING_10B16B:
            contrastfactor *= 1024
            self.to_png16(Filename.encode(), img, Height, Width, 10, minbrightness, contrastfactor, Compression)
        elif Encoding == PIXEL_ENCODING_12B12B or Encoding == PIXEL_ENCODING_12B16B:
            contrastfactor *= 4096
            self.to_png16(Filename.encode(), img, Height, Width, 12, minbrightness, contrastfactor, Compression)

        if self._debug:
            print(f"Wrote {Height} image lines to '{Filename}'")
            
    def _Lines2PngColour(self, Filename, Width, img, Encoding, Compression):
        Height = img.shape[0]

        if Width == 0:
            Width = img.shape[1]

        if Encoding == PIXEL_ENCODING_8B8B:
            err = self.to_pngcolour_f(Filename.encode(), img, Height, Width, 8, Compression)
        elif Encoding == PIXEL_ENCODING_10B10B or Encoding == PIXEL_ENCODING_10B16B or Encoding == PIXEL_ENCODING_12B12B or Encoding == PIXEL_ENCODING_12B16B:
            err = self.to_pngcolour_f(Filename.encode(), img, Height, Width, 16, Compression)

        if err > 0:
            raise IOError(f"Writing to '{Filename}' returned error code: {err}")

        if self._debug:
            print(f"Wrote {Height} image lines to '{Filename}'")


    def _demosaic(self, Encoding, Format, Lines):
        '''
        Debayer the raw input image lines
        Returns debayer'ed image lines
        '''

        try:
            import colour
            import colour_demosaicing
        except ImportError:
            raise ImportError('Please install the colour-demosaicing library:  pip install colour-demosaicing')
        colour.utilities.suppress_warnings(colour_warnings=True, colour_runtime_warnings=True, colour_usage_warnings=True, python_warnings=True)

        img = numpy.vstack(Lines)

    # convert pixels to 8-bit for PNG
        if Encoding == PIXEL_ENCODING_8B8B:
            imgf = img / 255.0
        elif Encoding == PIXEL_ENCODING_10B10B or Encoding == PIXEL_ENCODING_10B16B:
            imgf = img / 1023.0
        elif Encoding == PIXEL_ENCODING_12B12B or Encoding == PIXEL_ENCODING_12B16B:
            imgf = img / 4095.0

        CFA_STRING = ""
        if Format == PIXEL_FORMAT_BAYER_RG:
            CFA_STRING = 'RGGB'
        elif Format == PIXEL_FORMAT_BAYER_GR:
            CFA_STRING = 'GRBG'
        elif Format == PIXEL_FORMAT_BAYER_GB:
            CFA_STRING = 'GBRG'
        elif Format == PIXEL_FORMAT_BAYER_BG:
            CFA_STRING = 'BGGR'
        else:
            return

        # Uncomment line for the demosaic algorithm preferred
        return colour_demosaicing.demosaicing_CFA_Bayer_bilinear(imgf, CFA_STRING)
        #return colour_demosaicing.demosaicing_CFA_Bayer_bilinear(img, 'BGGR')
        #return colour_demosaicing.demosaicing_CFA_Bayer_Malvar2004(img, 'BGGR')
        #return colour.cctf_encoding(colour_demosaicing.demosaicing_CFA_Bayer_Menon2007(img, CFA_STRING))


def Compare(FileA, FileB, w, h, bpp):
    '''
    Compare two raw files, to see how similar they are.        
        - FileA, FileB the string names of the raw files
        - w, h the width and height of the file.
        - bpp (bits per pixel)
        
    '''
    with open(FileA, 'rb') as f:
        fa = f.read()        
    with open(FileB, 'rb') as f:
        fb = f.read()                
    
    #Arr2DA = numpy.zeros((h, w) , dtype = numpy.ubyte)
    if bpp == 8:
        Arr2DA = numpy.frombuffer(fa, dtype = numpy.ubyte)
        Arr2DB = numpy.frombuffer(fb, dtype = numpy.ubyte)
        Arr2DA = numpy.reshape(Arr2DA, (h, w))
        Arr2DB = numpy.reshape(Arr2DB, (h, w))
        _ImgCompare(Arr2DA, Arr2DB, 8)

    elif bpp == 10:#2x bytes per pixel
        Arr2DA = numpy.zeros( h*w , dtype = numpy.ushort)
        Arr2DB = numpy.zeros( h*w , dtype = numpy.ushort)
        for i in range(w*h):
            Arr2DA[i] = fa[2*i] + (fa[(2*i) +1]) << 8
            Arr2DB[i] = fb[2*i] + (fb[(2*i) +1]) << 8
        Arr2DA = numpy.reshape(Arr2DA, (h,w))
        Arr2DB = numpy.reshape(Arr2DB, (h,w))
        _ImgCompare(Arr2DA, Arr2DB, 10)

    elif bpp == 12:#2x bytes per pixel
        Arr2DA = numpy.zeros( h*w, dtype = numpy.ushort)
        Arr2DB = numpy.zeros( h*w, dtype = numpy.ushort)
        for i in range(w*h):
            Arr2DA[i] = fa[2*i] + (fa[(2*i) +1]) << 10
            Arr2DB[i] = fb[2*i] + (fb[(2*i) +1]) << 10
        Arr2DA = numpy.reshape(Arr2DA, (h,w))
        Arr2DB = numpy.reshape(Arr2DB, (h,w))
        _ImgCompare(Arr2DA, Arr2DB, 12)            

def _ImgCompare(ImgA, ImgB, B):
    '''
    Compare ImgA with ImgB, where the result is given as Mean Square Error (MSE), 
    Peak Signal to Noise Ratio (PSNR) as defined in CCSDS 120.1-G-2 pg 2-2, 
    and Maxsimum Absolute Error (MAE).
    
    Input:
        - ImgA, ImgB (2D array, with dimensions width x height, with B bits per pixel)    
    '''
    SumDiffSq = 0.0
    AbsMaxDiff = 0
    height = numpy.shape(ImgA)[0]
    width  = numpy.shape(ImgA)[1]
    tenp=height//100+1
    for i in range(height):
        for j in range(width):
            diff = int(ImgA[i][j]) - int(ImgB[i][j])
            if abs(diff) > AbsMaxDiff:
                AbsMaxDiff = abs(diff)
            SumDiffSq = SumDiffSq + float( abs(diff) )**2
        if i%tenp==0:
            print(f"{i//tenp}%\r",end="")
    mse = SumDiffSq / (height * width)
    if mse == 0.0:
        PeakSNR = 'inf'
    else:
        PeakSNR = 20*numpy.log10(  ((2**B) -1)   / numpy.sqrt(mse) )
    
    print(    f"Mean Square Error          (MSE) : {round(mse, 2)}")
    if mse == 0.0:
        print(f"Peak Signal to Noise ratio (PSNR): {PeakSNR} dB")
    else:
        print(f"Peak Signal to Noise ratio (PSNR): {round(PeakSNR, 2)} dB")
    print(    f"Maximum Absolute Error     (MAE) : {round(AbsMaxDiff, 2)}")
    
    return mse, PeakSNR, AbsMaxDiff



'''
Simera Sense TriScape100 Class
Copyright (c) 2019-2020 Simera Sense (info@simerasense.com)
Released under MIT License.
'''

from . import exceptions
from . import xscape
from . import snapshot
from . import cmv12000

# Module Constants


class TriScape100(snapshot.SnapShot, cmv12000.CMV12000):
    """
    TriScape100 class

    Inherits from the SnapShot and CMV12000 class, and extends it for TriScape100 specific commands and requests.
    """

    def __init__(self, EGSE = None, I2Caddr = None):
        """
        TriScape100 Constructor
    
        __init__(EGSE = None, I2Caddr = None, threadLock = None)
    
        Optional Arguments:
            EGSE        - Instance of Simera EGSE class
            I2Caddr     - Set if using the I2C control interface
        """

        # run the parent (xScape) instance constructor
        super().__init__(EGSE, I2Caddr)     

        # add the produt specific telemetry information
        self.ce_tlm_info = [
                            {'Name':'V_FeeSmps'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':   0, 'Max': 300}, 'Range_FeeOn':{'Min':2000, 'Max':2060}},
                            {'Name':'C_FeeSmps'    , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':   0, 'Max':  25}, 'Range_FeeOn':{'Min': 190, 'Max': 450}},
                            {'Name':'C_FeeLdo'     , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':   0, 'Max':  25}, 'Range_FeeOn':{'Min':   0, 'Max':  55}},
                            {'Name':'V_FeeNegSmps' , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'C_Brd5V0'     , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':   0, 'Max':  80}, 'Range_FeeOn':{'Min':   0, 'Max':  80}},
                            {'Name':'V_FeeOpAmp'   , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_SdramVtt'   , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min': 585, 'Max': 615}, 'Range_FeeOn':{'Min': 585, 'Max': 615}},
                            {'Name':'V_Brd3V3'     , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':3280, 'Max':3400}, 'Range_FeeOn':{'Min':3280, 'Max':3400}},
                            {'Name':'V_Brd2V5'     , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':2490, 'Max':2560}, 'Range_FeeOn':{'Min':2490, 'Max':2560}},
                            {'Name':'V_RefCal0'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':1016, 'Max':1032}, 'Range_FeeOn':{'Min':1016, 'Max':1032}},
                            {'Name':'V_FeeLdo'     , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':   0, 'Max':  10}, 'Range_FeeOn':{'Min':2950, 'Max':3150}},
                            {'Name':'V_IntTst0'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_REFM0'      , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_REFP0'      , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'C_BrdLdo'     , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':  85, 'Max': 130}, 'Range_FeeOn':{'Min':  85, 'Max': 130}},
                            {'Name':'C_Smps3V3'    , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':  90, 'Max': 220}, 'Range_FeeOn':{'Min': 310, 'Max': 500}},
                            {'Name':'V_Smps1V2'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':1190, 'Max':1240}, 'Range_FeeOn':{'Min':1190, 'Max':1240}},
                            {'Name':'V_Smps1V0'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min': 990, 'Max':1010}, 'Range_FeeOn':{'Min': 990, 'Max':1010}},
                            {'Name':'C_Smps1V0'    , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min': 200, 'Max': 530}, 'Range_FeeOn':{'Min': 200, 'Max': 650}},
                            {'Name':'C_Smps1V2'    , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':  20, 'Max': 200}, 'Range_FeeOn':{'Min':  20, 'Max': 200}},
                            {'Name':'V_Brd1V8'     , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':1790, 'Max':1840}, 'Range_FeeOn':{'Min':1790, 'Max':1840}},
                            {'Name':'C_SdramVtt'   , 'Unit':'mA', 'Used':True  , 'Range_FeeOff':{'Min':   0, 'Max':  15}, 'Range_FeeOn':{'Min':   0, 'Max':  15}},
                            {'Name':'V_RefCal1'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':1016, 'Max':1032}, 'Range_FeeOn':{'Min':1016, 'Max':1032}},
                            {'Name':'V_IntTst1'    , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_REFM1'      , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_REFP1'      , 'Unit':'mV', 'Used':False , 'Range_FeeOff':{'Min':   0, 'Max':   0}, 'Range_FeeOn':{'Min':   0, 'Max':   0}},
                            {'Name':'V_Fpga1V0'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min': 970, 'Max':1030}, 'Range_FeeOn':{'Min': 970, 'Max':1030}},
                            {'Name':'V_Fpga1V8'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':1745, 'Max':1855}, 'Range_FeeOn':{'Min':1745, 'Max':1855}},
                            {'Name':'V_Fpga2V5'    , 'Unit':'mV', 'Used':True  , 'Range_FeeOff':{'Min':2425, 'Max':2575}, 'Range_FeeOn':{'Min':2425, 'Max':2575}},
                            {'Name':'T_Fpga'       , 'Unit':'`C', 'Used':True  , 'Range_FeeOff':{'Min': -25, 'Max':  80}, 'Range_FeeOn':{'Min': -25, 'Max':  80}}
                           ]
                           
        self.fee_tlm_info = [
                            {'Name':'V_FeeSmps'    , 'Unit':'mV', 'Used':True  , 'Range':{'Min':1980, 'Max':2060}},
                            {'Name':'V_FeeLdo'     , 'Unit':'mV', 'Used':True  , 'Range':{'Min':2950, 'Max':3150}},
                            {'Name':'(unused)'     , 'Unit':'mV', 'Used':False , 'Range':{'Min':   0, 'Max':   0}},
                            {'Name':'V_TFLLow2'    , 'Unit':'mV', 'Used':True  , 'Range':{'Min':  40, 'Max':  55}},
                            {'Name':'V_TFLLow3'    , 'Unit':'mV', 'Used':True  , 'Range':{'Min':  40, 'Max':  55}},
                            {'Name':'V_Bandgap'    , 'Unit':'mV', 'Used':True  , 'Range':{'Min':1125, 'Max':1175}},
                            {'Name':'V_ResetL'     , 'Unit':'mV', 'Used':True  , 'Range':{'Min':  36, 'Max':  56}},
                            {'Name':'V_RefADC'     , 'Unit':'mV', 'Used':True  , 'Range':{'Min':1750, 'Max':1825}},
                            {'Name':'V_CmvRef'     , 'Unit':'mV', 'Used':True  , 'Range':{'Min': 530, 'Max': 585}},
                            {'Name':'V_Ramp2'      , 'Unit':'mV', 'Used':False , 'Range':{'Min':   0, 'Max':   0}},
                            {'Name':'V_Ramp1'      , 'Unit':'mV', 'Used':False , 'Range':{'Min':   0, 'Max':   0}},
                            {'Name':'V_IntTst'     , 'Unit':'mV', 'Used':False , 'Range':{'Min':   0, 'Max':   0}},
                            {'Name':'V_REFM'       , 'Unit':'mV', 'Used':False , 'Range':{'Min':   0, 'Max':   0}},
                            {'Name':'V_REFP'       , 'Unit':'mV', 'Used':False , 'Range':{'Min':   0, 'Max':   0}},
                            {'Name':'T_CMV'        , 'Unit':'`C', 'Used':True  , 'Range':{'Min': -15, 'Max':  65}}
                            ]

        # add product specific current consumption - (to be confirmed)
        self.total_current_info = {'Name':'Current', 'Unit':'mA',  'Range_FeeOff':{'Min': 400, 'Max':  700}, 'Range_FeeOn':{'Min': 800, 'Max':  1500}}

        # add product specific current limtis (latch-up protection)
        self.current_limits = [
                            {'Name':'C_FeeSmps'    ,'Limit':900},
                            {'Name':'C_FeeLdo'     ,'Limit':750},
                            {'Name':'C_Brd5V0'     ,'Limit':200},
                            {'Name':'C_BrdLdo'     ,'Limit':500},
                            {'Name':'C_Smps3V3'    ,'Limit':1000},
                            {'Name':'C_Smps1V0'    ,'Limit':1000},
                            {'Name':'C_Sdrm1V2'    ,'Limit':300},
                            {'Name':'C_SdramVtt'   ,'Limit':20},
                            ]      

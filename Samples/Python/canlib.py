#!/usr/bin/env python
import ctypes as ct
import sys
import struct
import logging
import inspect

# -------------------
# Canlib constants
# -------------------

canOK = 0
canERR_PARAM = -1
canERR_NOMSG = -2
canERR_NOTFOUND = -3
canERR_NOCHANNELS = -5
canERR_TIMEOUT = -7
canERR_INVHANDLE = -10
canERR_TXBUFOFL = -13
canERR_NOCARD = -26
canERR_SCRIPT_FAIL = -39
canERR_NOT_IMPLEMENTED = -32

canOPEN_EXCLUSIVE = 0x0008
canOPEN_REQUIRE_EXTENDED = 0x0010
canOPEN_ACCEPT_VIRTUAL = 0x0020
canOPEN_OVERRIDE_EXCLUSIVE = 0x0040
canOPEN_REQUIRE_INIT_ACCESS = 0x0080
canOPEN_NO_INIT_ACCESS = 0x0100
canOPEN_ACCEPT_LARGE_DLC = 0x0200
canOPEN_CAN_FD = 0x0400
canOPEN_CAN_FD_NONISO = 0x0800

canBITRATE_1M = -1
canBITRATE_500K = -2
canBITRATE_250K = -3
canBITRATE_125K = -4
canBITRATE_100K = -5
canBITRATE_62K = -6
canBITRATE_50K = -7
canBITRATE_83K = -8
canBITRATE_10K = -9

canFD_BITRATE_500K_80P = -1001
canFD_BITRATE_1M_80P = -1002
canFD_BITRATE_2M_80P = -1003

canIOCTL_PREFER_EXT = 1
canIOCTL_PREFER_STD = 2
canIOCTL_CLEAR_ERROR_COUNTERS = 5
canIOCTL_SET_TIMER_SCALE = 6
canIOCTL_SET_TXACK = 7
canIOCTL_GET_RX_BUFFER_LEVEL = 8
canIOCTL_GET_TX_BUFFER_LEVEL = 9
canIOCTL_FLUSH_RX_BUFFER = 10
canIOCTL_FLUSH_TX_BUFFER = 11
canIOCTL_GET_TIMER_SCALE = 12
canIOCTL_SET_TXRQ = 13
canIOCTL_GET_EVENTHANDLE = 14
canIOCTL_SET_BYPASS_MODE = 15
canIOCTL_SET_WAKEUP = 16
canIOCTL_MAP_RXQUEUE = 18
canIOCTL_GET_WAKEUP = 19
canIOCTL_SET_REPORT_ACCESS_ERRORS = 20
canIOCTL_GET_REPORT_ACCESS_ERRORS = 21
canIOCTL_CONNECT_TO_VIRTUAL_BUS = 22
canIOCTL_DISCONNECT_FROM_VIRTUAL_BUS = 23
canIOCTL_SET_USER_IOPORT = 24
canIOCTL_GET_USER_IOPORT = 25
canIOCTL_SET_BUFFER_WRAPAROUND_MODE = 26
canIOCTL_SET_RX_QUEUE_SIZE = 27
canIOCTL_SET_USB_THROTTLE = 28
canIOCTL_GET_USB_THROTTLE = 29
canIOCTL_SET_BUSON_TIME_AUTO_RESET = 30
canIOCTL_GET_TXACK = 31
canIOCTL_SET_LOCAL_TXECHO = 32
canIOCTL_SET_ERROR_FRAMES_REPORTING = 33
canIOCTL_GET_CHANNEL_QUALITY = 34
canIOCTL_GET_ROUNDTRIP_TIME = 35
canIOCTL_GET_BUS_TYPE = 36
canIOCTL_GET_DEVNAME_ASCII = 37
canIOCTL_GET_TIME_SINCE_LAST_SEEN = 38
canIOCTL_GET_TREF_LIST = 39

canCHANNELDATA_CHANNEL_CAP = 1
canCHANNELDATA_TRANS_CAP = 2
canCHANNELDATA_CHANNEL_FLAGS = 3
canCHANNELDATA_CARD_TYPE = 4
canCHANNELDATA_CARD_NUMBER = 5
canCHANNELDATA_CHAN_NO_ON_CARD = 6
canCHANNELDATA_CARD_SERIAL_NO = 7
canCHANNELDATA_TRANS_SERIAL_NO = 8
canCHANNELDATA_CARD_FIRMWARE_REV = 9
canCHANNELDATA_CARD_HARDWARE_REV = 10
canCHANNELDATA_CARD_UPC_NO = 11
canCHANNELDATA_TRANS_UPC_NO = 12
canCHANNELDATA_CHANNEL_NAME = 13
canCHANNELDATA_DLL_FILE_VERSION = 14
canCHANNELDATA_DLL_PRODUCT_VERSION = 15
canCHANNELDATA_DLL_FILETYPE = 16
canCHANNELDATA_TRANS_TYPE = 17
canCHANNELDATA_DEVICE_PHYSICAL_POSITION = 18
canCHANNELDATA_UI_NUMBER = 19
canCHANNELDATA_TIMESYNC_ENABLED = 20
canCHANNELDATA_DRIVER_FILE_VERSION = 21
canCHANNELDATA_DRIVER_PRODUCT_VERSION = 22
canCHANNELDATA_MFGNAME_UNICODE = 23
canCHANNELDATA_MFGNAME_ASCII = 24
canCHANNELDATA_DEVDESCR_UNICODE = 25
canCHANNELDATA_DEVDESCR_ASCII = 26
canCHANNELDATA_DRIVER_NAME = 27
canCHANNELDATA_CHANNEL_QUALITY = 28
canCHANNELDATA_ROUNDTRIP_TIME = 29
canCHANNELDATA_BUS_TYPE = 30
canCHANNELDATA_DEVNAME_ASCII = 31
canCHANNELDATA_TIME_SINCE_LAST_SEEN = 32
canCHANNELDATA_REMOTE_OPERATIONAL_MODE = 33
canCHANNELDATA_REMOTE_PROFILE_NAME = 34

canMSG_MASK = 0x00ff
canMSG_RTR = 0x0001
canMSG_STD = 0x0002
canMSG_EXT = 0x0004
canMSG_WAKEUP = 0x0008
canMSG_NERR = 0x0010
canMSG_ERROR_FRAME = 0x0020
canMSG_TXACK = 0x0040
canMSG_TXRQ = 0x0080
canFDMSG_MASK = 0xff0000
canFDMSG_EDL = 0x010000
canFDMSG_BRS = 0x020000
canFDMSG_ESI = 0x040000
canMSGERR_MASK = 0xff00
canMSGERR_HW_OVERRUN = 0x0200
canMSGERR_SW_OVERRUN = 0x0400
canMSGERR_STUFF = 0x0800
canMSGERR_FORM = 0x1000
canMSGERR_CRC = 0x2000
canMSGERR_BIT0 = 0x4000
canMSGERR_BIT1 = 0x8000
canMSGERR_OVERRUN = 0x0600
canMSGERR_BIT = 0xC000
canMSGERR_BUSERR = 0xF800

canDRIVER_NORMAL = 4
canDRIVER_SILENT = 1
canDRIVER_SELFRECEPTION = 8
canDRIVER_OFF = 0

kvEVENT_TYPE_KEY = 1

kvSCRIPT_STOP_NORMAL = 0
kvSCRIPT_STOP_FORCED = -9

kvDEVICE_MODE_INTERFACE = 0
kvDEVICE_MODE_LOGGER = 1

ENVVAR_MAX_SIZE = 4096

kvENVVAR_TYPE_INT = 1
kvENVVAR_TYPE_FLOAT = 2
kvENVVAR_TYPE_STRING = 3


class canError(Exception):
    def __init__(self, canlib, canERR):
        self.canlib = canlib
        self.canERR = canERR
        self.fn = canlib.fn

    def __canGetErrorText(self):
        msg = ct.create_string_buffer(80)
        self.canlib.dll.canGetErrorText(self.canERR, msg, ct.sizeof(msg))
        return msg.value

    def __str__(self):
        return "[canError] %s: %s (%d)" % (self.fn,
                                           self.__canGetErrorText(),
                                           self.canERR)


class canNoMsg(canError):
    def __init__(self, canlib, canERR):
        self.canlib = canlib
        self.canERR = canERR

    def __str__(self):
        return "No messages available"


class canScriptFail(canError):
    def __init__(self, canlib, canERR):
        self.canlib = canlib
        self.canERR = canERR

    def __str__(self):
        return "Script error"


class EnvvarException(Exception):
    pass


class EnvvarValueError(EnvvarException):
    def __init__(self, envvar, type_, value):
        msg = ("invalid literal for envvar ({envvar}) with"
               " type {type_}: {value}")
        msg.format(envvar=envvar, type_=type_, value=value)
        super(EnvvarValueError, self).__init__(msg)


class EnvvarNameError(EnvvarException):
    def __init__(self, envvar):
        msg = "envvar names must not start with an underscore: {envvar}"
        msg.format(envvar=envvar)
        super(EnvvarValueError, self).__init__(msg)


class canVersion(ct.Structure):
    _fields_ = [
        ("minor", ct.c_uint8),
        ("major", ct.c_uint8),
        ]

    def __str__(self):
        return "%d.%d" % (self.major, self.minor)


class bitrateSetting(object):
    def __init__(self, freq=1000000, tseg1=4, tseg2=3, sjw=1, nosamp=1,
                 syncMode=0):
        self.freq = freq
        self.tseg1 = tseg1
        self.tseg2 = tseg2
        self.sjw = sjw
        self.nosamp = nosamp
        self.syncMode = syncMode

    def __str__(self):
        txt = "freq    : %8d\n" % self.freq
        txt += "tseg1   : %8d\n" % self.tseg1
        txt += "tseg2   : %8d\n" % self.tseg2
        txt += "sjw     : %8d\n" % self.sjw
        txt += "nosamp  : %8d\n" % self.nosamp
        txt += "syncMode: %8d\n" % self.syncMode
        return txt


# -------------------
# Canlib class
# -------------------

class canlib(object):

    def __init__(self, debug=None):
        fmt = '[%(levelname)s] %(funcName)s: %(message)s'
        if debug:
            logging.basicConfig(stream=sys.stderr,
                                level=logging.DEBUG,
                                format=fmt)
        else:
            logging.basicConfig(stream=sys.stderr,
                                level=logging.ERROR,
                                format=fmt)

        if sys.platform.startswith('win'):
            self.dll = ct.WinDLL('canlib32')
            self.dll.canInitializeLibrary()
        else:
            self.dll = ct.CDLL('libcanlib.so')

        # protptypes
        self.dll.canGetVersion.argtypes = []
        self.dll.canGetVersion.restype = ct.c_short
        self.dll.canGetVersion.errcheck = self._canErrorCheck

        self.dll.canGetNumberOfChannels.argtypes = [ct.POINTER(ct.c_int)]
        self.dll.canGetNumberOfChannels.errcheck = self._canErrorCheck

        self.dll.canGetChannelData.argtypes = [ct.c_int, ct.c_int,
                                               ct.c_void_p, ct.c_size_t]
        self.dll.canGetChannelData.errcheck = self._canErrorCheck

        self.dll.canOpenChannel.argtypes = [ct.c_int, ct.c_int]
        self.dll.canOpenChannel.errcheck = self._canErrorCheck

        self.dll.canClose.argtypes = [ct.c_int]
        self.dll.canClose.errcheck = self._canErrorCheck

        self.dll.canSetBusParams.argtypes = [ct.c_int, ct.c_long, ct.c_uint,
                                             ct.c_uint, ct.c_uint, ct.c_uint,
                                             ct.c_uint]
        self.dll.canSetBusParams.errcheck = self._canErrorCheck

        self.dll.canGetBusParams.argtypes = [ct.c_int, ct.POINTER(ct.c_long),
                                             ct.POINTER(ct.c_uint),
                                             ct.POINTER(ct.c_uint),
                                             ct.POINTER(ct.c_uint),
                                             ct.POINTER(ct.c_uint),
                                             ct.POINTER(ct.c_uint)]
        self.dll.canGetBusParams.errcheck = self._canErrorCheck

        self.dll.canSetBusParamsFd.argtypes = [ct.c_int, ct.c_long, ct.c_uint,
                                               ct.c_uint, ct.c_uint]
        self.dll.canSetBusParamsFd.errcheck = self._canErrorCheck

        self.dll.canGetBusParamsFd.argtypes = [ct.c_int, ct.POINTER(ct.c_long),
                                               ct.POINTER(ct.c_uint),
                                               ct.POINTER(ct.c_uint),
                                               ct.POINTER(ct.c_uint)]
        self.dll.canGetBusParamsFd.errcheck = self._canErrorCheck

        self.dll.canBusOn.argtypes = [ct.c_int]
        self.dll.canBusOn.errcheck = self._canErrorCheck

        self.dll.canBusOff.argtypes = [ct.c_int]
        self.dll.canBusOff.errcheck = self._canErrorCheck

        self.dll.canTranslateBaud.atgtypes = [ct.POINTER(ct.c_long),
                                              ct.POINTER(ct.c_uint),
                                              ct.POINTER(ct.c_uint),
                                              ct.POINTER(ct.c_uint),
                                              ct.POINTER(ct.c_uint),
                                              ct.POINTER(ct.c_uint)]
        self.dll.canTranslateBaud.errcheck = self._canErrorCheck

        self.dll.canWrite.argtypes = [ct.c_int, ct.c_long, ct.c_void_p,
                                      ct.c_uint, ct.c_uint]
        self.dll.canWrite.errcheck = self._canErrorCheck

        self.dll.canWriteWait.argtypes = [ct.c_int, ct.c_long,
                                          ct.c_void_p, ct.c_uint,
                                          ct.c_uint, ct.c_ulong]
        self.dll.canWriteWait.errcheck = self._canErrorCheck

        self.dll.canReadWait.argtypes = [ct.c_int, ct.POINTER(ct.c_long),
                                         ct.c_void_p,
                                         ct.POINTER(ct.c_uint),
                                         ct.POINTER(ct.c_uint),
                                         ct.POINTER(ct.c_ulong), ct.c_ulong]
        self.dll.canReadWait.errcheck = self._canErrorCheck

        try:
            self.dll.canReadSpecificSkip.argtypes = [ct.c_int, ct.c_long,
                                                     ct.c_void_p,
                                                     ct.POINTER(ct.c_uint),
                                                     ct.POINTER(ct.c_uint),
                                                     ct.POINTER(ct.c_ulong)]
            self.dll.canReadSpecificSkip.errcheck = self._canErrorCheck
        except Exception as e:
            logging.debug(str(e) + ' (Not implemented in Linux)')

        try:
            self.dll.canReadSyncSpecific.argtypes = [ct.c_int, ct.c_long,
                                                     ct.c_ulong]
            self.dll.canReadSyncSpecific.errcheck = self._canErrorCheck
        except Exception as e:
            logging.debug(str(e) + ' (Not implemented in Linux)')

        self.dll.canSetBusOutputControl.argtypes = [ct.c_int, ct.c_ulong]
        self.dll.canSetBusOutputControl.errcheck = self._canErrorCheck

        self.dll.canIoCtl.argtypes = [ct.c_int, ct.c_uint, ct.c_void_p,
                                      ct.c_uint]
        self.dll.canIoCtl.errcheck = self._canErrorCheck

        try:
            self.dll.kvReadDeviceCustomerData.argtypes = [ct.c_int, ct.c_int,
                                                          ct.c_int,
                                                          ct.c_void_p,
                                                          ct.c_size_t]
            self.dll.kvReadDeviceCustomerData.errcheck = self._canErrorCheck

            self.dll.kvFileGetCount.argtypes = [ct.c_int, ct.POINTER(ct.c_int)]
            self.dll.kvFileGetCount.errcheck = self._canErrorCheck

            self.dll.kvFileGetName.argtypes = [ct.c_int, ct.c_int, ct.c_char_p,
                                               ct.c_int]
            self.dll.kvFileGetName.errcheck = self._canErrorCheck

            self.dll.kvFileCopyFromDevice.argtypes = [ct.c_int, ct.c_char_p,
                                                      ct.c_char_p]
            self.dll.kvFileCopyFromDevice.errcheck = self._canErrorCheck

            self.dll.kvScriptSendEvent.argtypes = [ct.c_int, ct.c_int,
                                                   ct.c_int, ct.c_int,
                                                   ct.c_uint]
            self.dll.kvScriptSendEvent.errcheck = self._canErrorCheck

            self.dll.kvScriptStart.argtypes = [ct.c_int, ct.c_int]
            self.dll.kvScriptStart.errcheck = self._canErrorCheck

            self.dll.kvScriptStop.argtypes = [ct.c_int, ct.c_int, ct.c_int]
            self.dll.kvScriptStop.errcheck = self._canErrorCheck

            self.dll.kvScriptUnload.argtypes = [ct.c_int, ct.c_int]
            self.dll.kvScriptUnload.errcheck = self._canErrorCheck

            self.dll.kvScriptEnvvarOpen.argtypes = [ct.c_int, ct.c_char_p,
                                                    ct.POINTER(ct.c_int),
                                                    ct.POINTER(ct.c_int)]
            self.dll.kvScriptEnvvarOpen.restype = ct.c_int64
            self.dll.kvScriptEnvvarOpen.errcheck = self._canErrorCheck

            self.dll.kvScriptEnvvarClose.argtypes = [ct.c_int64]
            self.dll.kvScriptEnvvarClose.errcheck = self._canErrorCheck

            self.dll.kvScriptEnvvarSetInt.argtypes = [ct.c_int64, ct.c_int]
            self.dll.kvScriptEnvvarSetInt.errcheck = self._canErrorCheck

            self.dll.kvScriptEnvvarGetInt.argtypes = [ct.c_int64,
                                                      ct.POINTER(ct.c_int)]
            self.dll.kvScriptEnvvarGetInt.errcheck = self._canErrorCheck

            self.dll.kvScriptEnvvarSetFloat.argtypes = [ct.c_int64, ct.c_float]
            self.dll.kvScriptEnvvarSetFloat.errcheck = self._canErrorCheck

            self.dll.kvScriptEnvvarGetFloat.argtypes = [ct.c_int64,
                                                        ct.POINTER(ct.c_float)]
            self.dll.kvScriptEnvvarGetFloat.errcheck = self._canErrorCheck

            self.dll.kvScriptEnvvarSetData.argtypes = [ct.c_int64, ct.c_void_p,
                                                       ct.c_int, ct.c_int]
            self.dll.kvScriptEnvvarSetData.errcheck = self._canErrorCheck
            self.dll.kvScriptEnvvarGetData.argtypes = [ct.c_int64, ct.c_void_p,
                                                       ct.c_int, ct.c_int]
            self.dll.kvScriptEnvvarGetData.errcheck = self._canErrorCheck

            self.dll.kvScriptLoadFileOnDevice.argtypes = [ct.c_int, ct.c_int,
                                                          ct.c_char_p]
            self.dll.kvScriptLoadFileOnDevice.errcheck = self._canErrorCheck

            self.dll.kvScriptLoadFile.argtypes = [ct.c_int, ct.c_int,
                                                  ct.c_char_p]
            self.dll.kvScriptLoadFile.errcheck = self._canErrorCheck

            self.dll.kvDeviceSetMode.argtypes = [ct.c_int, ct.c_int]
            self.dll.kvDeviceSetMode.errcheck = self._canErrorCheck

            self.dll.kvDeviceGetMode.argtypes = [ct.c_int,
                                                 ct.POINTER(ct.c_int)]
            self.dll.kvDeviceGetMode.errcheck = self._canErrorCheck

        except Exception as e:
            logging.debug(str(e) + ' (Not implemented in Linux)')

    def __del__(self):
        self.dll.canUnloadLibrary()

    def _canErrorCheck(self, result, func, arguments):
        if result == canERR_NOMSG:
            raise canNoMsg(self, result)
        elif result == canERR_SCRIPT_FAIL:
            raise canScriptFail(self, result)
        elif result < 0:
            raise canError(self, result)
        return result

    def getVersion(self):
        self.fn = inspect.currentframe().f_code.co_name
        v = self.dll.canGetVersion()
        version = canVersion(v & 0xff, v >> 8)
        return version

    def getNumberOfChannels(self):
        self.fn = inspect.currentframe().f_code.co_name
        chanCount = ct.c_int()
        self.dll.canGetNumberOfChannels(chanCount)
        return chanCount.value

    def getChannelData_Name(self, channel):
        self.fn = inspect.currentframe().f_code.co_name
        name = ct.create_string_buffer(80)
        self.dll.canGetChannelData(channel,
                                   canCHANNELDATA_DEVDESCR_ASCII,
                                   ct.byref(name), ct.sizeof(name))
        buf_type = ct.c_uint * 1
        buf = buf_type()
        self.dll.canGetChannelData(channel,
                                   canCHANNELDATA_CHAN_NO_ON_CARD,
                                   ct.byref(buf), ct.sizeof(buf))
        return "%s (channel %d)" % (name.value, buf[0])

    def getChannelData_CardNumber(self, channel):
        self.fn = inspect.currentframe().f_code.co_name
        buf_type = ct.c_ulong
        buf = buf_type()
        self.dll.canGetChannelData(channel,
                                   canCHANNELDATA_CARD_NUMBER,
                                   ct.byref(buf), ct.sizeof(buf))
        return buf.value

    def getChannelData_EAN(self, channel):
        self.fn = inspect.currentframe().f_code.co_name
        buf_type = ct.c_ulong * 2
        buf = buf_type()
        self.dll.canGetChannelData(channel,
                                   canCHANNELDATA_CARD_UPC_NO,
                                   ct.byref(buf), ct.sizeof(buf))
        (ean_lo, ean_hi) = struct.unpack('LL', buf)

        return "%02x-%05x-%05x-%x" % (ean_hi >> 12,
                                      ((ean_hi & 0xfff) << 8) | (ean_lo >> 24),
                                      (ean_lo >> 4) & 0xfffff, ean_lo & 0xf)

    def getChannelData_EAN_short(self, channel):
        self.fn = inspect.currentframe().f_code.co_name
        buf_type = ct.c_ulong * 2
        buf = buf_type()
        self.dll.canGetChannelData(channel,
                                   canCHANNELDATA_CARD_UPC_NO,
                                   ct.byref(buf), ct.sizeof(buf))
        (ean_lo, ean_hi) = struct.unpack('LL', buf)
        return "%04x-%x" % ((ean_lo >> 4) & 0xffff, ean_lo & 0xf)

    def getChannelData_Serial(self, channel):
        self.fn = inspect.currentframe().f_code.co_name
        buf_type = ct.c_ulong * 2
        buf = buf_type()
        self.dll.canGetChannelData(channel,
                                   canCHANNELDATA_CARD_SERIAL_NO,
                                   ct.byref(buf), ct.sizeof(buf))
        (serial_lo, serial_hi) = struct.unpack('LL', buf)
        # serial_hi is always 0
        return serial_lo

    def getChannelData_DriverName(self, channel):
        self.fn = inspect.currentframe().f_code.co_name
        name = ct.create_string_buffer(80)
        self.dll.canGetChannelData(channel,
                                   canCHANNELDATA_DRIVER_NAME,
                                   ct.byref(name), ct.sizeof(name))
        return name.value

    def getChannelData_Firmware(self, channel):
        self.fn = inspect.currentframe().f_code.co_name
        buf_type = ct.c_ushort * 4
        buf = buf_type()
        self.dll.canGetChannelData(channel,
                                   canCHANNELDATA_CARD_FIRMWARE_REV,
                                   ct.byref(buf), ct.sizeof(buf))
        (build, release, minor, major) = struct.unpack('HHHH', buf)
        return (major, minor, build)

    def openChannel(self, channel, flags=0):
        self.fn = inspect.currentframe().f_code.co_name
        return canChannel(self, channel, flags)

    def translateBaud(self, freq=1000000, tseg1=4, tseg2=3, sjw=1, nosamp=1,
                      syncMode=0):
        self.fn = inspect.currentframe().f_code.co_name
        freq_p = ct.c_long(freq)
        tseg1_p = ct.c_int(tseg1)
        tseg2_p = ct.c_int(tseg2)
        sjw_p = ct.c_int(sjw)
        nosamp_p = ct.c_int(nosamp)
        syncMode_p = ct.c_int(syncMode)
        self.dll.canTranslateBaud(ct.byref(freq_p),
                                  ct.byref(tseg1_p),
                                  ct.byref(tseg2_p),
                                  ct.byref(sjw_p),
                                  ct.byref(nosamp_p),
                                  ct.byref(syncMode_p))
        rateSetting = bitrateSetting(freq=freq_p.value, tseg1=tseg1_p.value,
                                     tseg2=tseg2_p.value, sjw=sjw_p.value,
                                     nosamp=nosamp_p.value,
                                     syncMode=syncMode_p.value)
        return rateSetting

    def unloadLibrary(self):
        self.dll.canUnloadLibrary()

    def reinitializeLibrary(self):
        self.unloadLibrary()
        self.dll.canInitializeLibrary()


class canChannel(object):

    def __init__(self, canlib, channel, flags=0):
        self.canlib = canlib
        self.dll = canlib.dll
        self.index = channel
        self.canlib.fn = 'openChannel'
        self.handle = self.dll.canOpenChannel(channel, flags)
        self.envvar = envvar(self)

    def close(self):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        self.dll.canClose(self.handle)
        self.handle = -1

    def setBusParams(self, freq, tseg1=0, tseg2=0, sjw=0, noSamp=0,
                     syncmode=0):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        self.dll.canSetBusParams(self.handle, freq, tseg1, tseg2, sjw,
                                 noSamp, syncmode)

    def getBusParams(self):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        freq = ct.c_long()
        tseg1 = ct.c_uint()
        tseg2 = ct.c_uint()
        sjw = ct.c_uint()
        noSamp = ct.c_uint()
        syncmode = ct.c_uint()
        self.dll.canGetBusParams(self.handle, ct.byref(freq), ct.byref(tseg1),
                                 ct.byref(tseg2), ct.byref(sjw),
                                 ct.byref(noSamp), ct.byref(syncmode))
        return (freq.value, tseg1.value, tseg2.value, sjw.value, noSamp.value,
                syncmode.value)

    def busOn(self):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        self.dll.canBusOn(self.handle)

    def busOff(self):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        self.dll.canBusOff(self.handle)

    # The variable name id (as used by canlib) is a built-in function in
    # Python, so we use the name id_ instead
    def write(self, id_, msg, flag=0):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        if not isinstance(msg, (bytes, str)):
            if not isinstance(msg, bytearray):
                msg = bytearray(msg)
            msg = bytes(msg)

        self.dll.canWrite(self.handle, id_, msg, len(msg), flag)

    def writeWait(self, id_, msg, flag=0, timeout=0):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        if not isinstance(msg, (bytes, str)):
            if not isinstance(msg, bytearray):
                msg = bytearray(msg)
            msg = bytes(msg)

        self.dll.canWriteWait(self.handle, id_, msg, len(msg), flag, timeout)

    def read(self, timeout=0):
        """Read a CAN message and metadata.

        Reads a message from the receive buffer. If no message is available,
        the function waits until a message arrives or a timeout occurs.

        Args:
            timeout (int): Timeout in milliseconds, -1 gives an infinite
                           timeout.

        Returns:
            id_ (int):    CAN identifier
            msg (bytes):  CAN data - max length 8
            dlc (int):    Data Length Code
            flag (int):   Flags, a combination of the canMSG_xxx and
                          canMSGERR_xxx values
            time (float): Timestamp from hardware
        """
        self.canlib.fn = inspect.currentframe().f_code.co_name
        # msg will be replaced by class when CAN FD is supported
        _MAX_SIZE = 8
        msg = ct.create_string_buffer(_MAX_SIZE)
        id_ = ct.c_long()
        dlc = ct.c_uint()
        flag = ct.c_uint()
        time = ct.c_ulong()
        self.dll.canReadWait(self.handle, id_, msg, dlc, flag, time, timeout)
        length = min(_MAX_SIZE, dlc.value)
        return(id_.value, bytearray(msg.raw[:length]), dlc.value, flag.value,
               time.value)

    def readDeviceCustomerData(self, userNumber=100, itemNumber=0):
        self.fn = inspect.currentframe().f_code.co_name
        buf = ct.create_string_buffer(8)
        user = ct.c_int(userNumber)
        item = ct.c_int(itemNumber)
        self.dll.kvReadDeviceCustomerData(self.handle, user, item, buf,
                                          ct.sizeof(buf))
        return struct.unpack('!Q', buf)[0]

    def readSpecificSkip(self, id_):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        # msg will be replaced by class when CAN FD is supported
        _MAX_SIZE = 8
        msg = ct.create_string_buffer(_MAX_SIZE)
        id_ = ct.c_long(id_)
        dlc = ct.c_uint()
        flag = ct.c_uint()
        time = ct.c_ulong()
        self.dll.canReadSpecificSkip(self.handle, id_, msg, dlc, flag, time)
        length = min(_MAX_SIZE, dlc.value)
        return(id_.value, bytearray(msg.raw[:length]), dlc.value, flag.value,
               time.value)

    def readSyncSpecific(self, id_, timeout=0):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        id_ = ct.c_long(id_)
        self.dll.canReadSyncSpecific(self.handle, id_, timeout)

    def scriptSendEvent(self, slotNo=0, eventType=kvEVENT_TYPE_KEY,
                        eventNo=ord('a'), data=0):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        self.dll.kvScriptSendEvent(self.handle, ct.c_int(slotNo),
                                   ct.c_int(eventType), ct.c_int(eventNo),
                                   ct.c_uint(data))

    def setBusOutputControl(self, drivertype=canDRIVER_NORMAL):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        self.dll.canSetBusOutputControl(self.handle, drivertype)

    def ioCtl_flush_rx_buffer(self):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        self.dll.canIoCtl(self.handle, canIOCTL_FLUSH_RX_BUFFER, None, 0)

    def ioCtl_set_timer_scale(self, scale):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        scale = ct.c_long(scale)
        self.dll.canIoCtl(self.handle, canIOCTL_SET_TIMER_SCALE,
                          ct.byref(scale), ct.sizeof(scale))

    def getChannelData_Name(self):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        return self.canlib.getChannelData_Name(self.index)

    def getChannelData_CardNumber(self):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        return self.canlib.getChannelData_CardNumber(self.index)

    def getChannelData_EAN(self):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        return self.canlib.getChannelData_EAN(self.index)

    def getChannelData_EAN_short(self):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        return self.canlib.getChannelData_EAN_short(self.index)

    def getChannelData_Serial(self):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        return self.canlib.getChannelData_Serial(self.index)

    def getChannelData_DriverName(self):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        return self.canlib.getChannelData_DriverName(self.index)

    def getChannelData_Firmware(self):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        return self.canlib.getChannelData_Firmware(self.index)

    def scriptStart(self, slot):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        self.dll.kvScriptStart(self.handle, slot)

    def scriptStop(self, slot, mode=kvSCRIPT_STOP_NORMAL):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        self.dll.kvScriptStop(self.handle, slot, mode)

    def scriptUnload(self, slot):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        self.dll.kvScriptUnload(self.handle, slot)

    def scriptLoadFileOnDevice(self, slot, localFile):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        self.dll.kvScriptLoadFileOnDevice(self.handle, slot,
                                          ct.c_char_p(localFile))

    def scriptLoadFile(self, slot, filePathOnPC):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        self.dll.kvScriptLoadFile(self.handle, slot, ct.c_char_p(filePathOnPC))

    def scriptEnvvarOpen(self, name):
        envvarType = ct.c_int()
        envvarSize = ct.c_int()
        envHandle = self.dll.kvScriptEnvvarOpen(self.handle, ct.c_char_p(name),
                                                ct.byref(envvarType),
                                                ct.byref(envvarSize))
        return envHandle, envvarType.value, envvarSize.value

    def scriptEnvvarClose(self, envHandle):
        self.dll.kvScriptEnvvarClose(ct.c_int64(envHandle))

    def scriptEnvvarSetInt(self, envHandle, value):
        value = int(value)
        self.dll.kvScriptEnvvarSetInt(ct.c_int64(envHandle), ct.c_int(value))

    def scriptEnvvarGetInt(self, envHandle):
        envvarValue = ct.c_int()
        self.dll.kvScriptEnvvarGetInt(ct.c_int64(envHandle),
                                      ct.byref(envvarValue))
        return envvarValue.value

    def scriptEnvvarSetFloat(self, envHandle, value):
        value = float(value)
        self.dll.kvScriptEnvvarSetFloat(ct.c_int64(envHandle),
                                        ct.c_float(value))

    def scriptEnvvarGetFloat(self, envHandle):
        envvarValue = ct.c_float()
        self.dll.kvScriptEnvvarGetFloat(ct.c_int64(envHandle),
                                        ct.byref(envvarValue))
        return envvarValue.value

    def scriptEnvvarSetData(self, envHandle, value, envSize):
        self.dll.kvScriptEnvvarSetData(ct.c_int64(envHandle),
                                       ct.c_char_p(value), 0,
                                       ct.c_int(envSize))

    def scriptEnvvarGetData(self, envHandle, envSize):
        envvarValue = ct.create_string_buffer(envSize)
        self.dll.kvScriptEnvvarGetData(ct.c_int64(envHandle),
                                       ct.byref(envvarValue), 0,
                                       ct.c_int(envSize))
        return envvarValue.value

    def fileGetCount(self):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        count = ct.c_int()
        self.dll.kvFileGetCount(self.handle, ct.byref(count))
        return count.value

    def fileGetName(self, fileNo):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        fileName = ct.create_string_buffer(50)
        self.dll.kvFileGetName(self.handle, ct.c_int(fileNo), fileName,
                               ct.sizeof(fileName))
        return fileName.value

    def fileCopyFromDevice(self, deviceFileName, hostFileName):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        self.dll.kvFileCopyFromDevice(self.handle, deviceFileName,
                                      hostFileName)

    def kvDeviceSetMode(self, mode):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        self.dll.kvDeviceSetMode(self.handle, ct.c_int(mode))

    def kvDeviceGetMode(self):
        self.canlib.fn = inspect.currentframe().f_code.co_name
        mode = ct.c_int()
        self.dll.kvDeviceGetMode(self.handle, ct.byref(mode))
        return mode.value


class envvar(object):
    class Attrib(object):
        def __init__(self, handle=None, type_=None, size=None):
            self.handle = handle
            self.type_ = type_
            self.size = size

    def __init__(self, channel):
        self.__dict__['_channel'] = channel
        self.__dict__['_attrib'] = {}

    def _ensure_open(self, name):
        assert not name.startswith('_'), ("envvar names must not start"
                                          " with an underscore: %s" % name)
        # We just check the handle here
        if name not in self.__dict__['_attrib']:
            self._attrib[name] = envvar.Attrib(*self._channel.scriptEnvvarOpen(name))

    def __getattr__(self, name):
        self._ensure_open(name)
        handle = self._attrib[name].handle
        if self._attrib[name].type_ == kvENVVAR_TYPE_INT:
            value = self._channel.scriptEnvvarGetInt(handle)
        elif self._attrib[name].type_ == kvENVVAR_TYPE_FLOAT:
            value = self._channel.scriptEnvvarGetFloat(handle)
        elif self._attrib[name].type_ == kvENVVAR_TYPE_STRING:
            size = self._attrib[name].size
            value = self._channel.scriptEnvvarGetData(handle, size)
        else:
            msg = "getting is not implemented for type {type_}"
            msg = msg.format(type_=self._attrib[name].type_)
            raise TypeError(msg)
        return value

    def __setattr__(self, name, value):
        self._ensure_open(name)
        handle = self._attrib[name].handle
        if self._attrib[name].type_ == kvENVVAR_TYPE_INT:
            value = self._channel.scriptEnvvarSetInt(handle, value)
        elif self._attrib[name].type_ == kvENVVAR_TYPE_FLOAT:
            value = self._channel.scriptEnvvarSetFloat(handle, value)
        elif self._attrib[name].type_ == kvENVVAR_TYPE_STRING:
            value = str(value)
            size = self._attrib[name].size
            value = self._channel.scriptEnvvarSetData(handle, value, size)
        else:
            msg = "setting is not implemented for type {type_}"
            msg = msg.format(type_=self._attrib[name].type_)
            raise TypeError(msg)


if __name__ == '__main__':
    cl = canlib()
    channels = cl.getNumberOfChannels()

    print("canlib version: %s" % cl.getVersion())

    if len(sys.argv) != 2:
        print("Please enter channel, example: %s 3\n" % sys.argv[0])
        for ch in range(0, channels):
            try:
                print("%d. %s (%s / %s)" % (ch, cl.getChannelData_Name(ch),
                                            cl.getChannelData_EAN(ch),
                                            cl.getChannelData_Serial(ch)))
            except (canError) as ex:
                print(ex)
        sys.exit()

    ch = int(sys.argv[1])
    if ch >= channels:
        print("Invalid channel number")
        sys.exit()

    try:
        ch1 = cl.openChannel(ch, canOPEN_ACCEPT_VIRTUAL)
        print("Using channel: %s, EAN: %s" % (ch1.getChannelData_Name(),
                                              ch1.getChannelData_EAN()))

        ch1.setBusOutputControl(canDRIVER_NORMAL)
        ch1.setBusParams(canBITRATE_1M)
        ch1.busOn()
    except (canError) as ex:
        print(ex)

    while True:
        try:
            msgId, msg, dlc, flg, time = ch1.read()
            print("%9d  %9d  0x%02x  %d  %s" % (msgId, time, flg, dlc, msg))
            for i in range(dlc):
                msg[i] = (msg[i]+1) % 256
            ch1.write(msgId, msg, flg)
        except (canNoMsg) as ex:
            None
        except (canError) as ex:
            print(ex)

    ch1.busOff()
    ch1.close()

from ctypes import *
from xml.dom import minidom
import _winreg
import platform
import sys
import struct
import logging
import inspect
import os
import re

#------------------------------------------------------------------#
# kvrlib constants                                                 #
#------------------------------------------------------------------#

kvrOK                                   =  0
kvrERR_NOT_INITIALIZED                  = -1
kvrERR_GENERIC                          = -2
kvrERR_CHECKSUM                         = -3
kvrERR_PARAMETER                        = -4
kvrERR_PASSWORD                         = -5
kvrERR_BLANK                            = -6
kvrERR_NO_DEVICE                        = -7
kvrERR_NO_ANSWER                        = -8
kvrERR_NOT_IMPLEMENTED                  = -9
kvrERR_PERMISSION_DENIED                = -10
kvrERR_OUT_OF_SPACE                     = -11
kvrERR_NO_SERVICE                       = -12
kvrERR_DUPLICATED_DEVICE                = -13

kvrNetworkState_UNKNOWN                 = 0
kvrNetworkState_INVALID                 = 1
kvrNetworkState_STARTUP                 = 2
kvrNetworkState_INITIALIZING            = 3
kvrNetworkState_NOT_CONNECTED           = 4
kvrNetworkState_CONNECTION_DELAY        = 5
kvrNetworkState_CONNECTING              = 6
kvrNetworkState_CONNECTED               = 7
kvrNetworkState_AUTHENTICATING          = 8
kvrNetworkState_AUTHENTICATION_FAILED   = 9
kvrNetworkState_ONLINE                  = 10
kvrNetworkState_FAILED_MIC              = 11

kvrBss_INFRASTRUCTURE                   = 0
kvrBss_INDEPENDENT                      = 1
kvrBss_ANY                              = 2

kvrRegulatoryDomain_JAPAN_TELEC         = 0
kvrRegulatoryDomain_EUROPE_ETSI         = 1
kvrRegulatoryDomain_NORTH_AMERICA_FCC   = 2
kvrRegulatoryDomain_WORLD               = 3
kvrRegulatoryDomain_CHINA_MII           = 4

kvrRemoteState_VOID                     = 0
kvrRemoteState_AVAILABLE                = 1
kvrRemoteState_DISCOVERED               = 2
kvrRemoteState_STARTING                 = 3
kvrRemoteState_STARTED                  = 4
kvrRemoteState_CONNECTION_DOWN          = 5
kvrRemoteState_CONNECTION_UP            = 6
kvrRemoteState_REDISCOVER               = 7
kvrRemoteState_UNWILLING                = 8
kvrRemoteState_REDISCOVER_PENDING       = 9
kvrRemoteState_CLOSING                  = 10
kvrRemoteState_REMOVE_ME                = 11
kvrRemoteState_STANDBY                  = 12
kvrRemoteState_CONFIG_CHANGED           = 13
kvrRemoteState_STOPPING                 = 14
kvrRemoteState_INSTALLING               = 15

kvrAddressTypeFlag_ALL                  = 0xff
kvrAddressTypeFlag_BROADCAST            = 0x01
kvrAddressTypeFlag_STORED               = 0x02

kvrServiceState_VOID                    = 0
kvrServiceState_AVAILABLE               = 1
kvrServiceState_DISCOVERED              = 2

kvrServiceState_STARTING                = 3
kvrServiceState_STARTED                 = 4
kvrServiceState_CONNECTION_DOWN         = 5
kvrServiceState_CONNECTION_UP           = 6
kvrServiceState_REDISCOVER              = 7
kvrServiceState_UNWILLING               = 8
kvrServiceState_REDISCOVER_PENDING      = 9
kvrServiceState_CLOSING                 = 10
kvrServiceState_REMOVE_ME               = 11
kvrServiceState_STANDBY                 = 12
kvrServiceState_CONFIG_CHANGED          = 13
kvrServiceState_STOPPING                = 14
kvrServiceState_INSTALLING              = 15

kvrStartInfo_NONE                       = 0
kvrStartInfo_START_OK                   = 1
kvrStartInfo_ERR_IN_USE                 = 2
kvrStartInfo_ERR_PWD                    = 3
kvrStartInfo_ERR_NOTME                  = 4
kvrStartInfo_ERR_CONFIGURING            = 5
kvrStartInfo_ERR_PARAM                  = 6
kvrStartInfo_ERR_ENCRYPTION_PWD         = 7



class kvrError(Exception):
    def __init__(self, kvrlib, kvrERR):
        self.kvrlib = kvrlib
        self.kvrERR = kvrERR

    def __kvrGetErrorText(self):
        msg = create_string_buffer(80)
        self.kvrlib.dll.kvrGetErrorText(self.kvrERR, msg, sizeof(msg))
        return msg.value

    def __str__(self):
        return "[kvrError] %s: %s (%d)" % (self.kvrlib.fn, self.__kvrGetErrorText(), self.kvrERR)


class kvrBlank(Exception):
    def __init__(self, kvrlib, kvrERR):
        self.kvrlib = kvrlib
        self.kvrERR = kvrERR

    def __str__(self):
        return "List was not set or no more results."


class kvrVersion(Structure):
    _fields_ = [
        ("minor", c_uint8),
        ("major", c_uint8),
        ]

    def __str__(self):
        return "%d.%d" % (self.major, self.minor)


class kvrConfig(object):
    MODE_R     = 0
    MODE_RW    = 1
    MODE_ERASE = 2

    def __init__(self, kvrlib, channel=0, mode=MODE_R, password=""):
        self.kvrlib = kvrlib
        self.channel = channel
        self.mode = mode
        self.password = password
        self._open()

    def _open(self):
        self.handle = self.kvrlib._configOpen(self.channel, self.mode, self.password)

    def openEx(channel=0, mode=MODE_R, password="", profile_no=0):
        if handle != None:
            self.close()
        self.channel = channel
        self.mode = mode
        self.password = password
        self.handle = self.kvrlib._configOpenEx(self.channel, self.mode,
                                                self.password, profile_no)

    def close(self):
        self.kvrlib.configClose(self.handle)
        self.handle = None

    def getXml(self):
        if self.handle == None:
            self._open()
        self.xml = minidom.parseString(self.kvrlib.configGet(self.handle))
        return self.xml

    def setXml(self):
        if self.handle == None:
            print "AutoOpen"
            self._open()
        self.kvrlib.configSet(self.handle, self.xml.toxml())

    def clear(self):
        self.kvrlib.configClear(self.handle)

#----------------------------------------------------------------------#
# Kvrlib class                                                         #
#----------------------------------------------------------------------#

class kvrlib(object):

    # ean:    73-30130-00671-3
    # ean_hi: 73301
    # ean_lo: 30006713

    @staticmethod
    def ean2ean_hi(ean):
        eanCompact = re.sub('-','',ean)
        match = re.match('(\d{5})(\d{8})',eanCompact)
        return int('0x%s' % match.group(1), 0)

    @staticmethod
    def ean2ean_lo(ean):
        eanCompact = re.sub('-','',ean)
        match = re.match('(\d{5})(\d{8})',eanCompact)
        return int('0x%s' % match.group(2), 0)

    @staticmethod
    def ean_hi_lo2ean(ean_hi, ean_lo):
        return "%02x-%05x-%05x-%x" % (ean_hi >> 12,
                                      ((ean_hi & 0xfff) << 8) | (ean_lo >> 24),
                                      (ean_lo >> 4) & 0xfffff, ean_lo & 0xf)


    kvrMessage = 8 * c_uint8

    aReg = _winreg.ConnectRegistry(None,_winreg.HKEY_LOCAL_MACHINE)
    aKey = _winreg.OpenKey(aReg, r"SOFTWARE\KVASER AB\CANLIB32")
    try:
        installDir= os.path.realpath(_winreg.QueryValueEx(aKey, "InstallDir")[0])
        # print installDir
    except Exception as er:
        print er
        exit(1)

    if (platform.architecture()[0] == '32bit'):
        path_32 = os.path.join(installDir, '32')
        if os.path.isdir(path_32):
            installDir = path_32

    libxml2dll = WinDLL(os.path.join(installDir, 'libxml2.dll'))
    irisflashdll = WinDLL(os.path.join(installDir, 'irisflash.dll'))
    irisdll = WinDLL(os.path.join(installDir, 'irisdll.dll'))
    kvrlibDll = WinDLL(os.path.join(installDir, 'kvrlib.dll'))

    def __init__(self, debug=None):
        # Don't know how to find these, see FB#13278
        self.dll = kvrlib.kvrlibDll
        # self.dll = WinDLL('kvrlib')
        self.dll.kvrInitializeLibrary()

        fmt = '[%(levelname)s] %(funcName)s: %(message)s'
        if debug:
            logging.basicConfig(stream=sys.stderr,
                                level=logging.DEBUG,
                                format=fmt)
        else:
            logging.basicConfig(stream=sys.stderr,
                                level=logging.ERROR,
                                format=fmt)

        self.dll.kvrGetVersion.argtypes = []
        self.dll.kvrGetVersion.restype = kvrVersion

        self.dll.kvrAddressFromString.argtypes = [c_int32,
                                                  POINTER(kvrAddress),
                                                  c_char_p]
        self.dll.kvrAddressFromString.errcheck = self._kvrErrorCheck

        self.dll.kvrStringFromAddress.argtypes = [c_char_p, c_uint32, POINTER(kvrAddress)]
        self.dll.kvrStringFromAddress.errcheck = self._kvrErrorCheck

        self.dll.kvrDeviceGetServiceStatus.argtypes = [POINTER(kvrDeviceInfo),
                                                       POINTER(c_int32),
                                                       POINTER(c_int32)]
        self.dll.kvrDeviceGetServiceStatus.errcheck = self._kvrErrorCheck

        self.dll.kvrDeviceGetServiceStatusText.argtypes = [POINTER(kvrDeviceInfo), c_char_p, c_uint32]
        self.dll.kvrDeviceGetServiceStatusText.errcheck = self._kvrErrorCheck

        self.dll.kvrDiscoveryClearDevicesAtExit.argtypes = [c_uint]
        self.dll.kvrDiscoveryClearDevicesAtExit.errcheck = self._kvrErrorCheck

        self.dll.kvrDiscoveryClose.argtypes = [c_int32]
        self.dll.kvrDiscoveryClose.errcheck = self._kvrErrorCheck

        self.dll.kvrDiscoveryOpen.argtypes = [POINTER(c_int32)]
        self.dll.kvrDiscoveryOpen.errcheck = self._kvrErrorCheck

        self.dll.kvrDiscoveryGetDefaultAddresses.argtypes = [POINTER(kvrAddress),
                                                             c_uint32,
                                                             POINTER(c_uint32),
                                                             c_uint32]
        self.dll.kvrDiscoveryGetDefaultAddresses.errcheck = self._kvrErrorCheck

        self.dll.kvrDiscoveryGetResults.argtypes = [c_int32, POINTER(kvrDeviceInfo)]
        self.dll.kvrDiscoveryGetResults.errcheck = self._kvrErrorCheck

        self.dll.kvrDiscoverySetAddresses.argtypes = [c_int32,
                                                      POINTER(kvrAddress),
                                                      c_uint32]
        self.dll.kvrDiscoverySetAddresses.errcheck = self._kvrErrorCheck

        self.dll.kvrDiscoverySetEncryptionKey.argtypes = [POINTER(kvrDeviceInfo), c_char_p]
        self.dll.kvrDiscoverySetEncryptionKey.errcheck = self._kvrErrorCheck

        self.dll.kvrDiscoverySetPassword.argtypes = [POINTER(kvrDeviceInfo), c_char_p]
        self.dll.kvrDiscoverySetPassword.errcheck = self._kvrErrorCheck

        self.dll.kvrDiscoveryStart.argtypes = [c_int32, c_uint32, c_uint32]
        self.dll.kvrDiscoveryStart.errcheck = self._kvrErrorCheck

        self.dll.kvrDiscoveryStoreDevices.argtypes = [POINTER(kvrDeviceInfo), c_uint32]
        self.dll.kvrDiscoveryStoreDevices.errcheck = self._kvrErrorCheck

        self.dll.kvrConfigActiveProfileSet.argtypes = [c_uint32, c_uint32]
        self.dll.kvrConfigActiveProfileSet.errcheck = self._kvrErrorCheck

        self.dll.kvrConfigActiveProfileGet.argtypes = [c_uint32, POINTER(c_uint32)]
        self.dll.kvrConfigActiveProfileGet.errcheck = self._kvrErrorCheck

        self.dll.kvrConfigNoProfilesGet.argtypes = [c_uint32, POINTER(c_uint32)]
        self.dll.kvrConfigNoProfilesGet.errcheck = self._kvrErrorCheck

        self.dll.kvrConfigClose.argtypes = [c_int32]
        self.dll.kvrConfigClose.errcheck = self._kvrErrorCheck

        self.dll.kvrConfigOpen.argtypes = [c_int32, c_int32, POINTER(c_char), POINTER(c_int32)]
        self.dll.kvrConfigOpen.errcheck = self._kvrErrorCheck

        self.dll.kvrConfigClear.argtypes = [c_int32]
        self.dll.kvrConfigClear.errcheck = self._kvrErrorCheck

        self.dll.kvrConfigOpenEx.argtypes = [c_int32, c_int32, POINTER(c_char),
                                             POINTER(c_int32), c_uint32]
        self.dll.kvrConfigOpenEx.errcheck = self._kvrErrorCheck

# kvrConfigVerifyXml
# kvrConfigInfoGet
        self.dll.kvrConfigSet.argtypes = [c_int32, c_char_p]
        self.dll.kvrConfigSet.errcheck = self._kvrErrorCheck

        self.dll.kvrConfigGet.argtypes = [c_int32, c_char_p, c_uint32]
        self.dll.kvrConfigGet.errcheck = self._kvrErrorCheck
        self.dll.kvrGetErrorText.argtypes = [c_int32, c_char_p, c_uint32]
        self.dll.kvrInitializeLibrary.argtypes = []

        self.dll.kvrHostName.argtypes = [c_uint32, c_uint32, c_uint32, c_char_p, c_uint32]
        self.dll.kvrHostName.errcheck = self._kvrErrorCheck
        self.dll.kvrNetworkConnectionTest.argtypes = [c_int32, c_int32]
        self.dll.kvrNetworkConnectionTest.errcheck = self._kvrErrorCheck
# kvrNetworkGenerateWepKeys
# kvrNetworkGenerateWpaKeys
# kvrNetworkGetAddressInfo
# kvrNetworkGetConnectionStatus
# kvrNetworkGetHostName
# kvrNetworkGetRssiRtt
        self.dll.kvrUnloadLibrary.argtypes = []
        self.dll.kvrServiceQuery.argtypes = [POINTER(c_int)]
        self.dll.kvrServiceQuery.errcheck = self._kvrErrorCheck
        self.dll.kvrServiceStart.argtypes = [POINTER(c_int)]
        self.dll.kvrServiceStart.errcheck = self._kvrErrorCheck
        self.dll.kvrServiceStop.argtypes = [POINTER(c_int)]
        self.dll.kvrServiceStop.errcheck = self._kvrErrorCheck
# kvrWlanStartScan
# kvrWlanGetScanResults
# kvrWlanGetSecurityText

    def configClose(self, handle):
        self.dll.kvrConfigClose(handle)

    def configOpen(self, channel=0, mode=kvrConfig.MODE_R):
        return kvrConfig(self, channel, mode)

    def configGet(self, handle):
        XML_BUFFER_SIZE = 2046
        xml_buffer = create_string_buffer(XML_BUFFER_SIZE)
        self.dll.kvrConfigGet(handle, xml_buffer, XML_BUFFER_SIZE)
        return xml_buffer.value

    def configClear(self, handle):
        self.dll.kvrConfigClear(handle)

    def configSet(self, handle, xml_buffer):
        self.dll.kvrConfigSet(handle, c_char_p(xml_buffer))

    @classmethod
    def deviceGetServiceStatus(self, device_info):
        kl = kvrlib()
        kl.fn = 'deviceGetServiceStatus'
        state = c_int32(-1)
        start_info = c_int32(-1)
        kl.dll.kvrDeviceGetServiceStatus(byref(device_info), byref(state), byref(start_info))
        return (state.value, start_info.value)

    @classmethod
    def deviceGetServiceStatusText(self, device_info):
        kl = kvrlib()
        kl.fn = 'deviceGetServiceStatusText'
        msg = create_string_buffer(80)
        kl.dll.kvrDeviceGetServiceStatusText(byref(device_info), msg, sizeof(msg))
        return msg.value

    @classmethod
    def addressFromString(self, type, address):
        kl = kvrlib()
        kl.fn = 'addressFromString'
        kvaddr = kvrAddress()
        kl.dll.kvrAddressFromString(type, kvaddr, address)
        return kvaddr

    @classmethod
    def stringFromAddress(self, address):
        kl = kvrlib()
        addr = create_string_buffer(80)
        kl.dll.kvrStringFromAddress(addr, sizeof(addr), address)
        return addr.value

    def discoveryClose(self, handle):
        self.fn = 'discoveryClose'
        self.dll.kvrDiscoveryClose(handle)

    def discoveryClearDevicesAtExit(self, onoff):
        self.fn = 'discoveryClearDevicesAtExit'
        self.dll.kvrDiscoveryClearDevicesAtExit(onoff)

    def discoveryOpen(self):
        return kvrDiscovery(self)

    def discoveryGetDefaultAddresses(self, addressTypeFlag, listSize):
        self.fn = 'getDefaultAddresses'
        address_list = kvrAddressList(listSize)
        address_list_count = c_uint32(listSize)
        self.dll.kvrDiscoveryGetDefaultAddresses(address_list.STRUCT_ARRAY,
                                                 address_list.elements,
                                                 byref(address_list_count),
                                                 addressTypeFlag)
        address_list.count = address_list_count.value;
        return address_list

    def discoveryStart(self, handle, delay_ms, timeout_ms):
        self.fn = 'discoveryStart'
        self.dll.kvrDiscoveryStart(handle,
                                   c_uint32(delay_ms),
                                   c_uint32(timeout_ms))

    def discoverySetAddresses(self, handle, address_list):
        self.fn = 'discoverySetAddresses'
        self.dll.kvrDiscoverySetAddresses(handle, address_list.STRUCT_ARRAY, address_list.count)

    def discoverySetEncryptionKey(self, device_info, key):
        self.fn = 'discoverySetEncryptionKey'
        self.dll.kvrDiscoverySetEncryptionKey(byref(device_info), c_char_p(key))

    def discoverySetPassword(self, device_info, password):
        self.fn = 'discoverySetPassword'
        self.dll.kvrDiscoverySetPassword(byref(device_info), c_char_p(password))

    def discoveryGetResult(self, handle, device_info):
        self.fn = 'discoveryGetResult'
        self.dll.kvrDiscoveryGetResults(handle, byref(device_info))

    def discoveryStoreDevices(self, deviceInfoList):
        self.fn = 'discoveryStoreDevices'
        self.dll.kvrDiscoveryStoreDevices(deviceInfoList.STRUCT_ARRAY, deviceInfoList.elements)

    def configActiveProfileSet(self, channel, profile_number):
        self.fn = 'configActiveProfileSet'
        self.dll.kvrConfigActiveProfileSet(channel, profile_number)

    def configActiveProfileGet(self, channel):
        self.fn = 'configActiveProfileGet'
        no_profiles = c_uint32(-1)
        self.dll.kvrConfigActiveProfileGet(channel, byref(no_profiles))
        return no_profiles.value

    def configNoProfilesGet(self, channel):
        self.fn = 'configNoProfilesGet'
        no_profiles = c_uint32(-1)
        self.dll.kvrConfigNoProfilesGet(channel, byref(no_profiles))
        return no_profiles.value

    def unload(self):
        self.fn = 'unloadLibrary'
        self.dll.kvrUnloadLibrary()

    def _configOpen(self, channel, mode, password):
        self.fn = 'configOpen'
        handle = c_int32(-1)
        self.dll.kvrConfigOpen(c_int32(channel), c_int32(mode), c_char_p(password), handle)
        return handle

    def _configOpenEx(self, channel, mode, password, profile_no):
        self.fn = 'configOpen'
        handle = c_int32(-1)
        self.dll.kvrConfigOpenEx(c_int32(channel), c_int32(mode), c_char_p(password),
                                 handle, profile_no)
        return handle

    def _kvrErrorCheck(self, result, func, arguments):
        if result == kvrERR_BLANK:
          raise kvrBlank(self, result)
        elif result < 0:
            raise kvrError(self, result)
        return result

    #------------------------------------------------------------------#
    # API                                                              #
    #------------------------------------------------------------------#

    def getVersion(self):
        self.fn = inspect.stack()[0][3]
        return self.dll.kvrGetVersion()


class kvrAddress(Structure):
    Type_UNKNOWN    = 0
    Type_IPV4       = 1
    Type_IPV6       = 2
    Type_IPV4_PORT  = 3
    Type_MAC        = 4

    TypeText = {Type_UNKNOWN: 'UNKNOWN',
                Type_IPV4: 'IPV4',
                Type_IPV6: 'IPV6',
                Type_IPV4_PORT: 'IPV4_PORT',
                Type_MAC: 'MAC'}

    _fields_ = [
        ("type", c_uint),
        ("address", c_ubyte * 20)]

    def __str__(self):
        type =  self.TypeText[self.type]
        try:
            addr = kvrlib.stringFromAddress(self);
        except (kvrError) as ex:
            addr = "unknown"
        return "%s (%s)" % (addr, type)


class kvrAddressList(Structure):
    _fields_ = [('elements', c_short),
                ('STRUCT_ARRAY', POINTER(kvrAddress))]

    def __init__(self, num_of_structs=20):
        elems = (kvrAddress * num_of_structs)()
        self.STRUCT_ARRAY = cast(elems, POINTER(kvrAddress))
        self.elements = num_of_structs
        self.count = 0

    def __str__(self):
        elements = []
        for i in range(0,self.elements):
            elements.append("%s" % self.STRUCT_ARRAY[i])
        return "\n".join(elements)


class kvrDeviceUsage():
    UNKNOWN        = 0
    FREE           = 1
    REMOTE         = 2
    USB            = 3
    CONFIG         = 4
    members = {UNKNOWN  : "UNKNOWN",
               FREE     : "FREE",
               REMOTE   : "REMOTE",
               USB      : "USB",
               CONFIG   : "CONFIG"}

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.members[self.value]

class kvrAccessibility():
    UNKNOWN       = 0
    PUBLIC        = 1
    PROTECTED     = 2
    PRIVATE       = 3
    members = {UNKNOWN   : "UNKNOWN",
               PUBLIC    : "PUBLIC",
               PROTECTED : "PROTECTED",
               PRIVATE   : "PRIVATE"}

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.members[self.value]


class kvrAvailability():
    NONE          = 0x0
    FOUND_BY_SCAN = 0x1
    STORED        = 0x2
    flags = {NONE         : "NONE",
             FOUND_BY_SCAN: "FOUND_BY_SCAN",
             STORED       : "STORED"}

    def __init__(self, value):
        self.value = value

    def __str__(self):
        text = []
        if bool(self.value & self.FOUND_BY_SCAN):
            text.append(self.flags[self.FOUND_BY_SCAN])
        if bool(self.value & self.STORED):
            text.append(self.flags[self.STORED])
        return str(text)


class kvrDeviceInfo(Structure):
    _fields_ = [
        ("struct_size",             c_uint32),
        ("ean_hi",                  c_uint32),
        ("ean_lo",                  c_uint32),
        ("ser_no",                  c_uint32),
        ("fw_major_ver",            c_int32),
        ("fw_minor_ver",            c_int32),
        ("fw_build_ver",            c_int32),
        ("name",                    c_char*256),
        ("host_name",               c_char*256),
        ("usage",                   c_int32),
        ("accessibility",           c_int32),
        ("accessibility_pwd",       c_char*256),
        ("device_address",          kvrAddress),
        ("client_address",          kvrAddress),
        ("base_station_id",         kvrAddress),
        ("request_connection",      c_int32),
        ("availability",            c_int32),
        ("encryption_key",          c_char*32),
        ("reserved1",               c_char*256),
        ("reserved2",               c_char*256)]

    def connect(self):
        self.request_connection = 1

    def disconnect(self):
        self.request_connection = 0

    def __str__(self):
        text = ""
        acc_pwd = "no"
        enc_key = "no"

        text += "name/hostname  : \"%s\" / \"%s\"\n" % (self.name, self.host_name)
        text += "  ean/serial   : %x-%x / %d\n" % (self.ean_hi, self.ean_lo, self.ser_no)
        text += "  fw           : %d.%d.%03d\n" % (self.fw_major_ver, self.fw_minor_ver, self.fw_build_ver)
        text += "  addr/cli/AP  : %s / %s / %s\n" % (self.device_address, self.client_address, self.base_station_id)
        text += "  usage/access : %s / %s\n" % (kvrDeviceUsage(self.usage), kvrAccessibility(self.accessibility))

        if self.accessibility_pwd != "":
            acc_pwd = "yes"
        if self.encryption_key != "":
            enc_key = "yes"

        text += "  pass/enc.key : %s / %s" % (acc_pwd, enc_key)
        return text

    def __repr__(self):
        return self.__str__()


class kvrDeviceInfoList(Structure):
    _fields_ = [('elements', c_short),
                ('STRUCT_ARRAY', POINTER(kvrDeviceInfo))]

    def __init__(self, deviceInfos):
        num_of_structs = len(deviceInfos)
        elems = (kvrDeviceInfo * num_of_structs)()
        self.STRUCT_ARRAY = cast(elems, POINTER(kvrDeviceInfo))

        for elem in range(0,num_of_structs):
            self.STRUCT_ARRAY[elem] = deviceInfos[elem]
        self.elements = num_of_structs
        self.count = 0

    def __str__(self):
        elements = []
        for i in range(0,self.elements):
            elements.append("%s" % (self.STRUCT_ARRAY[i]))
        return "\n".join(elements)


class kvrDiscovery(object):

    def __init__(self, kvrlib):
        self.kvrlib = kvrlib
        self.dll = kvrlib.dll
        self.kvrlib.fn = 'discoveryOpen'
        self.handle = c_int32(0xff)
        self.dll.kvrDiscoveryOpen(byref(self.handle))
        self.delay_ms = 100
        self.timeout_ms = 1000

    @classmethod
    def getDefaultAddresses(self, addressTypeFlag = kvrAddressTypeFlag_BROADCAST, listSize = 20):
        kl = kvrlib()
        return kl.discoveryGetDefaultAddresses(addressTypeFlag, listSize)

    def close(self):
        self.kvrlib.discoveryClose(self.handle)

    def clearDevicesAtExit(self, onoff):
        self.kvrlib.discoveryClearDevicesAtExit(onoff)

    def setAddresses(self, addressList):
        self.addressList = addressList
        self.kvrlib.discoverySetAddresses(self.handle, addressList)

    def setEncryptionKey(self, device_info, key):
        self.kvrlib.discoverySetEncryptionKey(device_info, key)

    def setPassword(self, device_info, password):
        self.kvrlib.discoverySetPassword(device_info, password)

    def setScanTime(self, delay_ms, timeout_ms):
        self.delay_ms = delay_ms
        self.timeout_ms = timeout_ms

    def start(self, delay_ms = None, timeout_ms = None):
        if delay_ms != None:
            self.delay_ms = delay_ms
        if timeout_ms != None:
            self.timeout_ms = timeout_ms
        self.kvrlib.discoveryStart(self.handle, self.delay_ms, self.timeout_ms)

    def storeDevices(self, deviceInfos):
        deviceInfoList = kvrDeviceInfoList(deviceInfos)
        self.kvrlib.discoveryStoreDevices(deviceInfoList)

    def getResults(self):
        self.start()
        deviceInfoList = []
        while True:
            try:
                deviceInfo = kvrDeviceInfo()
                self.kvrlib.discoveryGetResult(self.handle, deviceInfo)
                deviceInfoList.append(deviceInfo)
            except (kvrBlank) as ex:
                break;
        return deviceInfoList


if __name__ == '__main__':
    kl = kvrlib()
    print "kvrlib version: %s" % kl.getVersion()

    def usage():
        print "\nUsage: python kvrlip.py <ser_no> [-c|-s]\n"
        print "ser_no : serial number of device to connect"
        print "-c     : connect to remote device"
        print "-d     : disconnect to remote device"
        print "-s     : setup device connected to channel 0 (change some parameters)"
        sys.exit()

    if len(sys.argv) != 3:
        usage()

    if sys.argv[2] == "-c" or sys.argv[2] == "-d":
        print "Connecting to device with serial number %s" % sys.argv[1]

        addressList = kvrDiscovery.getDefaultAddresses(kvrAddressTypeFlag_BROADCAST)
        print 'Found %d addresses:' % addressList.count
        print addressList
        discovery = kl.discoveryOpen()
        discovery.setAddresses(addressList)

        delay_ms = 100
        timeout_ms = 1000
        discovery.setScanTime(delay_ms, timeout_ms)
        print 'Scanning devices...\n'
        deviceInfos = discovery.getResults()
        for deviceInfo in deviceInfos:
            if str(deviceInfo.ser_no) == sys.argv[1]:
                print "before:"
                print deviceInfo
                if sys.argv[2] == "-c":
                    deviceInfo.connect()
                    print 'Connecting to the following device:'
                else:
                    deviceInfo.disconnect()
                    print 'Disonnecting the following device:'
                print '---------------------------------------------'
                print "after:"
                print deviceInfo
                discovery.storeDevices(deviceInfos)
                break;
        discovery.close()

    elif sys.argv[2] == "-s":
        print "Setting up device on channel 0"
        try:
            config = kl.configOpen(channel=0, mode=kvrConfig.MODE_RW)
            config.getXml()
            print config.xml.toxml()
            print config.xml.getElementsByTagName('NETWORK')[0].attributes['ssid'].value
            print config.xml.getElementsByTagName('NETWORK')[0].attributes['device_name'].value
            config.xml.getElementsByTagName('NETWORK')[0].attributes['host_name'].value = "ture"
            print config.xml.getElementsByTagName('NETWORK')[0].attributes['host_name'].value
            config.setXml()
            config.close()
        except (kvrError) as ex:
            print ex

    else:
        usage()

    kl.unload()

from ctypes import *
import _winreg
import calendar
import datetime
import platform
import struct
import time
import inspect
import os
import sys

#------------------------------------------------------------------#
# kvmlib constants                                                 #
#------------------------------------------------------------------#

kvmOK                      =   0
kvmFail                    =  -1
kvmERR_PARAM               =  -3
kvmERR_LOGFILEOPEN         =  -8
kvmERR_NOSTARTTIME         =  -9
kvmERR_NOLOGMSG            = -10
kvmERR_LOGFILEWRITE        = -11
kvmEOF                     = -12
kvmERR_NO_DISK             = -13
kvmERR_LOGFILEREAD         = -14

kvmERR_QUEUE_FULL          = -20
kvmERR_CRC_ERROR           = -21
kvmERR_SECTOR_ERASED       = -22
kvmERR_FILE_ERROR          = -23
kvmERR_DISK_ERROR          = -24
kvmERR_DISKFULL_DIR        = -25
kvmERR_DISKFULL_DATA       = -26
kvmERR_SEQ_ERROR           = -27
kvmERR_FILE_SYSTEM_CORRUPT = -28
kvmERR_UNSUPPORTED_VERSION = -29
kvmERR_NOT_IMPLEMENTED     = -30
kvmERR_FATAL_ERROR         = -31
kvmERR_ILLEGAL_REQUEST     = -32
kvmERR_FILE_NOT_FOUND      = -33
kvmERR_NOT_FORMATTED       = -34
kvmERR_WRONG_DISK_TYPE     = -35
kvmERR_TIMEOUT             = -36
kvmERR_DEVICE_COMM_ERROR   = -37
kvmERR_OCCUPIED            = -38
kvmERR_USER_CANCEL         = -39
kvmERR_FIRMWARE            = -40
kvmERR_CONFIG_ERROR        = -41
kvmERR_WRITE_PROT          = -42

kvmDEVICE_MHYDRA          = 0

kvmFILE_KME24              = 0  # Deprecated, use KME40
kvmFILE_KME25              = 1  # Deprecated, use KME40
kvmFILE_KME40              = 2

class kvmError(Exception):
    def __init__(self, kvmlib, kvmERR):
        self.kvmlib = kvmlib
        self.kvmERR = kvmERR

    def __kvmGetErrorText(self):
        msg = create_string_buffer(80)
        self.kvmlib.dll.kvmGetErrorText(self.kvmERR, msg, sizeof(msg))
        return msg.value

    def __str__(self):
        return "[kvmError] %s: %s (%d)" % (self.kvmlib.fn, self.__kvmGetErrorText(), self.kvmERR)


class kvmDiskError(kvmError):
    def __init__(self, kvmlib, kvmERR):
        self.kvmlib = kvmlib
        self.kvmERR = kvmERR

class kvmNoDisk(kvmDiskError):
    def __init__(self, kvmlib, kvmERR):
        self.kvmlib = kvmlib
        self.kvmERR = kvmERR

class kvmDiskNotFormated(kvmDiskError):
    def __init__(self, kvmlib, kvmERR):
        self.kvmlib = kvmlib
        self.kvmERR = kvmERR


class kvmNoLogMsg(kvmError):
    def __init__(self, kvmlib, kvmERR):
        self.kvmlib = kvmlib
        self.kvmERR = kvmERR

    def __str__(self):
        return "No more log messages are availible (kvmERR_NOLOGMSG)"


class memoMsg(object):

    @staticmethod
    def differ(a, b):
        differ = False
        if a is not None and b is not None:
            differ = a != b
        return differ

    def __init__(self, timestamp=None):
        self.timeStamp = timestamp

    def __str__(self):
        if self.timeStamp is not None:
            text = "t:%14s " % (self.timeStamp/1000000000.0)
        else:
            text = "t:             - "
        return text

    def __eq__(self, other):
        return not self.__ne__(other)

    def _timestampDiffer(self, other):
        return (type(self) != type(other)) or memoMsg.differ(self.timeStamp, other.timeStamp)



class logMsg(memoMsg):
    def __init__(self, id=None, channel=None, dlc=None, flags=None, data=None, timestamp=None):
        super(logMsg, self).__init__(timestamp)
        self.id      = id
        self.channel = channel
        self.dlc     = dlc
        self.flags   = flags
        self.data    = data

    def __ne__(self, other):
        differ = self._timestampDiffer(other)
        if not differ:
            differ = differ or memoMsg.differ(self.channel, other.channel)
            differ = differ or memoMsg.differ(self.flags, other.flags)
            differ = differ or memoMsg.differ(self.id, other.id)
            differ = differ or memoMsg.differ(self.dlc, other.dlc)
            if self.data is not None and other.data is not None:
                for i in range(self.dlc):
                    differ = differ or memoMsg.differ(self.data[i], other.data[i])
        return differ

    def __str__(self):
        channel_s = "-" if self.channel is None else "%x" % self.channel
        text = super(logMsg, self).__str__()
        text += "ch:%s "  % ("-" if self.channel is None else "%x" % self.channel)
        text += "f:%s "   % (" -" if self.flags is None else "%2x" % self.flags)
        text += "id:%s "  % ("   -" if self.id is None else "%4x" % self.id)
        text += "dlc:%s " % ("-" if self.dlc is None else "%x" % self.dlc)
        if self.data is not None:
            text += "d:%02x %02x %02x %02x %02x %02x %02x %02x" % (self.data[0], self.data[1],
                                                                   self.data[2], self.data[3],
                                                                   self.data[4], self.data[5],
                                                                   self.data[6], self.data[7])
        else:
            text += "d: -  -  -  -  -  -  -  -"
        return text

class rtcMsg(memoMsg):
    def __init__(self, calendartime=None, timestamp=None):
        super(rtcMsg, self).__init__(timestamp)
        self.calendartime = calendartime

    def __ne__(self, other):
        differ = self._timestampDiffer(other)
        if not differ:
            differ = differ or memoMsg.differ(self.calendartime, other.calendartime)
        return differ

    def __str__(self):
        text = super(rtcMsg, self).__str__()
        text += " DateTime: %s" % self.calendartime
        return text


class trigMsg(memoMsg):
    def __init__(self, type=None, timestamp=None, pretrigger=None, posttrigger=None, trigno=None):
        super(trigMsg, self).__init__(timestamp)
        self.type        = type
        self.pretrigger  = pretrigger
        self.posttrigger = posttrigger
        self.trigno      = trigno

    def __ne__(self, other):
        differ = self._timestampDiffer(other)
        if not differ:
            differ = differ or memoMsg.differ(self.type, other.type)
            #print "%d TEST type: %s vs %s" % (differ, self.type, other.type)
            differ = differ or memoMsg.differ(self.trigno, other.trigno)
            #print "%d TEST trigno: %s vs %s" % (differ, self.trigno, other.trigno)
            differ = differ or memoMsg.differ(self.pretrigger, other.pretrigger)
            #print "%d TEST pretrigger: %s vs %s" % (differ, self.pretrigger, other.pretrigger)
            differ = differ or memoMsg.differ(self.posttrigger, other.posttrigger)
            #print "%d TEST POSTTRIGGER: %s vs %s" % (differ, self.posttrigger, other.posttrigger)
        return differ

    def __str__(self):
        text = super(trigMsg, self).__str__()
        text += "Log Trigger Event ("
        text += "type: 0x%x, " % (self.type)
        text += "trigno: 0x%02x, " % (self.trigno)
        text += "pre-trigger: %d, " % (self.pretrigger)
        text += "post-trigger: %d)\n" % (self.posttrigger)
        return text


# Info we can get from a LogFile:
#  - eventCount    The approximate number of events in the log file
#  - startTime     The time of the first event in the log file


class memoLogMsgEx(Structure):
    _fields_ = [('evType',    c_uint32),
                ('id',        c_uint32),      # The identifier
                ('timeStamp', c_int64),       # timestamp in units of 1 nanoseconds
                ('channel',   c_uint32),      # The channel on which the message arrived, 0,1,...
                ('dlc',       c_uint32),      # The length of the message
                ('flags',     c_uint32),      # Message flags
                ('data',      c_uint8 * 8)]   # Message data (8 bytes)

class memoLogRtcClockEx(Structure):
    _fields_ = [('evType',       c_uint32),
                ('calendarTime', c_uint32),    # RTC date (unix time format)
                ('timeStamp',    c_int64),
                ('padding',      c_uint8 * 24)]

class memoLogTriggerEx(Structure):
    _fields_ = [('evType',      c_uint32),
                ('type',        c_int32),
                ('preTrigger',  c_int32),
                ('postTrigger', c_int32),
                ('trigNo',      c_uint32),    # Bitmask with the activated trigger(s)
                ('timeStampLo', c_uint32),    # timestamp in units of 1 nanoseconds
                ('timeStampHi', c_uint32),    # Can't use int64 since it is not naturally aligned
                ('padding',     c_uint8 * 8)]

class memoLogRaw(Structure):
    _fields_ = [('evType', c_uint32),
                ('data',   c_uint8 * 32)]

class memoLogMrtEx(Union):
    _fields_ = [('msg', memoLogMsgEx),
                ('rtc', memoLogRtcClockEx),
                ('trig', memoLogTriggerEx),
                ('raw', memoLogRaw)]

class memoLogEventEx(Structure):

    MEMOLOG_TYPE_INVALID  =  0
    MEMOLOG_TYPE_CLOCK    =  1
    MEMOLOG_TYPE_MSG      =  2
    MEMOLOG_TYPE_TRIGGER  =  3

    _fields_ = [('event', memoLogMrtEx)]

    def createMemoEvent(self):
        type = self.event.raw.evType

        if type == self.MEMOLOG_TYPE_CLOCK:
            cTime = self.event.rtc.calendarTime
            ct = datetime.datetime.fromtimestamp(cTime)
            memoEvent = rtcMsg(timestamp=self.event.rtc.timeStamp, calendartime=ct)
            #print "Creating memoEvent:\n%s\n" % memoEvent

        elif type == self.MEMOLOG_TYPE_MSG:
            memoEvent = logMsg(timestamp=self.event.msg.timeStamp, id=self.event.msg.id,
                               channel=self.event.msg.channel, dlc=self.event.msg.dlc,
                               flags=self.event.msg.flags, data=self.event.msg.data)
            #print "Creating logEvent:\n%s\n" % memoEvent

        elif type == self.MEMOLOG_TYPE_TRIGGER:
            tstamp = self.event.trig.timeStampLo + self.event.trig.timeStampHi * 4294967296
            memoEvent = trigMsg(timestamp=tstamp, type=self.event.trig.type,
                                pretrigger=self.event.trig.preTrigger,
                                posttrigger=self.event.trig.postTrigger, trigno=self.event.trig.trigNo)
            #print "Creating trigEvent:\n%s\n" % memoEvent
        else:
            raise Exception("createMemoEvent: Unknown event type :%d" % type)

        return memoEvent

    def __str__(self):
        type = self.event.raw.evType
        text = "Unkown type %d" % type


        if type == self.MEMOLOG_TYPE_CLOCK:
            cTime = self.event.rtc.calendarTime
            text = "t:%11f " % (self.event.rtc.timeStamp / 1000000000.0)
            text += "DateTime: %s (%d)\n" % (datetime.datetime.fromtimestamp(cTime), cTime)

        if type == self.MEMOLOG_TYPE_MSG:
            timestamp = self.event.msg.timeStamp
            channel   = self.event.msg.channel
            flags     = self.event.msg.flags
            dlc       = self.event.msg.dlc
            id        = self.event.msg.id
            data      = self.event.msg.data
            text = "t:%11f ch:%x f:%2x id:%4x dlc:%x d:%x %x %x %x %x %x %x %x" % (timestamp/1000000000.0, channel, flags, id, dlc, data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7])

        if type == self.MEMOLOG_TYPE_TRIGGER:

            # txt = ""
            # for i in range(16,24):
            #     txt += "%x " % self.event.raw.data[i]
            # print txt

            evType      = self.event.trig.evType
            ttype       = self.event.trig.type
            preTrigger  = self.event.trig.preTrigger
            postTrigger = self.event.trig.postTrigger
            trigNo      = self.event.trig.trigNo
            tstamp = self.event.trig.timeStampLo + self.event.trig.timeStampHi * 4294967296
#            print "STAMP:",self.event.trig.timeStampHi, self.event.trig.timeStampLo
            text =  "t:%11f " % (tstamp/1000000000.0)
            #text =  "t  : %11x\n" % (tstamp)
            #text += " et: %x (%x)\n" % (evType, type)
            text += "Log Trigger Event ("
            text += "type: 0x%x, " % (ttype)
            text += "trigNo: 0x%02x, " % (trigNo)
            text += "pre-trigger: %d, " % (preTrigger)
            text += "post-trigger: %d)\n" % (postTrigger)
        return text

#----------------------------------------------------------------------#
# kvmlib class                                                         #
#----------------------------------------------------------------------#

class kvmlib(object):

    @staticmethod
    def kvmDeviceTypeFromEan(ean):
        if ean == '73-30130-00567-9' or ean == '73-30130-99010-4' or ean == '73-30130-00778-9':
            return kvmDEVICE_MHYDRA
        raise Exception("kvmDeviceTypeFromEan: Unknown EAN:%s" % ean)

    installDir = os.environ.get('KVDLLPATH')
    if installDir is None:
        curDir = os.path.dirname(os.path.realpath(__file__))
        baseDir = os.path.join(curDir, "..", "..")
        if 8 * struct.calcsize("P") == 32:
            installDir = os.path.join(baseDir, "Bin")
        else:
            installDir = os.path.join(baseDir, "bin_x64")

    installDir = os.path.realpath(installDir)
    if not os.path.isfile(os.path.join(installDir,"kvmlib.dll")):
        if os.path.isfile(os.path.join(".","kvmlib.dll")):
            installDir = "."
        else:
            raise Exception("ERROR: Expected to find kvmlib.dll at %s, set KVDLLPATH" % installDir)

    kvaMemolibDll0600 = WinDLL(os.path.join(installDir, 'kvaMemoLib0600.dll'))
    kvaMemolibDll = WinDLL(os.path.join(installDir, 'kvaMemoLib.dll'))
    kvmlibDll = WinDLL(os.path.join(installDir, 'kvmlib.dll'))

    def __init__(self):
        self.handle = None
        self.kmeHandle = None
        self.logFileIndex = None

        self.dll = kvmlib.kvmlibDll
        self.dll.kvmInitialize()

        self.dll.kvmInitialize.argtypes = []

        self.dll.kvmGetErrorText.argtypes = [c_int32, c_char_p, c_size_t]
        self.dll.kvmGetErrorText.errcheck = self._kvmErrorCheck

        self.dll.kvmDeviceFormatDisk.argtypes = [c_int32, c_int, c_uint32, c_uint32]
        self.dll.kvmDeviceFormatDisk.errcheck = self._kvmErrorCheck

        self.dll.kvmKmfGetUsage.argtypes = [c_int32, POINTER(c_uint32), POINTER(c_uint32)]
        self.dll.kvmKmfGetUsage.errcheck = self._kvmErrorCheck

        self.dll.kvmDeviceDiskSize.argtypes = [c_int32, POINTER(c_uint32)]
        self.dll.kvmDeviceDiskSize.errcheck = self._kvmErrorCheck

        self.dll.kvmDeviceGetRTC.argtypes = [c_int32, POINTER(c_ulong)]
        self.dll.kvmDeviceSetRTC.errcheck = self._kvmErrorCheck

        self.dll.kvmLogFileGetCreatorSerial.argtypes = [c_int32, POINTER(c_uint)]
        self.dll.kvmLogFileGetCreatorSerial.errcheck = self._kvmErrorCheck

        self.dll.kvmLogFileGetStartTime.argtypes = [c_int32, POINTER(c_uint32)]
        self.dll.kvmLogFileGetStartTime.errcheck = self._kvmErrorCheck

        self.dll.kvmDeviceOpen.argtypes = [c_int32, POINTER(c_int), c_int]
        self.dll.kvmDeviceOpen.errcheck = self._kvmErrorCheck

        self.dll.kvmDeviceMountKmf.argtypes = [c_int32]
        self.dll.kvmDeviceMountKmf.errcheck = self._kvmErrorCheck

        self.dll.kvmLogFileDismount.argtypes = [c_int32]
        self.dll.kvmLogFileDismount.errcheck = self._kvmErrorCheck

        self.dll.kvmLogFileMount.argtypes = [c_int32, c_uint32, POINTER(c_uint32)]
        self.dll.kvmLogFileMount.errcheck = self._kvmErrorCheck

        self.dll.kvmKmfReadConfig.argtypes = [c_int32, POINTER(None), c_size_t, POINTER(c_size_t)]
        self.dll.kvmKmfReadConfig.errcheck = self._kvmErrorCheck

        self.dll.kvmDeviceSetRTC.argtypes = [c_int32, c_ulong]
        self.dll.kvmDeviceSetRTC.errcheck = self._kvmErrorCheck

        self.dll.kvmDeviceDiskStatus.argtypes = [c_int32, POINTER(c_int)]
        self.dll.kvmDeviceDiskStatus.errcheck = self._kvmErrorCheck

        self.dll.kvmLogFileGetCount.argtypes = [c_int32, POINTER(c_uint32)]
        self.dll.kvmLogFileGetCount.errcheck = self._kvmErrorCheck

        self.dll.kvmLogFileReadEvent.argtypes = [c_int32, POINTER(memoLogEventEx)]
        self.dll.kvmLogFileReadEvent.errcheck = self._kvmErrorCheck

        self.dll.kvmKmfValidate.argtypes = [c_int32]
        self.dll.kvmKmfValidate.errcheck = self._kvmErrorCheck

        self.dll.kvmKmfWriteConfig.argtypes = [c_int32, POINTER(None), c_uint]
        self.dll.kvmKmfWriteConfig.errcheck = self._kvmErrorCheck

        self.dll.kvmClose.argtypes = [c_int32]
        self.dll.errcheck = self._kvmErrorCheck

        self.dll.kvmKmeOpenFile.argtypes = [c_char_p, POINTER(c_int32), c_int32]
        self.dll.kvmKmeOpenFile.errcheck = self._kvmErrorCheck

        self.dll.kvmKmeCountEvents.argtypes = [c_int32, POINTER(c_uint32)]
        self.dll.kvmKmeCountEvents.errcheck = self._kvmErrorCheck

        self.dll.kvmKmeCloseFile.argtypes = [c_int32]
        self.dll.kvmKmeCloseFile.errcheck = self._kvmErrorCheck


    def _kvmErrorCheck(self, result, func, arguments):
        if result == kvmERR_NOLOGMSG:
            raise kvmNoLogMsg(self, kvmERR_NOLOGMSG)
        if result == kvmERR_NO_DISK:
            raise kvmNoDisk(self, kvmERR_NO_DISK)
        if result == kvmERR_NOT_FORMATTED:
            raise kvmDiskNotFormated(self, kvmERR_NOT_FORMATTED)
        if result < 0:
            raise kvmError(self, result)
        return result

    def openDeviceEx(self, memoNr=0, devicetype=kvmDEVICE_MHYDRA):
        # Deprecated, use deviceOpen() instead
        self.deviceOpen(memoNr, devicetype)

    def deviceOpen(self, memoNr=0, devicetype=kvmDEVICE_MHYDRA):
        self.fn  = inspect.stack()[0][3]
        status_p = c_int()
        self.handle = self.dll.kvmDeviceOpen(c_int32(memoNr), byref(status_p), c_int(devicetype))
        if status_p.value < 0:
            self.handle = None
            print "ERROR memoNr:%d, devicetype:%d\n" %(memoNr, devicetype)
            raise kvmError(self, status_p.value)

    def openLog(self):
        # Deprecated, use deviceMountKmf() instead
        self.deviceMountKmf()

    def deviceMountKmf(self):
        self.fn = inspect.stack()[0][3]
        status = c_int()
        status = self.dll.kvmDeviceMountKmf(c_int32(self.handle))

    def readConfig(self):
        # Deprecated, use kmfReadConfig() instead
        self.kmfReadConfig()

    def kmfReadConfig(self):
        buf = create_string_buffer(8*32*1024)
        actual_len = c_size_t(0)
        self.dll.kvmKmfReadConfig(c_int32(self.handle), byref(buf), sizeof(buf), byref(actual_len))
        return buf.raw[:actual_len.value]

    def getFileSystemUsage(self):
        # Deprecated, use kmfGetUsage() instead
        self.kmfGetUsage()

    def kmfGetUsage(self):
        totalSectorCount    = c_uint32()
        usedSectorCount     = c_uint32()
        self.dll.kvmKmfGetUsage(c_int32(self.handle), byref(totalSectorCount), byref(usedSectorCount))
        return ((totalSectorCount.value*512)/(1000*1000), (usedSectorCount.value*512)/(1000*1000))

    def getDiskSize(self):
        # Deprecated, use deviceGetDiskSize() instead
        self.deviceGetDiskSize()

    def deviceGetDiskSize(self):
        diskSize = c_uint32()
        self.dll.kvmDeviceDiskSize(c_int32(self.handle), byref(diskSize))
        return (diskSize.value*512)/(1000*1000)

    def logFileGetStartTime(self):
        startTime = c_uint32()
        self.dll.kvmLogFileGetStartTime(c_int32(self.handle), byref(startTime))
        return datetime.datetime.fromtimestamp(startTime.value)

    def getRTC(self):
        # Deprecated, use deviceGetRTC() instead
        self.deviceGetRTC()

    def deviceGetRTC(self):
        time = c_ulong()
        self.dll.kvmDeviceGetRTC(c_int32(self.handle), byref(time))
        return datetime.datetime.fromtimestamp(time.value)

    def setRTC(self, timestamp):
        # Deprecated, use deviceSetRTC() instead
        self.deviceSetRTC(timestamp)

    def deviceSetRTC(self, timestamp):
        unixTime = c_ulong(int(time.mktime(timestamp.timetuple())))
        self.dll.kvmDeviceSetRTC(c_int32(self.handle), unixTime)

    def isDiskPresent(self):
        # Deprecated, use deviceGetDiskStatus() instead
        self.deviceGetDiskStatus()

    def deviceGetDiskStatus(self):
        present = c_int(0)
        self.dll.kvmDeviceDiskStatus(c_int32(self.handle), byref(present))
        return not(present.value == 0)

    def getLogFileCount(self):
        # Deprecated, use logFileGetCount() instead
        self.logFileGetCount()

    def logFileGetCount(self):
        self.fn = inspect.stack()[0][3]
        fileCount = c_uint32()
        self.dll.kvmLogFileGetCount(c_int32(self.handle), byref(fileCount))
        return fileCount.value

    def getSerialNumber(self):
        # Deprecated, use deviceGetSerialNumber() instead
        self.deviceGetSerialNumber()

    def deviceGetSerialNumber(self):
        self.fn = inspect.stack()[0][3]
        serial = c_uint()
        self.dll.kvmDeviceGetSerialNumber(c_int32(self.handle), byref(serial))
        return serial.value

    def logCloseFile(self):
        # Deprecated, use logFileDismount() instead
        self.logFileDismount()

    def logFileDismount(self):
        self.fn = inspect.stack()[0][3]
        self.dll.kvmLogFileDismount(c_int32(self.handle))
        self.logFileIndex = None
        self.eventCount = 0

    def logOpenFile(self, fileIndx):
        # Deprecated, use logFileMount() instead
        self.logFileMount(fileIndx)

    def logFileMount(self, fileIndx):
        if self.logFileIndex is not None:
            self.logFileDismount
        self.fn = inspect.stack()[0][3]
        eventCount = c_uint32()
        self.dll.kvmLogFileMount(c_int32(self.handle), c_uint32(fileIndx), byref(eventCount))
        self.logFileIndex = fileIndx
        self.eventCount = eventCount.value
        self.events = []
        return self.eventCount

    def logReadEventEx(self):
        # Deprecated, use logFileReadEvent() instead
        self.logFileReadEvent()

    def logFileReadEvent(self):
        self.fn = inspect.stack()[0][3]
        logevent = memoLogEventEx()
        try:
            self.dll.kvmLogFileReadEvent(c_int32(self.handle), byref(logevent))
        except (kvmNoLogMsg) as ex:
            return None
        memoEvent = logevent.createMemoEvent()
        return memoEvent

    def readEvents(self):
        # Deprecated, use logFileReadEvents instead
        return self.logFileReadEvents()

    def logReadEvents(self):
        # Deprecated, use logFileReadEvents() instead
        self.logFileReadEvents()

    def logFileReadEvents(self):
        self.fn = inspect.stack()[0][3]
        while True:
            event = self.logFileReadEvent()
            if event is None:
                break
            self.events.append(event)
        return self.events

    def validateDisk(self, fix=0):
        # Deprecated, use kmfValidate() instead
        self.kmfValidate(fix)

    def kmfValidate(self, fix=0):
        self.fn = inspect.stack()[0][3]
        self.dll.kvmKmfValidate(c_int32(self.handle))

    def writeConfigLif(self, lifData):
        # Deprecated, use kmfWriteConfig() instead
        self.kmfWriteConfig(lifData)

    def kmfWriteConfig(self, lifData):
        self.fn = inspect.stack()[0][3]
        buf = create_string_buffer(lifData)
        self.dll.kvmKmfWriteConfig(c_int32(self.handle), byref(buf), len(lifData))

    def writeConfig(self, config):
        self.kmfWriteConfig(config.toLif())

    def formatDisk(self, reserveSpace=10, dbaseSpace=2, fat32=True):
        # Deprecated, use deviceFormatDisk() instead
        self.deviceFormatDisk(reserveSpace, dbaseSpace, fat32)

    def deviceFormatDisk(self, reserveSpace=10, dbaseSpace=2, fat32=True):
        self.fn = inspect.stack()[0][3]
        return self.dll.kvmDeviceFormatDisk(c_int32(self.handle), c_int(fat32), c_uint32(reserveSpace),
                                      c_uint32(dbaseSpace))

    def closeDevice(self):
        # Deprecated, use close() instead
        self.close()

    def close(self):
        self.fn = inspect.stack()[0][3]
        self.dll.kvmClose(c_int32(self.handle))
        self.handle = None

    def kmeOpenFile(self, filename, filetype=kvmFILE_KME40):
        self.fn = inspect.stack()[0][3]
        if self.kmeHandle is not None:
            self.kmeCloseFile()
        status_p = c_int32()
        self.kmeHandle = self.dll.kvmKmeOpenFile(filename, byref(status_p), c_int32(filetype))
        if status_p.value != 0:
            self.kmeHandle = None
            print "ERROR filename:%s, filetype:%s\n" %(filename, filetype)
            raise kvmError(self, status_p.value)

    def kmeCountEvents(self):
        self.fn = inspect.stack()[0][3]
        eventCount = c_uint32(0)
        self.dll.kvmKmeCountEvents(c_int32(self.kmeHandle), byref(eventCount))
        return eventCount.value

    def kmeCloseFile(self):
        self.fn = inspect.stack()[0][3]
        self.dll.kvmKmeCloseFile(c_int32(self.kmeHandle))
        self.kmeHandle = None



if __name__ == '__main__':
    ml = kvmlib()
    print "Open device..."
    ml.deviceOpen(memoNr=1)
    print "Open device log area..."
    ml.deviceMountKmf()
    print "Validate disk..."
    ml.kmfValidate()
    print "Serial number:%d" % ml.deviceGetSerialNumber()
    print "Check disk size (formatting)..."
    ml.deviceFormatDisk(reserveSpace=0)
    (diskSize, usedDiskSize) = ml.kmfGetUsage()
    print "Disk size: %d MB" % (diskSize)
    print "Allocate about 100 MB space for log..."
    reservedSpace = diskSize - 8
    ml.deviceFormatDisk(reserveSpace=reservedSpace)
    (diskSize, usedDiskSize) = ml.kmfGetUsage()
    print "Size: %d MB\nUsed: %d MB" % (diskSize, usedDiskSize)
    print "Current time is %s" % datetime.datetime.now()
    print "Current device time is %s" % ml.deviceGetRTC()
    print "Setting time..."
    ml.deviceSetRTC(datetime.datetime.now())
    print "Current device time is %s" % ml.deviceGetRTC()
    ml.close()

from __future__ import print_function

import kvMemoConfig
import canlib
import kvmlib
import re
import time


class kvDevice():
    # ean:    73-30130-00671-3
    # ean_hi: 73301
    # ean_lo: 30006713

    @staticmethod
    def ean2ean_hi(ean):
        eanCompact = re.sub('-', '', ean)
        match = re.match('(\d{5})(\d{8})', eanCompact)
        return int('0x%s' % match.group(1), 0)

    @staticmethod
    def ean2ean_lo(ean):
        eanCompact = re.sub('-', '', ean)
        match = re.match('(\d{5})(\d{8})', eanCompact)
        return int('0x%s' % match.group(2), 0)

    @staticmethod
    def ean_hi_lo2ean(ean_hi, ean_lo):
        return "%02x-%05x-%05x-%x" % (ean_hi >> 12,
                                      ((ean_hi & 0xfff) << 8) | (ean_lo >> 24),
                                      (ean_lo >> 4) & 0xfffff, ean_lo & 0xf)

    @staticmethod
    def allDevices():
        devices = []
        cl = canlib.canlib()
        indx = -1
        cl.reinitializeLibrary()
        for ch in range(cl.getNumberOfChannels()):
            try:
                dev = kvDevice(ch=ch)
            except canlib.canError as e:
                if e.canERR == canlib.canERR_NOTFOUND:
                    return devices
                else:
                    raise e
            if indx == -1 or dev != devices[indx]:
                devices.append(dev)
                indx += 1
        return devices

    def __init__(self, ch=None, flags=0, canlibHnd=None, ean=None,
                 serial=None):
        if canlibHnd is None:
            self.canlib = canlib.canlib()
        else:
            self.canlib = canlibHnd

        if ean is not None:
            ch = self._findChannel(ean, serial)

        if ch is not None:
            self.channel = self.canlib.openChannel(ch, flags)
            self._loadInfo()
            self.close()
        else:
            self.channel = None
            self._loadInfo()
            self._ean = ean
            self._serial = serial
        self._channel = ch
        self.memo = None

    def _loadInfo(self):
        if self.channel is not None:
            self._card = self.cardNumber()
            self._name = self.name()
            self._ean = self.ean()
            self._serial = self.serial()
            self._fw = self.fw()
            self._driver = self.driverName()
            self._defaultHostname = self.defaultHostname()
        else:
            self.channel = None
            self._card = None
            self._name = None
            self._ean = None
            self._serial = None
            self._fw = None
            self._driver = None
            self._defaultHostname = None

    def memoOpenEx(self):
        # Deprecated, use memoOpen() instead.
        self.memoOpen()

    def memoOpen(self):
        deviceType = kvmlib.kvmlib.kvmDeviceTypeFromEan(self._ean)
        self.memo = kvmlib.kvmlib()
        self.memo.deviceOpen(memoNr=self._card, devicetype=deviceType)

    def memoClose(self):
        self.memo.close()
        self.memo = None

    def readConfig(self):
        memoWasClosed = False
        if self.memo is None:
            memoWasClosed = True
            self.memoOpen()
        self.config = kvMemoConfig.kvMemoConfig(
            param_lif=self.memo.kmfReadConfig())
        if memoWasClosed:
            self.memoClose()
        return self.config

    def writeConfig(self, config=None):
        if config is not None:
            self.config = config
        memoWasClosed = False
        if self.memo is None:
            memoWasClosed = True
            self.memoOpen()
        self.memo.writeConfig(self.config)
        if memoWasClosed:
            self.memoClose()

    def memoReadEvents(self, fileIndx):
        self.memo.logFileMount(fileIndx)
        memoEvents = self.memo.logFileReadEvents()
        self.memo.logFileDismount()
        return memoEvents

    def lastKnowncanlibChannel(self):
        return self._channel

    def cardNumber(self):
        return self.channel.getChannelData_CardNumber()

    def close(self):
        self.channel.close()
        self.channel = None

    def driverName(self):
        return self.channel.getChannelData_DriverName()

    def ean(self):
        return self.channel.getChannelData_EAN()

    def fw(self):
        (major, minor, build) = self.channel.getChannelData_Firmware()
        return (major, minor, build)

    def name(self):
        return self.channel.getChannelData_Name()

    def serial(self):
        return self.channel.getChannelData_Serial()

    def setModeVirtualLogger(self):
        self.channel.kvDeviceSetMode(canlib.kvDEVICE_MODE_LOGGER)
        if self.channel.kvDeviceGetMode() != canlib.kvDEVICE_MODE_LOGGER:
            raise Exception("ERROR: Could not set device in virtual logger"
                            " mode. Is CAN power applied?.")

    def setModeNormal(self):
        self.channel.kvDeviceSetMode(canlib.kvDEVICE_MODE_INTERFACE)
        if self.channel.kvDeviceGetMode() != canlib.kvDEVICE_MODE_INTERFACE:
            raise Exception("ERROR: Could not set device in normal mode.")

    def defaultHostname(self):
        ean_part = '%x' % kvDevice.ean2ean_lo(self._ean)
        return 'kv-%s-%06d' % (ean_part[-5:], self._serial)

    def hasScript(self):
        if self._ean == '73-30130-00567-9' or self._ean == '73-30130-00778-9':
            return True
        else:
            return False

    def open(self, flags=0, timeout=10):
        if self.channel is not None:
            self.close()
        startTime = time.time()
        while True:
            ch = self._findChannel(self._ean, self._serial)
            if ch is not None:
                self.channel = self.canlib.openChannel(ch, flags)
                self._channel = ch
                self._loadInfo()

            if self.channel is None:
                print('Waiting for device %s %s. Slept %ds (timeout:%d)' % (
                    self._ean, self._serial, time.time() - startTime, timeout))
                time.sleep(2)
            if (not (self.channel is None)) or (
                    (time.time() - startTime) > timeout):
                break
        if self.channel is None:
            raise Exception("ERROR: Could not find device %s %s (timeout: %d"
                            " s)." % (self._ean, self._serial, timeout))

    def _findChannel(self, wanted_ean, wanted_serial=None):
        channel = None
        self.canlib.reinitializeLibrary()
        for ch in range(self.canlib.getNumberOfChannels()):
            try:
                ean = self.canlib.getChannelData_EAN(ch)
                serial = self.canlib.getChannelData_Serial(ch)
            except canlib.canError as e:
                if e.canERR == canlib.canERR_NOCARD:
                    print('Card was removed')
                    break
                else:
                    raise e
            if (ean == wanted_ean) and (
                    serial == wanted_serial or wanted_serial is None):
                channel = ch
                break
        return channel

    def _waitToDisappear(self, timeout=10):
        startTime = time.time()
        print('Wait for disappear', end="")
        while self._findChannel(self._ean, self._serial) is not None:
            if time.time() - startTime > timeout:
                print("\nWARNING: Timeout (%s s) reached while waiting for"
                      " device (ean:%s, sn:%s) to disappear!" % (timeout,
                                                                 self._ean,
                                                                 self._serial))
                print('I will keep running and assume that I was too slow...')
                return
            time.sleep(1)
            print('.', end="")

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        if other is None:
            return False
        if self._ean == other._ean and self._serial == other._serial:
            return True
        else:
            if (self._serial is None or other._serial is None) and \
               self._ean == other._ean:
                return True
            else:
                return False

    def __hash__(self):
        return hash("%s %s" % (self._ean, self._serial))

    def __str__(self):
        text = 'Device: %s\n' % self._name
        text = text + 'EAN           : %s\n' % self._ean
        text = text + 'S/N           : %s\n' % self._serial
        if self._fw is not None:
            fwVersion = "v%d.%d.%d" % self._fw
        else:
            fwVersion = "None"
        text = text + 'FW            : %s\n' % fwVersion
        text = text + 'Card          : %s\n' % self._card
        text = text + 'Drv           : %s\n' % self._driver
        text = text + 'Canlib channel: %s\n' % self._channel
        return text

if __name__ == '__main__':
    devices = kvDevice.allDevices()
    print("List all %d devices..." % (len(devices)))
    for dev in devices:
        print("\n", dev)

    print("Open device...")
    cmd = 'kvDevice(ch=2)'
    dev = eval(cmd)
    print("-------------- %s \n %s" % (cmd, dev))
    cmd = 'kvDevice(ean="73-30130-99010-4")'
    dev = eval(cmd)
    print("-------------- %s \n %s" % (cmd, dev))
    cmd = 'kvDevice(ean="73-30130-00567-9", serial=71)'
    dev = eval(cmd)
    print("-------------- %s \n %s" % (cmd, dev))
    cmd = 'kvDevice(ean="73-30130-00567-9", serial=75)'
    dev = eval(cmd)
    print("-------------- %s \n %s" % (cmd, dev))

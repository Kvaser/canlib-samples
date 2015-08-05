from ctypes import *
import platform
import struct
import inspect
import os

KvaXmlStatusOK = 0
KvaXmlStatusFail = -1
KvaXmlStatusERR_ATTR_NOT_FOUND = -3
KvaXmlStatusERR_ATTR_VALUE = -4
KvaXmlStatusERR_ELEM_NOT_FOUND = -5
KvaXmlStatusERR_VALUE_RANGE = -6
KvaXmlStatusERR_VALUE_UNIQUE = -7
KvaXmlStatusERR_VALUE_CONSECUTIVE = -8
KvaXmlStatusERR_POSTFIXEXPR = -9
KvaXmlStatusERR_XML_PARSER = -10
KvaXmlStatusERR_DTD_VALIDATION = -11
KvaXmlStatusERR_INTERNAL = -20

kvaErrorText = {
    KvaXmlStatusOK: "OK",
    KvaXmlStatusFail: "Generic error",
    KvaXmlStatusERR_ATTR_NOT_FOUND: "Failed to find an attribute in a node",
    KvaXmlStatusERR_ATTR_VALUE: "The attribute value is not correct," +
                                " e.g. whitespace after a number.",
    KvaXmlStatusERR_ELEM_NOT_FOUND: "Could not find a required element",
    KvaXmlStatusERR_VALUE_RANGE: "The value is outside the allowed range",
    KvaXmlStatusERR_VALUE_UNIQUE: "The value is not unique; usually idx " +
                                  "attributes",
    KvaXmlStatusERR_VALUE_CONSECUTIVE: "The values are not conecutive; " +
                                       "usually idx attributes",
    KvaXmlStatusERR_POSTFIXEXPR: "The postfix expression could not be parsed",
    KvaXmlStatusERR_XML_PARSER: "The XML settings contain syntax errors.",
    KvaXmlStatusERR_DTD_VALIDATION: "The XML settings do not follow the DTD.",
    KvaXmlStatusERR_INTERNAL: "Internal errors, e.g. null pointers."
}


class kvaError(Exception):
    def __init__(self, kvalib, kvaERR):
        self.kvalib = kvalib
        self.kvaERR = kvaERR

    def __kvaXmlGetLastError(self):
        msg = create_string_buffer(1*1024)
        err = c_int(self.kvaERR)
        self.kvalib.dll.kvaXmlGetLastError(msg, sizeof(msg), byref(err))
        print("=%d===%s=====" % (err.value, msg.value))
        return msg.value

    def __str__(self):
        self.__kvaXmlGetLastError()
        return "[kvaError] %s: %s (%d)\n" % (self.kvalib.fn,
                                             kvaErrorText[self.kvaERR],
                                             self.kvaERR)


class kvaMemoLibXml(object):

    installDir = os.environ.get('KVDLLPATH')
    if installDir is None:
        curDir = os.path.dirname(os.path.realpath(__file__))
        baseDir = os.path.join(curDir, "..", "..")
        if 8 * struct.calcsize("P") == 32:
            installDir = os.path.join(baseDir, "Bin")
        else:
            installDir = os.path.join(baseDir, "bin_x64")

    installDir = os.path.realpath(installDir)
    if not os.path.isfile(os.path.join(installDir, "kvamemolibxml.dll")):
        if os.path.isfile(os.path.join(".", "kvamemolibxml.dll")):
            installDir = "."
        else:
            raise Exception("ERROR: Expected to find kvamemolibxml.dll at %s, set KVDLLPATH" % installDir)

    libxml2Dll = WinDLL(os.path.join(installDir, 'libxml2.dll'))
    kvaMemoLibXmlDll = WinDLL(os.path.join(installDir, 'kvamemolibxml.dll'))

    def __init__(self):
        self.dll = kvaMemoLibXml.kvaMemoLibXmlDll
        self.dll.kvaXmlInitialize()

        self.dll.kvaXmlGetLastError.argtypes = [c_char_p, c_uint,
                                                POINTER(c_int)]
        # self.dll.kvaXmlGetLastError.errcheck = self._kvaErrorCheck

        self.dll.kvaBufferToXml.argtypes = [c_char_p, c_uint, c_char_p,
                                            POINTER(c_uint), POINTER(c_long),
                                            c_char_p]
        self.dll.kvaBufferToXml.errcheck = self._kvaErrorCheck

        self.dll.kvaXmlToBuffer.argtypes = [c_char_p, c_uint, c_char_p,
                                            POINTER(c_uint), POINTER(c_long)]
        self.dll.kvaXmlToBuffer.errcheck = self._kvaErrorCheck

    def _kvaErrorCheck(self, result, func, arguments):
        if result < 0:
            raise kvaError(self, result)
        return result

    def kvaBufferToXml(self, conf_lif):
        self.fn = inspect.stack()[0][3]
        version = c_long(0)
        total_size = 500*1024
        xml_size = c_uint(total_size)
        xml_buf = create_string_buffer(total_size)
        script_path = c_char_p("")
        self.dll.kvaBufferToXml(c_char_p(conf_lif), len(conf_lif), xml_buf,
                                byref(xml_size), byref(version), script_path)
        return xml_buf.value

    def kvaXmlToBuffer(self, conf_xml):
        self.fn = inspect.stack()[0][3]
        version = c_long(0)
        total_size = 500*1024
        lif_size = c_uint(total_size)
        lif_buf = create_string_buffer(total_size)
        self.dll.kvaXmlToBuffer(c_char_p(conf_xml), len(conf_xml), lif_buf,
                                byref(lif_size), byref(version))
        return lif_buf.raw[:lif_size.value]

from xml.dom import minidom
import canlib
import kvaMemoLibXml

# If you do not have canlib.py in the current directory, set the environmental variable:
#
#  [C:\]set PYTHONPATH=c:\dev\canlib\Samples\Python
#
#  invoke with -help for more help

TRIG_LOG_ALL  = 'TRIG_LOG_ALL'
TRIG_ON_EVENT = 'TRIG_ON_EVENT'
TRIG_SCRIPTED = 'TRIG_SCRIPTED'

ACTION_START_LOG = 'ACTION_START_LOG'
ACTION_STOP_LOG  = 'ACTION_STOP_LOG'

#----------------------------------------------------------------------#
# kvFilter class                                                       #
#----------------------------------------------------------------------#


class kvFilter(object):
    def __init__(self):
        self.msgStop = []
        self.msgPass = []

    def add(self, object):
        if isinstance(object, kvFilterMsgStop):
            self.addMsgStop(object)
        else:
            raise Exception("ERROR: (kvFilter) Can not add object of type %s!" % type(object).__name__)

    def addMsgStop(self, msgStop):
        self.msgStop.append(msgStop)

class kvFilterMsgStop(object):
    def __init__(self, active=True, protocol=None, msgid=None, msgid_min=None):
        self.active    = active
        self.msgid     = msgid
        self.msgid_min = msgid_min
        if self.msgid_min is None:
            self.msgid_min = self.msgid

#----------------------------------------------------------------------#
# kvTrigger class                                                      #
#----------------------------------------------------------------------#


class kvTrigger(object):

    def __init__(self, logmode=TRIG_LOG_ALL, fifomode=True):
        self.logmode        = logmode
        self.fifomode       = fifomode
        self.trigVarTimer   = []
        self.trigVarMsgId   = []
        self.statement      = []

    def addTrigVarTimer(self, trigVarTimer):
        self.trigVarTimer.append(trigVarTimer)

    def addTrigVarMsgId(self, trigVarMsgId):
        self.trigVarMsgId.append(trigVarMsgId)

    def addStatement(self, trigStatement):
        self.statement.append(trigStatement)

class kvScript(object):
    def __init__(self, filename):
        self.filename = filename

class kvTrigVarTimer(object):
    def __init__(self, idx=0, offset=600, repeat=False, channel=0, timeout=0):
        self.idx     = idx
        self.offset  = offset
        self.repeat  = False
        self.channel = channel
        self.timeout = timeout

class kvTrigVarMsgId(object):
    def __init__(self, idx=0, channel=0, timeout=0, msgid=0, msgid_min=None, protocol="NONE"):
        self.idx       = idx
        self.channel   = channel
        self.timeout   = timeout
        self.msgid     = msgid
        self.msgid_min = msgid_min
        self.protocol  = protocol
        if self.msgid_min is None:
            self.msgid_min = self.msgid

class kvTrigStatement(object):
    def __init__(self, noOfActions=1, preTrigger=0, postTrigger=0, postFixExpr=0, function=ACTION_START_LOG, param=0):
        self.noOfActions = noOfActions
        self.preTrigger  = preTrigger
        self.postTrigger = postTrigger
        self.postFixExpr = postFixExpr
        self.function    = function
        self.param       = param

class kvMemoConfig(object):

    def __init__(self, version="1.5", afterburner=0, log_all=False, fifo_mode="NO", param_lif=None, param_xml=None):
        if param_lif is not None:
            self.parseLif(param_lif)
        elif param_xml is not None:
            self.parseXml(param_xml)
        else:
            imp = minidom.DOMImplementation()
            doctype = imp.createDocumentType(qualifiedName="KVASER", publicId="", systemId="")
            self.document = imp.createDocument(None, 'KVASER', doctype)
            root = self.document.documentElement
            self.document.appendChild(root)
            comment = self.document.createComment("Created with memoConfig.py")
            root.appendChild(comment)
            child = self.document.createElement("VERSION")
            text = self.document.createTextNode(version)
            child.appendChild(text)
            root.appendChild(child)
            xmlSettings = self.document.createElement("SETTINGS")
            root.appendChild(xmlSettings)
            xmlMode = self.document.createElement("MODE")
            xmlMode.setAttribute("log_all", "YES" if log_all else "NO")
            xmlMode.setAttribute("fifo_mode", fifo_mode)
            xmlSettings.appendChild(xmlMode)
            xmlCanpower = self.document.createElement("CANPOWER")
            xmlCanpower.setAttribute("timeout", str(afterburner))
            xmlSettings.appendChild(xmlCanpower)


    def addBusparams(self, rateParam, channel=0, silent=False):
        child = self.document.getElementsByTagName('BUSPARAMS')
        if not child:
            child = self.document.createElement("BUSPARAMS")
            self.document.documentElement.appendChild(child)
        else:
            child = child[0]
        PhSeg2 = rateParam.tseg2
        PhSeg1 = PhSeg2
        PrSeg = (rateParam.tseg1 + rateParam.tseg2) - (PhSeg1 + PhSeg2)
        PSC = (16000000 / (rateParam.freq * (1 + PrSeg + PhSeg1 + PhSeg2))) - 1
        newchild = self.document.createElement("parameters")
        newchild.setAttribute("channel", str(channel))
        newchild.setAttribute("PhSeg1", str(PhSeg1))
        newchild.setAttribute("PhSeg2", str(PhSeg2))
        newchild.setAttribute("PrSeg", str(PrSeg))
        newchild.setAttribute("PSC", str(PSC))
        newchild.setAttribute("samples", str(rateParam.nosamp))
        newchild.setAttribute("SJW", str(rateParam.sjw))
        newchild.setAttribute("silent", "YES" if silent else "NO")
        newchild.setAttribute("highspeed", "YES" if rateParam.syncMode else "NO")
        child.appendChild(newchild)

    def add(self, object):
        if isinstance(object, kvTrigger):
            self.addTrigger(object)
        elif isinstance(object, kvFilter):
            self.addFilter(object)
        else:
            raise Exception("ERROR: (kvMemoConfig) Can not add object of type %s!" % type(object).__name__)

    def addFilter(self, filter):
        xmlFilterBlock = self.document.createElement("FILTERBLOCK")
        self.document.documentElement.appendChild(xmlFilterBlock)
        # numPassFilter  = len(filter.msgPass)
        # numFilter      = numPassFilter + len(filter.msgStop)
        # print "numFilter: %d" % numFilter
        # #qqqmac hard coded for now
        # if numFilter == 1:
        #     maskHigh = 0
        #     maskLow  = 1
        # xmlFilterArray = self.document.createElement("filterarray")
        # xmlFilterArray.setAttribute("activeFiltersMaskHigh", str(maskHigh))
        # xmlFilterArray.setAttribute("activeFiltersMaskLow", str(maskLow))
        # xmlFilterArray.setAttribute("numberOfPassFilters", str(numPassFilter))
        # xmlFilterArray.setAttribute("totalNumberOfFilters", str(numFilter))
        # xmlFilterBlock.appendChild(xmlFilterArray)
        xmlFilterArray = self.document.createElement("filterarray")
        xmlFilterBlock.appendChild(xmlFilterArray)
        xmlFilterArray.setAttribute("activeFiltersMaskHigh", "0x0")
        xmlFilterArray.setAttribute("activeFiltersMaskLow", "0x3")
        xmlFilterArray.setAttribute("numberOfPassFilters", str(0))
        xmlFilterArray.setAttribute("totalNumberOfFilters", str(2))
        xmlFilterArray.setAttribute("channel", str(0))
        xmlFilterMsg = self.document.createElement("filterMsg")
        xmlFilterArray.appendChild(xmlFilterMsg)
        xmlFilterMsg.setAttribute("filter", "FILTER_TYPE_ONLY_ID")
        xmlFilterMsg.setAttribute("idx", str(0))
        xmlFilterMsg.setAttribute("msgid", "0x1")
        xmlFilterMsg.setAttribute("msgid_min", str(1))
        xmlFilterMsg.setAttribute("type", "STOP")

        xmlFilterMsg = self.document.createElement("filterMsg")
        xmlFilterArray.appendChild(xmlFilterMsg)
        xmlFilterMsg.setAttribute("filter", "FILTER_TYPE_ONLY_ID")
        xmlFilterMsg.setAttribute("idx", str(1))
        xmlFilterMsg.setAttribute("msgid", "0xa")
        xmlFilterMsg.setAttribute("msgid_min", "0x7")
        xmlFilterMsg.setAttribute("type", "STOP")


        xmlFilterArray = self.document.createElement("filterarray")
        xmlFilterBlock.appendChild(xmlFilterArray)
        xmlFilterArray.setAttribute("activeFiltersMaskHigh", "0x0")
        xmlFilterArray.setAttribute("activeFiltersMaskLow", "0x7")
        xmlFilterArray.setAttribute("numberOfPassFilters", str(0))
        xmlFilterArray.setAttribute("totalNumberOfFilters", str(3))
        xmlFilterArray.setAttribute("channel", str(1))
        xmlFilterMsg = self.document.createElement("filterMsg")
        xmlFilterArray.appendChild(xmlFilterMsg)
        xmlFilterMsg.setAttribute("filter", "FILTER_TYPE_ONLY_ID")
        xmlFilterMsg.setAttribute("idx", str(0))
        xmlFilterMsg.setAttribute("msgid", "0x1")
        xmlFilterMsg.setAttribute("msgid_min", str(1))
        xmlFilterMsg.setAttribute("type", "STOP")

        xmlFilterMsg = self.document.createElement("filterMsg")
        xmlFilterArray.appendChild(xmlFilterMsg)
        xmlFilterMsg.setAttribute("filter", "FILTER_TYPE_ONLY_ID")
        xmlFilterMsg.setAttribute("idx", str(1))
        xmlFilterMsg.setAttribute("msgid", "0x2")
        xmlFilterMsg.setAttribute("msgid_min", str(2))
        xmlFilterMsg.setAttribute("type", "STOP")

        xmlFilterMsg = self.document.createElement("filterMsg")
        xmlFilterArray.appendChild(xmlFilterMsg)
        xmlFilterMsg.setAttribute("filter", "FILTER_TYPE_ONLY_ID")
        xmlFilterMsg.setAttribute("idx", str(2))
        xmlFilterMsg.setAttribute("msgid", "0x9")
        xmlFilterMsg.setAttribute("msgid_min", "0x6")
        xmlFilterMsg.setAttribute("type", "STOP")

    def addTrigger(self, trigger):
        xmlTriggerBlock = self.document.createElement("TRIGGERBLOCK")
        self.document.documentElement.appendChild(xmlTriggerBlock)
        # qqqmac We currently need a triggerblock
        if trigger == None:
            return

        xmlTriggers = self.document.createElement("TRIGGERS")
        xmlTriggerBlock.appendChild(xmlTriggers)
        for obj in trigger.trigVarTimer:
            xmlTrigger = self.document.createElement("TRIGGER_TIMER")
            xmlTrigger.setAttribute("idx", str(obj.idx))
            xmlTrigger.setAttribute("offset", str(obj.offset))
            xmlTrigger.setAttribute("repeat", "YES" if obj.repeat else "NO")
            #xmlTrigger.setAttribute("channel", str(obj.channel))
            xmlTrigger.setAttribute("timeout", str(obj.timeout))
            xmlTriggers.appendChild(xmlTrigger)


        for obj in trigger.trigVarMsgId:
            xmlTrigger = self.document.createElement("TRIGGER_MSG_ID")
            xmlTrigger.setAttribute("idx", str(obj.idx))
            xmlTrigger.setAttribute("channel", str(obj.channel))
            xmlTrigger.setAttribute("timeout", str(obj.timeout))
            xmlTrigger.setAttribute("msgid", str(obj.msgid))
            xmlTrigger.setAttribute("msgid_min", str(obj.msgid_min))
            xmlTrigger.setAttribute("protocol", str(obj.protocol))
            xmlTriggers.appendChild(xmlTrigger)

        xmlStatements = self.document.createElement("STATEMENTS")
        xmlTriggerBlock.appendChild(xmlStatements)
        for obj in trigger.statement:
            xmlStatement = self.document.createElement("STATEMENT")
            xmlStatement.setAttribute("noOfActions", str(obj.noOfActions))
            xmlStatement.setAttribute("preTrigger", str(obj.preTrigger))
            xmlStatement.setAttribute("postTrigger", str(obj.postTrigger))
            xmlStatements.appendChild(xmlStatement)
            xmlPostFixExpr = self.document.createElement("POSTFIXEXPR")
            text = self.document.createTextNode(str(obj.postFixExpr))
            xmlPostFixExpr.appendChild(text)
            xmlStatement.appendChild(xmlPostFixExpr)
            xmlAction = self.document.createElement("ACTION")
            xmlAction.setAttribute("function", obj.function)
            xmlAction.setAttribute("param", str(obj.param))
            xmlStatement.appendChild(xmlAction)


    def addScript(self, script, channel=0):
        xmlScripts = self.document.createElement("SCRIPTS")
        self.document.documentElement.appendChild(xmlScripts)
        xmlScript = self.document.createElement("script")
        xmlScript.setAttribute("used", "1")
        xmlScript.setAttribute("primary", "1")
        xmlScript.setAttribute("defaultChannel", str(channel))
        xmlScripts.appendChild(xmlScript)
        newchild = self.document.createElement("scriptfilename")
        text = self.document.createTextNode(script.filename)
        newchild.appendChild(text)
        xmlScripts.appendChild(newchild)

    def parseLif(self, conf_lif):
        xl = kvaMemoLibXml.kvaMemoLibXml()
        conf_xml = xl.kvaBufferToXml(conf_lif)
        self.document = minidom.parseString(conf_xml)

    def parseXml(self, conf_xml):
        self.document = minidom.parseString(conf_xml)

    def toXml(self):
        return self.document.toxml()

    def toLif(self):
        xl = kvaMemoLibXml.kvaMemoLibXml()
        conf_lif = xl.kvaXmlToBuffer(self.document.toxml())
        return conf_lif

if __name__ == '__main__':

    cl = canlib.canlib()
    rate = cl.translateBaud(freq=canlib.canBITRATE_1M)
    print rate

    print "- Manually creating configuration -----------------"
    memoConfig = kvMemoConfig(afterburner=10000)
    memoConfig.addBusparams(channel=0, rateParam=rate)
    memoConfig.addBusparams(channel=1, rateParam=rate)

    trigger = kvTrigger(logmode=TRIG_ON_EVENT, fifomode=False)
    trigVarTimer = kvTrigVarTimer(idx=0, offset=10)
    trigger.addTrigVarTimer(trigVarTimer)
    trigVarTimer = kvTrigVarTimer(idx=1, offset=20)
    trigger.addTrigVarTimer(trigVarTimer)
    trigStatement = kvTrigStatement(postFixExpr=0, function=ACTION_START_LOG, param=1)
    trigger.addStatement(trigStatement)
    trigStatement = kvTrigStatement(postFixExpr=1, function=ACTION_STOP_LOG, param=1)
    trigger.addStatement(trigStatement)

    memoConfig.addTrigger(trigger)

    script = kvScript("test_script.txe")
    memoConfig.addScript(script, channel=0)
    outfile = open("firstTry.xml", 'w')
    outfile.write(memoConfig.toXml())
    outfile.close()

    print "- Converting conf.lif to xml -----------------"
    infile = open("conf.lif", 'rb')
    conf_lif = infile.read()
    infile.close()
    memoConfig2 = kvMemoConfig(param_lif=conf_lif)
    outfile = open("conf.xml", 'w')
    outfile.write(memoConfig2.toXml())
    outfile.close()

    print "- Writing manual configuration to firstTry.lif -----------------"
    outfile = open("firstTry.lif", 'wb')
    outfile.write(memoConfig.toLif())
    outfile.close()

    print "- Converting firstTry.lif to xml -----------------"
    infile = open("firstTry.lif", 'rb')
    conf_lif = infile.read()
    infile.close()

    memoConfig2 = kvMemoConfig(param_lif=conf_lif)
    outfile = open("firstTry2.xml", 'w')
    outfile.write(memoConfig2.toXml())
    outfile.close()

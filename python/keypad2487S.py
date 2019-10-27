#-------------------------------------------------------------------------------
#
# Insteon keypad 2487S
#

import iofun
import message

from switch import Switch
from querier import Querier
from querier import MsgHandler
from threading import Timer
from linkdb import *
from device import LinkRecordAdder

from us.pfrommer.insteon.msg import Msg
from us.pfrommer.insteon.msg import MsgListener
from us.pfrommer.insteon.msg import InsteonAddress

def out(msg = ""):
	iofun.out(msg)
def outchars(msg = ""):
	iofun.outchars(msg)

class DefaultMsgHandler(MsgHandler):
	def __init__(self, name):
		MsgHandler.__init__(self, name)
	def processMsg(self, msg):
		out(self.name + " got msg: " + msg.toString())
		return 1


class ExtMsgHandler(MsgHandler):
	def __init__(self, name = "ExtMsgHandler"):
		MsgHandler.__init__(self, name)
	def processMsg(self, msg):
		tmp = msg.getByte("command1") & 0xFF
		if (tmp != 0x2e):
			out(self.name + " got unexpected msg: " + msg.toString())
			return 0
		if msg.isExtended():
			out(self.name + " got ext: " + msg.toString())
			return 1
		else:
			out(self.name + " got ack, waiting for ext msg!")
			return 0

class Flags1MsgHandler(MsgHandler):
	def __init__(self, name):
		MsgHandler.__init__(self, name)
	def processMsg(self, msg):
		tmp = msg.getByte("command2") & 0xFF
		out(self.name + " = " + format(tmp, '08b'))
		f = ""
		f +=  "Plock ON|"  if (tmp & (0x1 << 0)) else "Plock OFF|"
		f +=  "LED on TX ON|" if (tmp & (0x1 << 1)) else "LED on TX OFF|"
		f +=  "Resume Dim bit ON|" if (tmp & (0x1<<2)) else "Resum Dim bit OFF|"
		f +=  "LED OFF|" if (tmp & (0x1 << 4)) else "LED ON|"
		f +=  "KeyBeep ON|" if (tmp & (0x1 << 5)) else "KeyBeep OFF|"
		f +=  "RF Disable ON|" if (tmp & (0x1 << 6)) else "RF Disable OFF|"
		f +=  "Powerline Disable ON|" if (tmp & (0x1<<7)) else "Powerline Disable OFF"
		out(self.name + " got flags1: " + f);
		return 1

class Flags2MsgHandler(MsgHandler):
	def __init__(self, name):
		MsgHandler.__init__(self, name)
	def processMsg(self, msg):
		tmp = msg.getByte("command2") & 0xFF
		out(self.name + " = " + format(tmp, '08b'))
		f = ""
		f +=  "TenD ON|"  if (tmp & (0x1 << 0)) else "TenD OFF|"
		f +=  "NX10Flag ON|" if (tmp & (0x1 << 1)) else "NX10Flag OFF|"
		f +=  "blinkOnError ON|" if (tmp & (0x1 << 2)) else "blinkOnError OFF|"
		f +=  "CleanupReport ON|" if (tmp & (0x1 << 3)) else "CleanupReport OFF|"
		f +=  "Detach Load ON|" if (tmp & (0x1 << 5)) else "Detach Load OFF|"
		f +=  "Smart Hops ON|" if (tmp & (0x1 << 6)) else "Smart Hops OFF"
		out(self.name + " got flags2: " + f);
		return 1

class CountMsgHandler(MsgHandler):
	def __init__(self, name):
		MsgHandler.__init__(self, name)
	def processMsg(self, msg):
		tmp = msg.getByte("command2") & 0xFF
		out(self.name + " = " + format(tmp, '02d'))
		return 1

class LEDStatusMsgHandler(MsgHandler):
	label = None
	def __init__(self, l):
		self.label = l
	def processMsg(self, msg):
		tmp = msg.getByte("command2") & 0xFF
		iofun.out(self.label + " = " + format(tmp, '02d') + " = " +
				  '{0:08b}'.format(tmp))
		return 1

class KPRecordFormatter(RecordFormatter):
	def __init__(self):
		pass
	def format(self, rec):
		dumpRecord(rec)


class Keypad2487S(Switch):
	"""==============  Insteon Keypad2487S ==============="""
	def __init__(self, name, addr):
		Switch.__init__(self, name, addr)

	def readFlags1(self):
		"""readFlags1()
		read plock/led/resum/beep etc flags"""
		self.querier.setMsgHandler(Flags1MsgHandler("read flags1"))
		self.querier.querysd(0x1f, 0x00)

	def readFlags2(self):
		"""readFlags2()
		read TenD/NX10/blinkOnError etc flags"""
		self.querier.setMsgHandler(Flags2MsgHandler("read flags2"))
		self.querier.querysd(0x1f, 0x05)

	def readCRCErrorCount(self):
		"""readCRCErrorCount()
		read CRC error counts"""
		self.querier.setMsgHandler(CountMsgHandler("CRC error count"))
		self.querier.querysd(0x1f, 0x02)

	def readSNFailureCount(self):
		"""readSNFailureCount()
		read SN failure counts """
		self.querier.setMsgHandler(CountMsgHandler("S/N failure count"))
		self.querier.querysd(0x1f, 0x03)

	def readDeltaFlag(self):
		"""readDeltaFlag()
		read database delta flag """
		self.querier.setMsgHandler(CountMsgHandler("database delta flag"))
		self.querier.querysd(0x1f, 0x01)

	def setOpFlags(self, cmd):
		"""setOpFlags(cmd)
	        set operating flags commands
    00 Programming lock On
    01 Programming lock off
    02 LED on with Insteon TX (LED in Light pipe disabled so this command has no effect)
    03 LED off with Insteon TX
    04 Resume Dim On
    05 Resume Dim Off
    06 8 key for Keypad Loadsense off for OutletD
    07 6 key for Keypad or Loadsense On for OUtletD
    08 Led Backlight Off
    09 Led Backlight On
    0A KeyBeep On
    0B KeyBeep Off
    0C Rf Off ... as an originator, will still hop messages
    0D Rf On
    0E Insteon Off
    0F Insteon On ... will go back to on every power cycle
    10 TenDflag On turns on App retries read out of database and cu error report
    11 TenDflag Off
    12 X10Offflag On Disables all X10 rx and tx
    13 X10Offflag Off
    14 Error Blink Off
    15 Error Blink On
    16 Cleanup Report is Off
    17 Cleanup Report is On
    ...
    1A Detach Load Off
    1B Detach Load (See Detach Load Notes Below)
    1C Start Hops of last Rx ACK (SmartHops)
    1D Start Hops of 1"""
		self.querier.setMsgHandler(DefaultMsgHandler("set operating flags"))
		self.querier.queryext(0x20, cmd, [])

	def getLEDStatus(self):
		"""getLEDStatus()
		get current led status """
		self.querier.setMsgHandler(LEDStatusMsgHandler("led level"))
		self.querier.querysd(0x19, 0x01)

	def setOnMask(self, group = 0, mask = 0):
		"""setOnMask(group/button = 0, mask = 0)
		set on mask of device"""
		self.querier.setMsgHandler(DefaultMsgHandler("set on mask"))
		self.querier.queryext(0x2e, 0x00, [group, 0x02, mask]);

	def setOffMask(self, group = 0, mask = 0):
		"""setOffMask(group/button = 0, mask = 0)
		set off mask of device"""
		self.querier.setMsgHandler(DefaultMsgHandler("set off mask"))
		self.querier.queryext(0x2e, 0x00, [group, 0x03, mask]);
#
#   convenience functions for database manipulation
#
	def addControllerForButton(self, addr, button):
		"""addControllerForButton(addr, button)
		add device with "addr" as controller for button (1=load, 3=A, 4=B, 5=C, 6=D) """
		group = button
		data = [03, 28, button]; # not sure what the first two entries are supposed to be
		self.modifyDB(LinkRecordAdder(self, addr, group, data, True))
	def addResponderForButton(self, addr, group, button):
		"""addResponderForButton(addr, group, button)
		add device with "addr" as responder on group "group" for button (1=load, 3=A, 4=B, 5=C, 6=D) """
		data = [03, 28, button]; # not sure what the first two entries are supposed to be
		self.modifyDB(LinkRecordAdder(self, addr, group, data, False))

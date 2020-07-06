from time import localtime, time, strftime
from enigma import eTimer

from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.EpgListMulti import EPGListMulti
from EpgSelectionBase import EPGSelectionBase, EPGBouquetSelection, EPGServiceZap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Screens.Setup import Setup

# Various value are in minutes, while others are in seconds.
# Use this to remind us what is going on...
SECS_IN_MIN = 60

class EPGSelectionMulti(EPGSelectionBase, EPGBouquetSelection, EPGServiceZap):
	def __init__(self, session, zapFunc, startBouquet, startRef, bouquets):
		EPGSelectionBase.__init__(self, session, startBouquet, startRef, bouquets)
		EPGBouquetSelection.__init__(self, False)
		EPGServiceZap.__init__(self, config.epgselection.multi, zapFunc)

		self.skinName = ['MultiEPG', 'EPGSelectionMulti']
		self.askTime = -1

		self['now_button'] = Pixmap()
		self['next_button'] = Pixmap()
		self['more_button'] = Pixmap()
		self['now_button_sel'] = Pixmap()
		self['next_button_sel'] = Pixmap()
		self['more_button_sel'] = Pixmap()
		self['now_text'] = Label()
		self['next_text'] = Label()
		self['more_text'] = Label()
		self['date'] = Label()

		self['epgcursoractions'] = HelpableActionMap(self, 'DirectionActions',
			{
				'left': (self.leftPressed, _('Go to previous event')),
				'right': (self.rightPressed, _('Go to next event')),
				'up': (self.moveUp, _('Go to previous channel')),
				'down': (self.moveDown, _('Go to next channel'))
			}, -1)

		self['epgactions'] = HelpableActionMap(self, 'EPGSelectActions',
			{
				'nextService': (self.nextPage, _('Move down a page')),
				'prevService': (self.prevPage, _('Move up a page')),
				'nextBouquet': (self.nextBouquet, _('Go to next bouquet')),
				'prevBouquet': (self.prevBouquet, _('Go to previous bouquet')),
				'input_date_time': (self.enterDateTime, _('Go to specific data/time')),
				'epg': (self.openSingleEPG, _('Show single epg for current channel')),
				'info': (self.openEventView, _('Show detailed event info')),
				'infolong': (self.openSingleEPG, _('Show single epg for current channel')),
				'tv': (self.bouquetList, _('Toggle between bouquet/epg lists')),
				'menu': (self.createSetup, _('Setup menu'))
			}, -1)

		self['list'] = EPGListMulti(selChangedCB=self.onSelectionChanged, timer=session.nav.RecordTimer)

	def createSetup(self):
		self.closeEventViewDialog()
		self.session.openWithCallback(self.onSetupClose, Setup, 'epgmulti')

	def onSetupClose(self, test = None):
		self['list'].setFontsize()
		self['list'].setItemsPerPage()
		self['list'].recalcEntrySize()

	def onCreate(self):
		self['list'].recalcEntrySize()
		self['lab1'].show()
		self.show()
		self.listTimer = eTimer()
		self.listTimer.callback.append(self.loadEPGData)
		self.listTimer.start(1, True)

	def loadEPGData(self):
		self._populateBouquetList()
		self.setTitle(self["bouquetlist"].getCurrentBouquet())
		self['list'].fillEPG(self.services, self.askTime)
		self['list'].moveToService(self.startRef)
		self['lab1'].hide()

	def refreshList(self):
		self.refreshTimer.stop()
		self['list'].updateEPG(0)

	def leftPressed(self):
		self['list'].updateEPG(-1)

	def rightPressed(self):
		self['list'].updateEPG(1)

	def bouquetChanged(self):
		self.bouquetRoot = False
		now = time() - int(config.epg.histminutes.value) * SECS_IN_MIN
		self.services = self.getBouquetServices(self.getCurrentBouquet())
		self['list'].fillEPG(self.services, self.askTime)
		self['list'].instance.moveSelectionTo(0)
		self.setTitle(self['bouquetlist'].getCurrentBouquet())

	def nextBouquet(self):
		self.moveBouquetDown()
		self.bouquetChanged()

	def prevBouquet(self):
		self.moveBouquetUp()
		self.bouquetChanged()

	def onDateTimeInputClosed(self, ret):
		if len(ret) > 1 and ret[0]:
			self.askTime = ret[1]
			self['list'].fillEPG(self.services, self.askTime)

	def eventViewCallback(self, setEvent, setService, val):
		l = self['list']
		old = l.getCurrent()
		if val == -1:
			self.moveUp()
		elif val == +1:
			self.moveDown()
		cur = l.getCurrent()
		if cur[0] is None and cur[1].ref != old[1].ref:
			self.eventViewCallback(setEvent, setService, val)
		else:
			setService(cur[1])
			setEvent(cur[0])

	def applyButtonState(self, state):
		if state == 0:
			self['now_button'].hide()
			self['now_button_sel'].hide()
			self['next_button'].hide()
			self['next_button_sel'].hide()
			self['more_button'].hide()
			self['more_button_sel'].hide()
			self['now_text'].hide()
			self['next_text'].hide()
			self['more_text'].hide()
			self['key_red'].setText('')
		else:
			if state == 1:
				self['now_button_sel'].show()
				self['now_button'].hide()
			else:
				self['now_button'].show()
				self['now_button_sel'].hide()
			if state == 2:
				self['next_button_sel'].show()
				self['next_button'].hide()
			else:
				self['next_button'].show()
				self['next_button_sel'].hide()
			if state == 3:
				self['more_button_sel'].show()
				self['more_button'].hide()
			else:
				self['more_button'].show()
				self['more_button_sel'].hide()

	def onSelectionChanged(self):
		count = self['list'].getCurrentChangeCount()
		if self.askTime != -1:
			self.applyButtonState(0)
		elif count > 1:
			self.applyButtonState(3)
		elif count > 0:
			self.applyButtonState(2)
		else:
			self.applyButtonState(1)
		datestr = ''
		cur = self['list'].getCurrent()
		event = cur[0]
		if event is not None:
			now = time()
			beg = event.getBeginTime()
			nowTime = localtime(now)
			begTime = localtime(beg)
			if nowTime[2] != begTime[2]:
				datestr = strftime(config.usage.date.dayshort.value, begTime)
			else:
				datestr = '%s' % _('Today')
		self['date'].setText(datestr)
		EPGSelectionBase.onSelectionChanged(self)

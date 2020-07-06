import skin
from time import localtime, time, strftime

from enigma import eEPGCache, eListbox, eListboxPythonMultiContent, loadPNG, gFont, getDesktop, eRect, eSize, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_VALIGN_TOP, RT_WRAP, BT_SCALE, BT_KEEP_ASPECT_RATIO, BT_ALIGN_CENTER
from skin import parseColor, parseFont

from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend, MultiContentEntryPixmapAlphaTest
from Components.config import config
from EpgListBase import EPGListBase

# Various value are in minutes, while others are in seconds.
# Use this to remind us what is going on...
SECS_IN_MIN = 60

class EPGListSingle(EPGListBase):
	def __init__(self, epgConfig, selChangedCB = None, timer = None, timeFocus = None):
		EPGListBase.__init__(self, selChangedCB, timer)

		self.epgConfig = epgConfig
		self.timeFocus = timeFocus or time()
		self.eventFontName = "Regular"
		if self.screenwidth == 1920:
			self.eventFontSize = 28
		else:
			self.eventFontSize = 20

		self.l.setBuildFunc(self.buildEntry)

	def applySkin(self, desktop, screen):
		if self.skinAttributes is not None:
			attribs = [ ]
			for (attrib, value) in self.skinAttributes:
				if attrib in ('EventFontSingle', 'EventFontMulti', 'EventFont'):
					font = parseFont(value, ((1,1),(1,1)) )
					self.eventFontName = font.family
					self.eventFontSize = font.pointSize
				else:
					attribs.append((attrib,value))
			self.skinAttributes = attribs
		rc = EPGListBase.applySkin(self, desktop, screen)
		self.setItemsPerPage()
		return rc

	def setItemsPerPage(self):
		if self.numberOfRows:
			self.epgConfig.itemsperpage.default = self.numberOfRows
		if self.listHeight > 0:
			itemHeight = self.listHeight / self.epgConfig.itemsperpage.value
		else:
			itemHeight = 32
		if itemHeight < 20:
			itemHeight = 20
		self.l.setItemHeight(itemHeight)
		self.instance.resize(eSize(self.listWidth, self.listHeight / itemHeight * itemHeight))
		self.listHeight = self.instance.size().height()
		self.listWidth = self.instance.size().width()
		self.itemHeight = itemHeight

	def setFontsize(self):
		self.l.setFont(0, gFont(self.eventFontName, self.eventFontSize + self.epgConfig.eventfs.value))

	def postWidgetCreate(self, instance):
		instance.setWrapAround(False)
		instance.selectionChanged.get().append(self.selectionChanged)
		instance.setContent(self.l)

	def preWidgetRemove(self, instance):
		instance.selectionChanged.get().remove(self.selectionChanged)
		instance.setContent(None)

	def recalcEntrySize(self):
		esize = self.l.getItemSize()
		width = esize.width()
		height = esize.height()
		fontSize = self.eventFontSize + self.epgConfig.eventfs.value
		dateScale, timesScale, wideScale = skin.parameters.get("EPGSingleColumnScales", (5.7, 6.0, 1.5))
		dateW = int(fontSize * dateScale)
		timesW = int(fontSize * timesScale)
		left, dateWidth, sepWidth, timesWidth, breakWidth = skin.parameters.get("EPGSingleColumnSpecs", (0, dateW, 5, timesW, 20))
		if config.usage.time.wide.value:
			timesWidth = int(timesWidth * wideScale)
		self._weekdayRect = eRect(left, 0, dateWidth, height)
		left += dateWidth + sepWidth
		self._datetimeRect = eRect(left, 0, timesWidth, height)
		left += timesWidth + breakWidth
		self._descrRect = eRect(left, 0, width - left, height)
		self.showend = True  # This is not an unused variable. It is a flag used by EPGSearch plugin

	def buildEntry(self, service, eventId, beginTime, duration, eventName):
		clockTypes = self.getPixmapForEntry(service, eventId, beginTime, duration)
		r1 = self._weekdayRect
		r2 = self._datetimeRect
		r3 = self._descrRect
		split = int(r2.width() * 0.55)
		t = localtime(beginTime)
		et = localtime(beginTime + duration)
		res = [
			None, # no private data needed
			(eListboxPythonMultiContent.TYPE_TEXT, r1.left(), r1.top(), r1.width(), r1.height(), 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, strftime(config.usage.date.dayshort.value, t)),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.left(), r2.top(), split, r2.height(), 0, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, strftime(config.usage.time.short.value + " -", t)),
			(eListboxPythonMultiContent.TYPE_TEXT, r2.left() + split, r2.top(), r2.width() - split, r2.height(), 0, RT_HALIGN_RIGHT | RT_VALIGN_CENTER, strftime(config.usage.time.short.value, et))
		]
		eventW = r3.width()
		if clockTypes:
			clockSize = 26 if self.isFullHd else 21
			eventW -= clockSize
			res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.left()+r3.width()-clockSize, (r3.height()-clockSize)/2, clockSize, clockSize, self.clocks[clockTypes]))
			if self.wasEntryAutoTimer and clockTypes in (2, 7, 12):
				eventW -= clockSize
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.left()+r3.width()-clockSize*2, (r3.height()-clockSize)/2, clockSize, clockSize, self.autotimericon))
		res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.left(), r3.top(), eventW, r3.height(), 0, RT_HALIGN_LEFT | RT_VALIGN_CENTER, eventName))
		return res

	def getSelectionPosition(self):
		# Adjust absolute indx to indx in displayed view
		indx = self.l.getCurrentSelectionIndex() % self.epgConfig.itemsperpage.value
		sely = self.instance.position().y() + self.itemHeight * indx
		if sely >= self.instance.position().y() + self.listHeight:
			sely -= self.listHeight
		return self.listWidth, sely

	def fillSimilarList(self, refstr, eventId):
		# search similar broadcastings
		t = time()
		if eventId is None:
			return
		self.list = self.epgcache.search(('RIBDN', 1024, eEPGCache.SIMILAR_BROADCASTINGS_SEARCH, refstr, eventId))
		if self.list and len(self.list):
			self.list.sort(key=lambda x: x[2])
		self.l.setList(self.list)
		self.recalcEntrySize()
		self.selectionChanged()

	def fillEPG(self, service):
		t = time()
		epgTime = t - config.epg.histminutes.value*SECS_IN_MIN
		test = [ 'RIBDT', (service.ref.toString(), 0, epgTime, -1) ]
		self.list = self.queryEPG(test)

		odds = chr(0xc2) + chr(0x86)
		odde = chr(0xc2) + chr(0x87)
		# Assume that events *might* have leading 0xC2+0x86 chars and
		# trailing 0xC2+0x87 ones, which need to be removed...(probably from
		# now and next?).
		# Just step through the list until we don't modify one whose start
		# time is after "now".
		# NOTE: that the list is a list of tuples, so we can't modify just the
		#       Title, but have to replace it with a modified tuple.
		#
		for i in range(0, len(self.list)):
			if self.list[i][4][:2] == odds and self.list[i][4][-2:] == odde:
				tlist = list(self.list[i])
				tlist[4] = tlist[4][2:-2]
				#DEBUG print "Stripped >%s< to >%s<" % (self.list[i][4], tlist[4])
				self.list[i] = tuple(tlist)
			else:
				if self.list[i][2] > t:
					break
		# Add explicit gaps if data isn't available.
		for i in range(len(self.list) - 1, 0, -1):
			thisBeg = self.list[i][2]
			prevEnd = self.list[i-1][2] + self.list[i-1][3]
			if prevEnd + 5 * SECS_IN_MIN < thisBeg:
				self.list.insert(i, (self.list[i][0], None, prevEnd, thisBeg - prevEnd, None))
		self.l.setList(self.list)
		self.recalcEntrySize()
		# select the event that contains the requested 
		idx = 0
		for x in self.list:
			if self.timeFocus < x[2]+x[3]:
				self.instance.moveSelectionTo(idx)
				break
			idx += 1

	def sortEPG(self, type):
		list = self.list
		if list:
			eventId = self.getSelectedEventId()
			if type == 1:
				list.sort(key=lambda x: (x[4] and x[4].lower(), x[2]))
			else:
				assert(type == 0)
				list.sort(key=lambda x: x[2])
			self.l.invalidate()
			self.moveToEventId(eventId)

	def getSelectedEventId(self):
		x = self.l.getCurrentSelection()
		return x and x[1]

	def moveToEventId(self, eventId):
		if not eventId:
			return
		index = 0
		for x in self.list:
			if x[1] == eventId:
				self.instance.moveSelectionTo(index)
				break
			index += 1

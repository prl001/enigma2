from Screens.Screen import Screen
from Components.Label import Label
from Components.ActionMap import ActionMap
from Components.HelpMenuList import HelpMenuList
from Components.Sources.StaticText import StaticText
from Screens.Rc import Rc
from enigma import eActionMap
from sys import maxint

class HelpMenu(Screen, Rc):
	def __init__(self, session, list):
		Screen.__init__(self, session)
		self.setup_title = _("Help")
		Screen.setTitle(self, self.setup_title)
		Rc.__init__(self)
		self.onSelChanged = [ ]
		self["list"] = HelpMenuList(list, self.close, rcPos=self.getRcPositions())
		self["longshift_key0"] = Label("")
		self["longshift_key1"] = Label("")

		self["actions"] = ActionMap(["WizardActions"],
		{
			"ok": self["list"].ok,
			"back": self.close,
		}, -1)

		# Wildcard binding with slightly higher priority than
		# the wildcard bindings in
		# InfoBarGenerics.InfoBarUnhandledKey, but with a gap
		# so that other wildcards can be interposed if needed.

		self.onClose.append(self.doOnClose)
		eActionMap.getInstance().bindAction('', maxint - 100, self["list"].handleButton)

		# Ignore keypress breaks for the keys in the
		# ListboxActions context.

		self["listboxFilterActions"] = ActionMap(["ListboxHelpMenuActions"],
			{
				"ignore": lambda: 1,
			}, 1)

		self.onLayoutFinish.append(self.doOnLayoutFinish)

	def doOnLayoutFinish(self):
		self["list"].onSelChanged.append(self.SelectionChanged)
		self.SelectionChanged()

	def doOnClose(self):
		eActionMap.getInstance().unbindAction('', self["list"].handleButton)

	def SelectionChanged(self):
		self.clearSelectedKeys()
		selection = self["list"].getCurrent()

		longText = [""] * 2
		longButtons = []
		shiftButtons=[]
		if selection:
			for button in selection[3]:
				if len(button) > 1:
					if button[1] == "SHIFT":
						self.selectKey("SHIFT")
						shiftButtons.append(button[0])
					elif button[1] == "long":
						longText[0] = _("Long key press")
						longButtons.append(button[0])
				self.selectKey(button[0])

			textline = 0
			if len(selection[3]) > 1:
				if longButtons:
					print "[HelpMenu] SelectionChanged", longButtons
					longText[textline] = _("Long press: ") + ', '.join(longButtons)
					textline += 1
				if shiftButtons:
					longText[textline] = _("SHIFT: ") + ', '.join(shiftButtons)

		self["longshift_key0"].setText(longText[0])
		self["longshift_key1"].setText(longText[1])

class HelpableScreen:
	def __init__(self):
		self["helpActions"] = ActionMap( [ "HelpActions" ],
			{
				"displayHelp": self.showHelp,
			})
		self["key_help"] = StaticText(_("HELP"))

	def showHelp(self):
		try:
			if self.secondInfoBarScreen and self.secondInfoBarScreen.shown:
				self.secondInfoBarScreen.hide()
		except:
			pass
		self.session.openWithCallback(self.callHelpAction, HelpMenu, self.helpList)

	def callHelpAction(self, *args):
		if args:
			(actionmap, context, action) = args
			actionmap.action(context, action)

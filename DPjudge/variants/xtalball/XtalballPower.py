from DPjudge import Power

class XtalballPower(Power):
	#	----------------------------------------------------------------------
	def __init__(self, game, name, type = None):
		Power.__init__(self, game, name, type)
	#	----------------------------------------------------------------------
	def __repr__(self):
		text = Power.__repr__(self).decode('latin-1')
		for listName, orders in self.list.items():
			if orders: text += '%s\n%s\n' % (listName, '\n'.join(orders))
		return text.encode('latin-1')
	#	----------------------------------------------------------------------
	def reinit(self, includeFlags = 6):
		Power.reinit(self, includeFlags)
		#	-----------------------------------
		#	Initialize the transient parameters
		#	-----------------------------------
		if includeFlags & 4:
			self.list, self.notes = {'SOONER': [], 'LATER': []}, {}
	#	----------------------------------------------------------------------
	def movesSubmitted(self):
		if self.name not in self.game.map.powers: return 1
		if (not self.game.skip
		and [x for x in self.game.powers if x.units and not x.list['SOONER']]):
			return self.list['SOONER'] or not self.units
		if self.game.skip: return self.list['LATER']
		return self.list['LATER'] or not self.units
	#	----------------------------------------------------------------------


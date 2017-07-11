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
		if includeFlags & 5:
			self.list, self.notes = {}, {}
			for lock in self.game.locks: self.list[lock] = []
	#	----------------------------------------------------------------------
	def isEliminated(self, public = False, personal = False):
		if not Power.isEliminated(self, public, personal): return False
		elif self.type: return True
		elif self.game.skip: return False
		elif not (self.homes and self.game.phase == 'M' and
			'GARRISON' in self.game.rules): return True
		return self.game.findNextPhase('A') == self.game.map.findNextPhase(
			self.game.findNextPhase('M', len(self.game.locks) - 2), 'A')
	#	----------------------------------------------------------------------
	def movesSubmitted(self):
		if self.name not in self.game.map.powers: return 1
		return self.list[self.game.locks[-1]] or not (
			self.units or self.game.skip)
	#	----------------------------------------------------------------------


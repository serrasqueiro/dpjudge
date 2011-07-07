from DPjudge import Power

class StandardPower(Power):
	#	----------------------------------------------------------------------
	def __init__(self, game, name, type = None):
		Power.__init__(self, game, name, type)
	#	----------------------------------------------------------------------
	def __repr__(self):
		text = Power.__repr__(self).decode('latin-1')
		if self.orders: text += 'ORDERS\n'
		for unit, order in self.orders.items():
			#	-----------------------------
			#	Handle "REORDER", "INVALID",
			#	and "ORDER" (NO_CHECK) orders
			#	-----------------------------
			if unit[0] not in 'RIO': text += unit + ' '
			text += order + '\n'
		return text.encode('latin-1')
	#	----------------------------------------------------------------------
	def reinit(self, includeFlags = 6):
		Power.reinit(self, includeFlags)
		#	-----------------------------------
		#	Initialize the transient parameters
		#	-----------------------------------
		if includeFlags & 4:
			self.orders, self.held = {}, 0
	#	----------------------------------------------------------------------
	def movesSubmitted(self):
		return self.orders or not self.units
	#	----------------------------------------------------------------------


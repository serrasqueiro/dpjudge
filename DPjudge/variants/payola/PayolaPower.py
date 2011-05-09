from DPjudge import Power

class PayolaPower(Power):
	#	----------------------------------------------------------------------
	class Offer:
		#	------------------------------------------------------------------
		def __init__(self, power, code, unit, order, amt, plateau):
			num = power.seq()
			vars(self).update(locals())
		#	------------------------------------------------------------------
	#	----------------------------------------------------------------------
	def __init__(self, game, name, type = None):
		Power.__init__(self, game, name, type)
	#	----------------------------------------------------------------------
	def __repr__(self):
		text = Power.__repr__(self).decode('latin-1')
		if self.elect:
			text += 'ELECT %s\n' % ' '.join(map(':'.join, self.elect.items()))
		for power in self.sent: text += 'SENT %s\n' % power
		if self.accept and (self.centers or self.units or self.retreats):
			text += 'ACCEPT %s\n' % self.accept
		if self.state: text += 'STATE %s\n' % self.state
		for offer in self.sheet: text += '%s\n' % offer
		return text.encode('latin-1')
	#	----------------------------------------------------------------------
	def reinit(self, includePersistent = 1):
		Power.reinit(self, includePersistent)
		#	-----------------------------------
		#	Initialize the transient parameters
		#	-----------------------------------
		self.overpaid, self.offers, self.sheet, self.sent = 0, [], [], []
		self.accept = self.liquid = self.left = None
		#	-----------------------------------------------
		#	The three attributes below are ZeroSum-specific
		#	-----------------------------------------------
		self.gained, self.lost = [], []
		#	-------------------------------------------
		#	And here are two that are Exchange-specific
		#	-------------------------------------------
		self.elect, self.state = {}, ''
	#	----------------------------------------------------------------------
	def initAccept(self):
		self.accept = (self.abbrev + '?')[self.isDummy():]
	#	----------------------------------------------------------------------
	def initialize(self, game):
		Power.initialize(self, game)
		if 'VASSAL_DUMMIES' in game.rules and self.isDummy(): return
		victory = game.map.victory[0]
		if self.abbrev:
			if 'ZEROSUM' in game.rules: self.funds['+'] = 10 * len(self.centers)
			self.balance = (self.income(len(self.centers))
						or (victory >> 1) * len(self.units))
			self.initAccept()
		elif self.type == 'INVESTOR': self.balance = 0
	#	----------------------------------------------------------------------
	def resign(self, gmResign = 0):
		if not self.centers: self.balance = 0
		Power.resign(self, gmResign)
	#	----------------------------------------------------------------------
	def income(self, count, asVassal = 0):
		if ('VASSAL_DUMMIES' in self.game.rules
		and self.isDummy() and not asVassal): return 0
		bux = 0
		if 'ZEROSUM' in self.game.rules:
			bux = self.funds.get('+', 0)
			if '+' in self.funds: del self.funds['+']
		elif self.game.tax: bux = count * self.game.tax
		elif 'FLAT_TAX' in self.game.rules:
			bux = count * len(self.game.map.powers)
		elif self.game.taxes:
			for center in self.centers: bux += self.game.taxes.get(center, 0)
		else:
			#	------------------------------------------------------------
			#	NOTE: In a Variable Length game, income goes down with VC's!
			#	------------------------------------------------------------
			for tax in range(count): bux += self.game.win - count + tax
		if self.game.cap: bux = min(self.game.cap, bux)
		if 'VASSAL_DUMMIES' in self.game.rules:
			for vassal in [x for x in self.game.powers if x.ceo == [self.name]]:
				bux += vassal.income(len(vassal.centers), 1)
		return bux
	#	----------------------------------------------------------------------
	def setBalance(self, amt):
		self.balance = self.liquid = amt
	#	----------------------------------------------------------------------
	def reserve(self, amt):
		self.liquid = max(self.liquid - amt, 0)
	#	----------------------------------------------------------------------
	def spend(self, amt):
		self.left -= amt
	#	----------------------------------------------------------------------
	def reduce(self):
		flat = 1
		self.overpaid += 1
		for offer in self.offers:
			if offer.amt > offer.plateau:
				flat = 0
				offer.amt -= 1
		if flat:
			for offer in self.offers:
				offer.plateau, offer.amt = 0, max(offer.amt - 1, 0)
	#	----------------------------------------------------------------------
	def seq(self):
		return len(self.offers)
	#	----------------------------------------------------------------------
	def newOffer(self, code, unit, order, amt = 0, plateau = 0):
		self.offers += [self.Offer(self, code, unit, order, amt, plateau)]
	#	----------------------------------------------------------------------
	def addOffer(self, code, unit, orders, amt = 0, plateau = 0):
		if type(orders) in (str, unicode): orders = [orders]
		full = []
		for order in orders:
			full += [' '.join(self.game.addUnitTypes(self.game.expandOrder(
				unit.split() + order.split()), processing=1)[2:])]
		orders = full
		if code == '!':
			if 'H' not in orders: self.newOffer(':', unit, 'H')
			return self.newOffer(code, unit, orders, amt, plateau)
		for order in orders:
			bribe = ((code != '&') and (code != '>' or order[0] != '-')
				and  (code != '@' or order[0] == '-')) and amt
			self.newOffer(':', unit, order, bribe, bribe and plateau)
		if code != ':': self.newOffer(code, unit, None, amt, plateau)
	#	----------------------------------------------------------------------
	def addDefaults(self):
		yes = [x.unit for x in self.offers if x.code == ':']
		[self.addOffer(':', y, 'H') for y in self.units if y not in yes]
	#	----------------------------------------------------------------------
	def countTransfer(self, powerName):
		self.sent += [powerName]
	#	----------------------------------------------------------------------
	def latePowers(self):
		if self.phaseType in 'MAR' + 'D'[:'EXCHANGE' in self.rules]:
			return Game.latePowers(self)
		return ['MASTER']
	#	----------------------------------------------------------------------
	def movesSubmitted(self):
		if self.game.phaseType == 'M':
			return self.offers or not self.units or not (self.balance
			or 'ZERO_FOREIGN' in self.game.rules
			or 'PAY_DUMMIES' in self.game.rules
			and ('VASSAL_DUMMIES' not in self.game.rules or not self.isDummy()))
		#	------------------------------------------------
		#	For non-dividend phases, call everyone submitted
		#	------------------------------------------------
		if self.game.phaseType != 'D': return 1
		return '/share' in self.funds or not self.dividendLimit()
	#	----------------------------------------------------------------------
	def dividendLimit(self):
		if self.type: return
		out = 0
		for power in self.game.powers: out += power.funds.get(self.abbrev, 0)
		if out > self.funds.get(self.abbrev, 0): return self.balance // out
	#	----------------------------------------------------------------------


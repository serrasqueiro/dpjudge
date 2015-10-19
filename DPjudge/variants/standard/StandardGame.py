import random

from DPjudge import Game

from StandardPower import StandardPower

class StandardGame(Game):
	#	----------------------------------------------------------------------
	def __init__(self, gameName, fileName = 'status'):
		self.powerType = StandardPower
		Game.__init__(self, gameName, fileName)
	#	----------------------------------------------------------------------
	def reinit(self, includeFlags = 6):
		#	------------------------------------
		#	Initialize the persistent parameters
		#	------------------------------------
		if includeFlags & 2:
			self.rules = []
		Game.reinit(self, includeFlags)
	#	----------------------------------------------------------------------
	def parsePowerData(self, power, word, includeFlags):
		parsed = Game.parsePowerData(self, power, word, includeFlags)
		if parsed: return parsed
		word = [x.upper() for x in word]
		upline = ' '.join(word)
		#	-----
		#	Modes
		#	-----
		if self.mode:
			#	----------------------------
			#	Power-specific data (orders)
			#	----------------------------
			if self.mode == 'ORDERS':
				if not includeFlags & 1: return -1
				#	------------------------------------------------------
				#	Even NO_CHECK games check that the order contains only
				#	recognized tokens, and announce this error immediately
				#	------------------------------------------------------
				word = self.expandOrder(word)
				if len(word) < 3 and (len(word) == 1 or word[1] != 'H'):
					return self.error.append('BAD ORDER: ' + upline)
				#	--------------------------------
				#	Now parse and validate the order
				#	--------------------------------
				unit, order = ' '.join(word[:2]), ' '.join(word[2:])
				if unit in power.orders:
					return self.error.append('UNIT REORDERED: ' + upline)
				#	----------------------------------------------------
				#	NO_CHECK games take the raw order text and keep it
				#	internally under the name "ORDER 1", "ORDER 2", etc.
				#	In validateStatus(), each may change from "ORDER" to
				#	"INVALID".  The addOrder() method can also change it
				#	from "ORDER" to "REORDER" (if to a twice-ordered
				#	unit).  The Game.moveResults() method knows to take
				#	any orders thus marked "INVALID" or "REORDER" and
				#	include them in the results file with annotation.
				#	----------------------------------------------------
				if 'NO_CHECK' in self.rules:
					unit, order = 'ORDER ' + `len(power.orders) + 1`, upline
				power.orders[unit], power.held = order, 1
			else: return 0
			return 1
		#	--------------------------------------
		#	Power-specific information (transient)
		#	--------------------------------------
		elif word[0] == 'ORDERS' and len(word) == 1: 
			self.mode, self.modeRequiresEnd = word[0], None
		else: return 0
		return 1
	#	----------------------------------------------------------------------
	def validateStatus(self):
		for power in [x for x in self.powers if x.orders]:
			#	-------------------------------------------------------
			#	Make sure all units are ordered (in non-NO_CHECK games)
			#	-------------------------------------------------------
			if 'DEFAULT_UNORDERED' not in self.rules: [self.error.append(
				'UNIT LEFT UNORDERED: %s, ' % power.name + unit)
				for unit in power.units if unit not in power.orders]
			for unit, order in power.orders.items():
				#	-----------------------------------------------------
				#	Convert NO_CHECK "ORDER"s to "INVALID" as appropriate
				#	-----------------------------------------------------
				if unit[:5] == 'ORDER':
					word = self.expandOrder(order.split())
					word = self.addUnitTypes(word)
					word = self.map.defaultCoast(word)
					if not self.validOrder(power,
						' '.join(word[:2]), ' '.join(word[2:]), report=0):
						power.orders['INVALID ' + unit[6:]] = order
						del power.orders[unit]
				#	-------------------------------------------------------
				#	Non-NO_CHECK.  Validate the order and report all errors
				#	-------------------------------------------------------
				else: self.validOrder(power, unit, order)
		#	-------------------------------------------------------------
		#	Go validate the rest of the data read in from the status file
		#	-------------------------------------------------------------
		Game.validateStatus(self)
	#	----------------------------------------------------------------------
	def defaultOrders(self, power):
		if not power.units: return
		if not [x for x in power.units if self.orders.get(x)]: power.cd = 1
		hold = not ('CD_SUPPORTS' in self.rules and power.cd and power.isCD(1))
		for unit in power.units: self.orders.setdefault(unit, 'H')
		if hold: return
		#	------------------------------------------------------
		#	CD_SUPPORTS implementation.  Assign orders to units in
		#	ascending order of the number of enemy units adjacent
		#	to them.  If the unit can support a friendly unit that
		#	can be attacked by two or more enemy units, make it a
		#	candidate to receive support from this unit.  Decide
		#	on any unit to support from among the candidates based
		#	on which one sorts highest given the following ordered
		#	list of data about them:
		#	1.	Whether it's an SC (1 or 0) MINUS whether enough
		#		supports to counter the number of enemy units
		#		against it have been ordered so far (also 1 or 0).
		#	2.  The number of supports still needed (having taken
		#		into account all those already ordered) to counter
		#		the largest possible enemy attack.
		#	3.	The strength of this largest possible attack.
		#	This certainly doesn't always guarantee a perfect
		#	defense, but it's not bad, and hey, the player is CD,
		#	what does he expect?
		#	------------------------------------------------------
		sequence = []
		for unit in power.units:
			count = 0
			for foreign in self.powers:
				if power is not foreign:
					for enemy in foreign.units:
						if self.abuts(enemy[0], enemy[2:], 'S', unit[2:]):
							count += 1
			sequence.append((count, unit))
		sequence.sort()
		for count, unit in sequence:
			sups = []
			for other in power.units:
				if self.abuts(unit[0], unit[2:], 'S', other[2:]):
					needs = [x[0] for x in sequence if x[1] == other][0] - 1
					has = len([x for x in power.units
						if self.orders.get(x) == 'S ' + other])
					if needs > 0: sups.append(
						((other[2:5] in self.map.scs) - (has >= needs),
						needs - has, needs, other))
			sups.sort()
			if sups: self.orders[unit] = 'S ' + random.choice([x[-1]
				for x in sups if x[:-1] == sups[-1][:-1]])
		for unit in power.units: power.orders[unit] = self.orders[unit]
	#	----------------------------------------------------------------------
	def determineOrders(self):
		#	----------------------------------
		#	Fill a "proxy table" to list which
		#	(if any) units are proxied to whom
		#	----------------------------------
		self.orders, proxy = {}, {}
		for power in self.powers:
			for unit, order in power.orders.items():
				if power is self.unitOwner(unit):
					if order[0] == 'P': proxy[unit] = ''.join(order.split()[1:])
					elif unit in proxy: del proxy[unit]
		#	-----------------------------------------------------
		#	Determine the orders to be issued to each unit, based
		#	on unit ownership and the proxy table created above.
		#	-----------------------------------------------------
		for power in self.powers:
			for unit, order in power.orders.items():
				if order[0] != 'P' and (power is self.unitOwner(unit)
				or proxy.get(unit) == power.name):
					self.orders[unit] = order
					if 'FICTIONAL_OK' in self.rules:
						#	---------------------------------------
						#	In games using FICTIONAL_OK, units may
						#	have orders that have not been expanded
						#	completely at this point.  Do this now.
						#	---------------------------------------
						word = self.map.defaultCoast(self.addUnitTypes(
							self.expandOrder((unit + ' ' + order).split()), 1))
						self.orders[' '.join(word[:2])] = ' '.join(word[2:])
		#	------------------------------------------------
		#	Add default HOLD orders for all unordered units.
		#	If a proxied unit was not ordered by the power
		#	to whom it was proxied, it will be caught here.
		#	------------------------------------------------
		for power in self.powers: self.defaultOrders(power)
		#self.save(1)
		#	-------------------------------------
		#	In NO_CHECK games, ensure that orders
		#	to other player's units are reported
		#	as invalid if no proxy was given.
		#	-------------------------------------
		if 'NO_CHECK' in self.rules:
			for power in self.powers:
				for unit, order in power.orders.items():
					if (unit[0] not in 'RI' and proxy.get(unit) != power.name
					and power is not self.unitOwner(unit)):
						order = unit + ' ' + order
						power.orders['INVALID %d' % len(power.orders)] = order
	#	----------------------------------------------------------------------
	def postMoveUpdate(self):
		for power in self.powers: power.orders, power.cd = {}, 0
		return Game.postMoveUpdate(self)
	#	----------------------------------------------------------------------
	def addOrder(self, power, word):
		#	-------------------------------
		#	Check that the order is valid.
		#	If not, self.error will say why
		#	-------------------------------
		word = self.map.defaultCoast(self.addUnitTypes(self.expandOrder(word)))
		if word and len(word[-1]) == 1 and not word[-1].isalpha():
			word = word[:-1]
		if len(word) < 2:
			return self.error.append('BAD ORDER: ' + ' '.join(word))
		unit, order = ' '.join(word[:2]), ' '.join(word[2:])
		owner = self.unitOwner(unit)
		if (('FICTIONAL_OK' not in self.rules and not owner)
		or	('ORDER_ANY' not in self.rules and owner is not power)):
			self.error += ['UNORDERABLE UNIT: ' + ' '.join(word)]
		elif order:
			valid = self.validOrder(power, unit, order)
			if valid != None:
				#	------------------------------------------------------
				#	Valid order.  But is it to a unit already ordered?
				#	This is okay in a NO_CHECK game, and we HOLD the unit.
				#	If not, pack it back into the power's order list.
				#	------------------------------------------------------
				power.cd = 0
				if valid == -1: order += ' ?'
				if unit not in power.orders: power.orders[unit] = order
				elif 'NO_CHECK' in self.rules:
					count = len(power.orders)
					if power.orders[unit] not in ('H', order):
						power.orders['REORDER %d' % count] = power.orders[unit]
						count += 1
						power.orders[unit] = 'H'
					power.orders['REORDER %d' % count] = ' '.join(word)
				else: self.error += ['UNIT REORDERED: ' + unit]
	#	----------------------------------------------------------------------
	def process(self, now = 0, email = None, roll = 0):
		#	-------------------------------------------------------------
		#	Convert all raw movement phase "ORDER"s in a NO_CHECK game to
		#	standard orders before calling Game.process().  All "INVALID"
		#	and "REORDER" orders are left raw -- the Game.moveResults()
		#	method knows how to detect and report them.
		#	-------------------------------------------------------------
		if ('NO_CHECK' in self.rules and self.phaseType == 'M' and now
		and (self.preview or self.ready(now))):
			for power in self.powers:
				orders, power.orders, cd = power.orders, {}, power.cd
				for status, order in orders.items():
					if status[:5] != 'ORDER': power.orders[status] = order
					else: self.addOrder(power, order.split())
				power.cd = cd
		return Game.process(self, now, email, roll)
	#	----------------------------------------------------------------------
	def updateOrders(self, power, orders):
		curPower, hadOrders, hasOrders, powers = power, [], [], []
		for line in orders:
			word = line.strip().split()
			if not word: continue
			who, parsed = self.getPower(word)
			if who:
				word = word[parsed:]
				if not word:
					curPower = who
					continue
			else: who = curPower
			nmr = len(word) == 1 and word[0][word[0][:1] in '([':len(
				word[0]) - (word[0][-1:] in '])')].upper() in ('NMR', 'CLEAR')
			if who not in powers:
				if not power.controls(who): return self.error.append(
					'NO CONTROL OVER ' + who.name + (
					'PROXY_OK' in self.rules and 
					' (NO NEED TO SPECIFY THE POWER FOR PROXIED UNITS)' or ''))
				#	--------------------------------------------------
				#	Empty orders before sticking any new orders in it.
				#	--------------------------------------------------
				hadOrders += [who.orders]
				powers += [who]
				who.orders = {}
				if nmr: continue
			elif nmr:
				who.orders = {}
				hasOrders = [x for x in hasOrders if x is not who]
				continue
			if 'NO_CHECK' in self.rules:
				data = self.expandOrder(word)
				if len(data) < 3 and (len(data) == 1 or data[1] != 'H'):
					self.error.append('BAD ORDER: ' + line.upper())
					continue
				who.orders['ORDER %d' % (len(who.orders) + 1)] = ' '.join(word)
			else: self.addOrder(who, word)
			if who.orders and who not in hasOrders: hasOrders += [who]
		#	------------------------------------------
		#	Make sure the player can update his orders
		#	------------------------------------------
		if not powers: return 1
		for who, oldOrders in zip(powers, hadOrders):
			self.canChangeOrders(oldOrders, who.orders,
				'PROXY_OK' in self.rules and not who.units)
			if (not self.error and who.orders and
				'NO_CHECK' not in self.rules and
				'DEFAULT_UNORDERED' not in self.rules):
				[self.error.append('UNIT LEFT UNORDERED: ' +
					(who.name + ' ', '')[who is power] + x)
					for x in who.units if x not in who.orders]
		if self.error: return self.error
		#	-------------------------------------------
		#	Clear CD flag, even if orders were cleared.
		#	-------------------------------------------
		for who in powers: who.cd = 0
		if hasOrders:
			self.logAccess(power, '', 'Orders updated')
			if len(powers) == len(hasOrders): self.process()
			else: self.save()
		else:
			self.logAccess(power, '', 'Orders cleared')
			self.save()
	#	----------------------------------------------------------------------
	def getOrders(self, power):
		if self.phaseType in 'RA': return '\n'.join(power.adjust)
		text = ''
		for unit, order in power.orders.items():
			text += ((text and '\n' or '') +
				(unit + ' ', '')['NO_CHECK' in self.rules] + order)
		return text
	#	----------------------------------------------------------------------


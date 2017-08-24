from DPjudge import Game, host

from XtalballPower import XtalballPower

class XtalballGame(Game):
	#	----------------------------------------------------------------------
	def __init__(self, gameName, fileName = 'status'):
		self.variant, self.powerType = 'xtalball', XtalballPower
		Game.__init__(self, gameName, fileName)
	#	----------------------------------------------------------------------
	def __repr__(self):
		text = Game.__repr__(self).strip()
		if len(self.locks) > 2:
			text += '\nLOCKS %d' % len(self.locks)
		return text + '\n'
	#	----------------------------------------------------------------------
	def phaseRepr(self, phase = None):
		if self.skip:
			return 'SKIP ' + ' '.join((phase
			or self.phase).split()[:-1]) + ' ' + self.locks[self.skip]
		return Game.phaseRepr(self, phase)
	#	----------------------------------------------------------------------
	def reinit(self, includeFlags = 6):
		#	------------------------------------
		#	Initialize the persistent parameters
		#	------------------------------------
		if includeFlags & 2:
			self.rules = ['FICTIONAL_OK', 'PROXY_OK']
			self.locks = []
		#	-----------------------------------
		#	Initialize the transient parameters
		#	-----------------------------------
		if includeFlags & 4:
			self.largest = self.smallest = None
			self.skip = 0
		Game.reinit(self, includeFlags)
	#	----------------------------------------------------------------------
	def unitOwner(self, unit, power = None):
		owner = Game.unitOwner(self, unit)
		#	--------------------------------------------------
		#	See if we've been passed a specific power.  If so,
		#	check any pending "adjust" orders (build, remove,
		#	and retreat) to see if this unit is mentioned.
		#	This method is called this way when displaying the
		#	locked-in orders for a certain power.
		#	--------------------------------------------------
		if power:
			if 'BUILD ' + unit in power.adjust: return power
			if 'REMOVE ' + unit in power.adjust: return
			for word in [x.split() for x in power.adjust]:
				if word[1] + ' ' + word[-1] == unit: return power
		return owner
	#	----------------------------------------------------------------------
	def parseGameData(self, word, includeFlags):
		parsed = Game.parseGameData(self, word, includeFlags)
		if parsed or self.mode: return parsed
		upword, found = word[0].upper(), 0
		if includeFlags & 4:
			#	--------------------------------------
			#	Game-specific information (transient)
			#	--------------------------------------
			found = 1
			if upword == 'SKIP':
				if len(word) == 4:
					if self.phase:
						self.error += ['TWO AWAIT/PHASE/WAIT/SKIP STATEMENTS']
					else:
						self.phase = ' '.join(word[1:3]).upper() + ' MOVEMENT'
						self.skip = word[3].upper()
				else: self.error += ['SKIP REQUIRES SEASON, YEAR AND LOCK']
			else: found = 0
		if not found and includeFlags & 2:
			#	--------------------------------------
			#	Game-specific information (persistent)
			#	--------------------------------------
			found = 1
			if upword == 'LOCKS':
				if self.locks: self.error += ['TWO LOCKS STATEMENTS']
				else:
					wrong = 1
					if len(word) == 2 and word[1].isdigit():
						try:
							num = int(word[1])
							if num > 1 and num < 7:
								self.locks = [y for x, y in enumerate(
									['SOONEST', 'SOONER', 'SOON', 'LATE', 'LATER',
									'LATEST']) if x in [1, 4, 2, 3, 0, 5][:num]]
								wrong = 0
						except: pass
					if wrong:
						self.error += ['LOCKS SHOULD BE A NUMBER BETWEEN 2 AND 6']
			else: found = 0
		return found
	#	----------------------------------------------------------------------
	def finishGameData(self):
		if not self.locks: self.locks = ['SOONER', 'LATER']
		if self.skip:
			try: self.skip = self.locks.index(self.skip)
			except:
				self.error += ['UNKNOWN SKIP LOCK: ' + self.skip]
				self.skip = 0
		Game.finishGameData(self)
	#	----------------------------------------------------------------------
	def parsePowerData(self, power, word, includeFlags):
		parsed = Game.parsePowerData(self, power, word, includeFlags)
		if parsed: return parsed
		word = [x.upper() for x in word]
		upline = ' '.join(word)
		#	-------------------------------------------
		#	Power-specific data (SOONER and/or LATER)
		#	-------------------------------------------
		#	Note that SOONER are orders entered during
		#	a previous turn and thus should be included
		#	even if includeFlags & 1 is 0, because the
		#	latter is only concerned with LATER orders.
		#	-------------------------------------------
		if word[0] in self.locks and len(word) == 1: 
			self.mode, self.modeRequiresEnd = word[0], None
		elif self.mode == self.locks[-1] and not includeFlags & 1:
			return -1
		elif self.mode and word[0] in ('A', 'F'):
			word = self.expandOrder(upline)
			if len(word[-1]) == 1 and not word[-1].isalpha():
				word = word[:-1]
				upline = upline[:-2]
			if len(word) < 3: return self.error.append('BAD ORDER: ' + upline)
			unit, order = ' '.join(word[:2]), ' '.join(word[2:])
			valid = self.validOrder(power, unit, order)
			if valid != None:
				power.list[self.mode] += [upline + ' ?' *
					(valid == -1 and not upline.endswith(' ?'))]
			if self.mode == self.locks[-1]: power.held = 1
		else: return 0
		return 1
	#	----------------------------------------------------------------------
	def validateStatus(self):
		sizes = [len(x.centers) for x in self.powers if x.centers]
		if sizes: self.smallest, self.largest = min(sizes), max(sizes)
		for rule in ['NO_CHECK']:
			if rule in self.rules:
				self.error += [rule + ' RULE IS INVALID IN CRYSTAL BALL']
		Game.validateStatus(self)
	#	----------------------------------------------------------------------
	def determineOrders(self, singlePower = None, processing = 1):
		#	---------------------------------------------------------
		#	First, determine which orders are considered and ignored,
		#	and fill a "proxy table" to list which (if any) units are
		#	proxied to whom.
		#	---------------------------------------------------------
		powerList = singlePower and [singlePower] or self.powers
		self.orders, proxy = {}, {}
		for power in powerList:
			proxyCount = orderCount = 0
			power.notes = {}
			for count, order in enumerate(power.list[self.locks[self.skip]]):
				word = order.split()
				unit = ' '.join(word[:2])
				if word[2] == 'P':
					if proxyCount < self.smallest:
						proxyCount += 1
						owner = self.unitOwner(unit, singlePower)
						if power is owner:
							unit = ' '.join(word[:2])
							proxy[unit] = (''.join(word[3:]), count)
							power.notes[count] = 'proxied'
						else: power.notes[count] = 'no unit'
					else: power.notes[count] = 'ignored'
				elif orderCount == self.largest: power.notes[count] = 'ignored'
				else: orderCount += 1
				if power.notes.get(count) != 'ignored':
					for prev in range(count):
						if (unit == ' '.join(
							power.list[self.locks[0]][prev].split()[:2])):
							power.notes[prev] = 'revoked'
		if self.skip: return
		#	-----------------------------------------------------
		#	Determine the orders to be issued to each unit, based
		#	on unit ownership and the proxy table created above.
		#	-----------------------------------------------------
		for power in powerList:
			for count, command in enumerate(power.list[self.locks[self.skip]]):
				if count in power.notes: continue
				word = self.map.defaultCoast(self.addUnitTypes(
					self.expandOrder(command), processing = processing))
				unit, order = ' '.join(word[:2]), ' '.join(word[2:])
				owner = self.unitOwner(unit, singlePower)
				if power is owner:
					self.orders[unit], power.notes[count] = order, 'ordered'
				elif proxy.get(unit, ' ')[0] == power.name:
					self.orders[unit], power.notes[count] = order, 'byProxy'
				elif not owner and ('BLIND' not in self.rules
				or self.visible(owner, unit, 'H').get(power.name, 0) & 8):
					power.notes[count] = 'no unit'
				elif 'NO_PROXY' in self.rules:
					power.notes[count] = 'foreign'
				elif len(powerList) > 1: power.notes[count] = 'noProxy'
				else: power.notes[count] = 'proxy??'
		#	------------------------------------------------
		#	Add default HOLD orders for all unordered units.
		#	If a proxied unit was not ordered by the power
		#	to whom it was proxied, mark the proxy "refused"
		#	------------------------------------------------
		for power in powerList:
			unitList = power.units
			if singlePower: unitList += [x[6:] for x in singlePower.adjust
				if x[:5] == 'BUILD']
			for unit in unitList:
				if unit in self.orders or not self.unitOwner(unit, singlePower):
					continue
				if unit in proxy:
					if len(powerList) == 1: continue
					power.notes[proxy[unit][1]] = 'refused'
				self.orders[unit] = 'H'
				power.list[self.locks[0]] += [unit + ' H']
				power.notes[len(power.notes)] = 'default'
	#	----------------------------------------------------------------------
	def preMoveUpdate(self):
		if self.skip:
			#	-------------------------------------------
			#	Lock order lists before the first game turn
			#	Announce and advance
			#	-------------------------------------------
			self.setDeadline()
			deadline = ('\nThe deadline for orders will be %s.\n' %
				self.timeFormat())
			self.openMail('Xtalball lock notice')
			self.mail.write('OFFICIAL Order lists locked\n', 0)
			self.mail.write('BROADCAST\n'
				'The order lists for turn %d of the game have been locked.\n'
				'Prepare to enter your next order list.\n'
				'%sENDPRESS\nSIGNOFF\n' % (len(self.locks) - self.skip, deadline))
			self.mail.close()
			self.mail = None
			#	---------------------------
			#	Move the order sheets ahead
			#	---------------------------
			for power in self.powers:
				if not power.list[self.locks[-1]]: power.cd = 1
				for i in range(self.skip, len(self.locks)):
					power.list[self.locks[i-1]] = power.list[self.locks[i]]
				del power.list[self.locks[len(self.locks)-1]]
			self.skip -= 1
			if self.skip and not self.roll:
				self.phase = self.findNextPhase('M')
				self.phaseType = self.phase.split()[-1][0]
			else: self.advancePhase()
			self.save()
			return
		#	----------------
		#	Broadcast orders
		#	----------------
		self.openMail('Xtalball orders', 'lists')
		if 'PUBLIC_LISTS' in self.rules:
			self.mail.write(
				'OFFICIAL Crystal Ball orders %s %.1s%s%.1s\n' %
				tuple([self.name] + self.phase.split()), 0)
			self.mail.write('BROADCAST\n', 0)
		else: self.mail.write('SIGNOFF\n', 0)
		self.mail.write('%s ORDERS\n%s\n' %
			(self.phase, '=' * (len(self.phase) + 7)))
		for player in self.map.powers:
			for guy in [x for x in self.powers
				if x.name == player and x.units]:
				for count, order in enumerate(guy.list[self.locks[0]]):
					if ('LIMIT_LISTS' in self.rules
					and count > self.largest): break
					self.mail.write('%-10s[%s] %s\n' %
						(player.title() + ':', guy.notes[count], order))
				self.mail.write('\n')
				break
		self.mail.write('ENDPRESS\nSIGNOFF\n', 0)
		self.mail.close()
		self.mail = None
		#	---------------------------
		#	Move the order sheets ahead
		#	---------------------------
		for power in self.powers:
			if not power.list[self.locks[-1]]: power.cd = 1
			for i in range(1, len(self.locks)):
				power.list[self.locks[i-1]] = power.list[self.locks[i]]
			del power.list[self.locks[len(self.locks)-1]]
#			if not power.lists[self.locks[0]] and power.units:
#				power.lists[self.locks[0]] = [power.units[0] + ' H']
		return Game.preMoveUpdate(self)
	#	----------------------------------------------------------------------
	def otherResults(self):
		if self.phaseType == 'A' and 'GARRISON' in self.rules:
			#	Add HOLD orders for incoming GARRISON builds
			for power in self.powers:
				if not power.list and power.adjust and 'SC?' in power.centers:
					power.list = {self.locks[0]: ['%s %s H' % tuple(x.split()[1:])
						for x in power.adjust]}
		return Game.otherResults(self)
	#	----------------------------------------------------------------------
##			The methods below are an initial attempt to make the game realize
##			when a solo will have occurred.  The problem is that retreats can
##			matter, or not, or can occur after the movement phase that seals
##			the deal, or not, etc.
##	#	----------------------------------------------------------------------
##	def capture(self, sender, receiver, text, subject):
##		self.results = text
##	#	----------------------------------------------------------------------
##	def process(self, now = 0, email = None):
##		if not Game.process(self, now, email) and game.phase[-1] == 'M':
##			save, self.mailPress, self.preview = self.mailPress, self.capture, 1
##			Game.process(self, now = 2)
##			self.mailPress, self.preview = save, 0
##			if 'VICTORY!' in self.results:
##				Game.process(self, now = 2, email = email)
	#	----------------------------------------------------------------------
	def getOrders(self, power):
		text = ''
		if self.phaseType in 'RA':
			text = '%s:\n' % self.phase + ('\n'.join(power.adjust) or '(NMR)')
		next = self.skip and 'First' or 'Next'
		for lock in self.locks[self.skip:]:
			text += (text and '\n\n' or '') + next + ' mbvement phase:\n'
			if power.list[lock]:
				text += '\n'.join(power.list[lock])
			else: text += '(NMR)'
			next = 'Subsequent'
		return text
	#	----------------------------------------------------------------------
	def addOrder(self, power, order, which):
		word = self.expandOrder(order)
		if word and len(word[-1]) == 1 and not word[-1].isalpha():
			word = word[:-1]
		if len(word) < 3:
			return self.error.append('BAD ORDER: ' + line)
		unit, order = ' '.join(word[:2]), ' '.join(word[2:])
		valid = self.validOrder(power, unit, order)
		if valid != None:
			power.list[which] += [' '.join(word + ['?'] * (valid == -1))]
	#	----------------------------------------------------------------------
	def updateOrders(self, power, orders):
		which = self.locks[-1]
		distributor = self.distributeOrders(power, orders,
			proxy = 'PROXY_OK' in self.rules)
		if not distributor: return 1
		hadOrders, hasOrders = [], []
		for who, what in distributor:
			if 'list' not in vars(who):
				self.error.append(
					'THE ' * (who.name in ('MASTER', 'JUDGEKEEPER')) +
					who.name + ' HAS NO UNITS OF ITS OWN TO ORDER')
				return 1
			#	--------------------------------------------------
			#	Empty orders before sticking any new orders in it.
			#	--------------------------------------------------
			hadOrders += [(who, who.list[which])]
			who.list[which] = []
			for order in what: self.addOrder(who, order, which)
			if who.list[which]: hasOrders += [who]
		#	------------------------------------------
		#	Make sure the player can update his orders
		#	------------------------------------------
		for who, oldOrders in hadOrders:
			self.canChangeOrders(oldOrders, who.list[which],
				'PROXY_OK' in self.rules and not who.units)
		if self.error: return 1
		#	-------------------------------------------
		#	Clear CD flag, even if orders were cleared.
		#	-------------------------------------------
		for who, what in hadOrders: who.cd = 0
		if not hasOrders:
			self.logAccess(power, '', 'Orders cleared')
			self.save()
			return
		self.logAccess(power, '', 'Orders updated')
		if len(hasOrders) < len(hadOrders): self.save()
		else: self.process()
		return
	#	----------------------------------------------------------------------
	def findStartPhase(self, skip = False):
		ret = Game.findStartPhase(self, skip)
		if skip: return ret
		self.skip = len(self.locks) - 1
		self.phase = self.findPreviousPhase('M', self.skip - 1)
		self.phaseType = 'M'
		return self.phase
	#	----------------------------------------------------------------------


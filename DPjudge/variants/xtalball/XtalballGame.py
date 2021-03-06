from DPjudge import Game, host

from XtalballPower import XtalballPower

class XtalballGame(Game):
	#	----------------------------------------------------------------------
	def __init__(self, gameName, fileName = 'status'):
		self.variant, self.powerType = 'xtalball', XtalballPower
		Game.__init__(self, gameName, fileName)
	#	----------------------------------------------------------------------
	def reinit(self, includeFlags = 6):
		#	------------------------------------
		#	Initialize the persistent parameters
		#	------------------------------------
		if includeFlags & 2:
			self.rules = ['FICTIONAL_OK', 'PROXY_OK']
		#	-----------------------------------
		#	Initialize the transient parameters
		#	-----------------------------------
		if includeFlags & 4:
			self.largest = self.smallest = None
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
		if word[0] in ('SOONER', 'LATER') and len(word) == 1: 
			self.mode, self.modeRequiresEnd = word[0], None
		elif self.mode == 'LATER' and not includeFlags & 1:
			return -1
		elif self.mode and word[0] in ('A', 'F'):
			word = self.expandOrder(word)
			if len(word[-1]) == 1 and not word[-1].isalpha():
				word = word[:-1]
				upline = upline[:-2]
			if len(word) < 3: return self.error.append('BAD ORDER: ' + upline)
			unit, order = ' '.join(word[:2]), ' '.join(word[2:])
			valid = self.validOrder(power, unit, order)
			if valid != None:
				power.list[self.mode] += [upline + ' ?' *
					(valid == -1 and not upline.endswith(' ?'))]
			if self.mode == 'LATER': power.held = 1
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
			for count, order in enumerate(power.list['SOONER']):
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
							power.list['SOONER'][prev].split()[:2])):
							power.notes[prev] = 'revoked'
		#	-----------------------------------------------------
		#	Determine the orders to be issued to each unit, based
		#	on unit ownership and the proxy table created above.
		#	-----------------------------------------------------
		for power in powerList:
			for count, command in enumerate(power.list['SOONER']):
				if count in power.notes: continue
				word = self.map.defaultCoast(self.addUnitTypes(
					self.expandOrder(command.split()),
					processing = processing))
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
		if self.skip: return
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
				power.list['SOONER'] += [unit + ' H']
				power.notes[len(power.notes)] = 'default'
	#	----------------------------------------------------------------------
	def preMoveUpdate(self):
		if not self.skip:
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
					for count, order in enumerate(guy.list['SOONER']):
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
			if power.list['SOONER'] and not power.list['LATER']: power.cd = 1
			power.list = {'SOONER': power.list['LATER']
				or (power.units and [power.units[0] + ' H']) or []}
		return Game.preMoveUpdate(self)
	#	----------------------------------------------------------------------
	def otherResults(self):
		if self.phaseType == 'A' and 'GARRISON' in self.rules:
			#	Add HOLD orders for incoming GARRISON builds
			for power in self.powers:
				if not power.list and power.adjust and 'SC?' in power.centers:
					power.list = {'SOONER': ['%s %s H' % tuple(x.split()[1:])
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
##	def process(self, now = 0, email = None, roll = 0):
##		if not Game.process(self, now, email, roll) and game.phase[-1] == 'M':
##			save, self.mailPress, self.preview = self.mailPress, self.capture, 1
##			Game.process(self, now = 2)
##			self.mailPress, self.preview = save, 0
##			if 'VICTORY!' in self.results:
##				Game.process(self, now = 2, email = email, roll = roll)
	#	----------------------------------------------------------------------
	def getOrders(self, power):
		text = ''
		if self.phaseType in 'RA':
			text = '%s:\n' % self.phase + ('\n'.join(power.adjust) or '(NMR)')
		if not self.skip and self.phase != self.map.phase:
			text += (text and '\n\n' or '') + 'Next movement phase:\n'
		if power.list['SOONER']:
			text += '\n'.join(power.list['SOONER'])
			if ((self.skip or self.phase != self.map.phase)
			and self.phaseType == 'M'):
				text += ('\n\nSubsequent movement phase:\n' +
					('\n'.join(power.list['LATER']) or '(NMR)'))
		else: text += '(NMR)'
		return text
	#	----------------------------------------------------------------------
	def updateOrders(self, power, orders, which = None):
		#	-------------------------------------------------------------
		#	Determine which order list (SOONER or LATER) is to be updated
		#	-------------------------------------------------------------
		if not which:
			which = 'LATER'
			if (not self.skip
			and [x for x in self.powers if x.units and not x.list['SOONER']]):
				which = 'SOONER'
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
				#	----------------------------------------
				#	Empty the order list and then stick each
				#	order (if any) into it, if it is valid.
				#	----------------------------------------
				powers += [who]
				hadOrders += [power.list[which]]
				who.list[which] = []
				if nmr: continue
			elif nmr:
				who.list[which] = []
				hasOrders = [x for x in hasOrders if x is not who]
				continue
			word = self.expandOrder(word)
			if word and len(word[-1]) == 1 and not word[-1].isalpha():
				word = word[:-1]
			if len(word) < 3:
				self.error += ['BAD ORDER: ' + line]
				continue
			unit, order = ' '.join(word[:2]), ' '.join(word[2:])
			valid = self.validOrder(who, unit, order)
			if valid != None:
				who.list[which] += [' '.join(word + ['?'] * (valid == -1))]
				if who not in hasOrders: hasOrders += [who]
		#	------------------------------------------
		#	Make sure the player can update his orders
		#	------------------------------------------
		if not powers: return 1
		for who, oldOrders in zip(powers, hadOrders):
			self.canChangeOrders(hadOrders, who.list[which],
				'PROXY_OK' in self.rules and not who.units)
		if self.error: return self.error
		#	-------------------------------------------
		#	Clear CD flag, even if orders were cleared.
		#	-------------------------------------------
		for who in powers: who.cd = 0
		if not hasOrders:
			self.logAccess(power, '', 'Orders cleared')
			self.save()
			return
		self.logAccess(power, '', 'Orders updated')
		if len(hasOrders) < len(powers):
			self.save()
			return
		#	--------------------------------------
		#	If this is not the first turn, there's
		#	a locked-in turn ready.  Process it.
		#	--------------------------------------
		if which != 'SOONER':
			self.process()
			return
		#	---------------------------------------------
		#	This is the first game turn.  If this was the
		#	last player to lock in an order list for it,
		#	announce to everyone that it's time for Fall.
		#	---------------------------------------------
		if not [x for x in self.powers
				if not x.list['SOONER'] and (not x.isDummy()
				or 'CD_DUMMIES' not in self.rules)]:
			self.setDeadline()
			deadline = ('\nThe deadline for orders will be %s.\n' %
				self.timeFormat())
			self.openMail('Xtalball lock notice')
			self.mail.write('OFFICIAL Order lists locked\n', 0)
			self.mail.write('BROADCAST\n'
				'All players have now entered an order list for the '
				'first turn\nof the game, and should now enter their '
				'next order list.\n%sENDPRESS\nSIGNOFF\n' % deadline)
			self.mail.close()
			self.mail = None
		self.save()
	#	----------------------------------------------------------------------
	def findStartPhase(self):
		Game.findStartPhase(self, 1)
	#	----------------------------------------------------------------------


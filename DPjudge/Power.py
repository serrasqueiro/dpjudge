import random, string

import host

class Power:
	#	----------------------------------------------------------------------
	def __init__(self, game, name, type = None):
		vars(self).update(locals())
		self.reinit()
	#	----------------------------------------------------------------------
	def __repr__(self):
		text = '\n' + (self.type and self.type + ' ' or '') + self.name
		if self.player: text += '\nPLAYER ' + ' '.join(self.player)
		if self.address and not self.isResigned() and not self.isDummy():
			text += '\nADDRESS ' + ' '.join(self.address)
		if self.ceo: text += '\nCONTROL ' + ' '.join(self.ceo)
		elif self.password: text += '\nPASSWORD ' + self.password
		if self.omniscient: text += '\nOMNISCIENT!'[:10 + self.omniscient]
		if self.wait: text += '\nWAIT'
		if self.vote: text += ('\nVOTE ' +
			{'0': 'LOSS', '1': 'SOLO', 'YES': 'YES'}.get(self.vote,
			self.vote + 'WAY'))
		for line in self.msg: text += '\nMSG ' + line
		if self.homes or not self.type and self.homes is not None: 
			text += '\nINHABITS ' + ' '.join(self.homes)
		if self.centers: text += '\nOWNS ' + ' '.join(self.centers)
		if self.sees: text += '\nSEES ' + ' '.join(self.sees)
		if self.hides: text += '\nHIDES ' + ', '.join(self.hides)
		if self.balance != None: self.funds['$'] = self.balance
		if self.funds:
			text += '\nFUNDS'
			for type, amt in self.funds.items():
				text += ' ' + {'$': '$' + `amt`}.get(type, `amt` + type)
		for unit, places in self.retreats.items():
			text += '\n' + ' '.join([unit, '-->'] + places)
		text = '\n'.join([text] + self.units + self.adjust) + '\n'
		return text.encode('latin-1')
	#	----------------------------------------------------------------------
	def reinit(self, includeFlags = 6):
		#	---------------------------------------------
		#	Reinitializes the power specific data.
		#   Relevant bit values for includeFlags:
		#		2: include persistent data
		#		4: include transient data
		#	---------------------------------------------

		#	------------------------------------
		#	Initialize the persistent parameters
		#	------------------------------------
		if includeFlags & 2:
			address = password = abbrev = None
			omniscient = 0
			player, msg = [], []
		#	-----------------------------------
		#	Initialize the transient parameters
		#	-----------------------------------
		if includeFlags & 4:
			wait = balance = homes = vote = None
			held = adjusted = goner = 0
			centers, units, adjust, ceo = [], [], [], []
			retreats, funds, sees, hides = {}, {}, [], []
		vars(self).update(locals())
	#	----------------------------------------------------------------------
	def compare(self, other):
		return cmp(self.type, other.type) or cmp(self.name, other.name)
	#	----------------------------------------------------------------------
	def initialize(self, game):
		self.game = game
		if self.type: return
		if self.homes is None:
			if game.map.homeYears: self.homes = []
			else: self.homes = game.map.homes.get(self.name, [])
		if 'MOBILIZE' in game.rules: self.centers = ['SC!']
		elif 'BLANK_BOARD' in game.rules:
			if not self.centers:
				self.centers = game.map.centers.get(self.name, [])
				self.units = self.units or [x for x in game.map.units.get(self.name, []) if x[2:5] not in self.centers]
		else: 
			self.centers = self.centers or game.map.centers.get(self.name, [])
			self.units = self.units or game.map.units.get(self.name, [])
	#	----------------------------------------------------------------------
	def resign(self, byMaster = 0):
		for num, power in enumerate(self.game.powers):
			if power.name == self.name: break
		if self.type or self.game.status[1] == 'forming':
			if (self.game.status[1] in ('forming', 'active', 'waiting')
			and self.type != 'MONITOR'):  # maybe should be "if self.centers"?
				#	Tell at least the GM about the resignation
				self.game.openMail('Diplomacy resignation notice',
					mailTo = self.game.master[1], mailAs = host.dpjudge)
				self.game.mail.write(
					(("You have resigned %s from game '%s'.\n",
					"%s has resigned from game '%s'.\n")[not byMaster])
					% (self.game.anglify(self.name), self.game.name))
				self.game.mail.write(
					'\n(This notice is sent ONLY to the GameMaster.)')
				self.game.mail.close()
			del self.game.powers[num]
		else:
			if (self.game.status[1] in ('active', 'waiting')
			and (self.units or self.centers)):
				self.game.avail += ['%s-(%s)' % (self.name,
					('%d/%d' % (len(self.units), len(self.centers)),
					'?/?')['BLIND' in self.game.rules])]
				self.game.delay = None
				self.game.changeStatus('waiting')
			when = self.game.phaseAbbr()
			if when[0] == '?':
				when = self.game.outcome and self.game.outcome[0] or ''
			if when and self.player[1:2] != [when]:
				if self.player and self.address:
					try:
						player = self.player[0].split('|')
						player[1] = self.address[0]
						self.player[0] = '|'.join(player)
					except: pass
				self.player[:0] = [when]
			else: del self.player[0]
			if self.player: self.player[:0] = ['RESIGNED']
			if 'BLIND' in self.game.rules: self.removeBlindMaps()
			self.password = None
			if not self.isDummy() and self.address:
				self.message, self.pressSent = [], 1
				self.game.openMail('Diplomacy resignation notice', 
					mailTo = ','.join(self.address), mailAs = host.dpjudge)
				self.game.mail.write(
					(("The Master has resigned you as %s from game '%s'.",
					"You have resigned as %s from game '%s'.")[not byMaster])
					% (self.game.anglify(self.name), self.game.name))
				self.game.mail.close()
			self.message, self.pressSent = [], 1
			if self.units or self.centers:
				self.game.mailPress(None, ['All!'],
					(("The Master has resigned %s from game '%s'.",
					"%s has resigned from game '%s'.")[not byMaster])
					% (self.game.anglify(self.name), self.game.name) +
					('', '\nThe deadline for orders is now %s.\n' %
					self.game.timeFormat())[not self.game.avail],
					subject = 'Diplomacy resignation notice')
			else:
				#	Tell at least the GM about the resignation
				self.game.openMail('Diplomacy resignation notice',
					mailTo = self.game.master[1], mailAs = host.dpjudge)
				self.game.mail.write(
					(("You have resigned %s from game '%s'.\n",
					"%s has resigned from game '%s'.\n")[not byMaster])
					% (self.game.anglify(self.name), self.game.name))
				self.game.mail.write(
					'\n(This notice is sent ONLY to the GameMaster.)')
				self.game.mail.close()
		self.address = None
		self.game.save()
	#	----------------------------------------------------------------------
	def takeover(self, dppd = None, email = None, password = None,
		byMaster = 0):
		resigned, dummy = self.isResigned(), self.isDummy()
		revived, generated = not dppd, not password
		phase = self.game.phaseAbbr()
		if phase[0] == '?':
			phase = self.game.outcome and self.game.outcome[0] or ''
		if not resigned and not dummy:
			if not password or self.isValidPassword(password) != 1:
				return ('You need to specify the password of the current ' +
					'player in order to take over.')
		elif not password:
			password = self.generatePassword()
		if resigned or dummy:
			if len(self.player) > 2: self.player = self.player[2:]
			elif not power:
				return 'Cannot revive a power never assigned to a player.'
			else: self.player = []
		if self.player and (not dppd or
			self.player[0].split('|')[0] == dppd.split('|')[0]): revived = 1
		else: self.player[:0] = [dppd, phase]
		self.address = [self.player[0].split('|')[1]]
		if email and email != self.address[0]:
			self.address[:0] = [email]
		self.password = password
		self.game.openMail('Diplomacy takeover notice',
			mailTo = self.name, mailAs = host.dpjudge)
		self.game.mail.write(
			"You are %s %s in game '%s'.\n" %
			(('now', 'again')[revived], self.game.anglify(self.name), self.game.name) +
			("Your password is '%s'.\n" % password) * (generated or byMaster) +
			"Welcome %sto the DPjudge.\n" % ('back ' * revived))
		self.game.mail.close()
		if resigned: self.game.avail = [x for x in self.game.avail
			if not x.startswith(self.name + '-')]
		if not self.game.avail:
			self.game.changeStatus('active')
			self.game.setDeadline()
		self.game.save()
		if 'BLIND' in self.game.rules: self.game.makeMaps()
		self.game.mailPress(None, ['All!'],
			"The abandoned %s has been taken over in game '%s'.\n" %
			(self.game.anglify(self.name), self.game.name) +
			('', 'The deadline for orders is now %s.\n' %
			self.game.timeFormat())[not self.game.avail],
			subject = 'Diplomacy position taken over')
	#	----------------------------------------------------------------------
	def dummy(self):
		if self.isResigned(): self.player[0] = 'DUMMY'
		else:
			when = self.game.phaseAbbr()
			if self.player[1:2] != [when]:
				if when[0] == '?': when = self.game.outcome[0]
				if self.player and self.address:
					try:
						player = self.player[0].split('|')
						player[1] = self.address[0]
						self.player[0] = '|'.join(player)
					except: pass
				self.player[:0] = [when]
			else: del self.player[0]
			self.player[:0] = ['DUMMY']
		try: self.game.avail.remove([x for x in self.game.avail
			if x.startswith(self.name)][0])
		except: pass
		if not self.game.avail:
			self.game.changeStatus('active')
			self.game.setDeadline()
		self.password = None
		self.game.save()
		if 'BLIND' in self.game.rules: self.game.makeMaps()
		self.game.mailPress(None, ['All!'],
			"%s has been dummied in game '%s'.\n" %
			(self.game.anglify(self.name), self.game.name) +
			('', 'The deadline for orders is now %s.\n' %
			self.game.timeFormat())[not self.game.avail],
			subject = 'Diplomacy position dummied')
	#	----------------------------------------------------------------------
	def isResigned(self):
		return self.player[:1] == ['RESIGNED']
	#	----------------------------------------------------------------------
	def isDummy(self):
		return self.player[:1] == ['DUMMY']
	#	----------------------------------------------------------------------
	def isCD(self, after = 0):
		#	-----------------------------------
		#	Set after to 1 to reveal what will happen after the grace expires.
		#	A power is CD...
		#	if	a CIVIL_DISORDER rule is on
		#		and the player has not RESIGNED
		#		and the deadline has passed,
		#	or	it is an unCONTROLled DUMMY
		#		and the CD_DUMMIES rule is on,
		#	or	it is an CONTROLled DUMMY
		#		and the CD_DUMMIES rule is on
		#		and the grace period has expired.
		#	-----------------------------------
		game = self.game
		return not self.type and self.player and (
			self.isDummy() and (
				not self.ceo and 'CD_DUMMIES' in game.rules or (
					after or game.deadline <= game.Time() and (
						not self.ceo or game.graceExpired()
					)
				) and (
					self.ceo and 'CD_DUMMIES' in game.rules or
					{'M': 'CD_SUPPORTS', 'R': 'CD_RETREATS', 'A': 'CD_BUILDS'}
					.get(game.phaseType) in game.rules
				)
			) or
			not self.isResigned() and (
				after or game.deadline <= game.Time() and game.graceExpired()
			) and
			'CIVIL_DISORDER' in game.rules and
			{'M': 'CD_SUPPORTS', 'R': 'CD_RETREATS', 'A': 'CD_BUILDS'}
			.get(game.phaseType) in game.rules
		)
	#	----------------------------------------------------------------------
	def isValidPassword(self, password):
		#	-------------------------------------------------------------------
		#	If power is run by controller, password is in the controller's data
		#	-------------------------------------------------------------------
		if self.ceo:
			ceo = [x for x in self.powers if x.name == power.ceo[0]][0]
			return ceo.isValidPassword(password)
		#	---------------------------
		#	Determine password validity
		#	---------------------------
		password = password.upper()
		if (self.password and password == self.password.upper()
			or password == self.game.password.upper()): return 1
		#	----------------------------------------
		#	Check against omniscient power passwords
		#	----------------------------------------
		if self.name == 'MASTER': return
		if [1 for x in self.game.powers if x.omniscient
			and x.password and password == x.password.upper()]: return 2
	#	----------------------------------------------------------------------
	def generatePassword(self):
		random.seed()
		return ''.join(random.sample(string.lowercase + string.digits, 6))
	#	----------------------------------------------------------------------
	def removeBlindMaps(self):
		for suffix in ('.ps', '.pdf', '.gif', '_.gif'):
			try: os.unlink(host.gameMapDir + '/' + self.game.name + '.' +
				(self.abbrev or 'O') +
				`hash((self.password or self.game.password) + self.name)` +
				suffix)
			except: pass
	#	----------------------------------------------------------------------
	def movesSubmitted(self):
		#	Each variant had pretty much better override this guy!  :-)
		return False
	#	----------------------------------------------------------------------

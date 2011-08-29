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
		if self.homes is not None: text += '\nINHABITS ' + ' '.join(self.homes)
		if self.centers: text += '\nOWNS ' + ' '.join(self.centers)
		if self.sees: text += '\nSEES ' + ' '.join(self.sees)
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
			address = password = abbrev = vote = None
			omniscient = 0
			player, msg = [], []
		#	-----------------------------------
		#	Initialize the transient parameters
		#	-----------------------------------
		if includeFlags & 4:
			wait = balance = homes = None
			held = adjusted = goner = 0
			centers, units, adjust, ceo = [], [], [], []
			retreats, funds, sees = {}, {}, []
		vars(self).update(locals())
	#	----------------------------------------------------------------------
	def compare(self, other):
		return cmp(self.type, other.type) or cmp(self.name, other.name)
	#	----------------------------------------------------------------------
	def initialize(self, game):
		self.game = game
		if self.homes is None:
			self.homes = game.map.homes.get(self.name, self.type and None or [])
		if self.type: return
		if 'MOBILIZE' in game.rules: self.centers = ['SC!']
		elif 'BLANK_BOARD' in game.rules:
			if not self.centers:
				self.centers = game.map.centers.get(self.name, [])
				self.units = self.units or [x for x in game.map.units.get(self.name, []) if x[2:5] not in self.centers]
		else: 
			self.centers = self.centers or game.map.centers.get(self.name, [])
			self.units = self.units or game.map.units.get(self.name, [])
	#	----------------------------------------------------------------------
	def resign(self, gm_resign = 0):
		for num, power in enumerate(self.game.powers):
			if power.name == self.name: break
		if (self.game.status[1] in ('forming', 'active', 'waiting')
		and self.type != 'MONITOR'):  # maybe should be "if self.centers"?
			#	Tell at least the GM about the resignation
			self.game.openMail('Diplomacy resignation notice',
				mailTo = self.game.master[1], mailAs = host.dpjudge)
			if gm_resign == 0:
				self.game.mail.write("'%s' has resigned from game '%s'.\n" \
					"\n(This notice is sent ONLY to the GameMaster.)" %
					(self.game.anglify(self.name), self.game.name))
			elif gm_resign == 1:
				self.game.mail.write("You have resigned '%s' from game '%s'.\n"
					'\n(This notice is sent ONLY to the game Master.)' %
					(self.game.anglify(self.name), self.game.name))
			self.game.mail.close()
		if self.type: del self.game.powers[num]
		else:
			if (self.game.status[1] in ('active', 'waiting')
			and (self.units or self.centers)):
				self.game.avail += ['%s-(%s)' % (self.name,
					('%d/%d' % (len(self.units), len(self.centers)),
					'?/?')['BLIND' in self.game.rules])]
				self.game.delay = None
				self.game.changeStatus('waiting')
			when = self.game.phaseAbbr()
			if self.player[1:2] != [when]:
				if when[0] == '?': when = self.game.outcome[0]
				self.player[:0] = [when]
			else: del self.player[0]
			if self.player: self.player[:0] = ['RESIGNED']
			if 'BLIND' in self.game.rules: self.removeBlindMaps()
			self.password = None
			if not self.isDummy() and self.address:
				self.message, self.pressSent = [], 1
				self.game.openMail('Diplomacy resignation notice', 
					mailTo = ','.join(self.address), mailAs = host.dpjudge)
				if gm_resign == 0: self.game.mail.write("You have resigned "
					"as '%s' from game '%s'" % (self.name , self.game.name))
				elif gm_resign == 1: self.game.mail.write(
					"The MASTER has resigned you as '%s' from game '%s'" %
					(self.game.anglify(self.name), self.game.name))
				self.game.mail.close()
			self.message, self.pressSent = [], 1
			if gm_resign == 0: self.game.mailPress(None, ['All!'],
				"%s has resigned from game '%s'" %
				(self.game.anglify(self.name), self.game.name) +
				('', '\nThe deadline for orders is now %s.\n' %
				self.game.timeFormat())[not self.game.avail],
				subject = 'Diplomacy resignation notice')
			elif gm_resign == 1: self.game.mailPress(None, ['All!'],
				"The MASTER has resigned %s from game '%s'" %
				(self.name, self.game.name) +
				('', '\nThe deadline for orders is now %s.\n' %
				self.game.timeFormat())[not self.game.avail],
				subject = 'Diplomacy resignation notice')
		self.game.save()
	#	----------------------------------------------------------------------
	def removeBlindMaps(self):
		for suffix in ('.ps', '.pdf', '.gif', '_.gif'):
			try: os.unlink(host.dpjudgeDir + '/maps/' + self.game.name + '.' +
				(self.abbrev or 'O') +
				`hash((self.password or self.game.password) + self.name)` +
				suffix)
			except: pass
	#	----------------------------------------------------------------------
	def dummy(self):
		if self.isResigned(): self.player[0] = 'DUMMY'
		else:
			when = self.game.phaseAbbr()
			if when[0] == '?': when = self.game.outcome[0]
			self.player[:0] = [when]
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
	def isCD(self):
		#	-----------------------------------
		#	A power is CD...
		#	if	a CIVIL_DISORDER rule is on
		#		and the player has not RESIGNED
		#		and the deadline has passed,
		#	or	it is an unCONTROLled DUMMY
		#		and the CD_DUMMIES rule is on.
		#	-----------------------------------
		game = self.game
		return not self.type and self.player and (
			self.isDummy() and not self.ceo and (
				'CD_DUMMIES' in game.rules or
				game.deadline <= game.Time() and
				{'M': 'CD_SUPPORTS', 'R': 'CD_RETREATS', 'A': 'CD_BUILDS'}
				.get(game.phaseType) in game.rules
			) or
			not self.isResigned() and
			game.deadline <= game.Time() and game.graceExpired() and
			'CIVIL_DISORDER' in game.rules and
			{'M': 'CD_SUPPORTS', 'R': 'CD_RETREATS', 'A': 'CD_BUILDS'}
			.get(game.phaseType) in game.rules
		)
	#	----------------------------------------------------------------------
	def movesSubmitted(self):
		#	Each variant had pretty much better override this guy!  :-)
		return False
	#	----------------------------------------------------------------------

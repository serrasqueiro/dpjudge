import host

class Power:
	#	----------------------------------------------------------------------
	def __init__(self, game, name, type = None):
		address = wait = password = abbrev = balance = vote = None
		held = adjusted = goner = home = omniscient = 0
		player, msg, centers, units, adjust, ceo = [], [], [], [], [], []
		retreats, funds = {}, {}
		vars(self).update(locals())
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
		if self.home != 0: text += '\nHOME ' + ' '.join(self.home)
		if self.centers: text += '\nOWNS ' + ' '.join(self.centers)
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
	def compare(self, other):
		return cmp(self.type, other.type) or cmp(self.name, other.name)
	#	----------------------------------------------------------------------
	def initialize(self, game):
		self.game = game
		if self.type: return
		self.centers, self.units = game.map.centers.get(self.name, []), []
		if 'MOBILIZE' in game.rules: self.centers = ['SC!']
		else: self.units = game.map.units.get(self.name, [])
		if 'BLANK_BOARD' in game.rules:
			self.units = [x for x in self.units if x[2:5] not in self.centers]
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
			if self.player[1:2] !=[when]:
				if when[0] == '?': when = self.game.outcome[0]
				self.player[:0] = [when]
			else: del self.player[0]
			if self.player: self.player[:0] = ['RESIGNED']
			if 'BLIND' in self.game.rules: self.removeBlindMaps(self.password)
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
	def removeBlindMaps(self, pwd):
		for suffix in ('.ps', '.pdf', '.gif', '_.gif'):
			try: os.unlink(host.dpjudgeDir + '/maps/' +
				self.game.name + pwd + suffix)
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
		return not self.type and self.player and (not self.isResigned()
		and game.deadline <= game.Time()
		and ((('CIVIL_DISORDER' in game.rules or 'CD_DUMMIES' not in game.rules
			and {'M': 'CD_SUPPORTS', 'R': 'CD_RETREATS', 'A': 'CD_BUILDS'}
			.get(game.phaseType) in game.rules) and game.graceExpired())
		or	self.isDummy() and 'CD_DUMMIES' in game.rules and not self.ceo))
	#	----------------------------------------------------------------------
	def movesSubmitted(self):
		#	Each variant had pretty much better override this guy!  :-)
		return False
	#	----------------------------------------------------------------------

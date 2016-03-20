import random, string, os

import host

from Time import Time

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
		if self.cd: text += '\nCD'
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
		#		1: include orders
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
			balance = homes = None
			centers, units, ceo = [], [], []
			retreats, funds, sees, hides = {}, {}, [], []
		#	---------------------------------------
		#	Initialize the order-related parameters
		#	---------------------------------------
		if includeFlags & 5:
			wait = vote = None
			cd = 0
			adjust = []
		held = goner = 0
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
		if 'MOBILIZE' in game.rules:
			self.centers = ['SC!'] * ('IMMOBILE_DUMMIES' in game.rules and
				self.isDummy() and len(game.map.homes.get(self.name, [])) or 1)
		elif 'BLANK_BOARD' in game.rules:
			if not self.centers:
				self.centers = game.map.centers.get(self.name, [])
				self.units = self.units or [x for x in
					game.map.units.get(self.name, []) if x[2:5] not in
					self.centers]
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
			and not self.isEliminated()):
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
			if not self.isEliminated():
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
			elif revived:
				return 'Cannot revive a power never assigned to a player.'
			else: self.player = []
		if self.player and (not dppd or
			self.player[0].split('|')[0] == dppd.split('|')[0]): revived = 1
		else: self.player[:0] = [dppd, phase]
		if self.isDummy():
			self.address = self.password = None
		else:
			self.address = [self.player[0].split('|')[1]]
			if email and email != self.address[0]:
				self.address[:0] = [email]
			self.password = password
			self.game.openMail('Diplomacy takeover notice',
				mailTo = self.name, mailAs = host.dpjudge)
			self.game.mail.write(
				"You are %s %s in game '%s'.\n" %
				(('now', 'again')[revived],
				self.game.anglify(self.name), self.game.name) +
				("Your password is '%s'.\n" % password) *
				(generated or byMaster) + "Welcome %sto the %s.\n" %
				('back ' * revived, host.dpjudgeNick))
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
	def controller(self):
		if not self.ceo or self.ceo[0] == 'MASTER': return None
		for power in self.game.powers:
			if power.name == self.ceo[0]: return power
		return None
	#	----------------------------------------------------------------------
	def controls(self, power):
		return (power is self or power.controller() is self or
			self.name == 'MASTER')
	#	----------------------------------------------------------------------
	def vassals(self, public = False, all = False, indirect = False):
		return [x for x in self.game.powers if
			(x.ceo[:1] == [self.name] or indirect and self.name == 'MASTER')
			and (all or not x.isEliminated(public))]
	#	----------------------------------------------------------------------
	def isResigned(self):
		return self.player[:1] == ['RESIGNED']
	#	----------------------------------------------------------------------
	def isDummy(self, public = False):
		return self.player[:1] == ['DUMMY'] and not (
			public and 'HIDE_DUMMIES' in self.game.rules)
	#	----------------------------------------------------------------------
	def isEliminated(self, public = False, personal = False):
		return not (self.units or self.centers or self.retreats or
			(public and 'BLIND' in self.game.rules) or
			(not personal and self.vassals()))
	#	----------------------------------------------------------------------
	def isCD(self, after = 0):
		#	-----------------------------------
		#	Set after to 1 to reveal what will happen after the grace expires,
		#   or to -1 to know the status before any deadline expires.
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
					after > 0 or 'NO_DEADLINE' not in game.rules and
					game.deadline and game.deadline <= game.getTime() and (
						not self.ceo or game.graceExpired()
					)
				) and (
					self.ceo and 'CD_DUMMIES' in game.rules or
					'CIVIL_DISORDER' in game.rules
				)
			) or
			not self.isResigned() and (
				after > 0 or 'NO_DEADLINE' not in game.rules and
				game.deadline and game.deadline <= game.getTime() and
				game.graceExpired()
			) and
			'CIVIL_DISORDER' in game.rules
		)
	#	----------------------------------------------------------------------
	def isValidPassword(self, password):
		#	-------------------------------------------------------------------
		#	If power is run by controller, password is in the controller's data
		#	-------------------------------------------------------------------
		ceo = self.controller()
		if ceo: return ceo.isValidPassword(password)
		#	---------------------------
		#	Determine password validity
		#	---------------------------
		if not password: return 0
		password = password.upper()
		if password == host.judgePassword.upper(): return 5
		if password == self.game.password.upper(): return 4
		if self.password and password == self.password.upper(): return 3
		#	----------------------------------------
		#	Check against omniscient power passwords
		#	----------------------------------------
		if self.name == 'MASTER': return 0
		if [1 for x in self.game.powers if x.omniscient
			and x.password and password == x.password.upper()]: return 2
		return 0
	#	----------------------------------------------------------------------
	def isValidUserId(self, userId):
		#	-------------------------------------------------------------------
		#	If power is run by controller, userId is in the controller's data
		#	-------------------------------------------------------------------
		ceo = self.controller()
		if ceo: return ceo.isValidUserId(userId)
		#	---------------------------
		#	Determine userId validity
		#	---------------------------
		if userId < 0: return 0
		id = '#' + str(userId)
		if self.game.master and id == self.game.master[0]: return 4
		if self.player and id == self.player[0].split('|')[0]: return 3
		#	----------------------------------------
		#	Check against omniscient power passwords
		#	----------------------------------------
		if self.name == 'MASTER': return 0
		if [1 for x in self.game.powers if x.omniscient
			and x.player and id == x.player[0].split('|')[0]]: return 2
		return 0
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
		for vassal in self.vassals(all = True):
			vassal.removeBlindMaps()
	#	----------------------------------------------------------------------
	def movesSubmitted(self):
		#	Each variant had pretty much better override this guy!  :-)
		return False
	#	----------------------------------------------------------------------
	def canVote(self):
		return not self.ceo and (self.centers or
			[1 for x in self.vassals() if x.centers])
	#	----------------------------------------------------------------------
	def visible(self, unit, order = None):
		#	--------------------------------------------------------------
		#	This function returns a dictionary listing a number for each
		#	of the powers.  The number is a bitmap, with the following
		#	meaning.  If the bitvalue 1 is set, this means the power could
		#	"see" the unit in question BEFORE the move.  If the bitvalue 2
		#	is set, this means the power could "see" (AFTER the move) the
		#	location where the unit in question began the turn.  If the
		#	bitvalue 4 is set, the power could "see" (BEFORE the move) the
		#	location where the unit in question ended the turn, and if the
		#	bitvalue 8 is set, the power could "see" (AFTER the move) the
		#	location where the unit in question ended the turn.  If "unit"
		#	is simply a center location, determines center visibility.
		#	--------------------------------------------------------------
		game = self.game
		if 'command' not in vars(game): game.command = {}
		shows, order = {'MASTER': 15}, order or game.command.get(unit, 'H')
		old = new = unit.split()[-1][:3]
		dislodging = 0
		if order[0] == '-' and (game.phaseType != 'M'
		or not game.result.get(unit)):
			new = order.split()[-1][:3]
			if game.phaseType == 'M':
				#	-------------------------------------------------------
				#	If this unit is dislodging another unit (which might be
				#	of the same power), we'll pretend that any unit able to
				#	see the destination after the move can also see it
				#	before the move. This way the unit will always be
				#	arriving, allowing to depict both the dislodging and
				#	dislodged units.
				#	-------------------------------------------------------
				dislodging = [x for p in game.powers for x in p.units
					if x[2:5] == new[:3]
					and 'dislodged' in game.result.get(x, [])] and 1 or 0
		rules = game.rules
		for seer in game.powers:
			shows[seer.name] = 15 * bool(self is seer or seer.omniscient
				or seer is self.controller())
			if (shows[seer.name]
			or ('SEE_NO_SCS', 'SEE_NO_UNITS')[' ' in unit] in rules): continue
			#	--------------------------------------------------
			#	Get the list of the "seer"s sighted units (if any)
			#	with their positions before and after any movement
			#	--------------------------------------------------
			vassals = [seer] + seer.vassals()
			units = [y for x in vassals for y in x.units]
			adjusts = [y for x in vassals for y in x.adjust]
			retreats = [y for x in vassals for y in x.retreats.keys()]
			if 'NO_UNITS_SEE' in rules: before = after = []
			else:
				spotters = 'AF'
				if ' ' in unit:
					if 'UNITS_SEE_SAME' in rules: spotters = unit[0]
					elif 'UNITS_SEE_OTHER' in rules:
						spotters = spotters.replace(unit[0], '')
				before = after = [x[2:] for x in units + retreats
					if x[0] in spotters]
				if game.phaseType == 'M':
					after = []
					for his in units:
						if his[0] not in spotters: continue
						if (game.command.get(his, 'H')[0] != '-'
							or game.result.get(his)): after += [his[2:]]
						else:
							after += [game.command[his].split()[-1]]
				elif game.phaseType == 'R':
					if 'popped' not in vars(game): game.popped = []
					if adjusts:
						after = [x for x in before if x not in
							[y[2:] for y in retreats]]
						for adjusted in adjusts:
							word = adjusted.split()
							if word[1][0] not in spotters: continue
							if word[3][0] == '-' and word[2] not in game.popped:
								after += [word[-1]]
					else:
						after = [x for x in before if x not in
							[y[2:] for y in game.popped if y in retreats]]
				elif game.phaseType == 'A':
					after = [z for z in before if z not in
						[x[1] for x in [y.split()[1:] for y in adjusts]
						if len(x) > 1]] + [x[1] for x in
						[y.split()[1:] for y in adjusts if y[0] == 'B']
						if len(x) > 1 and x[0][0] in spotters]
			#	------------------------------------------------
			#	Get the list of the "seer"s sighted scs (if any)
			#	------------------------------------------------
			if 'NO_SCS_SEE' in rules: pass
			elif ('OWN_SCS_SEE' in rules
			or game.map.homeYears and not [x for x in game.powers if x.homes]):
				#	------------------------------------
				#	The seer's owned centers are sighted
				#	------------------------------------
				scs = [y for x in vassals for y in x.centers]
				if 'SC!' in scs:
					scs = [x[8:11] for x in adjusts if x[:5] == 'BUILD']
				after += scs
				if 'OWN_SCS_SEE' in rules:
					if 'lost' in vars(game):
						for what, who in game.lost.items():
							if what in scs and who not in vassals:
								scs.remove(what)
							elif what not in scs and who in vassals:
								scs.append(what)
					before += scs
			else:
				#	-----------------------------------
				#	The seer's home centers are sighted
				#	-----------------------------------
				scs = [y for x in vassals for y in x.homes or []]
				#	----------------------------------------------------------
				#	Also add locations where the power had units at game start
				#	(helping void variant games, where units start on non-SCs)
				#	----------------------------------------------------------
				if 'BLANK_BOARD' not in rules and 'MOBILIZE' not in rules:
					scs += [y[2:] for x in vassals
						for y in game.map.units.get(x.name, [])]
				after += scs
				before += scs
			#	-------------------------------------------------
			#	When it comes to visibility, we can ignore coasts
			#	-------------------------------------------------
			before = set([x[:3] for x in before])
			after = set([x[:3] for x in after])
			both = before & after
			before, after = before - both, after - both
			old, new = old[:3], new[:3]
			places = (' ' in unit and unit in self.hides and
				[(new, 4)] or old == new and [(old, 5)] or [(old, 1), (new, 4)])
			#	-------------------------------------------------------
			#	Set the bitmap for this "seer" if any unit or sc in the
			#	lists (before, after, scs) can see the site in question
			#	-------------------------------------------------------
			for bit in [b * m for (y, m) in places for (b, l) in [(1, before),
				(2 + ((m & 4) and dislodging), after), (3, both)]
				for x in l if x == y or game.abuts('?', y, 'S', x)]:
				shows[seer.name] |= bit
		return shows
	#	----------------------------------------------------------------------
	def showLines(self, unit, notes = [], line = None):
		game = self.game
		list, lost, found, gone, came, all = [], [], [], [], [], []
		#list += ['# Show ' + unit]
		if game.phaseType == 'M':
			if game.command.get(unit, 'H')[0] != '-' or game.result[unit]:
				there = unit
			else: there = unit[:2] + game.command[unit].split()[-1]
			cmd = None
		else:
			word = unit.split()
			unit = ' '.join(word[1:3])
			if len(word) > 4 and word[2] not in notes:
				cmd, there = ' '.join(word[3:]), unit[:2] + word[-1]
			elif unit == 'WAIVED' or (len(word) > 3 and word[-1] == 'HIDDEN'):
				return line and ['SHOW MASTER ' + ' '.join([x.name
					for x in game.powers if x == self or x == self.controller()
					or x.omniscient]), line] or []
			else: cmd, there = word[0][0], unit
		c = not cmd and 'M' or len(cmd) == 1 and cmd or 'M'
		for who, how in self.visible(unit, cmd).items():
			if how & 8:
				if how & 1: all += [who]
				elif how & 4: came.append(who)
				elif game.phaseType == 'A':
					if c in 'BR': all += [who]
					if c != 'B': found.append(who)
				elif c not in 'RD': found.append(who)
			elif how & 1:
				if how & 2: gone.append(who)
				else:
					if c not in 'RD': lost.append(who)
					if c in 'BRD': all += [who]
		if game.phaseType == 'M':
			fmt = '%s %s %s.' + '  (*dislodged*)' * ('dislodged' in notes)
		else:
			fmt = '%-11s %s %s.'
		for who, what in ((found, 'FOUND'), (came, 'ARRIVES')):
			if not who: continue
			list += ['SHOW ' + ' '.join(who),
				fmt % (game.anglify(self.name) + ':',
				game.anglify((unit, there)[what[0] in 'FA'], self), what)]
		if line: list += ['SHOW ' + ' '.join(all), line]
		for who, what in ((gone, 'DEPARTS'), (lost, 'LOST')):
			if not who: continue
			list += ['SHOW ' + ' '.join(who),
				fmt % (game.anglify(self.name) + ':',
				game.anglify((unit, there)[what[0] in 'FA'], self), what)]
		return list
	#	----------------------------------------------------------------------

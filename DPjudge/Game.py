import os, random, socket, textwrap, urllib, glob, re, shutil
from codecs import open

import host

from Status import Status
from Power import Power
from Mail import Mail
from View import View
from Time import Time, TimeZone

class Game:
	#	----------------------------------------------------------------------
	def __init__(self, name = '', fileName = 'status'):
		if 'variant' not in vars(self): variant = ''
		if 'powerType' not in vars(self): powerType = Power
		if 'view' not in vars(self): view = View(self)
		if 'victory' not in vars(self): victory = None
		vars(self).update(locals())
		if name: self.loadStatus(fileName)
		else: self.reinit()
	#	----------------------------------------------------------------------
	def __repr__(self):
		text = ('GAME ' + self.name + (self.await == 2 and '\nWAIT '
				or self.await and '\nAWAIT '
				or self.skip and '\nSKIP ' or '\nPHASE ') + self.phase)
		if self.judge: text += '\nJUDGE ' + self.judge
		if self.map: text += '\n%s ' % (
			['MAP', 'TRIAL'][self.map.trial]) + self.map.name
		if len(self.morphs) > 3 or [1 for x in self.morphs if not x.strip()]:
			text += '\nMORPH'
			for morph in self.morphs: text += '\n' + morph
			text += '\nEND MORPH'
		else:
			for morph in self.morphs: text += '\nMORPH ' + morph
		if self.gm.player: text += '\nMASTER ' + ' '.join(self.gm.player)
		if self.gm.address: text += '\nADDRESS ' + ' '.join(self.gm.address)
		if self.gm.password: text += '\nPASSWORD ' + self.gm.password
		tester = self.tester.rstrip('@')
		if tester and tester[-1] == '!':
			text += '\nTESTER ' + tester[:-1]
		if self.groups: text += '\nGROUPS ' + ('|').join(self.groups)
		if self.start: text += '\nSTART ' + self.start
		if self.end: text += '\nFINISH ' + self.end
		if self.outcome: text += '\nRESULT ' + ' '.join(self.outcome)
		if self.avail and self.phase != 'FORMING':
			text += '\nNEED ' + ' '.join(self.avail)
		if len(self.desc) > 3 or [1 for x in self.desc if not x.strip()]:
			text += '\nDESC'
			for each in self.desc: text += '\n' + each
			text += '\nEND DESC'
		else:
			for each in self.desc: text += '\nDESC ' + each
		if len(self.origin) > 3 or [1 for x in self.origin if not x.strip()]:
			text += '\nNAME'
			for each in self.origin: text += '\n' + each
			text += '\nEND NAME'
		else:
			for each in self.origin: text += '\nNAME ' + each
		if self.private: text += '\nPRIVATE ' + self.private
		if self.rotate: text += '\nROTATE ' + ' '.join(self.rotate)
		for each in self.rules:
			if each not in self.metaRules: text += '\nRULE ' + each
		for each in self.norules: text += '\nRULE !' + each
		for each in self.playerTypes: text += '\nALLOW ' + each
		if self.proposal: text += '\nPROPOSAL ' + ' '.join(self.proposal)
		if self.deadline: text += '\nDEADLINE ' + self.deadline
		if self.zone: text += '\nZONE %s' % self.zone
		if self.delay: text += '\nDELAY %d' % self.delay
		if self.timing:
			text += '\nTIMING ' + ' '.join(map(' '.join, self.timing.items()))
		for terrain, changes in self.terrain.items():
			for site, abuts in changes.items():
				text += '\n%s %s ' % (terrain, site) + ' '.join(abuts)
		#	---------------
		#	Legacy keywords
		#	---------------
		if self.judge: text += '\nJUDGE ' + self.judge
		if self.signon: text += '\nSIGNON ' + self.signon
		return '\n'.join([x for x in text.split('\n')
					if x not in self.directives]).encode('latin-1') + '\n'
	#	----------------------------------------------------------------------
	def reinit(self, includeFlags = 6):
		#	---------------------------------------------
		#	Reinitializes the game data.
		#   Relevant bit values for includeFlags:
		#		2: include persistent data
		#		4: include transient data
		#	---------------------------------------------

		#	------------------------------------
		#	Initialize the persistent parameters
		#	------------------------------------
		if includeFlags & 2:
			if includeFlags & 4:
				powers = []
				gm = Power(self, 'MASTER')
				gm.omniscient = 3
				jk = Power(self, 'JUDGEKEEPER')
				jk.omniscient = 4
				jk.password = host.judgePassword
				jk.address = host.judgekeepers
			playerTypes, desc, master, norules = [], [], [], []
			rotate, directives, origin = [], [], []
			avail, morphs = [], []
			try: metaRules = self.rules[:]
			except: metaRules, rules = [], []
			tester = host.tester or ''
			groups = password = start = ''
			map = private = zone = judge = signon = None
			timing, terrain, status = {}, {}, Status().dict.get(self.name, [])
			#	------------------------------------------------------
			#	When we run out of directory slots, the line below can
			#	be changed to '/'.join(host.gameDir, name[0], name)
			#	------------------------------------------------------
			gameDir = host.gameDir + '/' + self.name
		#	-----------------------------------
		#	Initialize the transient parameters
		#	-----------------------------------
		if includeFlags & 4:
			outcome, error, state = [], [], {}
			end = phase = ''
			mail = proposal = season = year = phaseType = mode = None
			preview = deadline = delay = processed = win = await = skip = None
			modeRequiresEnd, includeOwnership = None, -1

		vars(self).update(locals())
		for power in [self.gm] + self.powers:
			power.reinit(includeFlags)
		self.gm.omniscient = 3
	#	----------------------------------------------------------------------
	def unitOwner(self, unit, coastRequired = 1):
		for owner in self.powers:
			if unit in owner.units or (not (coastRequired or '/' in unit)
			and [1 for x in owner.units if not x.find(unit)]): return owner
	#	----------------------------------------------------------------------
	def convoyer(self, army, thru):
		areaType = self.map.areatype(thru[1])
		return (((areaType == 'WATER') == army or areaType == 'PORT'
			or areaType == 'COAST' and 'COASTAL_CONVOY' in self.rules)
			and (self.unitOwner('AF'[army] + ' ' + thru[army], not army)
			or 'FICTIONAL_OK' in self.rules))
	#	----------------------------------------------------------------------
	def canConvoy(self, unit, start, end, via = 0, helper = 0):
		army, pools, check = unit != 'F', [helper], self.map.abutList(start)
		if via:
			if via in check: check = [via]
			elif not army:
				check = [x for x in check if x[:3].upper() == via[:3]] or check
		for loc in [x.upper() for x in check if not (army and x.islower())]:
			if loc in pools: continue
			thru = loc[:3], loc
			if helper and thru[not army] in (end, end[:3]): return 1
			if not self.convoyer(army, thru): continue
			pool, size, can = [thru[army]], 0, 0
			while size < len(pool):
				for next in self.map.abutList(pool[size]):
					if not army: next = next[:3]
					elif next.islower(): continue
					next = next.upper()
					thru = next[:3], next
					if thru[army] in pools + pool: continue
					can |= thru[not army] in (end, end[:3])
					if can and (not via or via in pool
					and 'CONVOY_BACK' in self.rules): return 1
					if self.convoyer(army, thru): pool += [thru[army]]
				size += 1
			if via in pool:
				for omit in can * pool:
					if not (self.canConvoy(unit, via, start, 0, omit)
					or self.canConvoy(unit, via, end, 0, omit)): return
				return can
			pools += pool
		return (unit == '?' and 'PORTAGE_CONVOY' in self.rules
			and self.canConvoy('F', start, end, via, helper))
	#	----------------------------------------------------------------------
	def validOrder(self, power, unit, order, report = 1):
		"""
		This function has three return values:
			None	- the order is NOT valid at all
			-1		- it is NOT valid BUT it does not get reported because it
					may be used to signal support
			0		- it is valid BUT some unit mentioned does not exist
			1		- it is completely valid
		"""
		if not order: return
		word, owner, rules = order.split(), self.unitOwner(unit), self.rules
		#	--------------------------------------------------
		#	Strip any final punctuation, as is common in DPeye
		#	syntax to denote results. A '?' is also used for
		#	invalid orders with the SIGNAL_SUPPORT rule.
		#	--------------------------------------------------
		if len(word[-1]) == 1 and not word[-1].isalpha(): word = word[:-1]
		if not word: return
		error = ([], self.error)[report]
		map, status, signal = self.map, owner != None, 'SIGNAL_SUPPORT' in rules
		unitType, unitLoc, orderType = unit[0], unit[2:], word[0]
		#	-------------------------------------
		#	Make sure the unit exists or (if the
		#	player is in a game in which he can't
		#	necessarily know) could exist.  Also
		#	make sure any mentioned (supported or
		#	convoyed) unit could exist and could
		#	reach the listed destination.
		#	-------------------------------------
		if not map.isValidUnit(unit):
			return error.append('ORDER TO INVALID UNIT: ' + unit)
		if orderType in ('S', 'C') and word[1:]:
			if word[1] in ('A', 'F'):
				alter, other = word[1:3]
			else:
				alter, other = '?', word[1]
			other = alter + ' ' + other
			if not map.isValidUnit(other, 1):
				return error.append('ORDER INCLUDES INVALID UNIT: ' + other)
			if len(word) == 5 - (alter == '?'):
				if signal and orderType == 'S': alter = '?'
				other = alter + ' ' + word[-1]
				if not map.isValidUnit(other, 1):
					return error.append('ORDER INCLUDES INVALID UNIT ' +
						'DESTINATION ' + other)
		if 'FICTIONAL_OK' in rules: pass
		elif not status:
			return error.append('ORDER TO NON-EXISTENT UNIT: ' + unit)
		elif (power is not owner and 'PROXY_OK' not in rules
		and 'ORDER_ANY' not in rules):
			return error.append('ORDER TO FOREIGN UNIT: ' + unit)
		#	-----------------------------------------------------------------
		#	Validate that anything in a SHUT location is only ordered to HOLD
		#	-----------------------------------------------------------------
		if map.areatype(unitLoc) == 'SHUT' and orderType != 'H':
			if signal: status = -1
			else: return error.append('UNIT MAY ONLY BE ORDERED TO HOLD: ' + unit)
		#	----------------------------------
		#	Validate support and convoy orders
		#	----------------------------------
		if (orderType == 'C' and 'PORTAGE_CONVOY' not in rules
		and (unitType != 'F' or (map.areatype(unitLoc) not in ('WATER', 'PORT')
		and 'COASTAL_CONVOY' not in rules))): return error.append(
			'CONVOY ORDER FOR IMPROPER UNIT: %s ' % unit + order)
		if orderType in ('C', 'S'):
			#	-------------------------------------------
			#	Add the unit type (or '?') if not specified
			#	Note that the unit type is NOT added to the
			#	actual order -- just used during checking.
			#	-------------------------------------------
			orderText = ('SUPPORT', 'CONVOY')[orderType == 'C']
			if len(word) > 1 and word[1] not in ('A', 'F'):
				terrain = map.areatype(word[1])
				if orderType == 'C': word[1:1] = ['AF'[unitType == 'A']]
				elif terrain == 'WATER': word[1:1] = ['F']
				elif terrain == 'LAND': word[1:1] = ['A']
				elif terrain:
					it = [x for x in 'AF' if self.unitOwner(x + ' ' + word[1])]
					if 'FICTIONAL_OK' in rules: word[1:1] = ['?']
					elif it: word[1:1] = it
					else: return error.append(
						'CANNOT %s NON-EXISTENT UNIT: %s ' %
						(orderText, unit) + order)
				else: return error.append(
					'INVALID %s RECIPIENT: %s ' % (orderText, unit) + order)
			#	-------------------------------------
			#	Make sure we have enough to work with
			#	-------------------------------------
			if len(word) < 3: return error.append(
				'BAD %s ORDER: %s ' % (orderText, unit) + order)
			#	----------------------------
			#	Check that the recipient of
			#	the support or convoy exists
			#	----------------------------
			rcvr, dest = ' '.join(word[1:3]), word[2]
			if not self.unitOwner(rcvr, 0):
				if 'FICTIONAL_OK' not in rules: return error.append(
					orderText + ' RECIPIENT DOES NOT EXIST: %s ' % unit + order)
				if status > 0: status = 0
			#	-------------------------------
			#	Check that the recipient is not
			#	the same unit as the supporter.
			#	-------------------------------
			if unitLoc == dest: return error.append(
				'UNIT CANNOT SUPPORT ITSELF: %s ' % unit + order)
			#	------------------------------------
			#	Only units on coasts can be convoyed
			#	------------------------------------
			if orderType == 'C' and (word[1] != 'AF'[unitType == 'A']
			or map.areatype(dest) not in ('COAST', 'PORT')):
				return error.append(
					'UNIT CANNOT BE CONVOYED: %s ' % unit + order)
			#	---------------------------------------------------------
			#	Handle orders of the form C U xxx - xxx and S U xxx - xxx
			#	---------------------------------------------------------
			if len(word) == 5:
				if word[3] != '-': return error.append(
					'BAD %s ORDER: %s ' % (orderText, unit) + order)
				dest = word[4]
				if '/' in dest: return error.append(
					'COAST CANNOT APPEAR AS %s MOVE DESTINATION: %s ' %
					(orderText, unit) + order)
				if orderType == 'C':
					if not (map.areatype(dest) in ('COAST', 'PORT')
					and map.isValidUnit(word[1] + ' ' + dest, unit[0] < 'F')):
						return error.append(
							'BAD CONVOY DESTINATION: %s ' % unit + order)
				elif (not self.abuts(word[1], word[2], orderType, dest)
				and	 (rcvr[0] == 'F' and 'PORTAGE_CONVOY' not in rules
				or not self.canConvoy(word[1], word[2][:3], dest, 0, unitLoc))):
					if signal: status = -1
					else: return error.append(
						'SUPPORTED UNIT CANNOT REACH DESTINATION: %s ' %
						unit + order)
				#	----------------------------------
				#	Support across an adjacency listed
				#	in Map.abutRules['*'] is invalid.
				#	Ditto for abutRules['~'].
				#	----------------------------------
				elif ((unitLoc, dest) in map.abutRules.get('*', []) +
										 map.abutRules.get('~', [])):
					if signal: status = -1
					else: return error.append(
						'UNIT CANNOT PROVIDE SUPPORT TO DESTINATION: %s ' %
						unit + order)
			#	----------------------------------------------------
			#	Make sure that a convoy order was formatted as above
			#	----------------------------------------------------
			elif orderType == 'C': return error.append(
				'IMPROPER CONVOY ORDER: %s ' % unit + order)
			#	-----------------------------
			#	Make sure a support order was
			#	either as above or as S U xxx
			#	-----------------------------
			elif len(word) != 3 and (len(word) != 4 or word[-1] != 'H'):
				return error.append(
					'IMPROPER SUPPORT ORDER: %s ' % unit + order)
			#	---------------------------------------------------
			#	Make sure the support destination can be reached...
			#	---------------------------------------------------
			if orderType == 'S':
				if (not self.abuts(unitType, unitLoc, orderType, dest)
				or (unitLoc, dest) in map.abutRules.get('*', []) +
									  map.abutRules.get('~', [])):
					if signal: status = -1
					else: return error.append(
						'UNIT CANNOT DELIVER SUPPORT TO DESTINATION: %s ' %
						unit + order)
			#	-----------------------------------------------------
			#	...or that the fleet can perform the described convoy
			#	-----------------------------------------------------
			elif not self.canConvoy(rcvr[0], rcvr[2:5], dest, unitLoc):
				return error.append(
					'IMPOSSIBLE CONVOY ORDER: %s ' % unit + order)
			#	-----------------------------------------------------
			#	Make sure support or convoy is kosher with any LEAGUE
			#	-----------------------------------------------------
			if 'FICTIONAL_OK' not in rules:
				signal = orderType == 'S' and signal
				if not self.checkLeague(owner, unit, order, word,
				orderText, report and not signal):
					if signal: status = -1
					else: return
		#	---------------------
		#	Validate a move order
		#	---------------------
		elif orderType == '-':
			if 'IMMOBILE_DUMMIES' in rules and owner and owner.isDummy():
				return error.append('IMMOBILE UNIT CANNOT MOVE: %s ' %
					unit + order)
			if len(word) & 1:
				return error.append('BAD MOVE ORDER: %s ' % unit + order)
			#	--------------------------------------------------------
			#	Only a convoying army or portaging fleet can give a path
			#	--------------------------------------------------------
			if (len(word) > 2 and unitType != 'A'
			and ('PORTAGE_CONVOY' not in rules
			or map.areatype(unitLoc) not in ('COAST', 'PORT'))):
				return error.append('UNIT CANNOT CONVOY: %s ' % unit + order)
			#	-------------------------------------------
			#	Step through every "- xxx" in the order and
			#	ensure the unit can get there at every step
			#	-------------------------------------------
			src, orderType, visit = unitLoc, 'C-'[len(word) == 2], []
			if (word[-1] == unitLoc
			and (orderType < 'C' or 'CONVOY_BACK' not in self.rules)):
				return error.append('MOVING UNIT MAY NOT RETURN: %s ' %
					unit + order)
			if orderType == 'C':
				if map.areatype(word[-1]) not in ('COAST', 'PORT'):
					return error.append(
						'CONVOYING UNIT MUST REACH COAST: %s ' % unit + order)
				if unitType == 'A' and '/' in word[-1]: return error.append(
					'ARMY CANNOT CONVOY TO SPECIFIC COAST: %s ' % unit + order)
			if [1 for x in range(0, len(word), 2) if word[x] != '-']:
				return error.append('BAD MOVE ORDER: %s ' % unit + order)
			ride = word[1::2]
			for num, to in enumerate(ride):
				if to in visit and 'CONVOY_BACK' not in rules:
					return error.append('CONVOYING UNIT USED TWICE ' +
						'IN SAME CONVOY: %s ' % unit + order)
				visit += [to]
				if (not self.abuts(unitType, src, orderType, to)
				and (len(word) == 2 or unitType == 'A'
					and ('COASTAL_CONVOY' not in rules
						or not self.abuts('F', to, 'S', src))
					or unitType == 'F' and to[:3].upper() not in
						[x[:3].upper() for x in map.abutList(src[:3])])):
					return error.append(
						'UNIT CANNOT MOVE INTO DESTINATION: %s ' % unit + order)
				if num < len(ride) - 1:
					if ((unitType == 'F'
					or 'COASTAL_CONVOY' not in rules) and ((unitType == 'A'
					and map.areatype(to) not in ('WATER', 'PORT'))
					or unitType + map.areatype(to) == 'FWATER')):
						return error.append(
							'BAD CONVOY MOVE ORDER: %s ' % unit + order)
					if ('FICTIONAL_OK' not in rules
					and not self.unitOwner('AF'[unitType == 'A'] + ' ' + to)):
						return error.append(
							'CONVOY THROUGH NON-EXISTENT UNIT: %s ' %
							unit + order)
				#	----------------------------------------
				#	Portaging fleets must finish the turn on
				#	a coastal location listed in upper-case.
				#	----------------------------------------
				elif num and unitType == 'F' and (to not in map.locAbut
				or map.areatype(to) not in ('COAST', 'PORT')):
					return error.append('IMPOSSIBLE CONVOY: %s ' % unit + order)
				src = to
		#	---------------------
		#	Validate a hold order
		#	---------------------
		elif orderType == 'H':
			if len(word) != 1:
				return error.append('INVALID HOLD ORDER: %s ' % unit + order)
		#	----------------------
		#	Validate a proxy order
		#	----------------------
		elif orderType == 'P':
			if 'PROXY_OK' not in rules: return error.append(
				'PROXY ORDER NOT ALLOWED: %s ' % unit + order)
			if len(word) == 1: return error.append(
				'NO PROXY POWER SPECIFIED: %s ' % unit + order)
			if len(word) > 2: return error.append(
				'MORE THAN ONE PROXY POWER SPECIFIED: %s ' % unit + order)
			if word[1] == power.name: return error.append(
				'PROXY TO SELF NOT ALLOWED: %s ' % unit + order)
			proxyTo = [x for x in self.powers if x.name == word[1]]
			if not proxyTo: return error.append(
				'NO SUCH PROXY POWER: %s ' % unit + order)
			proxyTo = proxyTo[0]
			if proxyTo.isDummy(True): return error.append(
				'PROXY TO DUMMY NOT ALLOWED: %s ' % unit + order)
			if proxyTo.isEliminated(True): return error.append(
				'PROXY TO POWER NOT ALLOWED: %s ' % unit + order)
		else: return error.append('UNRECOGNIZED ORDER TYPE: %s ' % unit + order)
		#	--------
		#	All done
		#	--------
		return status
	#	----------------------------------------------------------------------
	def checkLeague(self, owner, unit, order, word, orderText, report):
		#	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
		#	At present, this method is not called during order input
		#	validation for games that use the FICTIONAL_OK rule.
		#	This is to assist Crystal Ball, in which we have no way
		#	of knowing whether any "owner" of a unit will be the same
		#	next turn.  Probably what should happen is this method
		#	should be called at adjudication time from somewhere
		#	in the XtalballGame object to drive whether an ordered
		#	unit should HOLD instead (of violating its league rules).
		#	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
		error = report and self.error or []
		if not owner or len(self.map.leagues.get(owner.name, [])) <= 1: return 1
		league, behave = self.map.leagues[owner.name][:2]
		supportee = self.unitOwner(word[1] + ' ' + word[2]) or owner
		his = self.map.leagues.get(supportee.name, [''])[0]
		ours = [league] + self.map.leagues[owner.name][2:]
		if behave == 'STRICT':
			if his != league: return error.append(
				'STRICT LEAGUE FORBIDS %s: %s ' %
				(orderText, unit) + order)
		elif his not in ours and '-' in word:
			vic = (self.unitOwner('A ' + word[-1])
				or self.unitOwner('F ' + word[-1], 0))
			if vic and self.map.leagues.get(vic.name, [''])[0] in ours:
				return error.append('LEAGUE FORBIDS %s: %s ' %
					(orderText, unit) + order)
		return 1
	#	----------------------------------------------------------------------
	def expandOrder(self, word):
		error, result = self.error, self.map.compact(' '.join(word))
		result = self.map.vet(self.map.rearrange(result), 1)
		#	---------------
		#	Weed out errors
		#	---------------
		final, order = [], ''
		for x, y in result:
			if y < 1:
				if y == -1:
					error.append('UNKNOWN POWER OR PLACENAME: ' + x)
					continue
				elif y == -2:
					error.append('UNKNOWN UNIT TYPE: ' + x)
					continue
				elif y == -3:
					error.append('UNKNOWN PLACENAME: ' + x)
				elif y == -4:
					z = x.split('/')[0]
					if z in self.map.aliases.values():
						error.append('UNKNOWN COAST: ' + x)
						x, y = z, -3
					else:
						error.append('UNKNOWN PLACENAME: ' + x)
				elif y == -5:
					error.append('UNKNOWN ORDER TYPE: ' + x)
					continue
				else:
					error.append('UNRECOGNIZED DATA IN ORDER: ' + x)
					continue
				y = -y
			if y == 1:
				#	------------------------------
				#	Remove power names
				#	Checking ownership of the unit
				#	might be better
				#	------------------------------
				continue
			elif y == 5:
				#	-------------------------------
				#	Remove the "H" from any order
				#	having the form "u xxx S xxx H"
				#	-------------------------------
				if order == 'S' and x == 'H': continue
				order += x
			elif y == 6:
				#	-----------------------------------
				#	Treat each move order the same
				#	Eventually we'd want to distinguish
				#	between them
				#	-----------------------------------
				x = '-'
				order += x
			elif y == 7:
				order = ''
			if 'NO_CHECK' in self.rules:
				#	----------------------------------
				#	Spot ambiguous placenames and
				#	coasts in support and convoy oders
				#	----------------------------------
				if y == 3:
					if x in self.map.unclear: 
						error.append('AMBIGUOUS PLACENAME: ' + x)
				if y == 4:
					if x.split('/')[0] in self.map.unclear:
						error.append('AMBIGUOUS PLACENAME: ' + x)
					#   --------------------------------------------------
					#   The below error, disallowing coastal designations
					#	in the destinations of support and portage convoy
					#	orders in a NO_CHECK game is no longer desired
					#	all the time; instead they should get silently
					#	suppressed in order to facilitate processing
					#	orders copied from a results file into the Master
					#	order box or through e-mail, e.g. when moving over
					#	a game from a different Judge
					#   --------------------------------------------------
					if order and order[0] in 'SC' and order[-1] == '-':
						error += ['COAST NOT ALLOWED IN %s ORDER: ' % 
							('CONVOY', 'SUPPORT')[order[0] == 'S'] + x]
						x, y = x.split('/')[0], 3
			final += [x]
		#	-------------------------------------------------------------
		#	Default any fleet move's coastal destination, then we're done
		#	-------------------------------------------------------------
		return self.map.defaultCoast(final)
	#	----------------------------------------------------------------------
	def addUnitTypes(self, item, processing = 0):
		#	-------------------------------------------------------------
		#	This method adds any missing "A"rmy and "F"leet designations
		#	and (current) coastal locations for fleets.  It is applied to
		#	an order (in [list] form) after the order is returned from
		#	Game.expandOrder().  In games that use the FICTIONAL_OK rule,
		#	this method does NOTHING, since the unit types to be added
		#	are obviously gleaned from the current state of the board,
		#	which is either inappropriate for the order (as in Crystal
		#	Ball) or to be kept unknown to the player (as in blind).
		#	-------------------------------------------------------------
		if not processing and 'FICTIONAL_OK' in self.rules: return item
		word, dependent, hadType = [], 1, 0
		for token in item:
			if not dependent: dependent = token in 'CS'
			elif token in 'AF': hadType = 1
			elif token in ('RETREAT', 'DISBAND', 'BUILD', 'REMOVE'): pass
			else:
				try:
					unit = [x for y in self.powers for x in
						(y.units, y.retreats.keys())[self.phaseType == 'R']
						if x[2:].startswith(token)][0]
					if not hadType: word += [unit[0]]
					if self.map.isValidUnit(word[-1] + unit[1:]):
						token = unit[2:]
				except: pass
				dependent = hadType = 0
			word += [token]
		return word
	#	----------------------------------------------------------------------
	def addRule(self, rule):
		if rule not in self.rules: self.rules += [rule]
	#	----------------------------------------------------------------------
	def loadMap(self, mapName = 'standard', trial = 0, lastPhase = 0):
		import Map
		self.map, phases = Map.Map(mapName, trial), []
		self.error += self.map.error
		if self.phase and not ' ' in self.phase and self.phase not in (
			'FORMING', 'COMPLETED'):
			self.phase = self.map.phaseLong(self.phase)
		#	-------------------------------------------
		#	Have the Game process all lines in the map
		#	file that were in DIRECTIVES clauses (this
		#	includes any RULE lines).  Do this for all
		#	directives given without a variant and for
		#	those specified for this Game's variant.
		#	-------------------------------------------
		self.loadDirectives(self.map.directives.get('ALL', []) +
				self.map.directives.get(self.status[0].upper(), []))
		if self.phase == 'FORMING': return
		#	------------------------------------------------------
		#	Create a list of possible entries in self.map.dynamic
		#	(map directives to be run in or after specific phases)
		#	------------------------------------------------------
		if not self.map.dynamic: return
		#	---------------------------------------------------------
		#	"FROM" previous phases (lowercase entries in Map.dynamic)
		#	---------------------------------------------------------
		try:
			file = open(self.file('results'), encoding = 'latin-1')
			phases += [line.split()[-1].lower() for line in file
				if line.startswith('Subject: Diplomacy results')]
			file.close()
		except: pass
		if lastPhase: phases += [lastPhase.lower()]
		#	----------------------------------------------------
		#	"FROM" the CURRENT phase (lowercase still) and "IN"
		#	the current phase (UPPERcase entries in Map.dynamic)
		#	----------------------------------------------------
		phases += [self.phaseAbbr().lower(), self.phase, self.phaseAbbr()]
		self.map.validate(phases)
	#	----------------------------------------------------------------------
	def file(self, name):
		return self.gameDir + '/' + name
	#	----------------------------------------------------------------------
	def setTimeZone(self, timeZone = 'GMT'):
		zone = TimeZone(timeZone)
		if not zone: return self.error.append('BAD TIME ZONE: ' + timeZone)
		self.zone = zone
		#	-------------------------------------------------------------
		#	Changing the deadline time (and not just the zone) may not be
		#	what the user expects. Also the TIMING line may influence the
		#	deadline, and we're not going to update that.
		#	-------------------------------------------------------------
		if self.deadline: self.deadline = self.getTime(self.deadline)
		if self.processed: self.processed = self.processed.changeZone(zone)
	#	----------------------------------------------------------------------
	def getTime(self, when = None, npar = 0):
		if not npar:
			try: npar = len(when)/2-1
			except: return Time(self.zone, when)
		return Time(self.zone, when, npar)
	#	----------------------------------------------------------------------
	def loadStatus(self, fileName = 'status', includeFlags = 7):
		#	---------------------------------------------
		#	Loads the status file data.
		#   Relevant bit values for includeFlags:
		#		1: include orders for each power
		#		2: include persistent data
		#		4: include transient data
		#	At least one of these bits should be set.
		#	---------------------------------------------
		if not includeFlags: return
		self.reinit(includeFlags)
		error, power = self.error, None
		try: file = open(self.file(fileName), encoding='latin-1')
		except: return setattr(self, 'name', 0)
		blockMode = 0
		for line in file:
			word = line.split()
			if not word:
				if not self.mode or not self.modeRequiresEnd:
					# Mark end of block, but skip consecutive empty lines. 
					if blockMode == 1:
						self.finishGameData() 
						blockMode = 2
					elif blockMode == 3:
						self.finishPowerData(power)
						blockMode = 2
					elif blockMode < 0:
						blockMode += 4
				continue
			upword = word[0].upper()
			if blockMode == 0:
				# Start of first block, the game data
				if upword != 'GAME':
					error += ['NOT A GAME DECLARATION: ' + ' '.join(word)]
					blockMode -= 4
				else: 
					# Allowed during renaming, when broadcasts are disabled.
					if word[1:] != [self.name] and self.tester[-1:] != '@':
						error += ['GAME NAME MISMATCH']
					blockMode = 1
					self.mode = self.modeRequiresEnd = None
			elif blockMode == 1:
				# Game data
				if (self.mode and upword == 'END' and len(word) == 2
					and word[1].upper() == self.mode):
					self.mode = self.modeRequiresEnd = None
				elif (not self.parseGameData(word, includeFlags)
					and includeFlags & 6 == 6):
					error += ['UNRECOGNIZED GAME DATA: ' + ' '.join(word)]
			elif blockMode == 2:
				# Power (or observer, etc.)
				power = self.determinePower(word)
				if not power:
					error += ['NOT A POWER DECLARATION: ' + ' '.join(word)]
					blockMode -= 4
				else:
					blockMode = 3
					self.mode = self.modeRequiresEnd = None
			elif blockMode == 3:
				# Power data
				if (self.mode and upword == 'END' and
					len(word) == 2 and word[1].upper() == self.mode):
					self.mode = self.modeRequiresEnd = None
				elif (not self.parsePowerData(power, word, includeFlags)
				and includeFlags & 7 == 7):
					error += ['UNRECOGNIZED POWER DATA: ' + ' '.join(word)]
		file.close()
		if blockMode == 1:
			self.finishGameData() 
		elif blockMode == 3:
			self.finishPowerData(power)
		self.validateStatus()
		self.collectState()
	#	----------------------------------------------------------------------
	def loadDirectives(self, directives):
		#	---------------------------------------------
		#	Loads map directives.
		#   Note that bit value 8 is set for includeFlags
		#	when calling parseGameData, to mark the rules
		#	as directives.
		#	---------------------------------------------
		error, power = self.error, None
		self.mode = self.modeRequiresEnd = None
		for line in directives:
			word = line.split()
			if not word: continue
			self.directives += [' '.join(word)]
			# Game data
			if self.mode and [x.upper() for x in word] == ['END', self.mode]:
				self.mode = self.modeRequiresEnd = None
			elif not self.parseGameData(word, 14):
				error += ['UNRECOGNIZED GAME DIRECTIVE: ' + ' '.join(word)]
	#	----------------------------------------------------------------------
	def parseGameData(self, word, includeFlags):
		#	---------------------------------------------
		#	Parses the game specific data.
		#   Relevant bit values for includeFlags:
		#		2: include persistent data
		#		4: include transient data
		#		8: mark rules as directives
		#	---------------------------------------------
		error, upword, found = self.error, word[0].upper(), 0
		#	-----
		#	Modes
		#	-----
		if self.mode:
			if not includeFlags & 2: return 0
			#	--------------------------------------
			#	Game-specific information (persistent)
			#	--------------------------------------
			if self.mode in ('DESC', 'DESCRIPTION'):
				self.desc += [' '.join(word)]
			elif self.mode == 'NAME':
				self.origin += [' '.join(word)]
			elif self.mode == 'MORPH':
				self.morphs += [' '.join(word)]
			else: return 0
			return 1
		#	-------------------------------------
		#	Game-specific information (transient)
		#	-------------------------------------
		if includeFlags & 4:
			found = 1
			if upword in ('AWAIT', 'PHASE', 'SKIP', 'WAIT'):
				self.await = (upword[0] in 'AW') * (6 - len(upword))
				self.skip = upword == 'SKIP'
				if len(word) > 1 and word[1].upper() != 'COMPLETED':
					if self.phase:
						error += ['TWO AWAIT/PHASE/SKIP/WAIT STATEMENTS']
					else: self.phase = ' '.join(word[1:]).upper()
			elif upword == 'DEADLINE':
				if self.deadline: error += ['TWO DEADLINES']
				else:
					self.deadline = self.getTime(' '.join(word[1:]))
					if not self.deadline:
						error += ['BAD DEADLINE: ' + ' '.join(word[1:])]
			elif upword == 'DELAY':
				if self.delay: error += ['TWO DELAYS']
				elif len(word) != 2: error += ['BAD DELAY']
				else:
					try:
						self.delay = int(word[1])
						if not (0 < self.delay < 73): raise
					except: error += ['BAD DELAY COUNT: ' + word[1]]
			else:
				found = 0
				if upword == 'RESULT':
					if len(word) > 1:
						if self.phase:
							error += ['RESULT WHILE PHASE NOT COMPLETED YET']
						elif not self.map: self.phase = word[1]
						else: self.phase = self.phaseLong(word[1])
		#	----------------------------------
		#	Game-specific information (orders)
		#	----------------------------------
		if not found and includeFlags & 1:
			found = 1
			if upword == 'RESULT':
				if len(word) > 1:
					self.outcome += word[1:]
					self.phase = 'COMPLETED'
			elif upword == 'FINISH':
				if self.end: error += ['TWO FINISH STATEMENTS']
				elif len(word) > 1: self.end = ' '.join(word[1:])
			elif upword == 'PROPOSAL':
				if self.proposal: error += ['TWO PROPOSALS']
				elif len(word) != 3: error += ['BAD PROPOSAL']
				else: self.proposal = word[1:]
			else: found = 0
		#	--------------------------------------
		#	Game-specific information (persistent)
		#	--------------------------------------
		if not found and includeFlags & 2:
			found = 1
			if upword == 'MASTER':
				if self.gm.player: error += ['TWO MASTER STATEMENTS']
				elif len(word) == 1: error += ['NO MASTER SPECIFIED']
				else:
					self.gm.player = word[1:]
					self.master = word[1].split('|')
			elif upword == 'PASSWORD':
				if len(word) != 2 or '<' in word[1] or '>' in word[1]:
					error += ['BAD PASSWORD: ' + ' '.join(word[1:]).
					replace('<', '&lt;').replace('>', '&gt;')]
				elif self.gm.password: error += ['TWO MASTER PASSWORDS']
				else: self.password = self.gm.password = word[1]
			elif upword == 'ADDRESS':
				if self.gm.address: error += ['TWO MASTER ADDRESSES']
				elif len(word) == 1: error += ['NO MASTER ADDRESS SPECIFIED']
				elif [1 for x in word[1].split(',')
					if x.count('@') != 1 or '@' not in x[1:-3]
					or not x.split('.')[-1].isalpha()
					or '.' not in x.split('@')[1]
					or '.' in (x.split('@')[1][0], x[-1])]:
						error += ['BAD MASTER ADDRESS']
				else: self.gm.address = word[1:]
			elif upword == 'TESTER':
				if self.tester and self.tester[-1] == '!':
					error += ['TWO TESTER STATEMENTS']
				elif len(word) == 1: self.tester = '!'
				else: self.tester = word[1] + '!'
			elif upword in ('DESC', 'DESCRIPTION'):
				if len(word) > 1: self.desc += [' '.join(word[1:])]
				else: self.mode, self.modeRequiresEnd = upword, 1
			elif upword == 'NAME':
				if len(word) > 1: self.origin += [' '.join(word[1:])]
				else: self.mode, self.modeRequiresEnd = upword, 1
			elif upword == 'NEED':
				if len(word) > 1: self.avail += word[1:]
			elif upword == 'GROUPS':
				self.groups = word[1].upper().split('|')
			elif upword == 'PRIVATE':
				if len(word) == 2: self.private = word[1].upper()
				else: error += ['INVALID PRIVATE STATEMENT']
			elif upword in ('RULE', 'RULES'):
				for rule in word[1:]:
					rule = rule.upper()
					item = rule.replace('!','')
					item =	{	'NO_PARTIAL': 'PUBLIC_PRESS',
								'FLEX_SETUP': 'BLANK_BOARD',
							}.get(item, item)
					if rule[0] == '!':
						self.norules += [item]
						continue
					self.addRule(item)
					if self.map and includeFlags & 8:
						if item not in self.map.rules: self.map.rules += [item]
						if item not in self.metaRules: self.metaRules += [item]
			elif upword == 'JUDGE':
				if self.judge: error += ['TWO JUDGE STATEMENTS']
				else: self.judge = ' '.join(word[1:])
			elif upword in ['MAP', 'TRIAL']:
				if self.map: error += ['TWO MAP STATEMENTS']
				elif len(word) == 2: self.loadMap(word[1].lower(), upword == 'TRIAL')
				else: error += ['BAD MAP STATEMENT']
			elif upword == 'ROTATE':
				if self.rotate: error += ['TWO ROTATE STATEMENTS']
				else: self.rotate = [x.upper() for x in word[1:]] or ['CONTROL']
			elif upword == 'START':
				if self.start: error += ['TWO START STATEMENTS']
				elif len(word) > 1: self.start = ' '.join(word[1:])
			elif upword == 'ALLOW':
				for allow in [x.upper() for x in word[1:]]:
					if allow not in (self.playerTypes +
						['POWER', 'OBSERVER', 'MONITOR']):
						self.playerTypes += [allow]
			elif upword == 'ZONE':
				if len(word) < 2: error += ['ZONE UNSPECIFIED']
				elif self.zone: error += ['TWO TIME ZONES']
				elif host.zoneFile: self.setTimeZone(word[1])
				else: error += ['ZONE CHANGE UNSUPPORTED']
			elif upword == 'TIMING':
				try:
					for num in range(1, len(word), 2):
						key = word[num].upper()
						if key == 'NOT' and self.timing.get(key):
							self.timing[key] += ',' + word[num + 1].upper()
						elif key in self.timing:
							error += ['TWO %s SPECS IN TIMING' % key]
						elif key == 'DAYS':
							days = word[num + 1]
							self.timing[key] = (days == days.lower() and
								days.upper() or days)
						else: self.timing[key] = word[num + 1].upper()
				except: error += ['BAD TIMING']
			elif upword == 'MORPH':
				if len(word) > 1: self.morphs += [' '.join(word[1:])]
				else: self.mode, self.modeRequiresEnd = upword, 1
			#	---------------
			#	Legacy keywords
			#	---------------
			elif upword == 'JUDGE':
				if self.judge: error += ['TWO JUDGE STATEMENTS']
				else: self.judge = ' '.join(word[1:])
			elif upword == 'SIGNON':
				if self.signon: error += ['TWO SIGNON STATEMENTS']
				else: self.signon = ' '.join(word[1:])
			else: found = 0
		return found
	#	----------------------------------------------------------------------
	def finishGameData(self):
		self.mode = self.modeRequiresEnd = None
		#	-----------------------------
		#	Other lines require a map --
		#	default to standard if needed
		#	-----------------------------
		if not self.map: self.loadMap()
		if self.morphs:
			error, self.map.error = self.map.error, []
			self.map.load(self.morphs)
			self.map.validate(force = 1)
			self.error += self.map.error
			self.map.error = error + self.map.error
		#	-----------------
		#	Update the Master
		#	-----------------
		if self.gm.player and not self.gm.address:
			try: self.gm.address = [self.gm.player[0].split('|')[1]]
			except: pass
		#	-------------------------
		#	Validate RULE consistency
		#	-------------------------
		self.validateRules()
	#	----------------------------------------------------------------------
	def determinePower(self, word):
		error = self.error
		upword = self.map.normPower(word[0])
		#	-----------------------
		#	Powers and other player
		#	types (observers, etc.)
		#	-----------------------
		if ((len(word) == 1 and upword in self.map.powers)
		or (len(word) == 2 and upword in (self.playerTypes +
				['POWER', 'OBSERVER', 'MONITOR'])
		and (upword == 'POWER'
		or self.map.normPower(word[1]) not in self.map.powers))):
			word.reverse()
			for power in self.powers:
				if self.map.normPower(word[0]) == power.name: break
			else:
				if self.phase == 'FORMING':
					if len(word) == 1: word += ['POWER']
				elif word[-1] == 'POWER': del word[-1]
				word = [self] + [x.upper() for x in word]
				try: power = self.powerType(*word)
				except:
					error += ['BAD PARTICIPANT ' + ' '.join(word[1:])]
					return None
				if power.name in self.map.powers: power.abbrev = (
					self.map.abbrev.get(power.name, power.name[0]))
				else: power.abbrev = None
				self.powers += [power]
			return power
		return None
	#	----------------------------------------------------------------------
	def parsePowerData(self, power, word, includeFlags):
		#	---------------------------------------------
		#	Parses the power specific data.
		#   Relevant bit values for includeFlags:
		#		1: include orders for each power
		#		2: include persistent data
		#		4: include transient data
		#	---------------------------------------------
		error, upword, found = self.error, word[0].upper(), 0
		#	-----
		#	Modes
		#	-----
		if self.mode:
			return 0
		#	------
		#	Orders
		#	------
		if upword in ('BUILD', 'REMOVE', 'RETREAT'):
			if not includeFlags & 1: return -1
			power.adjust += [' '.join(word).upper()]
			return 1
		#	-------------------------------
		#	Power-specific data (transient)
		#	-------------------------------
		if includeFlags & 4:
			found = 1
			if upword == 'CONTROL':
				if len(word) == 1:
					error += ['INVALID CONTROL FOR ' + power.name]
				elif power.password or power.ceo:
					error += ['TWO CONTROLS FOR ' + power.name]
				else: power.ceo = [x.upper() for x in word[1:]]
			elif upword == 'FUNDS':
				if len(word) == 1: error += ['NO FUNDS DATA']
				else:
					try:
						for money in word[1:]:
							if money[0] == '$': money = money[1:] + '$'
							for ch in range(len(money)):
								if money[ch].isdigit(): continue
								if power.funds.get(money[ch:]): error += [
								'DUPLICATE FUND TYPE: ' + money[ch:]]
							else: power.funds[money[ch:]] = int(money[:ch])
							break
						else: raise
						power.balance = power.funds.get('$')
					except:	error += ['BAD FUNDS: ' + money]
			elif upword in ('A', 'F') and ((len(word) > 3 and word[2] == '-->')
				or (len(word) == 2 and '-' not in word[1])):
				#	-----
				#	Units
				#	-----
				self.parseUnit(power, ' '.join(word[:2]).upper(), word[3:])
			elif upword == 'OWNS':
				for center in word[1:]:
					sc = center.upper()
					if sc in ('SC!','SC?','SC*'): power.centers += [sc]
					elif sc in power.centers: pass
					elif [1 for x in self.powers if sc in x.centers]:
						error += [sc + ' ALREADY OWNED']
					elif sc in self.map.scs: power.centers += [sc]
					else: error += ['BAD OWNED CENTER: ' + sc]
			elif upword in ('INHABITS', 'HOME'):
				power.homes = [x.upper() for x in word[1:]]
			elif upword == 'SEES':
				for sc in [x.upper() for x in word[1:]]:
					if sc in self.map.scs: power.sees += [sc]
					else: error += ['BAD SEEN CENTER: ' + sc]
			elif upword == 'HIDES':
				power.hides += [x.strip() for x in
					' '.join(word[1:]).upper().split(',')]
			else: found = 0
		#	--------------------------------
		#	Power-specific data (persistent)
		#	--------------------------------
		if not found and includeFlags & 2:
			found = 1
			if upword == 'PASSWORD':
				if len(word) != 2 or '<' in word[1] or '>' in word[1]:
					error += ['BAD PASSWORD: ' + ' '.join(word[1:]).
						replace('<', '&lt;').replace('>', '&gt;')]
				elif power.password or power.ceo:
					error += ['TWO PASSWORDS FOR ' + power.name]
				elif len(word) != 2: error += ['NO PASSWORD FOR ' + power.name]
				else: power.password = word[1]
			elif upword == 'PLAYER':
				if len(word) == 1: error += ['NO PLAYER DATA']
				elif power.player: error += ['TWO PLAYERS FOR ' + power.name]
				else:
					power.player = word[1:]
					if power.player[0].upper() in ('RESIGNED', 'DUMMY'):
						power.player[0] = power.player[0].upper()
					for num, item in enumerate(power.player):
						part = item.split('|')
						if not num and item in ('RESIGNED', 'DUMMY'): continue
						if num & 1:
							if (len(item) > 2 and (item[0] + item[-1]).isupper()
							and item[1:-1].isdigit()): continue
						elif item == 'DUMMY': continue
						elif len(part) == 3:
							for address in part[1].split(','):
								addr = address.split('@')
								if not (len(addr) == 2 and addr[0]
								and (not part[0] or (part[0][0] == '#'
									and part[0][1:].isdigit()))
								and '.' not in (addr[1][0], addr[1][-1])
								and addr[1][1:-1].count('.')): break
							else: continue
						error += ['BAD PLAYER DATA FOR ' + power.name]
						break
			elif upword == 'ADDRESS':
				if len(word) == 1: error += ['NO ADDRESS DATA']
				elif power.address: error += ['TWO ADDRESSES FOR ' + power.name]
				elif [1 for x in word[1].split(',')
					if x.count('@') != 1 or '@' not in x[1:-3]
					or not x.split('.')[-1].isalpha()
					or '.' not in x.split('@')[1]
					or '.' in (x.split('@')[1][0], x[-1])]:
						error += ['BAD ADDRESS FOR ' + power.name]
				else: power.address = word[1:]
			elif upword in ('OMNISCIENT', 'OMNISCIENT!'):
				if power.omniscient: error += ['DOUBLE OMNISCIENT?']
				else: power.omniscient = 1 + (upword[-1] == '!')
			elif upword == 'MSG':
				power.msg += [' '.join(word[1:])]
			else: found = 0
		#	----------------------------
		#	Power-specific data (orders)
		#	----------------------------
		if not found and includeFlags & 1:
			found = 1
			if upword == 'VOTE':
				if power.vote: error += ['TWO VOTES FOR ' + power.name]
				else:
					try:
						if len(word) != 2: raise
						power.vote = word[1].upper()
						if power.vote[-3:] == 'WAY':
							power.vote = power.vote[:-3]
							if not (0 <= int(power.vote)
								<= len(self.map.powers)): raise
						else: power.vote = {'LOSS': '0', 'SOLO': '1',
							'YES': 'YES'}[power.vote]
					except: error += ['BAD VOTE FOR ' + power.name]
			elif upword == 'WAIT':
				power.wait = 1
			elif upword == 'CD':
				power.cd = 1
			#	------------------------------------------
			#	Every other line (orders, offers, etc.) is
			#	handled by the variant-specific parsePowerData(),
			#	upon seeing this return value, telling it to
			#   handle the line by herself.  (NOTE: password,
			#	ceo, centers, units, player, msg, and
			#	adjust [build, remove, and retreat] are
			#	also power-data, but are handled above;
			#	they are common to all games.)
			#	------------------------------------------
			else: found = 0
		return found
	#	----------------------------------------------------------------------
	def finishPowerData(self, power):
		self.mode = self.modeRequiresEnd = None
	#	----------------------------------------------------------------------
	def validateStatus(self):
		#	-----------------------------------------
		#	Make sure the game has a map and a master
		#	-----------------------------------------
		if not self.gm.player: raise GameHasNoMaster
		if not self.map: self.loadMap()
		self.victory = self.map.victory
		if not self.victory:
			self.victory = [len(self.map.scs) // 2 + 1]
			if 'VICTORY_HOMES' in self.rules:
				powers = [x for x in self.powers if x.homes]
				if len(self.powers) > 1:
					scs = [y for y in self.map.scs if [1 for x in powers
						if y in x.homes]]
					if len(scs) > 1: self.victory = [
						len(scs) * (len(powers) - 1) // (2 * len(powers)) + 1]
		rules, error = self.rules, self.error
		if self.phase == 'FORMING':
			avail = self.available()
			if avail < 0:
				error += [('THERE %s %d MORE PLAYER%s THAN THERE ARE ' +
					'POSITIONS AVAILABLE') % [('ARE', -avail, 'S'),
					('IS', -avail, '')][avail == -1]]
				avail = 0
			self.avail = [`avail`]
			#	-----------------------------------
			#	Ensure all controlling powers exist
			#	-----------------------------------
			checked = []
			for controllers in self.map.controls.values():
				for controller in controllers:
					if controller in checked: continue
					checked += [controller]
					if controller not in self.map.powers + ['MASTER'] + [
						x.name for x in self.powers if not
						x.name.startswith('POWER#')]:
						error += ['CONTROLLING POWER %s IS NOT A POWER' %
							controller]
					elif controller in self.map.dummies:
						error += ['CONTROLLING POWER %s IS A DUMMY' %
							controller]
		if self.phase not in ('FORMING', 'COMPLETED') and not (
			self.deadline or 'NO_DEADLINE' in self.rules):
			error += ['GAME HAS NO DEADLINE!']
		if 'NO_RESERVES' in rules: self.map.reserves = []
		if 'NO_MILITIA' in rules: self.map.militia = []
		#	-------------------------
		#	Ensure game phase was set
		#	-------------------------
		if not self.phase: error += ['NO PHASE SPECIFIED']
		apart = self.phase.split()
		if len(apart) == 3:
			if apart[0] + ' ' + apart[2] not in self.map.seq:
				error += ['BAD PHASE (NOT IN FLOW)']
			self.season, self.phaseType = apart[0], apart[2][0]
			try: self.year = int(apart[1])
			except: error += ['NON-NUMERIC YEAR IN PHASE']
		else: self.season = self.year = self.phaseType = '-'
		#	-------------------------------------------
		#	Validate the BEGIN phase (if one was given)
		#	-------------------------------------------
		if self.phase == 'FORMING':
			apart = self.map.phase.split()
			try:
				int(apart[1])
				del apart[1]
				if ' '.join(apart) not in self.map.seq: raise
			except: error += ['BAD BEGIN PHASE']
		#	----------------------------
		#	Validate any rotation scheme
		#	----------------------------
		if len(self.rotate) & 1 and self.rotate not in (['AFTER'], ['CONTROL']):
			error += ['BAD CONTROL ROTATION']
		elif len(self.rotate) > 1:
			for how in range(0, len(self.rotate), 2):
				if (self.rotate[how] in ('FOR', 'AFTER', 'BEFORE', 'CONTROL')
				and self.rotate[how + 1][0] in self.map.phaseAbbrev): continue
				error += ['BAD CONTROL ROTATION']
				break
		#	---------------------
		#	Set victory condition
		#	---------------------
		if self.phase not in ('FORMING', 'COMPLETED'):
			try:
				#	Hmm. This seems to link changing victory conditions to
				#	work only in games where game-years advance by +1.
				#	This may also be done in another place in this file?
				year = abs(int(self.phase.split()[1]) - self.map.firstYear)
				win = self.victory[:]
				self.win = win[min(year, len(win) - 1)]
			except: error += ['BAD YEAR IN GAME PHASE']
		#	--------------------
		#	Validate timing data
		#	--------------------
		for key, val in self.timing.items():
			try:
				if key == 'AT':
					hour, minute = map(int, val.split(':'))
					if not (0 <= hour < 24 and 0 <= minute < 60): raise
				elif key == 'DAYS':
					if val == val.lower(): raise
					for num in range(7):
						if val[num].upper() not in 'SMTWTFS'[num] + '-': raise
				elif key != 'NOT':
					for val in ([val], val.split(','))[key == 'WARN']:
						if (int(val[:-1]) < (key not in ('WARN', 'GRACE'))
						or	val[-1] not in 'MHDPW'): raise
			except: error += ['BAD %s IN TIMING: ' % key + val]
		#	---------------------
		#	Initialize power data
		#	---------------------
		for power in self.powers:
			#	--------------------------
			#	Initialize homes if needed
			#	--------------------------
			if not power.type and power.homes is None:
				if self.map.homeYears: power.homes = []
				else: power.homes = self.map.homes.get(power.name, [])
			#	------------------------------------------
			#	Set default player vote (solo for himself)
			#	------------------------------------------
			if not power.canVote(): power.vote = None
			elif power.vote is None and 'PROPOSE_DIAS' not in rules:
				power.vote = '1'
		#	-------------------
		#	Validate power data
		#	-------------------
		for power in self.powers:
			#	----------------------------------
			#	Verify that every person is unique
			#	----------------------------------
			id = power.player and power.player[0].split('|')[0] or ''
			if id.startswith('#'):
				if self.gm.player and id == self.gm.player[0].split('|')[0]:
					error += ['THE MASTER HAS THE SAME ID AS ' + power.name]
				error += ['%s AND %s HAVE THE SAME ID' % (power.name, x.name)
					for x in self.powers if x is not power and
					x.name > power.name and x.player and
					x.player[0].split('|')[0] == id]
			#	------------------
			#	Validate passwords
			#	------------------
			if power.password:
				if self.gm.password and (
					power.password.lower() == self.gm.password.lower()):
					error += ['THE MASTER HAS THE SAME PASSWORD AS ' + power.name]
				error += ['%s AND %s HAVE THE SAME PASSWORD' % (power.name, x.name)
					for x in self.powers if x is not power and
					x.name > power.name and x.password and
					x.password.lower() == power.password.lower()]
			#	--------------------
			#	Validate controllers
			#	--------------------
			for who in power.ceo:
				if (who != 'MASTER'
					and not ([1 for x in self.map.powers if x == who]
					or [1 for x in self.powers if x.name == who])):
					error += ['BAD CONTROL FOR ' + power.name]
			if not power.type and not power.player and not power.ceo:
				error += ['NO PLAYER DATA FOR ' + power.name]
			#	--------------------------
			#	Validate adjustment orders
			#	--------------------------
			if (power.adjust and self.phaseType not in 'AR'
				and self.phase != 'COMPLETED'):
				error += ['ORDERS FOUND FOR PHASE NOT CURRENT']
				continue
			kind, goodOrders, builds, sites = None, [], 0, []
			for order in power.adjust:
				word = order.split()
				if not kind:
					kind = word[0]
					if (kind == 'RETREAT') == (self.phaseType == 'A'):
						error += ['IMPROPER ORDER TYPE: ' + order]
						continue
					if kind == 'BUILD':
						sites = self.buildSites(power)
						need = self.buildLimit(power, sites)
				elif kind != word[0]:
					error += ['MIXED ORDER TYPES: %s, ' % type + word[0]]
					continue
				if order == 'BUILD WAIVED': continue
				if len(word) < 3:
					error += ['BAD ADJUSTMENT ORDER: ' + order]
					continue
				if [1 for x in goodOrders if word[2][:3] == x[2][:3]]:
					error += ['DUPLICATE ORDER: ' + order]
				else: goodOrders += [word]
				unit = ' '.join(word[1:3])
				if kind == 'RETREAT':
					if (word[3:] != ['DISBAND']
					and (len(word) != 5 or word[3] != '-'
					or word[4] not in power.retreats.get(unit, []))):
						error += ['BAD RETREAT FOR %s: ' % power.name + order]
				elif kind == 'REMOVE':
					if unit not in power.units or len(word) > 3:
						error += ['BAD REMOVE FOR %s: ' % power.name + order]
				elif (not self.map.isValidUnit(unit)
					or len(word) > 3 + (word[3:4] == ['HIDDEN'])
					or not need or unit[2:5] not in sites):
					error += ['BAD BUILD FOR %s: ' % power.name + order]
				else: need -= 1
	#	----------------------------------------------------------------------
	def validateRules(self):
		ruleData, rulesForced, rulesDenied = self.loadRules()
		okrules, norules, ifrules = [], self.norules[:], []
		rules = [x for x in self.rules if x not in norules]
		metaRules = [x for x in self.metaRules if x not in norules]
		while 1:
			if not rules:
				for rule, cond in ifrules[:]:
					ifrules.pop(0)
					if rule in okrules and cond not in norules + okrules:
						rules = [cond]
						if cond not in metaRules: metaRules += [cond]
						break
				else: break
			rule = rules.pop(0)
			if rule in okrules: continue
			if rule in norules: norules.remove(rule)
			if rule not in ruleData:
				self.error += ['NO SUCH RULE: ' + rule]
				if rule in metaRules: metaRules.remove(rule)
				continue
			if ruleData[rule]['variant'] not in ('', self.status[0]):
				self.error += ['%sRULE %s REQUIRES %s VARIANT' %
					(rule in self.metaRules and 'MAP ' or
					 rule in metaRules and 'DERIVED ' or '', rule,
					ruleData[rule]['variant'].upper())]
				if rule in metaRules: metaRules.remove(rule)
				continue
			okrules += [rule]
			for deny in (ruleData[rule].get('-', []) +
						 ruleData[rule].get('!', [])):
				if deny in norules: continue
				norules += [deny]
				if deny in okrules:
					okrules.remove(deny)
					if deny in metaRules: metaRules.remove(deny)
			for force in ruleData[rule].get('+', []):
				if (ruleData[force]['variant'] in ('', self.status[0])
					 and force not in okrules):
					rules[:0] = [force]
					if force not in metaRules: metaRules += [force]
			for cond in ruleData[rule].get('=', []):
				if (ruleData[cond]['variant'] in ('', self.status[0])
					 and cond not in rules):
					ifrules += [(rule, cond)]
		self.rules = okrules
		self.metaRules = metaRules
		self.norules = [x for x in self.norules if x in norules]
	#	----------------------------------------------------------------------
	def available(self):
		return 'SOLITAIRE' not in self.rules and (
			len(self.map.powers) - len(self.map.dummies) - len(
			[1 for x in self.powers if x.type == 'POWER' and
			x.name not in self.map.dummies])) or 0
	#	----------------------------------------------------------------------
	def parseUnit(self, power, unit, retreats):
		#	-------------------------
		#	Check that the unit isn't
		#	in an occupied location.
		#	-------------------------
		loc, count = unit[2:5], 0
		for guy in self.powers:
			if retreats: sites = guy.retreats
			else: sites = guy.units
			if [self.error.append('TWO UNITS AT LOCATION: %s: ' %
				power.name + unit) for x in sites if x[2:].startswith(loc)]:
				return
		#	-------------------------------------
		#	Make sure that the unit specifies a
		#	valid placename, and that the type of
		#	unit specified can actually be there.
		#	-------------------------------------
		if not self.map.isValidUnit(unit, shutOK = 'HIBERNATE' in self.rules):
			return self.error.append('INVALID UNIT: %s: ' % power.name + unit)
		#	---------------------------------
		#	All is well.  Add the unit to the
		#	list of those owned by the power.
		#	---------------------------------
		if not retreats: power.units += [unit]
		elif not [self.error.append('INVALID RETREAT: %s - ' % unit + x)
			for x in retreats
			if not self.abuts(unit[0], unit[2:], '-', x, power)]:
			power.retreats[unit] = retreats
	#	----------------------------------------------------------------------
	def openMail(self, subject, copyFile = 0, mailTo = 0, mailAs = 0):
		#	----------------------------------------------------
		#	If copyFile is None, the mail to be sent will not be
		#	recorded in any local disk file. If mailTo defaults,
		#	the mail will be sent to host.dpjudge.
		#	If mailAs is 0, the mail will be sent as if from
		#	the game's Master (and a Master SIGNON is provided).
		#	----------------------------------------------------
		words = subject.split()
		if (self.name and self.name not in words
		and '(%s)' % self.name not in words): subject += ' (%s)' % self.name
		if not mailTo: mailTo = host.dpjudge
		elif mailTo != host.dpjudge and self.tester:
			mailTo = self.tester.rstrip('!')
			mailTo = mailTo * (len(mailTo) > 2 and
				mailTo[-1] != '@' and '@' in mailTo)
		else: mailTo = mailTo or host.dpjudge
		asMaster = self.gm.address and self.gm.address[0] or self.jk.address[0]
		self.mail = Mail(mailTo, subject,
			copy = copyFile and self.file(copyFile),
			mailAs = mailAs or asMaster,
			header = 'Errors-To: ' + asMaster)
		if not mailAs:
			self.mail.write('SIGNON M%s %s\n' % (self.name, self.gm.password), 0)
	#	----------------------------------------------------------------------
	def save(self, asBackup = 0):
		fileName = 'status'
		if asBackup:
			fileName += '.' + self.phaseAbbr()
		file = open(self.file(fileName), 'w')
		for x in [self] + self.powers:
			file.write(unicode(`x`, 'latin-1').encode('latin-1'))
		file.close()
		try: os.chmod(file.name, 0666)
		except: pass
		if asBackup:
			self.await = 1
			self.save()
		else: self.updateState()
	#	----------------------------------------------------------------------
	def fileResults(self, lines, subject = None):
		deadline = None
		if subject:
			#	----------------------
			#	Add a mail-like header
			#	----------------------
			lines[:0] = ['From %s %s\n' % (host.resultsFrom, (self.processed or
				self.getTime()).cformat()), 'Subject: %s\n' % subject, '\n']
			#	--------------------------------
			#	Replace the deadline on the last
			#	line of the previous season
			#	to match the current deadline.
			#	--------------------------------
			phase = subject.split()[-1]
			processed, deadline = self.processed, self.deadline
			self.deadline = None
			self.parseProcessed(lines, phase)
			self.processed = processed
			self.deadline, deadline = deadline, self.deadline
		mode = 'a'
		if deadline:
			try:
				file = open(self.file('results'), 'r', 'latin-1')
				rlines = file.readlines()
				file.close()
				num = 0
				for line in reversed(rlines):
					num -= 1
					if line.rstrip(): break
				if line.startswith('The deadline for '):
					word = line.split()
					rdeadline = Time(word[-1][:-1], ' '.join(word[-6:-1]))
					if rdeadline and rdeadline != deadline:
						lines[:0], mode = rlines[:num] + [' '.join(word[:-6]) +
							' %s.\n' % deadline.format(), '\n'], 'w'
			except: pass
		file = open(self.file('results'), mode)
		temp = ''.join(lines)
		file.write(temp.encode('latin-1'))
		del temp
		file.close()
		try: os.chmod(file.name, 0666)
		except: pass
		self.logAccess('TO', self.phase, 'ADVANCED')
	#	----------------------------------------------------------------------
	def fileSummary(self, reveal = 0, roll = 0):
		text, fileName = self.summary(reveal = reveal), self.file('summary')
		if not text: return
		if roll or self.tester or ('NO_REVEAL' in self.rules
		and not reveal) or 'SOLITAIRE' in self.rules:
			file = open(fileName, 'w')
			temp = '<pre>\n%s</pre>\n' % text
			file.write(temp.encode('latin-1'))
			del temp
			file.close()
			try: os.chmod(fileName, 0666)
			except: pass
			return
		#	------------------------------------
		#	Deliver game summary to Hall of Fame
		#	------------------------------------
		else:
			try: os.unlink(fileName)
			except: pass
			self.openMail('HoF: %s in ' %
				('Victory', 'Draw')[len(self.outcome) > 2] + self.name,
				copyFile = 'summary',
				mailTo = host.hall_keeper, mailAs = host.dpjudge)
			self.mail.copy.write('<pre>\n')
			self.mail.write(text)
			self.mail.copy.write('</pre>\n')
			self.mail.close()
		try:
			self.rules.remove('NO_REVEAL')
			self.save()
		except: pass
	#	----------------------------------------------------------------------
	def submitOrders(self, power, orders):
		#	----------------------------------------------------
		#	Before calling this function, set self.game.await if 
		#	you want it to submit a "PROCESS" order to the judge
		#	(that is, if this is the last set of orders needed),
		#	and "orders" should be ALL orders for the phase.
		#	----------------------------------------------------
		self.openMail('Diplomacy orders')
		if power: self.mail.write('BECOME %.1s\n' % power.name)
		for order in orders:
			word = order.split()
			if word[0] == 'RETREAT': del word[0]
			elif word[1] == 'WAIVED': word = ['WAIVE']
			self.mail.write(' '.join(word) + '\n')
		if not power: self.mail.write('PROCESS\n')
		self.mail.write('SIGNOFF\n')
		self.mail.close()
		self.mail = None
	#	----------------------------------------------------------------------
	def holdUnits(self, power):
		if not power.units: return
		self.openMail('Diplomacy orders: units held')
		self.mail.write('SET WAIT\nBECOME %.1s\n' % power.name)
		for unit in power.units: self.mail.write(unit + ' H\n')
		self.mail.write('SIGNOFF\n')
		self.mail.close()
	#	----------------------------------------------------------------------
	def clearOrders(self, power):
		self.openMail('Diplomacy orders cleared')
		self.mail.write('PRESS TO %.1s\n'
			'Your Diplomacy orders have been cleared. The judge will\n'
			'mark you late if your offers are not sent before the\n'
			'deadline, because an erroneous order (rather than the HOLD\n'
			'orders you had) has been issued for you.\n\n--The Master\n'
			'ENDPRESS\nBECOME %.1s\nA SWI - SWI\n'
			'SIGNOFF\n' % ((power.name,) * 2))
		self.mail.close()
	#	----------------------------------------------------------------------
	def transferCenter(self, fromPower, toPower, sc):
		if fromPower: fromPower.centers.remove(sc)
		if sc not in toPower.centers: toPower.centers += [sc]
	#	----------------------------------------------------------------------
	def parseSupplyCount(self, power, word):
		pass
	#	----------------------------------------------------------------------
	def finishPhase(self):
		pass
	#	----------------------------------------------------------------------
	def makeMaps(self):
		self.view.makeMaps()
	#	----------------------------------------------------------------------
	def addCoasts(self):
		#	-------------------------------------------------------------
		#	This method adds the matching coast to orders supporting or
		#	(portage) convoying a fleet to a multi-coast province.  The
		#	original reason for this code was because when the DPjudge
		#	was set up to only be a front-end to the Ken Lowe judge, all
		#	orders were being forwarded to a Ken Lowe judge, and that
		#	judge requires a coast specification or it will default to
		#	direct the support to a (maybe incorrect) coast.  The other
		#	reason this is necessary is to cause the map-maker code to
		#	draw the arrows in reference to the same physical spot on
		#	the map, ensuring that the support (or portage) and the move
		#	order are coordinated on the map.  The "orders" attribute of
		#	the Game object is modified for each unit offering that kind
		#	of support (or portage convoy).  This initial bit of code
		#	loads the orders into a local dictionary, because the entries
		#	in the self.orders dictionary may be in one of two forms.
		#	In the first of these forms, each dictionary entry is simply
		#	the order text, and in the second, the order text is in an
		#	"orders" attribute of the dictionary entry.  The local
		#	dictionary is populated with a copy of the orders, and if an
		#	order is changed, the correct data in the self.orders
		#	structure will be updated.
		#	-------------------------------------------------------------
		orders = {}
		for unit, order in self.orders.items():
			orders[unit] = hasattr(order, 'order') and order.order or order
		#	--------------------------------------------
		#	Add coasts to support and (portage) convoy
		#	orders for fleets moving to a specific coast
		#	--------------------------------------------
		for unit, order in orders.items():
			if order[:3] not in ('S F', 'C F'): continue
			word = order.split()
			rcvr = ' '.join(word[1:3])
			try: rcvr = [x for x in orders if x.startswith(rcvr)][0]
			except: continue
			orders[unit] = ' '.join([order[0], rcvr] + word[3:]).strip()
			if '-' in order:
				his = ' '.join(orders.get(rcvr, '').split()[-2:])
				if his[0] == '-' and his.split('/')[0] == ' '.join(word[3:]):
					orders[unit] = order[:2] + rcvr + ' ' + his
			if hasattr(self.orders[unit], 'order'):
				self.orders[unit].order = orders[unit]
			else: self.orders[unit] = orders[unit]
	#	----------------------------------------------------------------------
	def buildSites(self, power):
		try: homes = orig = power.homes
		except:
			error = 'DATA FOR NON-POWER: %s' % power.name
			if error not in self.error: self.error += [error]
			return
		powers = [x for x in self.powers if not x.type]
		if 'SC?' in power.centers or 'SC!' in power.centers:
			if (not homes and self.map.homeYears
			and not [x for x in powers if x.homes]):
				return self.map.homes.get(power.name, [])
			else: return homes
		if (not homes and self.map.homeYears
		and not [x for x in powers if x.homes]
		or 'BUILD_ANY' in self.rules or 'REMOTE_BUILDS' in self.rules
		or '&SC' in homes): homes = power.centers
		elif 'HOME_BUILDS' in self.rules:
			homes = [x for y in powers for x in y.homes]
		if 'REMOTE_BUILDS' in self.rules:
			if not [1 for x in orig if x in power.centers]: return []
		revert = [y for x in powers for y in x.homes
			if 'SC?' in x.centers or 'SC!' in x.centers]
		homes = [x for x in homes if x in power.centers and x not in
			[y[2:5] for z in powers for y in z.units] + revert]
		for alternative in [x[0] for x in self.map.alternative.get(
			power.name, [])
			if x[0] in homes and not [1 for y in x[1:] or power.homes
			if y in homes]]: homes.remove(alternative)
		return (homes + [x for x in (self.map.factory.get(power.name, []) *
				('NO_FACTORIES' not in self.rules) +
			self.map.partisan.get(power.name, []) * ('SC*' in power.centers))
			if x[:3] not in [z[2:5] for y in powers for z in y.units]])
	#	----------------------------------------------------------------------
	def buildLimit(self, power, sites = None):
		if sites is None: sites = self.buildSites(power)
		if not sites or power.name not in self.map.alternative: 
			return len(sites)
		return len([x for x in sites if x not in [
			y[0] for y in self.map.alternative[power.name]]])
	#	----------------------------------------------------------------------
	def buildAlternatives(self, power, sites = None):
		if sites is None: sites = self.buildSites(power)
		alternatives = []
		for limits in self.map.alternative.get(power.name, []):
			if limits[0] not in sites: continue
			if len(limits) == 1: limits = limits[:] + [
				x for x in power.homes if x in sites and
				x not in [y[0] for y in 
				self.map.alternative[power.name]]]
			else: limits = limits[:1] + [
				x for x in limits[1:] if x in sites]
			if len(limits) > 1: alternatives += [limits]
		return alternatives
	#	----------------------------------------------------------------------
	def sortPowers(self):
		self.powers.sort(Power.compare)
	#	----------------------------------------------------------------------
	def begin(self, roll = 0):
		if 'SOLITAIRE' in self.rules:
			self.map.dummies = self.map.powers[:]
		if self.error or self.status[1] != 'forming' and (
			self.status[1] != 'preparation' or self.available()):
			return ("To begin the game make sure that it's forming and " +
				"without errors")
		if not roll: self.rollin()
		self.findStartPhase()
		self.avail, avail = [], [x for x in self.map.powers
			if x not in self.map.dummies]
		self.win = self.victory[0]
		if not roll: self.setDeadline(firstPhase = 1)
		for starter in [x for x in self.powers if x.name in self.map.dummies]:
			starter.type = None
		for starter in [x for x in self.powers if x.name in avail]:
			starter.type = None
			avail.remove(starter.name)
		for starter in [x for x in self.powers if x.type == 'POWER']:
			starter.name, starter.type = random.choice(avail), None
			avail.remove(starter.name)
		if avail:
			self.morphs.append('UNPLAYED ' + ' '.join(avail))
			self.map.load(self.morphs[-1:])
			self.map.validate(force = 1)
		for starter in self.map.dummies:
			dummy = [x for x in self.powers if x.name == starter]
			if dummy:
				dummy = dummy[0]
				if not dummy.isDummy(): continue
			else:
				dummy = self.powerType(self, starter)
				self.powers.append(dummy)
				dummy.player = ['DUMMY']
			dummy.ceo = self.map.controls.get(starter) or []
		for starter in [x for x in self.powers if not x.type]:
			starter.abbrev = self.map.abbrev.get(starter.name, starter.name[0])
		for starter in [x for x in self.powers if not x.type]:
			starter.initialize(self)
			if starter.name in self.map.dummies: continue
			self.mailPress(None, [starter.name],
				'You have been selected to play %s in game %s.\n'
				'The first deadline will be %s.\n' %
				(self.anglify(starter.name), self.name, self.timeFormat()),
				subject = 'Diplomacy power assignment')
		self.sortPowers()
		self.start = self.getTime().format(3)
		if self.start[0] == '0': self.start = self.start[1:]
		self.changeStatus('active')
		#	---------------------------------------------
		#	Generate and broadcast initial unit positions
		#	and make the initial PostScript and gif map.
		#	---------------------------------------------
		lines = self.mapperHeader() + ['Starting position for ' +
			self.phaseName()] + self.list()
		lines += ['\nThe deadline for the first orders is %s.\n' %
			self.timeFormat(pseudo = 1)]
		self.mailResults([line + '\n' for line in lines],
			'Diplomacy game %s starting' % self.name)
		#	-------------------------------------------------------
		#	Save after sending, as self.list() will add power.sees.
		#	-------------------------------------------------------
		self.save()
		self.makeMaps()
	#	----------------------------------------------------------------------
	def parameters(self):
		timing, variant = '', []
		if self.phase == 'COMPLETED':
			try: del self.timing['NOT']
			except: pass
		for key, val in self.timing.items():
			timing += ' ' + key.title() + (val and (' ' + val) or '')
		timing = timing or ' Next 1D Move 3D'
		if 'DAYS' not in self.timing: timing += ' Days -MTWTF-'
		if self.map.name != self.variant: variant += [self.map.name.title()]
		if self.variant: variant += [self.variant.title()]
		if 'NO_DIAS' in self.rules: variant += ['No DIAS']
		text = ("\nThe parameters for '%s' %sre as follows:\n"
				'  Variant:  %s, Gunboat.\n  Timing:  %s\n  Press:    %s\n' %
			(self.name, ('a', 'we')[self.phase == 'COMPLETED'],
			', '.join(variant), timing, self.pressSettings()))
		flags = ', '.join([x for x in self.rules if x not in self.metaRules
			and x != 'EAVESDROP'])
		if flags: text += '\n'.join(textwrap.wrap('  Rules:    %s.' % flags,
			75, subsequent_indent = ' ' * 12)) + '\n'
		win = self.victory
		if self.outcome: self.year = int(self.outcome[0][1:-1])
		elif self.year == '-': self.year = int(self.map.phase.split()[1])
		try: div = [int(x[8:]) for x in self.map.flow
			if x[:8] == 'NEWYEAR:'][0]
		except: div = 1
		text += ('  Access:   Any.\n  Victory:  %d.\n  Judge:    %s.' %
			(win[min((self.year - int(self.map.phase.split()[1])) / div,
			len(win) - 1)], host.dpjudgeID))
		if self.start: text += '\n\nGame started: ' + self.start
		if self.end:
			victors = map(self.anglify, self.outcome[1:])
			if len(victors) > 1: victors[-1] = 'and ' + victors[-1]
			text += ('\nGame ended:   %s\n\n' % self.end +
				'\n'.join(textwrap.wrap('The game was ' +
				('won by ', 'declared a draw between ')[len(victors) > 1] +
				', '[len(victors) < 3:].join(victors) + '.\n', 75)))
		return text
	#	----------------------------------------------------------------------
	def list(self, email = None, playing = None, subject = ''):
		if not subject: subject = 'List of game ' + self.name
		elif subject[:4].upper() != 'RE: ': subject = 'RE: ' + subject
		if self.phase == 'COMPLETED':
			if email:
				self.openMail(subject, mailTo = email, mailAs = host.dpjudge)
				self.mail.write(
					"Game '%s' is completed.  No LIST available.  "
					'Use SUMMARY or HISTORY.' % self.name)
				self.mail.close()
			return
		lines = []
		for power in self.powers:
			spaced = 0
			if power.units or power.retreats:
				powerName = self.anglify(power.name) + ': '
				for unit in power.units + power.retreats.items():
					unit, option = (unit, (unit, None))[unit in power.units]
					if 'BLIND' in self.rules:
						shows = [x for x,y in
							power.visible(unit, 'H').items() if y & 8]
						if option:
							controllers = ['MASTER', power.name]
							boss = power.controller()
							if boss and boss not in controllers:
								controllers += [boss.name]
							controllers += [x.name for x in self.powers
								if x.omniscient and x.name not in controllers]
						if playing:
							if playing.name not in shows: continue
							if option and playing.name not in controllers:
								option = None
					if not spaced: lines += ['']
					spaced = 1
					if 'BLIND' in self.rules and not playing:
						if option:
							shows = [x for x in shows if x not in controllers]
							if shows:
								lines += ['SHOW ' + ' '.join(shows)]
								lines += [powerName + self.anglify(unit) + '.']
							shows = controllers
						lines += ['SHOW ' + ' '.join(shows)]
					lines += [powerName + self.anglify(unit) +
						(option and (' can retreat to ' +
						' or '.join(map(self.anglify, option))) or '') + '.']
				if 'BLIND' in self.rules and not playing: lines += ['SHOW']
		if 'active' in self.status or 'waiting' in self.status:
			lines += self.ownership(playing = (None, playing)
				['BLIND' in self.rules])
		if not email: return lines
		phase = self.phase.title().split()
		if len(phase) > 1:
			if phase[2][-1] == 's': phase[2] = phase[2][:-1]
			lines[:0] = ['Status of the %s phase for ' %
				phase[2] + self.phaseName()]
		if self.phase not in ('FORMING', 'COMPLETED'): lines[:0] = [
			"\nThe following players are signed up for game '%s':\n" %
			self.name + self.playerRoster('LIST', playing)[:-1]]
		lines[:0] = [self.parameters()]
		if self.avail:
			if self.avail[0].isdigit():
				what, why = 'join', (self.avail[0] + ' more player' +
					's'[self.avail[0] == '1':])
			else: why, what = ' and '.join([self.anglify(x.split('-')[0])
				for x in self.avail]), 'be taken over'
			lines[:0] = ["Game '%s' is waiting for %s to %s." %
				(self.name, why, what)]
		elif self.phase != 'COMPLETED':
			waiters = [self.anglify(x.name) for x in self.powers if x.wait]
			if waiters:
				if 'LIST_WAITERS' in self.rules:
					if len(waiters) > 1: waiters[-1] = 'and ' + waiters[-1]
					lines[:0] = [
						'The following player%s ha%s requested that '
						'orders not be processed\nuntil the deadline:\n' %
						('s'[len(waiters) == 1:],
						('s', 've')[len(waiters) > 1]) +
						', '[len(waiters) < 3:].join(waiters)]
				else: lines[:0] = [
					'One or more players have requested that '
					'orders not be processed\nuntil the deadline.']
			laters = [self.anglify(x) for x in self.latePowers()]
			if laters:
				if 'LIST_UNORDERED' in self.rules:
					if len(laters) > 1: laters[-1] = 'and ' + laters[-1]
					lines[:0] = [
						'The following player%s ha%s not yet submitted orders:'
						'\n' %
						('s'[len(laters) == 1:],
						('s', 've')[len(laters) > 1]) +
						', '[len(laters) < 3:].join(laters)]
				else: lines[:0] = [
					'One or more powers have not yet submitted orders.']
			lines[:0] = ["Game '%s' has a deadline of %s." %
				(self.name, self.timeFormat())]
		self.openMail(subject,
			mailTo = email, mailAs = host.dpjudge)
		if playing and not playing.isEliminated():
			lines += [self.playerOrders(playing)]
		self.mail.write('\n'.join(self.mapperHeader()) + '\n\n')
		self.mail.write('\n'.join(lines) + '\n')
		self.mail.close()
	#	----------------------------------------------------------------------
	def ownership(self, unowned = None, playing = None):
		self.includeOwnership = 0
		rules, master = self.rules, Power(self, 'MASTER')
		if unowned is None:
			homes = [x for y in self.powers for x in y.homes or []]
			unowned = [x for x in self.map.scs if x not in homes]
		if self.phase != self.map.phase:
			for power in self.powers:
				if power.type: continue
				power.centers = [x for x in power.centers
								if x not in ('SC?', 'SC*')]
				homes = power.homes
				if ('GARRISON' in rules and not power.centers
				and not power.type and (power.ceo
				or power.player and not power.isResigned())
				and not [0 for x in self.powers for y in x.units
					if x is not power and y[2:5] in homes]):
						power.centers = ['SC?'] * (len(power.units) + 1)
				if 'NO_PARTISANS' not in rules:
					held = len([x for x in homes if x not in power.centers])
					if 0 < held < len(homes): power.centers += (['SC*'] *
						len(self.map.partisan.get(power.name, [])))
		lines = ['']
		blind = 'BLIND' in rules
		hidden = 'HIDE_DUMMIES' in rules
		if blind: omnis = ['MASTER'] + [x.name for x in self.powers
			if x.omniscient]
		if 'VASSAL_DUMMIES' in rules and (blind or not hidden):
			lines += ['Vassal status of minor powers:', '']
			if blind and hidden and playing and playing.name not in omnis:
				lines += ['%s is a vassal of %s.' %
					(self.anglify(x.name), self.anglify(playing.name))
					for x in playing.vassals()]
			else:
				showing = blind and hidden and not playing
				for dummy in [x for x in self.powers if x.isDummy()]:
					if showing: lines += ['SHOW ' + ' '.join(omnis + (dummy.ceo
						and [x for x in dummy.ceo if x not in omnis] or []))]
					lines += [self.anglify(dummy.name) + (dummy.ceo and
						' is a vassal of %s.' % self.anglify(dummy.ceo[0]) or
						' is independent.')]
				if showing: lines += ['SHOW']
		showing = blind and not playing and 'SEE_ALL_SCS' not in rules
		lines += ['\nOwnership of supply centers:\n']
		for power in self.powers + [master]:
			if power is not master:
				controllers = [power.name]
				boss = power.controller()
				if boss: controllers += [boss.name]
			else: controllers = []
			if playing and playing.name not in omnis + controllers:
				continue
			if power is not master:
				powerName, centers = power.name, power.centers
				[unowned.remove(x) for x in centers if x in unowned]
			else: powerName, centers = 'UNOWNED', unowned
			powerName = self.anglify(powerName) + ':'
			for who in self.powers + [master]:
				seen = 0
				if who is power:
					seen = [(x, 'Undetermined Home SC')[x == 'SC!']
						for x in centers if x[-1] not in '?*']
				elif (showing and who is not master and not who.omniscient
				and who.name not in controllers):
					vassals = [who.name] + [x.name for x in who.vassals()]
					who.sees += [x for x in centers
						if x not in who.sees and [1 for y, z in
						power.visible(x).items() if z & 2
						and y in vassals]]
					seen = [x for x in centers if x in who.sees]
				if not seen: continue
				if showing:
					if who is master: lines += ['SHOW ' + ' '.join(omnis)]
					elif who is power: lines += ['SHOW ' +
						' '.join(omnis + controllers)]
					else: lines += ['SHOW ' + who.name]
				lines += [y.replace('\x7f', '-') for y in textwrap.wrap(
					('%-11s %s.' % (powerName,
					', '.join(map(self.anglify, sorted(seen)))))
					.replace('-', '\x7f'), 75, subsequent_indent = ' ' * 12)]
		if showing: lines += ['SHOW']
		return lines + ['']
	#	----------------------------------------------------------------------
	def mailResults(self, body, subject):
		#	-----------------------------------------------
		#	Mail results (tailored if BLIND) to all parties
		#	-----------------------------------------------
		if 'BLIND' in self.rules:
			for power in [x.name for x in self.powers] + ['MASTER']:
				lastLine, hide, text = '', 0, []
				for line in body:
					if line.startswith('SHOW'):
						showTo = line.split()[1:]
						hide = showTo and power not in showTo
					elif not hide and (line[:-1] or lastLine):
						lastLine = line[:-1]
						text += [line]
				self.mailPress(None, [power], ''.join(text), subject = subject)
		else: self.mailPress(None, ['All!'], ''.join(body), subject = subject)
		#	----------------------
		#	File into results file
		#	----------------------
		self.fileResults(body, subject)
	#	----------------------------------------------------------------------
	#							PRESS-HANDLING METHODS
	#	----------------------------------------------------------------------
	def eligiblePressRecipients(self, sendingPower, includeSelf = 0):
		#	------------------------------------
		#	You may send press to your own power
		#	if this is a grey or fake press game
		#	------------------------------------
		includeSelf |= ('WHITE_GREY' in self.rules
					or	'GREY_PRESS' in self.rules
					or	'FAKE_PRESS' in self.rules)
		#	---------------------------------------------------
		#	Determine any currently in-force press restrictions
		#	---------------------------------------------------
		late = []
		if (sendingPower.type == 'MONITOR'
		or	sendingPower.type == 'OBSERVER' and 'MUTE_OBSERVERS' in self.rules):
			rules = ['NO_PRESS']
		elif self.phase == 'FORMING':
			rules = [('PUBLIC_PRESS', 'NO_PRESS')['POWER_CHOICE' in self.rules]]
		elif self.phase == 'COMPLETED': rules = ['PUBLIC_PRESS']
		else:
			rules = self.rules
			#	-----------------------------------------
			#	Get a list of who is late (if it matters)
			#	-----------------------------------------
			late = ([], self.latePowers())['MUST_ORDER' in rules
				or (not self.avail and self.deadline and self.deadlineExpired()
				and ('LATE_SEND' not in rules or 'NO_LATE_RECEIVE' in rules))
				or 0]
			if sendingPower.name != 'MASTER' and sendingPower.name in late:
				if 'MUST_ORDER' in rules: rules = ['NO_PRESS']
				elif 'LATE_SEND' not in rules and 'NO_PRESS' not in rules:
					if ('TOUCH_PRESS' not in rules
					and 'REMOTE_PRESS' not in rules) or 'PUBLIC_PRESS' in rules:
						rules = ['PUBLIC_PRESS']
					else: rules = ['NO_PRESS']
		#	----------------------------------------
		#	Create list of eligible press recipients
		#	----------------------------------------
		if not self.powers: who = ['MASTER']
		else: who = self.powers + (['MASTER', 'ALL'], ['ALL', 'MASTER'])[
				'PRESS_MASTER' in self.rules]
		if sendingPower.name == 'MASTER': 
			who.remove('MASTER')
			who.append('JUDGEKEEPER')
		elif (('FTF_PRESS' in rules
		and (self.phaseType != 'M' or self.await or self.deadlineExpired()))
		or	'NO_PRESS' in rules): who = ['MASTER']
		#	-------------------------------------------------
		#	Backseat press.  For map-powers, a no-press game,
		#	and for non-map powers, a public-press game.
		#	-------------------------------------------------
		elif 'BACKSEAT_PRESS' in rules:
			who = who[-2:][:2 - (not sendingPower.type)]
		#	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
		#	Touch press.  This support is incomplete.
		#	Clicking "All" should be allowed ("All?")
		#	to send only to the listed powers?  Also,
		#	Remote press, which is kinda the opposite
		#	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
		elif 'TOUCH_PRESS' in rules or 'REMOTE_PRESS' in rules:
			if 'PUBLIC_PRESS' not in self.rules: who.remove('ALL')
			for power in self.powers:
				if not (power is sendingPower
				or [x for y in sendingPower.units for x in power.units
					if (self.validOrder(sendingPower, y, 'S ' + x, 0) == 1
					or self.validOrder(power, x, 'S ' + y, 0) == 1)
					and sendingPower.visible(y, 'H')[power.name] & 1
					and power.visible(x, 'H')[sendingPower.name] & 1]):
					if power in who: who.remove(power)
					elif power.name in who: who.remove(power.name)
			if 'REMOTE_PRESS' in rules:
				who = [x for x in self.powers if x is not sendingPower
					and x.centers and x not in who and x.name not in who]
				for power in who[:]:
					for unit, sc in [(y,z)
						for y in sendingPower.units for z in power.centers]:
						if self.abuts(unit[0], unit[2:], 'S', sc):
							who.remove(power)
							break
					else:
						for (unit, sc) in [(y,z)
							for y in power.units for z in sendingPower.centers]:
							if self.abuts(unit[0], unit[2:], 'S', sc):
								who.remove(power)
								break
				if 'PUBLIC_PRESS' in self.rules: who.append('ALL')
		elif 'PUBLIC_PRESS' in rules: who = who[-2:]
		readers = []
		for power in who:
			if type(power) not in (str, unicode):
				if power.type == 'MONITOR' or power.isResigned(): continue
				if 'HIDE_DUMMIES' not in self.rules:
					if power.address:
						if (power.isDummy()
						or sendingPower.ceo[:1] == [power.name]): continue
					elif power.ceo:
						if power.ceo[0] in ('MASTER', sendingPower.name):
							continue
					else: continue
				power = power.name
			if includeSelf or power != sendingPower.name: readers += [power]
		if (self.phase != 'FORMING' and 'NO_LATE_RECEIVE' in self.rules
		and sendingPower.name != 'MASTER' and self.deadlineExpired()):
			return [power for power in readers if power not in late]
		return readers
	#	----------------------------------------------------------------------
	def mailPress(self, sender, readers, message, claimFrom = None,
				  claimTo = None, subject = None, receipt = 1, private = 0):
		#	------------------------------------------------------------
		#	Parameters are:
		#		sender    - the Power sending press (None OK if subject)
		#		readers   -	a [list] of recipient NAMES (strings), which
		#					will be ['All'] for a broadcast or ['All!'];
		#					ignored if self.tester is set (see below)
		#					for results (to go to all AND any MONITORS).
		#		message   - a STRING of the lines forming the message
		#		claimFrom - a NAME (string) of Power to claim as sender
		#		claimTo   - as readers above; who to claim message is to
		#		subject   - if set, a subject to use instead of "press"
		#					and no pressHeader() will be inserted
		#		receipt   - if set to 0, no echo sent to sender
		#		private   - if set to 1, omniscient/eavesdroppers will
		#					not get a copy of the message
		#	------------------------------------------------------------
		if sender:
			claimFrom, claimTo = claimFrom or sender.name, claimTo or readers[:]
		sentTo = []
		#	---------------------------------------------------------------
		#	If there's a tester, send only to that address (if real)
		#	This variable can either be set for this game only, or in the
		#	host, so as to operate on all games on this server.
		#	When in interactive mode (e.g. using inspect), adding a '!' at
		#	the end of the string will ensure that upon the next call to
		#	self.save() the variable will be saved in the status file.
		#	To not send anything at all, use a single character, like '@'
		#	or '!' (the latter will store TESTER in the status file without
		#	a value).
		#	---------------------------------------------------------------
		if self.tester:
			email = self.tester 
			if email[-1] == '!': email = email[:-1]
			if len(email) > 2 and email[-1] != '@' and '@' in email:
				self.deliverPress(sender, 'MASTER', email, readers, message,
								  claimFrom, claimTo, subject = subject)
				sentTo += [email]
		else:
			#	-----------------------
			#	See who is listening in
			#	-----------------------
			omniscient = ['MASTER'][:'EAVESDROP' in self.rules
									or 'EAVESDROP!' in self.rules]
			omniscient += [x.name for x in self.powers if x.omniscient == 2]
			if private: omniscient = []
			#	----------------------------------------
			#	Now send the message to each destination
			#	----------------------------------------
			for reader in self.powers + ['MASTER'] + ['JUDGEKEEPER']:
				fromSender = 0
				#	----------------------------------
				#	Get the recipient's e-mail address
				#	----------------------------------
				if reader == 'MASTER':
					if (sender and sender.name != reader and readers == ['All']
					and 'PRESS_MASTER' in self.rules): continue
					power, email = reader, self.gm.address[0]
				elif reader == 'JUDGEKEEPER':
					fromSender = sender and sender.name != reader
					if (not sender or fromSender) and readers in (['All'], ['All!']): continue
					power, email = reader, host.judgekeeper
				else:
					if reader.type == 'MONITOR' and readers != ['All!']: continue
					power = reader.name
					if reader.address: email = reader.address[0]
					else:
						try: email = reader.controller().address[0]
						except: continue
				#	---------------------------------------------
				#	Make sure this party should receive the press
				#	---------------------------------------------
				if ((readers not in (['All'], ['All!'])
				and power not in (readers + (sender and [sender.name] or []))
				and power not in omniscient)
				or (sender and power == sender.name and not receipt)): continue
				#	-------------------------
				#	Format and send the press
				#	-------------------------
				if email not in sentTo:
					self.deliverPress(sender, power, email, readers, message,
									  claimFrom, claimTo, subject, fromSender)
					sentTo += [email]
		if not sender: return
		press = self.file('press')
		file = open(press, 'a')
		file.write((':: %s %s %s' % (self.phaseAbbr(),
			sender.name, ' '.join(readers))).encode('latin-1'))
		if claimFrom != sender.name:
			file.write(' | %s %s' % (claimFrom, ' '.join(claimTo)))
		file.write(('\n%s in %s:\n\n' %
			(self.pressHeader(claimFrom, claimTo, 0, claimFrom), self.name))
			.encode('latin-1'))
		file.write(message.encode('latin-1'))
		file.close()
		try: os.chmod(press, 0666)
		except: pass
		if (not self.tester and 'suspect' in self.status and
			host.judgekeeper not in sentTo):
			self.deliverPress(sender, 'MASTER', host.judgekeeper,
				readers, message, claimFrom, claimTo, subject, 1)
	#	---------------------------------------------------------------------
	def pressHeader(self, power, whoTo, reader, sender = 0, recipient = 0):
		text = ('Message', 'Broadcast message')[whoTo in (['All'], ['All!'])]
		omniscient = reader and (reader == 'MASTER' or [1 for x in self.powers
		if x.name == reader and x.omniscient])
		if sender:
			if sender != '(ANON)': text += ' from ' + self.anglify(sender)
			if omniscient and sender != power.name:
				text += ' [%s %s]' % (('by', 'from')[sender == '(ANON)'],
					self.anglify(power.name))
		else: text += ' sent'
		text += self.listReaders(whoTo)
		if recipient and omniscient and set(recipient) != set(whoTo):
			if text[-1] == ']': text = text[:-1] + ' '
			else: text += ' ['
			text += 'sent%s]' % ((self.listReaders(recipient),
			' as broadcast')[recipient in (['All'], ['All!'])])
		return text
	#	----------------------------------------------------------------------
	def listReaders(self, who):
		if not who or who in (['All'], ['All!']): return ''
		who = map(self.anglify, who)
		if len(who) == 1: return ' to ' + who[0]
		return ' to ' + ', '.join(who[:-1]) + ' and ' + who[-1]
	#	----------------------------------------------------------------------
	def deliverPress(self, sender, reader, email, recipient, message,
					 claimFrom, claimTo, subject = None, fromSender = 0):
		#	------------------------------------------------------
		#	If email is not None, the press is going to a specific
		#	private e-mail address, so it will look like it came
		#	from the host.dpjudge address, unless fromSender is
		#	explicitly set.
		#	------------------------------------------------------
		if email and not fromSender: mailAs = host.dpjudge
		elif sender.name == 'MASTER': mailAs = self.gm.address[0]
		else: mailAs = sender.address[0].split(',')[0]
		#	--------------
		#	Begin the mail
		#	--------------
		if subject: topic = subject
		elif not sender: topic = 'Diplomacy game %s notice' % self.name
		elif reader == sender.name:
			if recipient in (['All'], ['All!']): topic = 'Diplomacy broadcast sent'
			else: topic = 'Diplomacy press sent' + self.listReaders(recipient)
		elif claimFrom == '(ANON)': topic = 'Diplomacy press'
		else: topic = 'Diplomacy press from ' + self.anglify(claimFrom)
		self.openMail(topic, mailTo = email, mailAs = mailAs)
		mail = self.mail
		if not subject and sender and email:
			#	---------------------------------------
			#	The message is being sent directly to a
			#	player e-mail.  So format it ourselves.
			#	---------------------------------------
			#mail.write('\n'.join(self.mapperHeader()) + '\n')
			if reader == sender.name: mail.write(
				self.pressHeader(sender, recipient, reader) + ':\n\n')
			mail.write('%s in %s:\n\n' % (
			self.pressHeader(sender, claimTo, reader, claimFrom, recipient),
				self.name))
		#	--------------------
		#	Add the message body
		#	--------------------
		for line in message.split('\n'):
			if line.endswith('\r'): line = line[:-1]
			mail.write(line + '\n')
		#	---------
		#	Finish up
		#	---------
		if not subject and sender:
			if not email: mail.write('ENDPRESS\nSIGNOFF\n')
			elif reader == sender.name: mail.write('\nEnd of message.\n')
		mail.close()
	#	----------------------------------------------------------------------
	#							ADJUDICATION METHODS
	#	----------------------------------------------------------------------
	def ready(self, process = 0):
		return self.status[1] == 'active' and not self.error and (
			process == 2 or (('NO_DEADLINE' not in self.rules and
			self.deadline and self.deadline <= self.getTime())
			or process or not (self.await > 1 or
			[1 for power in self.powers if power.wait]
			or ('ALWAYS_WAIT' in self.rules and (self.phaseType == 'M'
			or self.phaseType in 'AR' and 'NO_MINOR_WAIT' not in self.rules))))
			and not self.latePowers(process))
	#	----------------------------------------------------------------------
	def findGoners(self, phase = 1):
		if self.phaseType == '-': return
		retreats, done, skip = {}, 0, 0
		while not skip or nextPhaseType not in 'MAR':
			nextPhaseType = self.findNextPhase(skip = skip).split()[-1][0]
			skip += 1
		if phase and (self.phaseType != 'R' or nextPhaseType != 'A'): return
		#	-------------------------------
		#	Create a dictionary listing all
		#	powers' potential retreat spots
		#	-------------------------------
		for power in self.powers: retreats[power] = [y[:3]
			for x in power.retreats.values() for y in x]
		#	----------------------------------------------------
		#	Set the goner flag if the player will own no centers
		#	----------------------------------------------------
		for power in self.powers:
			kept = len(power.centers)
			for other in self.powers:
				for unit in other.units:
					place = unit[2:5]
					if power is other: kept += place in self.map.scs
					else: kept -= place in power.centers
			if not [1 for x in retreats[power] if x in self.map.scs]:
				power.goner = not kept
		#	--------------------------------------------
		#	Now see if a goner's retreat can affect that
		#	of a non-goner.  If so, both are non-goners.
		#	--------------------------------------------
		while not done:
			done = 1
			for power, places in retreats.items():
				if power.goner and [x for y in places for x in self.powers
					if not x.goner and y in retreats[x]]:
					power.goner = done = 0
	#	----------------------------------------------------------------------
	def latePowers(self, after = 0):
		lateList = []
		#	----------------------------------------------------
		#	Determine if any power's retreats would be fruitless
		#	----------------------------------------------------
		self.findGoners()
		#	------------------------------
		#	See who is late and who is not
		#	------------------------------
		for power in [x for x in self.powers if not x.type and not x.cd]:
			cd = power.isCD(after)
			if self.phaseType == 'A':
				if power.adjust: continue
				units, centers = len(power.units), len(power.centers)
				if [x for x in power.centers if x in power.homes]:
					centers += (self.map.reserves.count(power.name) +
						min(self.map.militia.count(power.name),
						len([0 for x in power.units
							if x[2:5] in power.homes])))
				if cd and 'CD_BUILDS' not in self.rules and units < centers:
					sites = self.buildSites(power)
					need = min(self.buildLimit(power, sites), centers - units)
					power.adjust = ['BUILD WAIVED'] * need
					continue
				if (cd or centers == 0 or units == centers
				or (units < centers and not self.buildLimit(power))): continue
			elif self.phaseType == 'R':
				if power.adjust or not power.retreats: continue
				#	-----------------------------------------------------
				#	Disband all units with no future and no bounce-effect
				#	-----------------------------------------------------
				if cd or power.goner:
					if 'CD_RETREATS' not in self.rules or power.goner:
						power.adjust, power.cd = ['RETREAT %s DISBAND' % x
							for x in power.retreats], 1
					continue
			elif power.movesSubmitted() or cd: continue
			lateList += [power.name]
		return lateList
	#	----------------------------------------------------------------------
	def preMoveUpdate(self):
		#	---------------------------------------------------
		#	This method should be overridden by a variant class
		#	if it needs to do anything along with a movement
		#	phase (like send a broadcast or individual press).
		#	The moves are all decided and are in self.orders.
		#	NOTE that this function will NOT be invoked on
		#	phase previews -- only on actual processing!
		#	---------------------------------------------------
		return 1
	#	----------------------------------------------------------------------
	def postMoveUpdate(self):
		#	-------------------------------------------
		#	(See comment on Game.preMoveUpdate, above.)
		#	-------------------------------------------
		return 1
	#	----------------------------------------------------------------------
	def process(self, now = 0, email = None, roll = 0):
		#	----------------------------------------------------------------
		#	Tip: During tests or debugging, use self.tester to send mail to
		#	yourself only or, if you specify an invalid address like '@', to
		#	no one in particular.
		#	----------------------------------------------------------------
		if (now > 1 or self.ready(now) or self.preview
		or	self.graceExpired() and 'CIVIL_DISORDER' in self.rules):
			if not now and self.await < 2:
				if self.deadline and 'REAL_TIME' not in self.rules:
					#	-------------------------------------------
					#	If this game has a deadline, the cron job
					#	will find it next time around.  Mark that
					#	it should delay one cycle before processing
					#	(if the deadline hasn't passed yet).
					#	-------------------------------------------
					self.delay = self.deadline > self.getTime()
					return self.save()
				#	-----------------------------------------
				#	No deadline.  Process right away.
				#	Lock the game status file against changes
				#	and recursively call process with now
				#	augmented to 1.
				#	-----------------------------------------
				self.skip = None
				self.process(-1, email, roll)
				return
			#	---------------------------------------------
			#	We have received a PROCESS command via e-mail
			#	---------------------------------------------
			if not roll: self.processed = None
			if not self.preview: self.lateNotice(-1)
			if not self.preview: self.save(asBackup = 1)
			self.delay = None
			if self.phaseType == 'M':
				self.determineOrders()
				self.addCoasts()
				if not self.preview and not self.preMoveUpdate(): return
			for power in self.powers: power.wait = None
			if self.preview and email:
				tester, self.tester = self.tester, email
			self.resolve(roll = roll)
			if self.preview and email:
				self.tester = tester
			#	---------------------------------------------
			#	Move aside any rolled back status file backup
			#	---------------------------------------------
			if not self.preview and not roll: self.rollin()
		#	-------------------------------------------------
		#	Game not ready.  If we received a PROCESS command
		#	let the caller know we won't be honoring it.
		#	-------------------------------------------------
		elif now: return 'Game not ready for processing'
		#	---------------------------
		#	Update the game status file
		#	---------------------------
		if not self.preview:
			self.save()
	#	---------------------------------------------------------------------
	def reprocess(self, phase = None, includeFlags = 0):
		#	---------------------------------------------------------------
		#	Rollback to phase and immediately forward to the current phase,
		#	restoring orders and transient properties.
		#	The deadline remains unchanged and no message is broadcast.
		#	Mostly used after bug fixes to reproduce the results or when
		#	renaming the game to get the new name in the results for all
		#	phases.
		#	---------------------------------------------------------------
		if self.phase == 'FORMING': return
		textOnly, self.map.textOnly = self.map.textOnly, 1
		outphase, deadline = self.phase, self.deadline
		if outphase == 'COMPLETED':
			includeFlags |= 16
			outphase = self.outcome[0]
		else: outphase = self.phaseAbbr(outphase)
		self.tester += '@'
		error = (self.rollback(phase, includeFlags) or
			self.rollforward(outphase, includeFlags | 5))
		self.tester = self.tester[:-1]
		self.deadline = deadline
		self.map.textOnly = textOnly
		self.save()
		self.makeMaps()
		return error
	#	---------------------------------------------------------------------
	def rollback(self, phase = None, includeFlags = 0):
		#	---------------------------------------------------------------
		#	Rolls back to the specified phase, or to the previous phase if
		#	none is specified or to the FORMING stage if phase equals 1.
		#   Relevant bit values for includeFlags:
		#		1: include orders for each power
		#		2: include persistent power data
		#		16: force roll, even for inactive games or games with errors
		#	Bit 4 allows to include all transient data, which is always on.
		#	Bit 8 would remove all rules when saving, so gets masked out.
		#	Tip: During tests or debugging, use self.tester to send mail to
		#	yourself only or, if you specify an invalid address like '@', to
		#	no one in particular. With self.tester, a completed game will
		#	not be sent to the hall of fame.
		#	----------------------------------------------------------------
		includeFlags &= 247
		if self.phase == 'FORMING':
			return 'Cannot ROLLBACK forming game'
		waiting = self.status[1] == 'waiting'
		expected = ('active', 'completed')[self.phase == 'COMPLETED']
		if not includeFlags & 16 and (not waiting
		and self.status[1] not in ['completed', 'active'][
			'SOLITAIRE' not in self.rules:] or self.error):
			return ('ROLLBACK can only occur on an active or waiting, ' +
				'error-free game')
		if self.status[1] != expected: self.changeStatus(expected)
		outphase = (self.status[1] == 'completed' and
			self.outcome[0]) or self.map.phaseAbbr(self.phase, self.phase)
		startphase = self.probeStartPhase()
		if not startphase: return 'Invalid ROLLBACK start phase'
		startphase = self.phaseAbbr(startphase)
		if self.map.comparePhases(outphase, startphase) < 0:
			return 'Cannot ROLLBACK before start phase'
		if phase:
			if phase == 1: phase = 'FORMING'
			else:
				phase = phase.upper()
				if len(phase.split()) > 1: phase = self.phaseAbbr(phase)
			start = phase != 'FORMING' and (phase != startphase and 2 or 1) or 0
			if start and self.map.comparePhases(phase, startphase) < 0:
				return 'Cannot ROLLBACK before start phase'
			unphase = start and phase or startphase
			if unphase != outphase:
				if (self.map.comparePhases(unphase, outphase) >= 0 or 
					not os.path.isfile(self.file('status.' + unphase))):
					return 'Invalid ROLLBACK phase'
				while unphase != outphase:
					try: os.rename(self.file('status.' + unphase),
						self.file('status.' + unphase + '.0'))
					except: pass
					unphase = self.probeNextPhase(self.phaseLong(unphase))
					if not unphase: break
					unphase = self.phaseAbbr(unphase)
		else:
			phase = self.probePreviousPhase(self.phaseLong(outphase))
			if not phase: return 'Invalid ROLLBACK phase'
			phase = self.map.phaseAbbr(phase, phase)
			start = phase != 'FORMING' and (phase != startphase and 2 or 1) or 0
			try: os.rename(self.file('status.' + phase),
				self.file('status.' + phase + '.0'))
			except: pass
		if os.path.isfile(self.file('status.' + outphase + '.0')):
			try: os.unlink(self.file('status.rollback'))
			except: pass
			os.rename(self.file('status.' + outphase + '.0'),
				self.file('status.rollback'))
		os.rename(self.file('status'), self.file('status.' + outphase + '.0'))
		try: os.unlink(self.file('summary'))
		except: pass
		if phase != outphase:
			if os.path.isfile(self.file('results.0')):
				try: os.unlink(self.file('results'))
				except: pass
			else:
				try: os.rename(self.file('results'), self.file('results.0'))
				except: pass
		if not start:
			self.reinit(4)
			self.phase = 'FORMING'
			self.changeStatus(('forming', 'waiting')[waiting])
			self.save()
			self.mailPress(None, ['All!'],
				"Diplomacy game '%s' has been reset to the forming state,\n"
				'but the players retain their assigned power.\n'
				"The Master will have to either set the game to 'active' mode\n"
				'or roll forward.\n' % self.name,
				subject = 'Diplomacy rollback notice')
			name = self.name.encode('latin-1')
			try: [os.unlink(host.gameMapDir + '/' + x)
				for x in os.listdir(host.gameMapDir)
				if x.startswith(name)
				and re.match('^_?\.', x[len(name):])]
			except: pass
		else:
			# Load the phase.
			self.loadStatus('status.' + phase + '.0', includeFlags | 4)
			self.await = self.await > 1 and self.await
			self.skip = None
			self.changeStatus(('active', 'waiting')[waiting])
			self.setDeadline()
			self.delay = None
			self.save()
			self.mailPress(None, ['All!'],
				"Diplomacy game '%s' has been rolled back to %s\n"
				'and all orders have been %s.\n' %
				(self.name, self.phaseName(form = 2),
				includeFlags & 1 and 'restored' or 'cleared') +
				('NO_DEADLINE' not in self.rules and
				'\nThe new deadline is %s.\n' % self.timeFormat() or ''),
				subject = 'Diplomacy rollback notice')
			if phase != outphase or not os.path.isfile(self.file('results')):
				# Truncate the results
				if os.path.isfile(self.file('results.0')):
					file = open(self.file('results.0'), 'r', 'latin-1')
					lines = file.readlines()
					file.close()
					for num, text in enumerate(lines):
						if '%s ' % self.name + phase in text: break
					else:
						self.error += ['Diplomacy results for phase ' + phase +
							' not found in results file']
						num = len(lines)
					file = open(self.file('results'), 'w', 'latin-1')
					file.writelines(lines[:num-1])
					file.close()
					try: os.chmod(self.file('results'), 0666)
					except: pass
				else: self.error += ['No results file found']
			if phase != outphase or not glob.glob('%s/%s.*gif' %
				(host.gameMapDir, self.name)):
				# Remake the maps
				if start == 1:
					name = self.name.encode('latin-1')
					try: [os.unlink(host.gameMapDir + '/' + x)
						for x in os.listdir(host.gameMapDir)
						if x.startswith(name)
						and re.match('^_?\.', x[len(name):])
						and x.endswith('_.gif')]
					except: pass
				self.makeMaps()
		if self.error:
			return 'Errors during ROLLBACK:\n' + '\n'.join(self.error)
	#	---------------------------------------------------------------------
	def rollforward(self, phase = None, includeFlags = 4):
		#	---------------------------------------------------------------
		#	Rolls forward to the specified phase, or to the next phase if
		#	none is specified or to the ultimate rolled back phase if phase
		#	equals 1.
		#   Relevant bit values for includeFlags:
		#		1: include orders for each power
		#		2: include persistent data
		#		4: include transient data
		#		16: force roll, even for inactive games or games with errors
		#	Bit 8 would remove all rules when saving, so gets masked out.
		#	Tip: During tests or debugging, use self.tester to send mail to
		#	yourself only or, if you specify an invalid address like '@', to
		#	no one in particular.
		#	----------------------------------------------------------------
		includeFlags &= 247
		if self.phase == 'COMPLETED':
			return 'Cannot ROLLFORWARD completed game'
		elif self.phase == 'FORMING' and phase == 'FORMING': return
		waiting = self.status[1] == 'waiting'
		expected = ('active', 'forming')[self.phase == 'FORMING']
		if not includeFlags & 16 and (not waiting and
			self.status[1] != expected or self.error):
			return ('ROLLFORWARD can only occur on an active or waiting, ' +
				'error-free game')
		if self.status[1] != expected: self.changeStatus(expected)
		if os.path.exists(self.file('results.0')):
			file = open(self.file('results.0'), encoding='latin-1')
			rlines = file.readlines()
			file.close()
		else: rlines = None
		preview, self.preview = self.preview, 0
		self.tester += '@'
		if self.phase == 'FORMING':
			self.status[1] = 'forming'
			rlines = self.parseProcessed(rlines, 'starting')
			self.begin(roll = 1)
			if not phase: phase = self.phase
		elif waiting: self.status[1] = 'active'
		unphase = outphase = self.map.phaseAbbr(self.phase, self.phase)
		if not os.path.isfile(self.file('status.' + outphase + '.0')):
			return 'Invalid ROLLFORWARD phase'
		if not phase:
			# Check for the next phase.
			outphase = self.probeNextPhase()
			if not outphase: return 'Invalid ROLLFORWARD phase'
			phase = self.probeNextPhase(outphase)
			if not phase: return 'Invalid ROLLFORWARD phase'
			phase, outphase = self.phaseAbbr(phase), self.phaseAbbr(outphase)
		elif phase == 1:
			unphase = self.phase
			while unphase:
				phase = unphase
				unphase = self.probeNextPhase(unphase)
			phase = self.map.phaseAbbr(phase, phase)
			unphase = outphase
		else:
			phase = phase.upper()
			if len(phase.split()) > 1: phase = self.phaseAbbr(phase)
		if phase != outphase:
			if (self.map.comparePhases(phase, outphase) <= 0 or 
				not os.path.isfile(self.file('status.' + phase + '.0'))):
				return 'Invalid ROLLFORWARD phase'
			unphase = outphase
			while phase != unphase:
				# Load the phase, including orders.
				self.loadStatus('status.' + unphase + '.0',
					includeFlags | 1)
				# Capture the deadline and processed time.
				rlines = self.parseProcessed(rlines, unphase)
				# Process the phase, suppressing any mail
				self.process(now = 2, roll = includeFlags & 4 and 2 or 1)
				try: os.unlink(self.file('status.' + unphase + '.0'))
				except: pass
				if self.phase == 'COMPLETED':
					unphase = self.outcome[0]
					break
				unphase = self.map.phaseAbbr(self.phase, self.phase)
				if not os.path.isfile(self.file('status.' + unphase +
					'.0')): return 'Invalid ROLLFORWARD phase'
			self.makeMaps()
		self.preview, self.tester = preview, self.tester[:-1]
		# Merge the results of the rolled phases into results.0.
		self.processed = None
		if rlines:
			num = 0
			for line in rlines:
				if (line.startswith('Subject:')
				and line.split()[-1] == unphase): break
				num += 1
			else: rlines = None
			if rlines:
				shutil.copyfile(self.file('results'), self.file('results.0'))
				file = open(self.file('results.0'), 'a', encoding='latin-1')
				file.writelines(rlines[num-1:])
				file.close()
			else: os.unlink(self.file('results.0'))
		# Load the last phase
		prephase = self.phase
		self.loadStatus('status.' + unphase + '.0', includeFlags)
		self.await = self.await > 1 and self.await
		self.skip = None
		if self.phase != 'COMPLETED':
			self.changeStatus(('active', 'waiting')[waiting])
			self.setDeadline()
			self.delay = None
			self.save()
			self.mailPress(None, ['All!'],
				"Diplomacy game '%s' has been rolled forward to %s\n"
				'and all orders have been %s.\n' %
				(self.name, self.phaseName(form = 2),
				includeFlags & 1 and 'restored' or 'cleared') +
				('NO_DEADLINE' not in self.rules and
				'\nThe new deadline is %s.\n' % self.timeFormat() or ''),
				subject = 'Diplomacy rollforward notice')
		else:
			if prephase != 'COMPLETED' and self.outcome:
				victors = self.outcome[1]
				self.outcome, self.phase = None, prephase
				self.proposal = [len(victors) == 1 and victors[0] or
				('DIAS', 'NO_DIAS')['NO_DIAS' in self.rules]]
				self.endByAgreement(roll = 1)
			else:
				self.changeStatus('completed')
				self.save()
				self.mailPress(None, ['All!'],
					'The game is over once more. Thank you for playing.')
		if self.error:
			return 'Errors during ROLLFORWARD:\n' + '\n'.join(self.error)
	#	----------------------------------------------------------------------
	def rollin(self, branch = None):
		#	-----------------------------------------------------------------
		#	Rolls out all currently rolled back phases.
		#	Removes the results.0 backup file.
		#   Optionally rolls in a previously rolled out branch, starting from 
		#	the current phase.
		#	Returns the branch number of the rolled out branch if any.
		#	-----------------------------------------------------------------
		if branch and not os.path.isfile(self.file('status.' +
			self.phaseAbbr() + '.' + `branch`)): return 'Invalid ROLLIN phase'
		statusList, idx = glob.glob(self.file('status.*.0')), None
		if statusList:
			idx = 1
			while glob.glob(self.file('status.*.' + `idx`)): idx += 1
			for x in statusList:
				os.rename(x, x[:-1] + `idx`)
		try: os.unlink(self.file('results.0'))
		except: pass
		if branch:
			for x in glob.glob(self.file('status.*.' + `branch`)):
				phase = x.split('.')[-2]
				if self.map.comparePhases(phase, self.phase) >= 0:
					os.rename(x, self.file('status.' + phase + '.0'))
		return idx
	#	----------------------------------------------------------------------
	def parseProcessed(self, lines, phase):
		self.processed = None
		if not lines: return
		num = 0
		for line in lines:
			if line.startswith('Subject:') and line.split()[-1] == phase: break
			num += 1
		else: return lines
		if num > 1: lines = lines[num-1:]
		if lines[0].startswith('From '):
			self.processed = self.getTime(' '.join(lines[0].split()[2:]), 6)
		for line in lines[2:]:
			if not line.rstrip(): continue
			if not line.startswith(':: '): break
			word = line.split()
			if word[1] == "Deadline:":
				if word[-1] == (self.zone and self.zone.tzname() or 'GMT'):
					self.deadline = self.getTime(' '.join(word[3:-1]))
				else:
					self.deadline = Time(word[-1], ' '.join(word[3:-1]))
					self.processed.zone = self.deadline.zone
					self.processed = self.processed.changeZone(self.zone)
					self.deadline = self.deadline.changeZone(self.zone)
				break
		return lines
	#	----------------------------------------------------------------------
	def occupant(self, site, anyCoast = 0):
		#	-------------------------------------
		#	Returns the occupant of a site:
		#	"STP" --> "A STP" or "F STP/NC", etc.
		#	Returns None if no unit at that site.
		#	-------------------------------------
		if anyCoast: site = site[:3]
		for unit in self.command:
			if unit[2:].startswith(site): return unit
	#	----------------------------------------------------------------------
	def strengths(self):
		#	----------------------------------------------------------------
		#	This function sets self.combat to a dictionary of dictionaries,
		#	specifying each potential destination for every piece, with the
		#	strengths of each unit's attempt to get (or stay) there, and
		#	with the givers of supports that DON'T count toward dislodgement
		#	(i.e., supports given by the power owning the occupying unit).
		#	For example, the following orders, all by the same power:
		#	A MUN H, A SIL - MUN, A BOH S A SIL - MUN, A RUH - MUN
		#	would result in:
		#	{ 'MUN': { 1 : [ ['A MUN', [] ],
		#					 ['A RUH', [] ] ],
		#			   2 : [ ['A SIL', ['A BOH'] ] ]
		#			 }
		#	}
		#	----------------------------------------------------------------
		self.combat = {}
		for unit, order in self.command.items():
			word = order.split()
			if word[0] != '-' or self.result[unit]:
				place, strength = unit[2:5], 1
			else:
				origin = len(word) > 2 and word[-3] or unit[2:]
				place = word[-1][:3]
				pair, rules = (origin, place), self.map.abutRules
				#	----------------------------------------
				#	Adjacencies listed in Map.abutRules['*']
				#	cause unit movement to be HALF-strength.
				#	----------------------------------------
				if pair in rules.get('*', []): strength = 0.5
				#	----------------------------------------
				#	Adjacencies listed in Map.abutRules['~']
				#	cause unit movement to be ZERO-strength.
				#	----------------------------------------
				else: strength = +(pair not in rules.get('~', []))
			self.combat.setdefault(place, {}).setdefault(
				strength + self.supports[unit][0], []).append(
				[unit, self.supports[unit][1]])
	#	----------------------------------------------------------------------
	def checkDisruptions(self, mayConvoy, result, coresult = None):
		#	------------------------------------------------
		#	On entry, mayConvoy is the unit:order dictionary
		#	for all convoys that have a chance to succeed.
		#	On exit, the self.result entry for the convoying
		#	army, if any of its fleets WOULD BE dislodged,
		#	will BE SET TO the "result" parameter.
		#	------------------------------------------------
		for unit, order in mayConvoy.items():
			word = order.split()
			for place in [word[x] for x in range(1, len(word) - 1, 2)]:
				area, convoyer = place[:3], 'AF'[unit[0] == 'A'] + ' ' + place
				strongest = self.combat[area][max(self.combat[area])]
				for x in strongest:
					if self.unitOwner(convoyer) != self.unitOwner(x[0]): break
				else: continue
				if convoyer in [x[0] for x in strongest]:
					if 'WEAK_CONVOYS' not in self.rules: continue
				elif (len(strongest) > 1
				and 'SAFE_CONVOYS' not in self.rules): continue
				self.result[unit] = [result]
				if coresult: self.result[convoyer] = [coresult]
	#	----------------------------------------------------------------------
	def boing(self, unit):
		#	------------------------------------------
		#	Mark a unit bounced, and update the combat
		#	table to show the unit as having strength
		#	one at its current location.
		#	------------------------------------------
		self.result[unit] += ['bounce']
		self.combat.setdefault(unit[2:5], {}).setdefault(
			1 - ('WEAK_BOUNCES' in self.rules), []).append([unit, []])
		return 1
	#	----------------------------------------------------------------------
	def bounce(self):
		#	--------------------------------------------------------
		#	This method marks all units that can't get where they're
		#	going as "bounce"d.  It loops to handle bounce-chains.
		#	--------------------------------------------------------
		bounced = 1
		while bounced:
			bounced = 0
			#	------------------------------------------------
			#	STEP 6.  MARK (non-convoyed) PLACE-SWAP BOUNCERS
			#	------------------------------------------------
			for unit, order in self.command.items():
				word = order.split()
				if self.result[unit] or word[0] != '-' or len(word) > 2:
					continue
				crawlOk, site = 'COASTAL_CRAWL' in self.rules, '- ' + unit[2:]
				swap = self.occupant(word[1], anyCoast = not crawlOk)
				if not (crawlOk and swap and swap[0] == unit[0] == 'F'):
					site = site.split('/')[0]
				if not (self.command.get(swap, '').find(site)
				or self.result[swap]):
					me = self.supports[unit][0] - len(self.supports[unit][1])
					he = self.supports[swap][0] - len(self.supports[swap][1])
					we = self.unitOwner(unit) is self.unitOwner(swap) \
					or self.supports [unit][0] == self.supports[swap][0]
					if we or me <= he: self.boing(unit)
					if we or he <= me: self.boing(swap)
					bounced = 1
			if bounced: continue
			#	-----------------------
			#	No (more) swap-bouncers
			#	--------------------------------
			#	STEP 7.  MARK OUTGUNNED BOUNCERS
			#	--------------------------------
			for place, conflicts in self.combat.items():
				strength = sorted(conflicts.keys())
				for key in strength:
					if key != strength[-1] or len(conflicts[key]) != 1:
						for unit, noHelp in conflicts[key]:
							if (not self.result[unit]
							and self.command[unit][0] == '-'):
								bounced = self.boing(unit)
			if bounced or 'FRIENDLY_FIRE' in self.rules: continue
			#	----------------------------
			#	No (more) outgunned bouncers
			#	------------------------------------
			#	STEP 8.  MARK SELF-DISLODGE BOUNCERS
			#	------------------------------------
			for place, conflicts in self.combat.items():
				strength = sorted(conflicts.keys())
				if len(conflicts[strength[-1]]) != 1: continue
				strongest = conflicts[strength[-1]][0][0]
				if (self.command[strongest][0] != '-'
				or self.result[strongest]): continue
				noHelp = len(conflicts[strength[-1]][0][1])
				guy = self.occupant(place)
				if guy:
					owner = self.unitOwner(guy)
					if ((self.command[guy][0] != '-' or self.result[guy])
					and (owner is self.unitOwner(strongest)
					and	not ('DUMMY_FIRE' in self.rules and owner.isDummy())
					or	(len(strength) > 1
					and strength[-1] - noHelp <= strength[-2]))):
						bounced = self.boing(strongest)
			#	--------------------------------
			#	No (more) self-dislodge-bouncers
			#	--------------------------------
	#	----------------------------------------------------------------------
	def cutSupport(self, unit, direct = 0):
		#	--------------------------------------------------
		#	See if the order made by the unit cuts a support
		#	If so, cut it.  If "direct" is set, the order must
		#	not only be a move, but also a non-convoyed move.
		#	--------------------------------------------------
		order = self.command[unit]
		word = order.split()
		if word[0] != '-' or (direct and len(word) > 2): return
		otherUnit = self.occupant(word[-1], anyCoast = 1)
		coord = self.command.get(otherUnit, 'no unit at dest').split()
		supportTarget = 'F ' + coord[-1][:3]
		if (coord[0] == 'S' and	'cut' not in self.result[otherUnit]
		and	'void' not in self.result[otherUnit]
		#	EXCEPTION A: CANNOT CUT SUPPORT YOU YOURSELF ARE GIVING
		and (self.unitOwner(unit) is not self.unitOwner(otherUnit)
			#	EXCEPTION TO EXCEPTION A: THE FRIENDLY_FIRE RULE
			or 'FRIENDLY_FIRE' in self.rules
			or 'DUMMY_FIRE' in self.rules and self.unitOwner(unit).isDummy())
		#	EXCEPTION B: CANNOT CUT SUPPORT FOR A MOVE AGAINST YOUR LOCATION
		and coord[-1][:3] != unit[2:5]
		#	EXCEPTION C: OR (IF CONVOYED) FOR OR AGAINST ANY CONVOYING FLEET
		and	(len(word) == 2 or self.command.get(supportTarget, 'H')[0] != 'C'
			or 'void' in self.result.get(supportTarget, []))
		#	EXCEPTION D: OR IF THE MOVE IS ACROSS A SPECIAL ('*') BOUNDARY
		and (unit[2:], word[-1]) not in self.map.abutRules.get('*', [])
		#	EXCEPTION E: OR IF THE MOVE IS UNSUPPORTED AND ACROSS A STRAIT (~)
		and ((unit[2:], word[-1]) not in self.map.abutRules.get('~', [])
			or self.supports[unit][0] >= 1)):
			#	-------------------------
			#	Okay, the support is cut.
			#	-------------------------
			self.result[otherUnit] += ['cut']
			affected = ' '.join(coord[1:3])
			self.supports[affected][0] -= 1
			if otherUnit in self.supports[affected][1]:
				self.supports[affected][1].remove(otherUnit)
	#	----------------------------------------------------------------------
	def resolveMoves(self):
		#	-------------------------------------------------
		#	Fill self.command from the self.orders dictionary
		#	-------------------------------------------------
		self.command = {}
		for unit in [y for x in self.powers for y in x.units]:
			self.command[unit] = self.orders.get(unit, 'H')
			if hasattr(self.command[unit], 'order'):
				self.command[unit] = self.command[unit].order
		#	------------------------------------------
		#	STEP 0: DECLARE ALL RESULTS AS YET UNKNOWN
		#	------------------------------------------
		self.result, self.supports, mayConvoy = {}, {}, {}
		for unit in self.command:
			self.result[unit], self.supports[unit] = [], [0, []]
		#	-------------------------------------------
		#	STEP 1A. CANCEL ALL INVALID ORDERS GIVEN TO
		#			 UNITS ATTEMPTING TO MOVE BY CONVOY
		#	-------------------------------------------
		for unit, order in self.command.items():
			word = order.split()
			if word[0] != '-' or len(word) == 2: continue
			for convoyer in range(1, len(word) - 1, 2):
				convoyOrder = self.command.get(
					'AF'[unit[0] == 'A'] + ' ' + word[convoyer])
				if (convoyOrder not in
					['C %s - ' % x + word[-1] for x in (unit, unit[2:])]):
					if convoyOrder or 'SHOW_PHANTOM' in self.rules:
						self.result[unit] += ['no convoy']
					else: self.command[unit] = 'H'
					break
			#	----------------------
			#	List the valid convoys
			#	----------------------
			else: mayConvoy[unit] = order
		#	-----------------------------------------
		#	STEP 1B. CANCEL ALL INVALID CONVOY ORDERS
		#	-----------------------------------------
		for unit, order in self.command.items():
			if order[0] != 'C': continue
			word, moverType = order.split(), 'AF'[unit[0] == 'A']
			if word[1] != moverType: word[1:1] = [moverType]
			mover = moverType + ' ' + word[2]
			if self.unitOwner(mover):
				convoyer = mayConvoy.get(mover, '').split()
				if unit[2:] not in convoyer or word[-1] != convoyer[-1]:
					self.result[unit] += ['void']
			elif 'SHOW_PHANTOM' in self.rules: self.result[unit] += ['void']
			else: self.command[unit] = 'H'
		#	-----------------------------------------------------------
		#	STEP 2. CANCEL INCONSISTENT SUPPORT ORDERS AND COUNT OTHERS
		#	-----------------------------------------------------------
		for unit, order in self.command.items():
			if order[0] != 'S': continue
			word, signal = order.split(), 0
			#	----------------------------------------------
			#	See if the unit is allowed to give the support
			#	----------------------------------------------
			if 'SIGNAL_SUPPORT' in self.rules:
				if word[-1] == '?':
					signal = 1
					del word[-1]
					self.result[unit] += ['void']
					self.command[unit] = ' '.join(word)
			#	------------------------------------------------------
			#	Remove any trailing "H" from a support-in-place order.
			#	------------------------------------------------------
			if word[-1] == 'H':
				del word[-1]
				self.command[unit] = ' '.join(word)
			#	---------------------------------------------
			#	Stick the proper unit type (A or F) into the
			#	order; all supports will have it from here on
			#	---------------------------------------------
			where = 1 + (word[1] in 'AF')
			guy = self.occupant(word[where])
			#	---------------------------------------------
			#	See if there is a unit to receive the support
			#	---------------------------------------------
			if not guy:
				if 'SHOW_PHANTOM' not in self.rules: self.command[unit] = 'H'
				elif not signal: self.result[unit] += ['void']
				continue
			word[1:where + 1] = guy.split()
			self.command[unit] = ' '.join(word)
			#	---------------------------------------------------
			#	See if the unit's order matches the supported order
			#	---------------------------------------------------
			if signal: continue
			coord = self.command[guy].split()
			if ((len(word) < 5 and coord[0] == '-')
			or (len(word) > 4 and (coord[0], coord[-1]) != ('-', word[4]))
			or 'no convoy' in self.result[guy]):
				self.result[unit] += ['void']
				continue
			#	---------------------------
			#	Okay, the support is valid.
			#	---------------------------
			self.supports[guy][0] += 1
			#	----------------------------------------------
			#	If the unit is owned by the owner of the piece
			#	being attacked, add the unit to those whose
			#	supports are not counted toward dislodgement.
			#	----------------------------------------------
			if coord[0] != '-': continue
			owner = self.unitOwner(unit)
			other = self.unitOwner(self.occupant(coord[-1], anyCoast = 1))
			if (owner is other and 'FRIENDLY_FIRE' not in self.rules
			and not (owner.isDummy() and 'DUMMY_FIRE' in self.rules)):
				self.supports[guy][1] += [unit]
		#	-------------------------------------------------------
		#	STEP 3.  LET DIRECT (NON-CONVOYED) ATTACKS CUT SUPPORTS
		#	-------------------------------------------------------
		[self.cutSupport(x, 1) for x in self.command if not self.result[x]]
		#	--------------------------------------------
		#	STEPS 4 AND 5.  DETERMINE CONVOY DISRUPTIONS
		#	--------------------------------------------
		cut, cutters = 1, []
		while cut:
			cut = 0
			self.strengths()
			#	----------------------------------------------------------
			#	STEP 4.  CUT SUPPORTS MADE BY (non-maybe) CONVOYED ATTACKS
			#	----------------------------------------------------------
			self.checkDisruptions(mayConvoy, 'maybe')
			for unit in mayConvoy:
				if self.result[unit] or unit in cutters: continue
				self.cutSupport(unit)
				cutters += [unit]
				cut = 1
			if cut: continue
			#	--------------------------------------------------
			#	STEP 5.  LOCATE NOW-DEFINITE CONVOY DISRUPTIONS,
			#	         VOID SUPPORTS THESE CONVOYERS WERE GIVEN,
			#	         AND ALLOW CONVOYING UNITS TO CUT SUPPORT.
			#	--------------------------------------------------
			self.checkDisruptions(mayConvoy, 'no convoy', 'disrupted')
			for unit in mayConvoy:
				if 'no convoy' in self.result[unit]:
					for sup, help in self.command.items():
						if not (help.find('S ' + unit) or self.result[sup]):
							self.result[sup] = ['no convoy']
					self.supports[unit] = [0, []]
				elif 'maybe' in self.result[unit] and unit not in cutters:
					self.result[unit], cut = [], 1
					self.cutSupport(unit)
					cutters += [unit]
		#	-------------------------------------------------------
		#	Recalculate strengths now that some are reduced by cuts
		#	-------------------------------------------------------
		self.strengths()
		#	--------------------------------------------------
		#	Mark bounces, then dislodges, and if any dislodges
		#	caused a cut, loop over this whole kaboodle again.
		#	--------------------------------------------------
		self.dislodged, cut = {}, 1
		while cut:
			#	-------------------------
			#	STEPS 6-8.  MARK BOUNCERS
			#	-------------------------
			self.bounce()
			#	---------------------------------------
			#	STEP 9.  MARK SUPPORTS CUT BY DISLODGES
			#	---------------------------------------
			cut = 0
			for unit, order in self.command.items():
				if order[0] != '-' or self.result[unit]: continue
				attackOrder = order.split()
				victim = self.occupant(attackOrder[-1], anyCoast = 1)
				if (victim
				and self.command[victim][0] == 'S' and not self.result[victim]):
					word = self.command[victim].split()
					supported, supSite = self.occupant(word[2]), word[-1][:3]
					#	-------------------------------------------------
					#	This next line is the key.  Convoyed attacks can
					#	dislodge, but even when doing so, they cannot cut
					#	supports offered for or against a convoying fleet
					#	(They can cut supports directed against the
					#	original position of the army, though.)
					#	-------------------------------------------------
					if len(attackOrder) > 2 and supSite != unit[2:5]: continue
					self.result[victim] += ['cut']
					cut = 1
					for sups in self.combat.get(supSite, {}):
						for guy, noHelp in self.combat[supSite][sups]:
							if guy != supported: continue
							self.combat[supSite][sups].remove([guy, noHelp])
							if not self.combat[supSite][sups]:
								del self.combat[supSite][sups]
							sups -= 1
							if victim in noHelp: noHelp.remove(victim)
							self.combat[supSite].setdefault(sups, []).append(
								[guy, noHelp])
							break
						else: continue
						break
		#	---------------------------------------------
		#	STEP 10.  MARK DISLODGEMENTS AND UNBOUNCE ALL
		#	          MOVES THAT LEAD TO DISLODGING UNITS
		#	---------------------------------------------
		for unit, order in self.command.items():
			if order[0] != '-' or self.result[unit]: continue
			site = unit[2:5]
			loser = self.occupant(order.split()[-1], anyCoast = 1)
			if loser and (self.command[loser][0] != '-' or self.result[loser]):
				self.result[loser] = [x for x in self.result[loser]
					if x != 'disrupted'] + ['dislodged']
				self.dislodged[loser] = site
				#	-----------------------------------------------------
				#	Check for a dislodged swapper (attacker and dislodged
				#	unit must not be convoyed).  If found, remove the
				#	swapper from the combat list of the attacker's space.
				#	-----------------------------------------------------
				if self.command[loser][2:5] == site and '-' not in order[1:]:
					for sups, items in self.combat.get(site, {}).items():
						item = [x for x in items if x[0] == loser]
						if item:
							self.noEffect(item[0], site)
							break
			#	----------------------------------------------
			#	Unbounce any powerful-enough move that can now
			#	take the spot being vacated by the dislodger.
			#	----------------------------------------------
			if site in self.combat: self.unbounce(site)
		#	------------
		#	All finished
		#	------------
	#	----------------------------------------------------------------------
	def noEffect(self, unit, site):
		sups = [x for x,y in self.combat[site].items() if unit in y][0]
		self.combat[site][sups].remove(unit)
		if not self.combat[site][sups]:
			del self.combat[site][sups]
			if not self.combat[site]: del self.combat[site]
	#	----------------------------------------------------------------------
	def unbounce(self, site):
		most = max(self.combat[site])
		if len(self.combat[site][most]) > 1: return
		unbouncer = self.combat[site][most][0][0]
		if 'bounce' in self.result[unbouncer]:
			self.result[unbouncer].remove('bounce')
			try:
				del self.dislodged[unbouncer]
				return self.result[unbouncer].remove('dislodged')
			except:
				nextSite = unbouncer[2:5]
				self.noEffect([unbouncer, []], nextSite)
				if nextSite in self.combat: self.unbounce(nextSite)
	#	----------------------------------------------------------------------
	def anglify(self, words, power = None, retreating = 0):
		text, tokens, word = [], words.split(), ''
		if 'C' in tokens:
			num, unit = tokens.index('C') + 1, 'AF'[tokens[0] == 'A']
			if tokens[num] != unit: tokens.insert(num, unit)
		for num in range(len(tokens)):
			building, removing = word[:5] == 'Build', word == 'Removes'
			word = tokens[num]
			if word == 'RETREAT': continue
			if word == 'A':
				if building: word = 'an army in'
				elif removing: word = 'the army in'
				elif retreating: word = 'army in'
				else: word = 'Army'
			elif word == 'F':
				if building: word = 'a fleet in'
				elif removing or retreating:
					word = 'the fleet in'[retreating * 4:]
					if self.map.areatype(tokens[-1]) == 'WATER': word += ' the'
				else: word = 'Fleet'
			elif word == 'BUILD':
				word = 'Builds'[:6 - (tokens[num + 1][0] in 'WH')]
			elif word in ('C', 'S'):
				word = ('SUPPORT', 'CONVOY')[word == 'C']
				if 'SHOW_PHANTOM' not in self.rules:
					help = self.unitOwner(' '.join(tokens[num + 1:num + 3]))
					if help not in (None, power):
						word += ' ' + self.anglify(self.map.ownWord[help.name])
			else:
				try: word = {'REMOVE': 'Removes', 'WAIVED': 'waived',
				 			'HIDDEN': 'hidden',	'-': '->', 'H': 'HOLD'}[word]
				except:
					for loc in [y for y, x in self.map.locName.items()
						if x == word] + [y.strip('_')
						for x, y in self.map.powName.items()
						if x.strip('_') == word.strip('_')]:
						#	----------------------------
						#	A "roll-our-own" str.title()
						#	----------------------------
						word, up, par = '', 1, 0
						for char, ch in enumerate(loc):
							if ch == '(': par = 1
							elif up and not par:
								up = 0
								if loc[char:][:3] == 'OF ': ch = 'o'
							elif ch in '+.-' or ch == ' ' and not par: up = 1
							else: ch = ch.lower()
							if ch != '+': word += ch
						break
					else:
						if word in (['MASTER', 'JUDGEKEEPER', 'UNOWNED'] +
							[x.name for x in self.powers]): word = word.title()
						elif word in self.map.ownWord.values():
							word = word.replace('+', ' ').title()
			text += [word]
		return ' '.join(text)
	#	----------------------------------------------------------------------
	def rotateControl(self, when = 0):
		for pawn in self.powers:
			if pawn.ceo and (when not in ('FOR', 'CONTROL')
			or pawn.name in self.latePowers()):
				pawn.ceo = pawn.ceo[1:] + pawn.ceo[:1]
	#	----------------------------------------------------------------------
	def morphMap(self, lastPhase = 0):
		text, map = [], self.map
		shut = [x for y in self.powers for x in y.units
			if not map.isValidUnit(x)]
		self.loadMap(map.name, map.trial, lastPhase = lastPhase)
		phases = [self.phaseAbbr().lower(), self.phase, self.phaseAbbr()]
		map.validate(phases)
		self.error += map.error
		for power, unit in [(x,y) for x in self.powers for y in x.units]:
			desc = (self.anglify(map.ownWord[power.name]) + ' ' +
					self.anglify(unit, retreating = 1))
			if map.isValidUnit(unit):
				if unit in shut: text += ['The %s is no longer trapped.' % desc]
				continue
			terrain = map.areatype(unit[2:])
			if ('HIBERNATE' in self.rules
			and (terrain == 'SHUT' or unit[0] + terrain == 'FLAND')):
				if unit not in shut:
					text += ['The %s is trapped and must HOLD.' % desc]
				continue
			power.units.remove(unit)
			if terrain == 'LAND' and 'UNITS_ADAPT' in self.rules:
				power.units.append('A' + unit[1:])
				text += ['The %s becomes an army.' % desc]
			elif terrain == 'WATER' and 'UNITS_ADAPT' in self.rules:
				power.units.append('F' + unit[1:])
				text += ['The %s becomes a fleet.' % desc]
			elif terrain == 'COAST': unit = 'F ' + [x for x in map.locs
					if x.startswith(unit[2:5])][-1]
			else: text += ['The %s is destroyed.' % desc]
		return text and ([
			'The following units were affected by geographic changes:\n'] +
			text + [''])
	#	----------------------------------------------------------------------
	def advancePhase(self, roll = None):
		if roll: roll = roll & 2
		text = []
		for idx in range(len(self.map.seq)):
			if self.phase in (None, 'FORMING', 'COMPLETED'): break
			self.phase = self.findNextPhase()
			self.phaseType = self.phase.split()[-1][0]
			if not self.checkPhase(text) and not roll: break
			if roll and os.path.isfile(self.file('status.' +
				self.phaseAbbr() + '.0')): break
		else: raise FailedToAdvancePhase
		return text
	#	----------------------------------------------------------------------
	def findStartPhase(self, move1st = 0):
		self.phase = self.map.phase
		self.phaseType = self.phase.split()[-1][0]
		if 'MOBILIZE' in self.rules or 'BLANK_BOARD' in self.rules:
			if move1st and self.phaseType != 'M': 
				self.phase = self.findPreviousPhase('M')
				self.phaseType = 'M'
			if self.phaseType != 'A':
				self.phase = self.findPreviousPhase('A')
				self.phaseType = 'A'
	#	----------------------------------------------------------------------
	def findNextPhase(self, phaseType = None, skip = 0):
		return self.map.findNextPhase(self.phase, phaseType, skip)
	#	----------------------------------------------------------------------
	def findPreviousPhase(self, phaseType = None, skip = 0):
		return self.map.findPreviousPhase(self.phase, phaseType, skip)
	#	----------------------------------------------------------------------
	def probeStartPhase(self):
		curPhase, curPhaseType = self.phase, self.phaseType
		self.findStartPhase()
		phase = self.phase
		self.phase, self.phaseType = curPhase, curPhaseType
		return phase
	#	----------------------------------------------------------------------
	def probeNextPhase(self, phase = None):
		checkCurrent = phase is None
		phase = phase or self.phase
		if phase is None or phase == 'COMPLETED': return
		if phase == 'FORMING':
			phase = self.probeStartPhase()
			checkCurrent = True
		if checkCurrent:
			if [1 for x in ['', '.0'] if os.path.isfile(self.file('status.' +
				self.map.phaseAbbr(phase) + x))]: return phase
		for idx in range(len(self.map.seq)):
			phase = self.map.findNextPhase(phase)
			if [1 for x in ['', '.0'] if os.path.isfile(self.file('status.' +
				self.map.phaseAbbr(phase) + x))]: return phase
	#	----------------------------------------------------------------------
	def probePreviousPhase(self, phase = None):
		checkCurrent = phase is None
		phase = phase or self.phase
		if phase is None or phase == 'FORMING': return
		if phase == 'COMPLETED':
			if not self.outcome: return
			phase = self.phaseLong(self.outcome[0])
		if checkCurrent:
			if [1 for x in ['', '.0'] if os.path.isfile(self.file('status.' +
				self.map.phaseAbbr(phase) + x))]: return phase
		startPhase = self.probeStartPhase()
		for idx in range(len(self.map.seq)):
			if phase == startPhase: return 'FORMING'
			phase = self.map.findPreviousPhase(phase)
			if [1 for x in ['', '.0'] if os.path.isfile(self.file('status.' +
				self.map.phaseAbbr(phase) + x))]: return phase
	#	----------------------------------------------------------------------
	def checkPhase(self, text):
		if self.phase in (None, 'FORMING', 'COMPLETED'): return
		if self.phaseType == 'M': 
			if (self.includeOwnership > 0 or self.includeOwnership < 0 and
				('BLIND' in self.rules) > ('NO_UNITS_SEE' in self.rules)
				+ ('SEE_NO_SCS' in self.rules) + ('SEE_ALL_SCS' in self.rules)):
				text += self.ownership()
			self.includeOwnership = -1
			return
		if self.phaseType == 'R':
			if [1 for x in self.powers if x.retreats]: return
			for power in self.powers:
				power.retreats, power.adjust, power.cd = {}, [], 0
			return 1
		if self.phaseType == 'A':
			text += self.captureCenters()
			if self.phase == 'COMPLETED': return
			if self.phase.split()[1] in self.map.homeYears:
				for power in [x for x in self.powers if not x.type]:
					power.homes = power.centers
			for power in self.powers:
				units, centers = len(power.units), len(power.centers)
				if [x for x in power.centers if x in power.homes]:
					centers += (self.map.reserves.count(power.name) +
						min(self.map.militia.count(power.name),
						len([0 for x in power.units
							if x[2:5] in power.homes])))
				if (units > centers
				or (units < centers and self.buildLimit(power))): return
			for power in self.powers:
				while 'SC?' in power.centers: power.centers.remove('SC?')
				while 'SC*' in power.centers: power.centers.remove('SC*')
			return 1
		#	--------------------------------------
		#	Other phases.  For now take no action.
		#	--------------------------------------
		self.await = 2
		text += ['The game is waiting for processing of the %s phase.\n' %
			self.phase.title()]
	#	----------------------------------------------------------------------
	def calculateVictoryScore(self):
		score = {}
		for power in self.powers:
			score[power] = len([x for x in power.centers if x != 'SC*' and (
				'VICTORY_HOMES' not in self.rules or x in [
				z for y in self.powers for z in y.homes
				if y is not power and y.ceo != [power.name]])])
		if 'TEAM_VICTORY' in self.rules:
			for power in self.powers:
				if not power.ceo:
					score[power] += sum([score[x] for x in power.vassals()])
			for power in self.powers:
				if power.ceo: score[power] = 0
		return score
	#	----------------------------------------------------------------------
	def captureCenters(self, func = None):
		#	-----------------------------------------
		#	If no power owns centers, initialize them
		#	-----------------------------------------
		if not [1 for x in self.powers if x.centers]:
			for power in self.powers:
				power.centers = power.homes
		#	-------------------------------------------------------
		#	Remember the current center count for the various
		#	powers, for use in the victory condition check, then
		#	go through and see if any centers have been taken over.
		#	Reset the centers seen by each power.
		#	-------------------------------------------------------
		lastYear, unowned = self.calculateVictoryScore(), self.map.scs[:]
		for power in self.powers:
			[unowned.remove(x) for x in power.centers if x in unowned]
			power.sees = []
		self.lost = {}
		for power in self.powers + [None]:
			if power: centers = power.centers
			else: centers = unowned
			for center in centers[:]:
				for owner in self.powers:
					if ((not power or owner is not power
						and not ('VASSAL_DUMMIES' in self.rules
							and (owner.ceo == power.ceo
								or power.ceo == [owner.name],
								owner.ceo == [power.name])[not power.ceo]))
						and center in [x[2:5] for x in owner.units]):
						self.transferCenter(power, owner, center)
						if not power: unowned.remove(center)
						else: self.lost[center] = power
						break
		#	-----------------------------------
		#	Determine any vassal state statuses
		#	and the list of who owns what.
		#	-----------------------------------
		list = (self.vassalship() + self.ownership(unowned) +
			self.determineWin(lastYear, func))
		if 'BLIND' in self.rules:
			for power in self.powers:
				for unit in power.units:
					list += power.showLines('HOLD ' + unit, [])
			list += ['SHOW', '']
		self.lost = {}
		return list
	#	----------------------------------------------------------------------
	def determineWin(self, lastYear, func = None):
		#	----------------------------------------------------------------
		#	See if we have a win.  Criteria are the ARMADA Regatta victory
		#	criteria (adapted from David Norman's "variable length" system).
		#	----------------------------------------------------------------
		victors, thisYear = [], self.calculateVictoryScore()
		yearCenters = [thisYear[x] for x in self.powers]
		for power in self.powers:
			centers = thisYear[power]
			#	FIRST, YOU MUST HAVE ENOUGH CENTERS TO WIN
			if	(centers >= self.win
			#	AND YOU MUST GROW (NOT IN CASE OF "VICTORY_HOMES"
			#	WHERE IT MAY BE SUFFICIENT TO RETAKE A LOST HOME CENTER),
			#	OR, IF "HOLD_WIN", MUST HAVE HAD A WIN
			and ('VICTORY_HOMES' in self.rules or centers > lastYear[power],
			lastYear[power] >= self.win)['HOLD_WIN' in self.rules]
			#	AND YOU MUST BE ALONE IN THE LEAD (NOT REQUIRED IN CASE OF
			#	SHARED_VICTORY)
			and ('SHARED_VICTORY' in self.rules or
			(centers, yearCenters.count(centers)) == (max(yearCenters), 1))):
				victors += [power]
				func = None
		if victors and not self.preview: self.finish([x.name for x in victors])
		list = self.powerSizes(victors, func)
		if not victors: list += self.checkVotes(1)
		return list
	#	----------------------------------------------------------------------
	def vassalship(self):
		if 'VASSAL_DUMMIES' not in self.rules: return []
		#	------------------------------------------------------
		#	Determine vassal states (DUMMY powers whose homes are
		#	all controlled by a single great power or its vassals)
		#	------------------------------------------------------
		was, run = {}, {}
		for power in [x for x in self.powers if x.isDummy()]:
			was[power], run[power] = power.ceo[:], []
			for home in power.homes:
				owners = [y for y in self.powers if home in y.centers]
				if owners:
					run[power] += (owners[0].ceo + [owners[0].name])[:1]
		for power, runners in run.items():
			if (runners and runners[0] != power.name
			and runners == runners[:1] * len(runners)):
				del run[power]
				ceo = [x for x in self.powers if x.name == runners[0]]
				power.ceo = runners[:not ceo[0].isDummy()]
		#	-----------------------------------------
		#	Return supply centers to and from vassals
		#	-----------------------------------------
		for power in [x for x in self.powers if x.isDummy()]:
			#	----------------------------------------
			#	Give the DUMMY powers back their centers
			#	----------------------------------------
			for home in power.homes:
				owners = [y for y in self.powers if home in y.centers]
				if owners:
					self.transferCenter(owners[0], power, home)
			#	-----------------------------------------------------------
			#	Give the great powers back their centers from their vassals
			#	-----------------------------------------------------------
			ceo = power.controller()
			if ceo: [self.transferCenter(power, ceo, y)
				for y in power.centers if y in ceo.homes]
		#	---------------------------------------------------------
		#	Determine torn allegiance destructions (vassal units on
		#	SC's now controlled by a different great power than they)
		#	---------------------------------------------------------
		if 'TORN_ALLEGIANCE' not in self.rules: return []
		list = []
		for power in [x for x in self.powers if x.isDummy() and x.ceo]:
			for unit in power.units[:]:
				other = [z for z in self.powers
						if unit[2:5] in z.centers and z != power
						and [z.name] != power.ceo and z.ceo != power.ceo]
				if other:
					if not other[0].isDummy() or other[0].ceo:
						power.units.remove(unit)
						list += ['The %s %s '
								'with torn allegiance was destroyed.' %
								(self.anglify(self.map.ownWord[power.name]),
								self.anglify(unit, retreating=1))]
		return list
	#	----------------------------------------------------------------------
	def powerSizes(self, victors, func = None):
		list = []
		#	--------------------------------------------------------------
		#	Generate the table saying how many builds/removes are pending.
		#	This only gets added to the results if this is an "A"djustment
		#	phase about to begin, or if a victory has been attained.  If a
		#	function has been passed in, it is invoked for each text line,
		#	to process any variant-specific events based on SC size.
		#	--------------------------------------------------------------
		for power in self.powers:
			if power.name not in self.map.powers: continue
			units = len(power.units)
			needs = centers = len(power.centers)
			if needs == units == 0: continue
			owned = len([x for x in power.centers if x not in ('SC?', 'SC*')])
			if [x for x in power.centers if x in power.homes]:
				needs += (self.map.reserves.count(power.name) +
					min(self.map.militia.count(power.name),
					len([0 for x in power.units
						if x[2:5] in power.homes])))
			text = ('%-11s %2d Supply center%.2s %2d Unit%.2s  %s %2d unit%s.' %
				(self.anglify(power.name) + ':', owned, 's, '[owned == 1:],
				units, 's: '[units == 1:],
				('Builds ', 'Removes')[needs < units],
				abs(needs - units), 's'[abs(needs - units) == 1:]))
			#	------------------------------------------------------------
			#	Modify (if necessary) what we believe will be the next phase
			#	------------------------------------------------------------
			ceo = getattr(power, 'ceo', [])[:1]
			victory = victors and (power in victors or
				'TEAM_VICTORY' in self.rules and
				[1 for x in victors if [x.name] == ceo])
			if victory:
				text += '  (* VICTORY!! *)'
			if self.phase == 'COMPLETED' or self.phaseType == 'A':
				if 'BLIND' in self.rules:
					if victory: list += ['SHOW']
					else: list += ['SHOW MASTER ' + ' '.join([x.name
						for x in self.powers if x is power or x.omniscient
						or [x.name] == ceo])]
				list += [text]
			if func and self.phaseType != 'A': func(power, text.upper().split())
		return list + ['SHOW'] * ('BLIND' in self.rules) + ['']
	#	----------------------------------------------------------------------
	def phaseAbbr(self, phase = None):
		#	------------------------------------------
		#	Returns S1901M from "SPRING 1901 MOVEMENT"
		#	------------------------------------------
		return self.map.phaseAbbr(phase or self.phase)
	#	----------------------------------------------------------------------
	def phaseLong(self, phaseAbbr):
		#	------------------------------------------
		#	Returns "SPRING 1901 MOVEMENT" from S1901M
		#	------------------------------------------
		return self.map.phaseLong(phaseAbbr)
	#	----------------------------------------------------------------------
	def phaseName(self, form = 0, phase = None):
		#	---------------------------------------------------------------
		#	Takes a phase (the current phase by default) and returns
		#	the phase name in upper-lowercase format.  If "form" is 0
		#	(or not passed), the return format is:
		#		SPRING 1901 MOVEMENT --> Spring of 1901.  (gamename.S1901M)
		#	If "form" is 1, the return format is:
		#		SPRING 1901 MOVEMENT --> Spring of 1901.
		#	If "form" is 2, the return format is:
		#		SPRING 1901 MOVEMENT --> Spring 1901 Movement
		#	Note that in the first two forms, the word "of" is only
		#	included if the season is a season of the year [Spring,
		#	Fall, Winter, Summer, or Autumn].
		#	---------------------------------------------------------------
		phase = phase or self.phase
		if not phase: return ''
		word, season = phase.title().split(), ''
		if len(word) < 3: return ''
		for ch in word[0]:
			season += season and season[-1] == '.' and ch.upper() or ch
		return (season + ' ' +
			'of ' * (season in ('Spring', 'Fall', 'Winter', 'Summer', 'Autumn')
			and form != 2) + word[1] + (form != 2 and '.' or ' ' + word[2]) +
			'  (%s.%s)' % (self.name, self.phaseAbbr(phase)) * (not form))
	#	----------------------------------------------------------------------
	def moveResults(self):
		self.resolveMoves()
		list = ['Movement results for ' + self.phaseName(), '']
		self.result[None], rules = 'invalid', self.rules
		for power in [x for x in self.powers if x.units]:
			#	---------------------------------------
			#	Make any hidden units appear.
			#	---------------------------------------
			if 'BLIND' not in rules:
				for unit in power.hides:
					list += ['%s: %s FOUND.' %
						(self.anglify(power.name), self.anglify(unit))]
			for unit in power.units:
				#	--------------------------------------------------------
				#	Decide order annotations to be listed in the results.
				#	In a BLIND game, no one is told when orders were "void".
				#	However, any orders for CONVOYed armies that were "void"
				#	have to be marked somehow or it will look like they
				#	should have reached landfall.  We mark them "no convoy".
				#	--------------------------------------------------------
				notes = self.result[unit][:]
				if 'BLIND' in rules:
					if 'void' in notes:
						notes.remove('void')
						if self.command[unit].count('-') > 1:
							notes += ['no convoy']
				line = '%s: %s.%s' % (self.anglify(power.name),
					self.anglify(unit + ' ' + self.command[unit], power),
					notes and '  (*%s*)' % ', '.join(notes) or '')
				if 'BLIND' in rules:
					#	-----------------------------------------------------
					#	If this is a BLIND game, add a line before the result
					#	text line specifying who should see result text.
					#	Also, show any partial results that should be seen.
					#	-----------------------------------------------------
					list += power.showLines(unit, notes, line)
				#	-------------------------------------------
				#	I know it's tempting to line up the orders,
				#	but David Norman's Mapper doesn't read the
				#	output right if it has more than a single
				#	space between the colon and the order.
				#	-------------------------------------------
				else: list += [line]
			#	-------------------------------------------
			#	Add any invalid orders (if NO_CHECK is set)
			#	-------------------------------------------
			if 'NO_CHECK' in rules:
				for invalid, order in power.orders.items():
					if invalid[:7] in ('INVALID', 'REORDER'): list += [
						'%s: %s.  (*%s*)' %
						(self.anglify(power.name), order, invalid[:7].lower())]
			if 'BLIND' in rules: list += ['SHOW']
			list += ['']
		#	-------------------------------------------------------------
		#	Remove all hides now, because in blind games they are used to
		#	determine visibility.
		#	-------------------------------------------------------------
		for power in self.powers: power.hides = [] 
		#	----------------------
		#	Determine any retreats
		#	----------------------
		for power in self.powers:
			for unit in filter(self.dislodged.has_key, power.units):
				power.retreats.setdefault(unit, [])
				attacker, site = self.dislodged[unit], unit[2:]
				if self.map.locAbut.get(site): pushee = site
				else: pushee = site.lower()
				for abut in self.map.locAbut[pushee]:
					abut = abut.upper()
					where = abut[:3]
					if ((self.abuts(unit[0], site, '-', abut)
					or	 self.abuts(unit[0], site, '-', where))
					and not self.combat.get(where) and where != attacker):
						#	----------------------------------------
						#	Armies cannot retreat to specific coasts
						#	----------------------------------------
						if unit[0] == 'F': power.retreats[unit] += [abut]
						elif where not in power.retreats[unit]:
							power.retreats[unit] += [where]
		#	--------------------------
		#	List all possible retreats
		#	--------------------------
		destroyed, self.popped = {}, []
		if self.dislodged:
			if 'BLIND' in rules: who = (['SHOW', 'MASTER'] +
				[x.name for x in self.powers if x.omniscient])
			dis = ['\nThe following units were dislodged:\n']
			for power in self.powers:
				for unit in filter(self.dislodged.has_key, power.units):
					power.units.remove(unit)
					text = desc = ('The %s ' %
						self.anglify(self.map.ownWord[power.name]) +
						self.anglify(unit, retreating = 1))
					toWhere, line = power.retreats.get(unit), ''
					if ('NO_RETREAT' in rules or power.isDummy()
					and not power.ceo and ('IMMOBILE_DUMMIES' in rules
					or 'CD_DUMMIES' in rules > 'CD_RETREATS' in rules)):
						text += ' was destroyed.'
						destroyed[unit] = power
						self.popped += [unit]
						del self.dislodged[unit]
					elif toWhere: text += (' can retreat to %s.' %
						' or '.join(map(self.anglify, toWhere)))
					else:
						text += ' with no valid retreats was destroyed.'
						destroyed[unit] = power
						self.popped += [unit]
						del self.dislodged[unit]
					#	-----------------------------------------------------
					#	If this is a BLIND game, add a line before the result
					#	text line specifying who should NOT see result text.
					#	-----------------------------------------------------
					if 'BLIND' in rules:
						show = [x for x,y in power.visible(unit, 'H').
							items() if y & 8 and x in self.map.powers]
						who += [x for x in show if x not in who]
						if unit in self.popped:
							controllers, show = ['MASTER'] + show, []
						else:
							show.remove(power.name)
							controllers = ['MASTER', power.name]
							boss = power.controller()
							if boss:
								try:
									show.remove(boss.name)
									controllers += [boss.name]
								except: pass
							if show:
								dis += ['SHOW ' + ' '.join(show), desc + '.']
						show = [x.name for x in self.powers if x.omniscient]
						who += [x for x in show if x not in who]
						dis += ['SHOW ' + ' '.join(controllers + show)]
					#	------------------------------------
					#	Make long lines wrap around politely
					#	------------------------------------
					dis += [y.replace('\x7f', '-')
						for y in textwrap.wrap(text.replace('-', '\x7f'), 75)]
			if 'BLIND' in rules:
				list += [' '.join(who)]
				dis += ['SHOW']
			list += dis + ['']
		#	--------------------------------------------------------------
		#	Now (finally) actually move the units that succeeded in moving
		#	--------------------------------------------------------------
		for power in self.powers:
			for unit in power.units[:]:
				if self.command[unit][0] == '-' and not self.result[unit]:
					power.units.remove(unit)
					power.units += [unit[:2] + self.command[unit].split()[-1]]
		#	--------------------------------------------------------
		#	If units were destroyed, other units may go out of sight
		#	--------------------------------------------------------
		if destroyed:
			if 'BLIND' in self.rules:
				self.phaseType = 'R'
				for power in self.powers:
					for unit in power.units:
						list += power.showLines('HOLD ' + unit, [])
				list += ['SHOW']
				self.phaseType = 'M'
			for unit, power in destroyed.items():
				try: del power.retreats[unit]
				except: pass
		#	------------
		#	All finished
		#	------------
		if not self.preview: self.postMoveUpdate()
		return list
	#	----------------------------------------------------------------------
	def otherResults(self):
		self.command = {}
		conflicts, self.popped, owner = {}, [], 0
		list = ['%s orders for ' % self.phase.split()[2][:-1].title() +
			self.phaseName(), '']
		#	---------------------------------------------------
		#	Supply CIVIL_DISORDER retreat and adjustment orders
		#	---------------------------------------------------
		if self.phaseType == 'A':
			for power in [x for x in self.powers if not x.adjust]:
				diff = len(power.units) - len(power.centers)
				if [x for x in power.centers
					if x in power.homes]:
					diff -= (self.map.reserves.count(power.name) +
						min(self.map.militia.count(power.name),
						len([0 for x in power.units
							if x[2:5] in power.homes])))
				if not diff: continue
				power.cd = 1
				if diff > 0:
					pref = []
					for own, sc, home in (
						(0,0,0), (1,1,0), (1,1,1), (0,1,0), (0,1,1)):
						for kind in 'FA': pref.append(
							[x for x in power.units if x[0] == kind
							and (x[2:5] in self.map.scs) == sc
							and (x[2:5] in power.centers) == own
							and (x[2:5] in power.homes) == home])
					for unit in range(diff):
						pref = filter(None, pref)
						goner = random.choice(pref[0])
						pref[0].remove(goner)
						power.adjust += ['REMOVE ' + goner]
				else:
					sites = self.buildSites(power)
					need = min(self.buildLimit(power, sites), -diff)
					power.adjust = ['BUILD WAIVED'] * need
					if 'CD_BUILDS' in self.rules:
						options = []
						for site in [x.upper() for x in self.map.locType]:
							if site[:3] in sites: options += filter(
								self.map.isValidUnit,
								('A ' + site, 'F ' + site))
						alternatives = []
						for limits in self.map.alternative.get(
							power.name, []):
							if limits[0] not in sites: continue
							if len(limits) == 1: limits = limits[:] + [
								x for x in power.homes if x in sites and
								x not in [y[0] for y in 
								self.map.alternative[power.name]]]
							else: limits = limits[:1] + [
								x for x in limits[1:] if x in sites]
							if len(limits) > 1: alternatives += [limits]
						for build in range(need):
							if not options: break
							unit = random.choice(options)
							site = unit[2:5]
							power.adjust[build] = ('BUILD ' + unit +
								' HIDDEN' * ('HIDE_BUILDS' in self.rules or 
								site in self.map.hidden.get(power.name, [])))
							removals = [site]
							while removals:
								site, removals = removals[0], removals[1:]
								options = [x for x in options
									if x[2:5] != site]
								for limits in alternatives:
									if site not in limits: continue
									limits.remove(site)
									if len(limits) > 1: continue
									removals.append(limits[0])
									alternatives.remove(limits)
		elif self.phaseType == 'R':
			for power in [x for x in self.powers
				if x.retreats and not x.adjust]:
				power.cd = 1
				if 'CD_RETREATS' not in self.rules:
					power.adjust = [
						'RETREAT %s DISBAND' % x for x in power.retreats]
					continue
				taken = []
				for unit in power.retreats:
					sites = [x for x in power.retreats[unit]
						if x not in taken]
					for own, his in ((0,1), (0,0), (1,1), (1,0)):
						options = [x for x in sites
							if x[:3] in self.map.scs
							and (x[:3] in power.homes) == his
							and (x[:3] in power.centers) == own]
						if options: break
					else: options = sites
					if options:
						where = random.choice(options)
						taken.append(where)
						power.adjust += ['RETREAT %s - ' % unit + where]
					else: power.adjust += ['RETREAT %s DISBAND' % unit]
		#self.save(1)
		#	-------------------------------------------------
		#	Determine multiple retreats to the same location.
		#	-------------------------------------------------
		for power in self.powers:
			for order in power.adjust or []:
				word = order.split()
				if len(word) == 5:
					conflicts.setdefault(word[4][:3], []).append(word[2])
		#	-------------------------------------------------
		#	Determine retreat conflicts (*bounce, destroyed*)
		#	Note that Map.abutRules['*'] will cause units to
		#	be destroyed in PREFERENCE to other retreaters.
		#	Ditto for Map.abutRules['~'] (strait crossings),
		#	which are actually even WEAKER (drop them first).
		#	When finished, "self.popped" will be a list of all
		#	retreaters who didn't make it.
		#	-------------------------------------------------
		for site, retreaters in conflicts.items():
			for weak in '~*':
				if len(retreaters) < 2: continue
				for retreater in retreaters[:]:
					if (retreater, site) in self.map.abutRules.get(weak, []):
						self.popped += [retreater]
						retreaters.remove(retreater)
			if len(retreaters) > 1: self.popped += retreaters
		#	----------------------------
		#	Add the orders to the output
		#	----------------------------
		for power in self.powers:
			units, builds = power.units[:], []
			for order in power.adjust or []:
				word = order.split()
				if len(word) > 3 and word[-1] == 'HIDDEN':
					order = ' '.join(word[:-1])
				if word[0] == 'BUILD' and len(word) > 2:
					builds += [' '.join(word[1:])]
					sc = word[2][:3]
					if 'SC!' in power.centers:
						power.centers.remove('SC!')
						if sc not in power.centers:
							power.centers += [sc]
							self.includeOwnership = 1
					if '&SC' in power.homes and sc not in power.homes:
						power.homes.remove('&SC')
						power.homes += [sc]
				elif word[0] == 'REMOVE':
					units.remove(' '.join(word[1:3]))
				result = '%-11s %s.' % (
					self.anglify(power.name) + ':', self.anglify(order))
				if len(word) >= 5 and word[2] in self.popped:
					result += '  (*bounce, destroyed*)'
				if 'BLIND' in self.rules:
					list += power.showLines(order, self.popped, result)
				else: list += [result]
			if 'BLIND' in self.rules:
				for unit in units:
					list += power.showLines('HOLD ' + unit, self.popped)
			if self.phaseType == 'A':
				count = len(power.centers) - len(units) - len(builds)
				if [x for x in power.centers if x in power.homes]:
					count += (self.map.reserves.count(power.name) +
						min(self.map.militia.count(power.name),
						len([0 for x in units + builds
							if x[2:5] in power.homes])))
				if count:
					if 'BLIND' in self.rules: list += ['SHOW MASTER ' +
						' '.join([x.name for x in self.powers if x is power
						or x is power.controller() or x.omniscient])]
					list += ['%-12s%d unused build%s pending.' %
						(self.anglify(power.name) + ':', count,
						's'[count == 1:])]
				while 'SC?' in power.centers: power.centers.remove('SC?')
				while 'SC*' in power.centers: power.centers.remove('SC*')
		for power in self.powers:
			for order in power.adjust or []:
				word = order.split()
				if word[0] == 'BUILD' and len(word) > 2:
					if len(word) > 3 and word[-1] == 'HIDDEN':
						word = word[:-1]
						power.hides += [' '.join(word[1:])]
					power.units += [' '.join(word[1:])]
				elif word[0] == 'REMOVE':
					power.units.remove(' '.join(word[1:]))
				elif len(word) == 5:
					if word[2] not in self.popped:
						power.units += [word[1] + ' ' + word[-1]]
			power.adjust, power.retreats, power.cd = [], {}, 0
		if 'BLIND' in self.rules: list += ['SHOW']
		return list + ['']
	#	----------------------------------------------------------------------
	def mapperHeader(self):
		#	----------------------------------------------------------
		#	I'll get David Norman for this one!  Apparently, Mapper
		#	won't like results messages unless they have the "standard
		#	judge header" on them.  Sigh.  And not only that, but what
		#	we call W1902A has to be called F1902B to make it happy.
		#	----------------------------------------------------------
		phase = self.phaseAbbr()
		if phase[0] + phase[-1] == 'WA': phase = 'F%sB' % phase[1:-1]
		deadline = self.timeFormat(form = 1, pseudo = 1)
		return [
			':: Judge: %s  Game: %s  Variant: %s ' %
				(host.resultsID, self.name, self.map.name) + self.variant,
			':: Deadline: %s ' % phase + deadline,
			':: URL: %s%s?game=' % (host.resultsURL,
				'/index.cgi' * (os.name == 'nt')) + self.name, ''] or []
	#	----------------------------------------------------------------------
	def resolvePhase(self):
		return ["The %s phase of '%s' has been completed." %
				(self.phase.title(), self.name), '']
	#	----------------------------------------------------------------------
	def resolve(self, roll = None):
		thisPhase, lastPhase = self.phaseType, self.phaseAbbr()
		subject = 'Diplomacy results %s ' % self.name + lastPhase
		broadcast = self.mapperHeader()
		self.sortPowers()
		#	--------------------------------------------------------
		#	This method knows how to process movement, retreat, and
		#	adjustment phases.  For others, implement resolvePhase()
		#	--------------------------------------------------------
		if thisPhase == 'M': broadcast += self.moveResults()
		elif thisPhase in 'RA': broadcast += self.otherResults()
		#	-------------------------------------------------------------
		#	Use a subclass's resolvePhase() method for any non-MRA-phases
		#	-------------------------------------------------------------
		else: broadcast += self.resolvePhase()
		#	---------------------------------------------
		#	Rotate power control for any "AFTER" rotation
		#	---------------------------------------------
		for how in range(0, len(self.rotate), 2):
			if self.rotate[how] == 'AFTER' and (len(self.rotate) == 1
			or thisPhase == self.rotate[how + 1][0]): self.rotateControl()
		#	------------------------------------------------------
		#	Advance the phase.  This method may return a list with
		#	more lines to be packed onto the outgoing results mail
		#	------------------------------------------------------
		broadcast += self.advancePhase(roll)
		if self.phase != 'COMPLETED':
			#	---------------------------------------------------
			#	Make any unit changes based on upcoming map changes
			#	---------------------------------------------------
			if self.map.dynamic: broadcast += self.morphMap(lastPhase)
			phase = self.phase.title().split()
			broadcast += ['The next phase of %s will be %s for ' %
				(`self.name.encode('latin-1')`,
				phase[2]) + self.phaseName(form = 1)]
			if self.deadline: self.setDeadline()
			broadcast += ['The deadline for orders will be %s.' %
				self.timeFormat(pseudo = 1)]
			#	---------------------------------------------------------
			#	Rotate power control for any "BEFORE" and "FOR" rotations
			#	---------------------------------------------------------
			for how in range(0, len(self.rotate), 2):
				if self.rotate[how] != 'AFTER' and (len(self.rotate) == 1
				or phase[2].upper()[0] == self.rotate[how + 1][0]):
					self.rotateControl(self.rotate[how])
		else: broadcast += ['The game is over.  Thank you for playing.']
		self.await = self.await > 1 and self.await
		text = [x + '\n' for x in broadcast + ['']]
		if self.preview:
			self.mailPress(None, ['MASTER'],
				''.join(text), subject = 'PREVIEW ' + subject)
			return
		if roll: self.fileResults(text, subject)
		else: self.mailResults(text, subject)
		self.finishPhase()
		self.save()
		if not roll: self.makeMaps()
		if self.phase == 'COMPLETED': self.fileSummary(roll = roll)
	#	----------------------------------------------------------------------
	def checkVotes(self, append = 0):
		if 'PROPOSE_DIAS' in self.rules: return []
		votes = []
		for power in self.powers:
			try: power.canVote() and votes.append(int(power.vote))
			except: return []
		votes = filter(None, votes)
		if not votes or len(votes) > min(votes): return []
		if len(votes) == 1 or 'NO_DIAS' not in self.rules:
			self.proposal = ['DIAS']
		else:
			self.proposal = ['NO_DIAS']
		return self.endByAgreement(append)
	#	----------------------------------------------------------------------
	def endByAgreement(self, append = 0, roll = 0):
		lines = not append and [x + '\n' for x in self.mapperHeader()] or []
		result = self.proposal[0]
		if result in ('DIAS', 'NO_DIAS'):
			victors = sorted([x.name for x in self.powers
				if (x.vote > '0', x.canVote())[result == 'DIAS']])
		else: victors = [result]
		drawers = map(self.anglify, victors)
		drawers[-1] += '.'
		if len(drawers) > 1:
			drawers[-1] = 'and ' + drawers[-1]
			drawers = ', '[len(drawers) < 3:].join(drawers)
		else: drawers = drawers[0]
		info = ("Game '%s' has been " % self.name +
			('conceded to ', 'declared a draw between ')[len(victors) > 1])
		lines += [x + '\n' for x in textwrap.wrap(info + drawers, 75)]
		lines += ['\nCongratulations on a game well-played.\n']
		if not append:
			self.mailResults(lines, "Diplomacy game '%s' complete" % self.name)
		self.finish(victors)
		self.fileSummary(roll = roll)
		if append: return lines
	#	----------------------------------------------------------------------
	def finish(self, victors):
		self.end = self.getTime().format(3)
		self.outcome = [self.phaseAbbr()] + victors
		self.proposal, self.phase = None, 'COMPLETED'
		for power in self.powers:
			power.retreats, power.adjust, power.cd = {}, [], 0
		self.changeStatus('completed')
		self.save()
		if 'BLIND' in self.rules:
			for power in self.powers: power.removeBlindMaps()
			file = host.gameMapDir + '/' + self.name
			for suffix in ('.ps', '.pdf', '.gif', '_.gif'):
				try: os.rename(file + `hash(self.gm.password)` + suffix,
					file + suffix)
				except: pass
	#	----------------------------------------------------------------------
	def abuts(self, unitType, unitLoc, orderType, otherLoc, power = None):
		#	-----------------------------------------------
		#	First see if the map says the adjacency is good
		#	-----------------------------------------------
		if not self.map.abuts(unitType, unitLoc, orderType, otherLoc): return
		#	-----------------------------------------------
		#	Now check for game considerations.  If the unit
		#	exists, then we know its owner.  Check that the
		#	owner adheres to any abutRules ending in : or )
		#	(meaning that it is a specific power or that 
		#	the power owns a specific supply center).
		#	-----------------------------------------------
		who = power or self.unitOwner(unitType + ' ' + unitLoc)
		if who:
			for rule in [x for x,y in self.map.abutRules.items()
				if x[-1] in ':)' and (unitLoc, otherLoc) in y]:
				if rule[-1] == ':':
					if who.abbrev not in rule: return
				elif [x for x in rule[:-1].split(',')
					if x not in who.centers]: return
		return 1
	#	----------------------------------------------------------------------
	def timeFormat(self, form = 0, pseudo = 0):
		try: return self.deadline.format(form)
		except:
			if pseudo: return self.getTime().format(form)
			if self.phase == 'FORMING': return ''
			return 'Invalid Deadline! Notify Master!'
	#	----------------------------------------------------------------------
	def graceExpired(self):
		grace = self.timing.get('GRACE',
			'CIVIL_DISORDER' in self.rules and '0H')
		return grace and self.deadlineExpired(grace)
	#	----------------------------------------------------------------------
	def deadlineExpired(self, grace = '0H'):
		if 'NO_DEADLINE' in self.rules: return
		try: return self.getTime() >= self.deadline.offset(grace)
		except: pass
	#	----------------------------------------------------------------------
	def getDeadline(self, fileName = 'status'):
		try: file = open(self.file(fileName), encoding='latin-1')
		except: return
		blockMode = 0
		deadline = mode = None
		for line in file:
			word = line.split()
			if not word:
				# End of game data?
				if not mode: break
				continue
			upword = word[0].upper()
			if blockMode == 0:
				# Start of first block, the game data
				if upword != 'GAME': return
				blockMode = 1
				continue
			# Game data
			if (mode and upword == 'END' and len(word) == 2
				and word[1].upper() == mode): mode = None
			elif len(word) == 1 and upword in (
				'DESC', 'DESCRIPTION', 'NAME', 'MORPH'): mode = upword
			elif len(word) == 2 and upword == 'DEADLINE':
				deadline = self.getTime(word[1])
				break
		file.close()
		return deadline
	#	----------------------------------------------------------------------
	def setDeadline(self, firstPhase = 0):
		if 'NO_DEADLINE' in self.rules:
			self.deadline = None
			return
		now = self.getTime()
		at, days = self.timing.get('AT'), self.timing.get('DAYS', '-MTWTF-')
		try: delay = [y for x,y in self.timing.items()
			if not self.phase.split()[-1].find(x)][0]
		except: delay = self.timing.get('NEXT',
			('1D', '3D')[self.phaseType == 'M'])
		#	-------------------------------------------------------
		#	Determine earliest deadline.  If the game allows press,
		#	double the usual length of time for the first deadline.
		#	-------------------------------------------------------
		when = now.offset(delay)
		realtime = 'REAL_TIME' in self.rules or when < now.offset('20M')
		#	------------------------------------------
		#	Advance the deadline to the specified time
		#	unless the delay is less than half a day
		#	------------------------------------------
		if when < now.offset('12H'): at = 0
		if (firstPhase and 'NO_PRESS' not in self.rules
			and ('FTF_PRESS' not in self.rules or self.phaseType == 'M')):
			when = when.offset(delay)
		if at:
			#	-------------------------------------
			#	Pull the deadline back 20 minutes to
			#	provide fudge-time so that three days
			#	from 11:41, pushed to the next 11:40
			#	won't be four days away (for example)
			#	Increase this to 8 hours if the delay
			#	is expressed in whole days
			#	-------------------------------------
			if delay[-1:] in 'WD':
				whack = when.offset('-' + self.timing.get('FUDGE', '8H'))
				if whack < when.offset('-12H'): when = when.offset('-12H')
				else: when = whack
			when = when.offset(-1200).next(at)
		moved, skip = 1, 'JUMP_OFF_DAYS' in self.rules
		while moved:
			#	---------------------------------
			#	Specific day-of-week setting (the
			#	DAYS option to the TIMING line)
			#	---------------------------------
			whack = skip and now.next(when) or when
			day = whack.tuple()[6]
			while 1:
				day = (day + 1) % 7
				if (days[day].isalpha(),
					days[day].isupper())[self.phaseType == 'M']:
					if not skip or when == whack: break
					whack = whack.offset(86400)
				else:
					if skip: whack = whack.offset(86400)
					when = when.offset(86400)
			skip = 0
			#	--------------------------
			#	Vacation handling (the NOT
			#	option to the TIMING line)
			#	--------------------------
			outings, moved = self.timing.get('NOT', ''), 0
			vacations = filter(None, outings.split(','))
			while vacations:
				for vacation in vacations:
					if '-' in vacation: start, end = vacation.split('-')
					else: start = end = vacation
					start, end = self.getTime(start), self.getTime(end)
					end = end.offset(realtime and '1M' or end.npar() > 3 and
						'20M' or '1D')
					if when < start: continue
					if when < end:
						if at: when = end.next(at)
						elif realtime: when = end
						else: when = end.next(when)
						moved = 1
					if end <= now:
						vacations.remove(vacation)
						break
				else: break
			if vacations: self.timing['NOT'] = ','.join(vacations)
			elif outings: del self.timing['NOT']
		#	--------------------------------------------------------------
		#	Set deadline to the nearest :00, :20, or :40 of the given hour
		#	--------------------------------------------------------------
		if not realtime: when = when.trunc('20M')
		#	----------------------------------------------------------------
		#	Now set the deadline unless it's already set beyond the new time
		#	----------------------------------------------------------------
		self.deadline = max(self.deadline, when)
		return self.deadline
	#	----------------------------------------------------------------------
	def canChangeOrders(self, oldOrders, newOrders, proxyOnly = False):
		if self.deadline and self.deadline <= self.getTime() and not self.avail:
			if not newOrders and not proxyOnly:
				return self.error.append('ORDERS REQUIRED TO AVOID LATE STATUS')
			if oldOrders and 'NO_LATE_CHANGES' in self.rules:
				return self.error.append(
					'ORDER RESUBMISSION NOT ALLOWED AFTER DEADLINE')
		if 'MUST_ORDER' in self.rules and (
			oldOrders and not newOrders and not proxyOnly):
			return self.error.append('ORDERS REQUIRED AFTER SUBMISSION')
		return 1
	#	----------------------------------------------------------------------
	def getPower(self, word, ambiguous = 1):
		if not word: return ('', 0)
		ambiguous = ambiguous and len(word) > 1
		if not ambiguous: item, parsed = ''.join(word), len(word)
		elif word[0][0] in '([':
			item, parsed, ambiguous = word[0], 1, 0
			if item[-1] not in '])':
				for tail in word[1:]:
					if tail[0] in '([': break
					item += tail
					parsed += 1
					if tail[-1] in '])': break
				else: ambiguous = 1
		else:
			item, parsed, ambiguous = word[0], 1, 0
			if item[-1] != ':':
				for tail in word[1:]:
					item += tail
					parsed += 1
					if tail[-1] == ':': break
				else: ambiguous = 1
		if ambiguous: item, parsed = word[0], 1
		item = item.upper()
		upword = item[item[:1] in '([':len(item) - (item[-1:] in ']):')]
		if not upword: return ('', 0)
		ambiguous = ambiguous and upword == item
		powers = [x for x in self.powers if upword in
			[x.abbrev, x.name][ambiguous:]]
		if not powers and ambiguous and len(word[0]) > 1:
			item, parsed = ''.join(word).upper(), len(word)
			upword = item[item[:1] in '([':len(item) - (item[-1:] in ']):')]
			powers = [x for x in self.powers if upword == x.name]
		if not powers: return ('', 0)
		#	----------------------------------------
		#	Strip any comments immediately following
		#	----------------------------------------
		if parsed == len(word) or word[parsed][0] == '%':
			return (powers[0], len(word))
		return (powers[0], parsed)
	#	----------------------------------------------------------------------
	def distributeOrders(self, power, orders, clear = True):
		powers, distributor = [power], {power.name: []}
		curPower = power
		for order in orders:
			word = order.strip().split()
			if not word: continue
			who, parsed = self.getPower(word)
			if who:
				if who.name not in distributor:
					if not power.controls(who):
						self.error.append('NO CONTROL OVER ' + who.name)
						return
					powers += [who]
					distributor[who.name] = []
				word = word[parsed:]
				if not word:
					curPower = who
					continue
			else: who = curPower
			if clear and len(word) == 1 and word[0][word[0][:1] in '([':len(
				word[0]) - (word[0][-1:] in '])')].upper() in ('NMR', 'CLEAR'):
				distributor[who.name] = []
			else: distributor[who.name] += [' '.join(word)]
		return [(x, distributor[x.name]) for x in powers]
	#	----------------------------------------------------------------------
	def updateOffPhases(self, power, adjust):
		for who, adj in self.distributeOrders(power, adjust, False):
			self.addOffPhases(who, adj)
		#	-----------------------------------------
		#	Process the phase if everything is ready.
		#	-----------------------------------------
		if not self.error: self.process()
		return self.error
	#	----------------------------------------------------------------------
	def addOffPhases(self, power, adjust):
		if not adjust or '(NMR)' in adjust:
			if adjust and adjust.count('(NMR)') < len(adjust):
				self.error += ['ORDERS INCOMPLETE']
			adjust = []
		adjust.sort()
		if adjust == power.adjust:
			return self.error
		if not self.canChangeOrders(power.adjust, adjust): return
		if not adjust:
			power.adjust, power.cd = [], 0
			return self.save()
###		if 'NO_CHECK' in self.rules:
###			power.adjust, power.cd = self.adjust, 0
###			self.process()
###			return self.error
		orders, places, alternatives = [], [], []
		if adjust[0].startswith('BUILD'):
			alternatives = self.buildAlternatives(power)
		#	------------------------------------------------------------------
		#	Check for duplicate orders (building/removing the same unit twice)
		#	------------------------------------------------------------------
		for order in adjust:
			if order == 'BUILD WAIVED': continue
			word = order.split()
			site = word[2][:3]
			if site in places:
				self.error += ['DUPLICATE ORDER: ' + order]
			else:
				for limits in alternatives:
					if site in limits and len(
						[x for x in limits if x not in places]) == 1:
						self.error += ['BUILDS IN ALL ALTERNATIVE SITES ('
							+ ', '.join(limits) + '): ' + order]
						break
				else:
					places += [site]
					orders += [order]
		if not self.error: power.adjust, power.cd = adjust, 0
	#	----------------------------------------------------------------------
	def history(self, email, power = None):
		try:
			file = open(self.file('results'), encoding='latin-1')
			if 'BLIND' in self.rules:
				lines, show, blank = '', 1, 0
				for line in file:
					if line[:4] == 'SHOW':
						powers = line.strip().split()[1:]
						show = (self.phase == 'COMPLETED'
						or (not powers or power.name in powers))
					elif show and (len(line) > 1 or not blank):
						lines += line
						blank = len(line) == 1
			else: lines = file.read()
			file.close()
		except: lines = "No history available for game '%s'\n" % self.name
		self.openMail('History of game ' + self.name,
			mailTo = email, mailAs = host.dpjudge)
		self.mail.write(lines)
		self.mail.close()
	#	----------------------------------------------------------------------
	def summary(self, email = None, forPower = None, reveal = 0):
		try:
			file = open(self.file('results'), encoding='latin-1')
			lines = file.readlines()
			file.close()
		except: lines = []
		show, reading, save = 1, 0, ''
		count, owner, years = {}, {}, []
		year = end = None
		forPowerName = (('BLIND' not in self.rules or
			self.phase == 'COMPLETED') and 'MASTER' or
			forPower and forPower.name or '')
		for line in [x.strip() for x in lines]:
			if not line:
				if reading and owner.get(year): reading = 0
			elif line[:26] == 'Subject: Diplomacy results':
				word = line.split()
				end, year = word[4], word[4][1:-1]
			elif year and line[:12] == 'Ownership of':
				if year not in years: years += [year]
				reading, owner[year], count[year] = 1, {}, {}
			elif reading:
				line = line.upper()
				if line[:4] == 'SHOW':
					who = line.split()
					show = len(who) == 1 or forPowerName in who[1:]
					continue
				if not show: continue
				if save: line = save + ' ' + line
				if line[-1] == '.':
					power, save = line[:line.find(':')], ''
					if power == 'UNOWNED': letter = '.'
					else: letter = self.map.abbrev.get(power, power[0])
					centers = ' '.join(line[:-1].split()[1:]).split(', ')
					if not centers: continue
					for spot in centers: owner[year][self.map.aliases.
						get(spot.strip())] = letter
					count[year][power] = len(centers)
				else: save = line
		last, scs = {}, []
		for yr in sorted(owner):
			scs += [sc for sc in owner[yr] if sc not in scs]
			for power in count[yr]: last[power] = yr
		if None in scs: scs.remove(None)
		if not scs:
			if email:
				self.openMail('Summary of game ' + self.name,
					mailTo = email, mailAs = host.dpjudge)
				self.mail.write('No summary information is '
					'available for game %s.\n' % self.name)
				self.mail.close()
			return
		results = ('Summary of game %s through %s.\n\n%s%s\n\n'
				   'Historical Supply Center Summary\n%s\n    ' %
			(self.name, end, self.playerRoster(None, forPower, reveal)[:-1],
			self.parameters(), '-' * 32))
		scs.sort()
		for j in (0, 1):
			if j: results += '\nYear '
			for i in range(j, len(scs), 2): results += ' ' + scs[i].title()
		for year in years: results += ('\n%4s ' % year +
			' '.join([owner[year].get(sc, '?') for sc in scs]))
		results += '\n\nHistory of Supply Center Counts\n%s\n' % ('-' * 31)
		powers = sorted(self.map.powers)
		for decade in range((len(years) + 9) / 10):
			results += 'Power     '
			for year in years[decade * 10:][:10]: results += ('%4s' %
				("'"[len(year) < 3:] + year[-2:], year)[results[-1] == ' '])
			for power in powers:
				if years[decade * 10] <= last.get(power, -1):
					results += '\n%-10s' % self.anglify(power)
					for year in years[decade * 10:][:10]:
						if year <= last.get(power, -1):
							results += '  %2d' % count[year].get(power, 0)
			results += '\nIndex:    '
			for year in years[decade * 10:][:10]:
				if forPowerName == 'MASTER':
					if 'UNOWNED' in count[year]: del count[year]['UNOWNED']
					total, scCounts = 0, count[year].values()
					for num in scCounts: total += num * num
					results += '%4d' % (total / len(scCounts))
				else: results += '   ?'
			results += '\n\n'
		results += ('Index is the Calhamer Index:  the sum of squares '
					'of the number of\nsupply centers held by each power, '
					'divided by the number of powers\nremaining.  It is a '
					'measure of how far the game has progressed.\n')
		if email:
			self.openMail('Summary of game ' + self.name,
				mailTo = email, mailAs = host.dpjudge)
			self.mail.write(results)
			self.mail.close()
		return results
	#	----------------------------------------------------------------------
	def playerRoster(self, request = None, forPower = None, reveal = 0):
		results = '  Master:%9s%-*s %s\n' % ('', (22, 17)[request == 'LIST'],
			self.gm.player[0].split('|')[-1].replace('_', ' ') *
			(request != 'LIST'), self.gm.address[0])
		for powerName in self.map.powers:
			try: power = [x for x in self.powers if x.name == powerName][0]
			except: continue
			results += '  %-15s ' % (self.anglify(powerName) + ':')
			if power.player: player = power.player[:]
			elif not power.address: player = ['|someone@somewhere|']
			else: player = ['|%s|' % power.address[0]]
			if request == 'LIST': del player[1:]
			elif (power.isResigned() and self.phase != self.map.phase
			and power.isEliminated()): del player[:2]
			if player[0] == 'DUMMY':
				boss = power.controller()
				if boss: player[0] += '|' + boss.name
			for data in reversed(player):
				person = data.split('|')
				if len(person) > 2:
					late = 'late' * (not not (self.deadline
						and data == player[-1]
						and self.phase not in ('COMPLETED', 'FORMING')
						and powerName in self.latePowers()
						and self.deadlineExpired()
						and ('HIDE_LATE_POWERS' not in self.rules
						or forPower is not None
						and forPower.name in (powerName, 'MASTER'))))
					if (self.phase != 'COMPLETED' or ('NO_REVEAL' in self.rules
					and not reveal)) and (forPower is None
					or forPower.name not in ('MASTER', powerName)
					or forPower.name == powerName and data != player[-1]):
						person = (None, 'someone@somewhere', late)
				elif person[0] == 'RESIGNED':
					late = 'vacant'
					person = ('', '*', late)
				elif person[0] == 'DUMMY':
					late = 'dummy'
					if len(person) > 1 and (self.phase == 'COMPLETED'
					or 'HIDE_DUMMIES' not in self.rules
					or forPower is not None
					and forPower.name in (powerName, power[1], 'MASTER')):
						late = 'vassal of ' + self.anglify(person[1])
					person = ('', '*', late)
				else:
					results += '   from %-10s' % (data + ':')
					continue
				if request != 'LIST':
					results += ('%-22s %s\n' %
						(person[-1].replace('_', ' '), person[1]))
					continue
				status = ('%2d/%-2d' % (len(power.units) + len(power.retreats),
					len([x for x in power.centers if x != 'SC*'])),
					' ?/? ')['BLIND' in self.rules and (forPower is None
					or forPower.name not in ('MASTER', powerName))]
				if status == ' 0/0 ': late = status = ''
				results += '%-7s %5s     %s\n' % (late, status, person[1])
		return results + '\n'
	#	----------------------------------------------------------------------
	def updateAdjustOrders(self, power, orders):
		for who, adj in self.distributeOrders(power, orders):
			self.addAdjustOrders(who, adj)
		if not self.error: self.process()
		return self.error
	#	----------------------------------------------------------------------
	def addAdjustOrders(self, power, orders):
		if not orders:
			power.adjust, power.cd = [], 0
			return
		adjust, kept, places = [], [], []
		need, sites = len(power.centers) - len(power.units), 0
		if [x for x in power.centers if x in power.homes]:
			need += (self.map.reserves.count(power.name) +
				min(self.map.militia.count(power.name),
				len([0 for x in power.units
					if x[3:5] in power.homes])))
		orderType, claim = ('BUILD', 'REMOVE')[need < 0], []
		if need > 0: 
			sites = self.buildSites(power)
			need = min(need, self.buildLimit(power, sites))
			alternatives = self.buildAlternatives(power, sites)
		for order in orders:
			order = order.strip()
			if not order: continue
			word = self.expandOrder([order])
			if word[-1] in 'BDK': word = word[-1:] + word[:-1]
			if word[-1] in 'RH': word = word[-1:] + word[:-1]
			if word[0] == 'B': word[0] = 'BUILD'
			elif word[0] in 'RD': word[0] = 'REMOVE'
			elif word[0] in 'KH': word[0] = 'KEEP'
			elif word[0] == 'V': word[0] = 'WAIVED'
			if word[0] == orderType: pass
			elif word[0] in ('BUILD', 'REMOVE'):
				self.error += [word[0] + ' NOT ALLOWED: ' + order]
				continue
			elif word[0] != 'KEEP': word[:0] = [orderType]
			if word[0] != 'BUILD':
				word = word[:1] + self.addUnitTypes(word[1:])
			if len(word) == 4 and word[3] == 'HIDDEN': word = word[:-1]
			order = ' '.join(word)
			if word[0] in ('REMOVE', 'KEEP'):
				if len(word) == 3:
					unit = ' '.join(word[1:])
					if unit not in power.units:
						self.error += ['NO SUCH UNIT: ' + unit]
					elif word[0] == 'KEEP' and (order not in kept
					and ('REMOVE ' + unit) not in adjust): kept += [order]
					elif word[0] == 'REMOVE' and (order not in adjust
					and ('KEEP ' + unit) not in kept): adjust += [order]
					else: self.error += ['MULTIPLE ORDERS FOR UNIT: ' + unit]
				else: self.error += ['BAD ADJUSTMENT ORDER: ' + order]
			elif len(word) == 2 and word[1] in ('WAIVE', 'WAIVED', 'V'):
				if len(adjust) < need: adjust += ['BUILD WAIVED']
			elif len(word) == 3:
				site = word[2][:3]
				if ('&SC' in power.homes
				and site not in power.homes): claim += [site]
				if site not in sites:
					self.error += ['INVALID BUILD SITE: ' + order]
				elif site in places:
					self.error += ['MULTIPLE BUILDS IN SITE: ' + order]
				elif not self.map.isValidUnit(' '.join(word[1:])):
					self.error += ['INVALID BUILD ORDER: ' + order]
				else:
					for limits in alternatives:
						if site in limits and len(
							[x for x in limits if x not in places]) == 1:
							self.error += ['BUILDS IN ALL ALTERNATIVE SITES ('
								+ ', '.join(limits) + '): ' + order]
							break
					else:
						adjust += [order + ' HIDDEN' * (
							'HIDE_BUILDS' in self.rules or 
							site in self.map.hidden.get(power.name, []))]
						places += [site]
			else: self.error += ['BAD ADJUSTMENT ORDER: ' + order]
		if len(claim) > power.homes.count('&SC'):
			self.error += ['EXCESS HOME CENTER CLAIM']
		if self.error: return
		while 0 < need < len(adjust):
			try: adjust.remove('BUILD WAIVED')
			except: break
		if 'BUILD WAIVED' in adjust or power.isDummy() and not power.ceo:
			while len(adjust) < need:
				adjust.append('BUILD WAIVED')
		if len(adjust) != abs(need):
			self.error += ['ADJUSTMENT ORDERS IGNORED (MISCOUNTED)']
			return
		power.adjust, power.cd = adjust, 0
	#	----------------------------------------------------------------------
	def updateRetreatOrders(self, power, orders):
		for who, adj in self.distributeOrders(power, orders):
			self.addRetreatOrders(who, adj)
		if not self.error: self.process()
		return self.error
	#	----------------------------------------------------------------------
	def addRetreatOrders(self, power, orders):
		if not orders:
			power.adjust, power.cd = [], 0
			return
		adjust, retreated = [], []
		for order in orders:
			word = self.addUnitTypes(self.expandOrder([order]))
			if word[0] == 'R' and len(word) > 3:
				del word[0]
			if word[0] in 'RD': word = word[1:] + word[:1]
			unit = ' '.join(word[:2])
			try: unit = [x for x in power.retreats
				if x == unit or x.startswith(unit + '/')][0]
			except:
				self.error.append('UNIT NOT IN RETREAT: ' + unit)
				continue
			if unit in retreated:
				self.error.append('TWO ORDERS FOR RETREATING UNIT: ' + unit)
				continue
			word[1] = unit[2:]
			if len(word) == 3 and word[2] in 'RD':
				word[2] = 'DISBAND'
			elif len(word) == 4 and word[2] in 'R-':
				word[2] = '-'
				if word[3] not in power.retreats[unit]:
					self.error.append('INVALID RETREAT DESTINATION: ' +
						' '.join(word))
					continue
			else:
				self.error.append('BAD RETREAT ORDER: ' + ' '.join(word))
				continue
			retreated += [unit]
			adjust += ['RETREAT ' + ' '.join(word)]
		if not self.error:
			if len(retreated) != len(power.retreats):
				self.error += ['RETREAT ORDERS IGNORED (INCOMPLETE)']
			else: power.adjust, power.cd = adjust, 0
	#	----------------------------------------------------------------------
	def powerOrders(self, power):
		try:
			if self.phaseType in 'RA': orders = '\n'.join(power.adjust)
			else: orders = self.getOrders(power)
		except: orders = ''
		return ('Current orders for %s:\n\n%s\n\n' %
			(self.anglify(power.name), orders or '(None)'))
	#	----------------------------------------------------------------------
	def playerOrders(self, power):
		orders = self.powerOrders(power)
		orders += ''.join([self.powerOrders(x)
			for x in power.vassals(indirect = True)])
		return orders + 'End of orders.\n'
	#	----------------------------------------------------------------------
	def lateNotice(self, after = 0):
		#	-----------------------------------------------------------------
		#	Set after to 1 to force a late notice as if the grace expired,
		#   or to -1 to get a notice of the powers in CD who were expected
		#	to have orders in (so not the trivial cases, such as uncontrolled
		#	dummies or virtually eliminated powers).
		#	-----------------------------------------------------------------
		late, now = self.latePowers(after), self.getTime()
		text = ('Diplomacy Game:   %s (%s)\n'
				'Current Phase:    %s\n' %
				(self.name, host.dpjudgeID, self.phaseName(form = 2)))
		#	-----------------------------
		#	Pre-deadline warning messages
		#	-----------------------------
		if after > 0 or self.deadlineExpired():
			text += 'Missed Deadline:  %s\n' % self.timeFormat()
		elif after == 0:
			for power in late: self.mailPress(None, [power],
				"%s\n\nThe deadline for '%s' is approaching and\n"
				'orders for %s have not yet been submitted.\n\n'
				'The pending deadline is %s.\n' %
				('\n'.join(self.mapperHeader()),
				self.name, self.anglify(power), self.timeFormat()),
				subject = 'Diplomacy deadline reminder')
			return
		#	-----------------------------------------
		#	Other notices (late, beyond grace and cd)
		#	-----------------------------------------
		if not late and after < 0: return
		receivers, omnis = ['MASTER'], ['MASTER']
		who = '\n'.join(textwrap.wrap(', '.join(map(self.anglify,
			late or ['MASTER'])), 70, subsequent_indent = ' ' * 18))
		multi = 's' * (len(late) != 1)
		#	----------------------------
		#	Turn is processing -- notify
		#	the master of those in cd
		#	----------------------------
		if after < 0:
			self.mailPress(None, ['MASTER'], text + '%-18s' %
				('Power%s in CD: ' % multi) + who + '\n'
				+ '\n\n(This notice is sent ONLY to the GameMaster '
				+ 'and any omniscient observer.)',
				subject = 'Diplomacy CD notice')
			return
		#	----------------------------
		#	Past grace -- resign anyone
		#	who is still late and say so
		#	----------------------------
		if late and self.graceExpired():
			controllers = []
			for power in [x for x in self.powers if x.name in late]:
				controller = power.isDummy() and power.controller() or power
				if controller.name not in controllers:
					controllers += [controller.name]
			who = '\n'.join(textwrap.wrap(', '.join(map(self.anglify,
				controllers)), 70, subsequent_indent = ' ' * 18))
			multi = 's' * (len(controllers) != 1)
			self.mailPress(None, ['All!'], text + '%-18s' %
				('Dismissed Power%s: ' % multi) + who + '\n',
				subject = 'Diplomacy player dismissal')
			for power in [x for x in self.powers if x.name in controllers]:
				power.resign()
				#self.avail += ['%s-(%s)' % (power.name,
				#	('%d/%d' % (len(power.units), len(power.centers)), '?/?')
				#	['BLIND' in self.rules])]
				#if self.phase in self.map.phase:
				#	power.player = ['RESIGNED']
				#else:
				#	when = self.phaseAbbr()
				#	if when[0] == '?': when = self.outcome[0]
				#	power.player[:0] = ['RESIGNED', when]
			return
		#	-------------------------------------
		#	Normal late notice; first specify any
		#	consequences of continuing tardiness.
		#	-------------------------------------
		if late and self.timing.get('GRACE'):
			cd = len([1 for x in self.powers if x.name in late and x.isCD(1)])
			resign, cd = len(late) - cd > 0, cd > 0
			all = (('HIDE_DUMMIES' in self.rules or [1 for x in self.powers
				if x.name in late and not x.isDummy()]) and 'Powers'
				or (not cd and [1 for x in self.powers if x.name in late
				and x.controller()]) and 'Controlling powers'
				or ('VASSAL_DUMMIES' in self.rules and not [1 for x in
				self.powers if x.name in late and not x.ceo]) and 'Vassals'
				or 'Dummies')
			count = int(self.timing['GRACE'][:-1])
			penalty = ('\n\n%s who are still late %d %s%s after the\n'
				'deadline above will be %s.' % (all, count,
				{'W': 'week', 'D': 'day', 'H': 'hour', 'M': 'minute'}.
				get(self.timing['GRACE'][-1], 'second'), 's'[count == 1:],
				'either ' * resign * cd + 'summarily dismissed' * resign +
				'\nor ' * resign * cd + 'declared in civil disorder' * cd))
		else: penalty = ''
		#	-----------------------------------
		#	Send late notice.  If it's the same
		#	calendar hour as the deadline, send
		#	it to everyone.  Otherwise, only
		#	bother the late powers.
		#	-----------------------------------
		hide = 'HIDE_LATE_POWERS' in self.rules
		if now[:10] != self.deadline[:10]:
			receivers += [x.name for x in self.powers
				if not (x.isDummy() or x.isResigned()) and
				(x.name in late or [1 for y in x.vassals() if y.name in late])]
		else:
			receivers += [x.name for x in self.powers
				if not (x.isDummy() or x.isResigned())]
			omnis += [x.name for x in self.powers if x.omniscient]
		for receiver in receivers:
			if receiver in omnis: what, many, mate = who, multi, []
			else:
				power = [x for x in self.powers if x.name == receiver][0]
				mate = [receiver] * (receiver in late) + [
					y.name for y in power.vassals() if y.name in late]
				if hide:
					what = '\n'.join(textwrap.wrap(', '.join(map(self.anglify,
						mate)), 70, subsequent_indent = ' ' * 18))
					many = 's' * (len(mate) != 1)
				else: what, many = who, multi
			self.mailPress(None, [receiver],
				text + ('%-18s' % ('Late Power%s: ' % many) + what,
				'One or more powers are late.')[not what] + penalty + '\n',
				subject = ('Diplomacy deadline missed', 'Diplomacy late notice')
				[not mate], private = 1)
	#	----------------------------------------------------------------------
	def shortList(self):
		variant = self.map.name
		if self.variant: variant += ', ' + self.variant
		variant, press = variant.title(), ['-'] * 4
		if self.private: variant = 'PRIVATE, ' + variant
		if self.phase == 'FORMING': need = [
			'To join, e-mail "JOIN %s password%s"' %
			(self.name, (' privacyPassword', '')[not self.private]),
			'Forming: %s more player%s needed.' %
			(self.avail[0], 's'[self.avail[0] == '1':])]
		elif self.avail:
			avail = [' '.join(x.title().split('-')) for x in self.avail]
			need = ['To join, e-mail "TAKEOVER %s@%s password"' %
				(avail[0].split()[0].lower(), self.name) +
				' privacyPassword' * (self.private != None),
				'Openings: ' + ', '.join(avail)]
		else: need = []
		if 'NO_PRESS' not in self.rules:
			if 'FAKE_PRESS' in self.rules: press[3] = 'F'
			elif 'GREY_PRESS' in self.rules: press[1] = 'G'
			elif 'WHITE_GREY' in self.rules: press[:2] = ['W', 'G']
			else: press[0] = 'W'
			if 'PUBLIC_PRESS' not in self.rules: press[2] = 'P'
		result = ('%-9s %-9s%s, Gunboat, Moderated (%s), Press:%s.\n' %
			(self.name,
			self.phaseAbbr((None, self.map.phase)[self.phase == 'FORMING']),
			variant, self.gm.address[0].split('@')[0], ''.join(press)))
		indent = 20 + (len(need) == 1)
		if need: result += (' ' * indent + 'URL: %s%s?game=%s\n' %
			(host.dpjudgeURL, '/index.cgi' * (os.name == 'nt'), self.name))
		for line in need:
			result += ' ' * indent + line + '\n'
			indent += 1
		return result
	#	----------------------------------------------------------------------
	def reportOrders(self, power, email = None):
		header = '\n'.join(self.mapperHeader()) + '\n'
		if not email and 'BROADCAST_ORDERS' in self.rules:
			return self.mailPress(None, ['All'],
				header + self.playerOrders(power),
				subject = 'Diplomacy orders %s ' % self.name + self.phaseAbbr())
		if email:
			whoTo = email
			if power.address and not [
				1 for x in email.upper().split(',')
				if x in power.address[0].upper().split(',')]:
				whoTo += ',' + power.address[0]
		else: whoTo = power.address[0]
		self.openMail('Diplomacy orders %s ' % self.name + self.phaseAbbr(),
			mailTo = whoTo, mailAs = host.dpjudge)
		self.mail.write(header + self.playerOrders(power))
		self.mail.close()
	#	----------------------------------------------------------------------
	def setAbsence(self, power, nope):
		if not nope: return
		if 'NOT' in self.timing: self.timing['NOT'] += ','
		else: self.timing['NOT'] = ''
		self.timing['NOT'] += nope
		if nope[0] == '-':
			full = len(nope[1:]) > 8
			date = self.getTime(nope[1:], 3 + 2 * full) 
			line = 'until %s' % date.format(4 - 4 * full)
		elif '-' in nope:
			dates = nope.split('-')
			full = len(dates[0]) > 8
			date = self.getTime(dates[0], 3 + 2 * full) 
			line = 'from %s\n' % date.format(4 - 4 * full)
			full = len(dates[1]) > 8
			date = self.getTime(dates[1], 3 + 2 * full) 
			line += 'to %s' % date.format(4 - 4 * full)
		else:
			full = len(nope) > 8
			date = self.getTime(nope, 3 + 2 * full) 
			line = 'for %s' % date.format(4 - 4 * full)
		for who in (1, 0):
			who = ([x.name for x in self.powers
				if x.type != 'MONITOR'] *
				('SILENT_ABSENCES' not in self.rules),
				['MASTER'])[who]
			if who: self.mailPress(None, who,
				"An absence for game '%s' has been entered\n"
				'%s%s.\n' % (self.name, ('by %s ' %
				(power.name == 'MASTER' and 'the Master'
				or self.anglify(power.name))) *
				('HIDE_ABSENTEES' not in self.rules
				or 'MASTER' in who), line),
				subject = 'Diplomacy absences notice')
			self.save()
	#	----------------------------------------------------------------------
	def pressSettings(self):
		if 'NO_PRESS' in self.rules: return 'None.'
		press = []
		for rule, text in (	('FAKE_PRESS', 'Fake'),
							('GREY_PRESS', 'Grey'),
							('WHITE_GREY', 'White, Grey'),
							('YELLOW_PRESS', 'Yellow')):
			if rule in self.rules: press += [text]
		press = press or ['White']
		for rule, text in (	('FTF_PRESS', 'Face-to-Face Restrictions'),
							('TOUCH_PRESS', 'Touch'),
							('BACKSEAT_PRESS', 'Backseat')):
			if rule in self.rules: press += [text]
		if 'BACKSEAT_PRESS' not in self.rules:
			press += [('Private', 'Public')['PUBLIC_PRESS' in self.rules]]
		return ', '.join(press) + '.'
	#	----------------------------------------------------------------------
	def logAccess(self, power, pwd, origin = 0):
		if type(power) not in (str, unicode, int): power = power.name
		if not origin:
			try: origin = socket.gethostbyaddr(os.environ['REMOTE_ADDR'])[0]
			except: pass
			if not origin or origin == 'unknown':
				origin = os.environ.get('REMOTE_ADDR', 'unknown')
		access = self.file('access')
		#	--------------------
		#	Cheater-catcher code
		#	--------------------
		jk, gm = [x.upper().split('@')
			for x in (host.judgekeeper, self.gm.address[0])]
		outsider = (jk[0] != gm[0]
			or jk[1].split('.')[-2:] != gm[1].split('.')[-2:])
		powers = [[x.name, x.password.upper()]
			for x in self.powers if x.password]
		if ([power, pwd.upper()] in ['MASTER', self.gm.password.upper()] + powers
		and not self.private
		and origin != 'unknown'
		and not [1 for x in host.publicDomains if x in origin]):
			try: lines = open(access, encoding='latin-1').readlines()
			except: lines = []
			for line in lines:
				word = line.upper().strip().split()
				if len(word) < 8: continue
				if (word[5] == origin.upper() # and '@' not in word[5]
				and word[6] != power and word[6:] in powers
				and not [1 for x in (self.gm.password.upper(),
				host.judgePassword.upper()) if x in (word[7], pwd.upper())]):
					for addr in [self.gm.address[0]] + host.detectives * outsider:
						self.openMail('Diplomacy suspicious activity',
							mailTo = addr, mailAs = host.dpjudge)
						self.mail.write('GameMaster:\n\n'
							"The login just made by '%s' in game '%s' is\n"
							"suspiciously similar to logins made by '%s'.\n\n"
							'This may need to be investigated at\n'
							'%s?game=%s&power=MASTER&password=%s\n' %
							(self.anglify(power), self.name,
							self.anglify(word[6]),
							host.dpjudgeURL, self.name, self.gm.password))
						self.mail.close()
					break
		#	---------------------------
		#	End of cheater-catcher code
		#	---------------------------
		file = open(access, 'a')
		if pwd == self.gm.password: pwd = '!-MASTER-!'
		elif pwd == host.judgePassword: pwd = '!-JUDGEKEEPER-!'
		temp = '%s %-16s %-10s %s\n' % (self.getTime().cformat(), origin, power, pwd)
		file.write(temp.encode('latin-1'))
		del temp
		file.close()
		try: os.chmod(access, 0666)
		except: pass
	#	----------------------------------------------------------------------
	def mailMap(self, email, mapType, power = None):
		fileName = (host.gameMapDir + '/' + self.name +
			(power and 'BLIND' in self.rules and power.password or '')
			+ '.' + mapType)
		if not os.path.isfile(fileName): return
		import base64
		showName = self.name + '.' + mapType
		boundary = "----_=_NextPart_001_01C463A7.29323139"
		file = open(fileName, 'rb')
		contents = base64.encodestring(file.read())
		file.close()
		mail = Mail(email,
			subject = "Diplomacy %s map (%s)" % (mapType.upper(), self.name),
			header = 'Content-Type: multipart/mixed;\n'
					'\tboundary="%s"' % boundary)
		mail.write(
			'--%s\n'
			'Content-Type: text/plain;\n'
			'\tcharset="us-ascii"\n'
			'Content-Transfer-Encoding: quoted-printable\n\n'
			'The Diplomacy map %s is attached.\n\n'
			'--%s\n'
			'Content-Type: application/octet-stream; name="%s"\n'
			'Content-Transfer-Encoding: base64\n'
			'Content-Description: %s\n'
			'Content-Disposition: attachment; filename="%s"\n\n'
			'%s\n'
			'--%s--\n' %
			(boundary, showName, boundary, showName, showName, showName, 
			contents, boundary))
		mail.close()
		return 1
	#	-------------------------------------------------------
	def collectState(self):
		status = self.status[:]
		if status[1] == 'preparation': return
		if self.error and status[1] not in ('completed', 'terminated'):
			status[1] = 'error'
		self.state = {
						'MASTER':	self.gm.password + ':' +
							self.gm.player[0].split('|')[0],
						'STATUS':	':'.join(status).upper(),
						'PHASE':	self.phaseAbbr(),
						'DEADLINE':	self.deadline,
						'ZONE':		self.zone and self.zone.__repr__() or 'GMT',
						'PRIVATE':	self.private or '',
						'MAP':		self.map.name,
						'RULES':	':'.join(self.rules),
					}
		for power in self.powers:
			if power.player and power.password and power.player[0][0] == '#':
				if (status[1] == 'active' and self.deadlineExpired()
				and power.name in self.latePowers()): what = 'LATE'
				else: what = power.type or 'POWER'
				self.state[power.name] = ':'.join(
					(what, power.password, power.player[0].split('|')[0]))
	#	----------------------------------------------------------------------
	def updateState(self):
		# return # TEMP! BUT AS OF NEW YEARS MOMENT 2007, APACHE SEEMS WAY SICK
		if not host.dppdURL: return
		self.collectState()
		header = '|'.join([x + ':' + (y or '') for x,y in self.state.items()])
		if self.outcome: result = '|RESULT:' + ':'.join(self.outcome)
		else: result = ''
		header = ('JUDGE:%s|GAME:%s%s|' %
			(host.dpjudgeID, self.name, result) + header)
		dict = urllib.urlencode({'status': header.encode('latin-1')})
		for dppdURL in host.dppdURL.split(','):
			#   -----------------------------------------------------
			#	I don't know why, but we need to use the query string
			#	instead of a POST.  Something to look into.
			#   -----------------------------------------------------
			query = '?&'['?' in dppdURL]
			page = urllib.urlopen(dppdURL + query + 'page=update&' + dict)
			#   ----------------------------------------------------------
			#   Check for an error report and raise an exception if that's
			#   the case. Double check the DPPD code for any print
			#   statements, as it may reveal the whole game status info to
			#   the unsuspecting player.
			#   ----------------------------------------------------------
			lines = page.readlines()
			page.close()
			if [1 for x in lines if 'DPjudge Error' in x]:
				#	Make absolutely sure it doesn't print the game status!!
				print '\n'.join(lines) 
				raise DPPDStatusUpdateFailed
	#	----------------------------------------------------------------------
	def changeStatus(self, status):
		self.status[1] = status
		Status().changeStatus(self.name, status)
	#	----------------------------------------------------------------------
	def setState(self, mode):
		if self.status[1] == mode: return
		#if self.status[1] == 'preparation' and mode != 'forming':
		#	return 'Please allow the game to form first'
		if self.phase == 'FORMING':
			if mode == 'active': self.begin()
		elif self.phase == 'COMPLETED':
			return ('Please discuss with the judgekeeper why ' +
				'you consider changing the state of a completed game')
		elif mode == 'forming':
			return ('You can only go back to the forming state ' +
				'by performing a ROLLBACK to the FORMING phase')
		self.changeStatus(mode)
	#	----------------------------------------------------------------------
	def loadRules(self):
		rule = group = variant = ''
		data, forced, denied = {}, {}, {}
		try: file = open(host.packageDir + '/pages/Rules', encoding='latin-1')
		except: return data, forced, denied
		for line in file:
			word = line.strip().split()
			if word[:2] == ['<!--', 'RULE'] and word[-1][-1] == '>':
				if word[2] == 'GROUP': group = ' '.join(word[3:-1])
				elif word[2] == 'VARIANT':
					variant = word[3]
					forced[variant] = [x[1:] for x in word[4:-1] if x[0] == '+']
					denied[variant] = [x[1:] for x in word[4:-1] if x[0] == '!']
				elif word[2] != 'END':
					rule = word[2]
					if rule not in data:
						data[rule] = {'group': group, 'variant': variant}
					for control in word[3:-1]:
						if control[0] in '-=+!': data[rule].setdefault(
							control[0],[]).append(control[1:])
		file.close()
		return data, forced, denied
	#	----------------------------------------------------------------------


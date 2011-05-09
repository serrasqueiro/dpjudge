import os, time, random, socket, textwrap, urllib
from codecs import open

import host

from Status import Status
from Power import Power
from Mail import Mail

class Game:
	#	----------------------------------------------------------------------
	class Time(str):
		#	------------------------------------------------------------------
		def __new__(self, when = 0):
			return str.__new__(self, '%02d'*5 % (when or time.localtime())[:5])
		#	------------------------------------------------------------------
	#	----------------------------------------------------------------------
	def __init__(self, name = '', fileName = 'status'):
		if 'variant' not in vars(self): variant = ''
		if 'powerType' not in vars(self): powerType = Power
		vars(self).update(locals())
		if name: self.load(fileName)
		else: self.reinit()
	#	----------------------------------------------------------------------
	def __repr__(self):
		text = ('GAME ' + self.name + (self.await and '\nAWAIT '
				or self.skip and '\nSKIP ' or '\nPHASE ') + self.phase)
		if self.map: text += '\nMAP ' + self.map.name
		if len(self.morphs) > 3 or [1 for x in self.morphs if not x.strip()]:
			text += '\nMORPH'
			for morph in self.morphs: text += '\n' + morph
			text += '\nEND MORPH'
		else:
			for morph in self.morphs: text += '\nMORPH ' + morph
		if self.master: text += '\nMASTER ' + '|'.join(self.master)
		text += '\nPASSWORD ' + self.password
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
		if self.zone: text += '\nZONE ' + self.zone
		if self.delay: text += '\nDELAY %d' % self.delay
		if self.timing:
			text += '\nTIMING ' + ' '.join(map(' '.join, self.timing.items()))
		for terrain, changes in self.terrain.items():
			for site, abuts in changes.items():
				text += '\n%s %s ' % (terrain, site) + ' '.join(abuts)
		return '\n'.join([x for x in text.split('\n')
					if x not in self.directives]).encode('latin-1') + '\n'
	#	----------------------------------------------------------------------
	def reinit(self, includePersistent = 1):
		#	------------------------------------
		#	Initialize the persistent parameters
		#	------------------------------------
		if includePersistent:
			playerTypes, desc, master, powers, norules = [], [], [], [], []
			rotate, directives, origin = [], [], []
			avail, zones, morphs = [], [], []
			try: metaRules = self.rules[:]
			except: metaRules, rules = [], []
			groups = password = start = ''
			map = private = zone = None
			timing, terrain, status = {}, {}, Status().dict.get(name, [])
			#	------------------------------------------------------
			#	When we run out of directory slots, the line below can
			#	be changed to '/'.join(host.gameDir, name[0], name)
			#	------------------------------------------------------
			gameDir = host.gameDir + '/' + name
			os.putenv('TZ', 'GMT')
		#	-----------------------------------
		#	Initialize the transient parameters
		#	-----------------------------------
		outcome, error, state = [], [], {}
		end = phase = skip = ''
		mail = proposal = season = year = phaseType = None
		mode = preview = deadline = delay = win = await = None
		modeRequiresEnd = includeOwnership = None
		for power in self.powers: power.reinit(includePersistent)
		vars(self).update(locals())
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
		if via in check: check = [via]
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
					and 'NO_RETURN' not in self.rules): return 1
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
			0		- it is valid BUT some unit mentioned does not exist
			1		- it is completely valid
		"""
		if not order: return
		word, owner, rules = order.split(), self.unitOwner(unit), self.rules
		error = ([], self.error)[report]
		map, status = self.map, owner != None
		unitType, unitLoc, orderType = unit[0], unit[2:], word[0]
		#	-------------------------------------
		#	Make sure the unit exists or (if the
		#	player is in a game in which he can't
		#	necessarily know) could exist.  Also
		#	make sure any mentioned (supported or
		#	convoyed unit could exist and could
		#	reach the listed destination).
		#	-------------------------------------
		if 'FICTIONAL_OK' in rules:
			if not map.isValidUnit(unit):
				return error.append('ORDER TO INVALID UNIT: ' + unit)
			if word[0] in ('S', 'C') and word[1] in ('A', 'F'):
				other = ' '.join(word[1:3])
				if not map.isValidUnit(other, 1):
					return error.append('ORDER INCLUDES INVALID UNIT: ' + other)
				if len(word) == 5:
					other = word[1] + ' ' + word[4]
					if not map.isValidUnit(other, 1):
						return error.append('IMPOSSIBLE ORDER FOR ' + unit)
		elif not status:
			return error.append('ORDER TO NON-EXISTENT UNIT: ' + unit)
		elif (power is not owner and 'PROXY_OK' not in rules
		and 'ORDER_ANY' not in rules):
			return error.append('ORDER TO FOREIGN UNIT: ' + unit)
		#	-----------------------------------------------------------------
		#	Validate that anything in a SHUT location is only ordered to HOLD
		#	-----------------------------------------------------------------
		if map.areatype(unitLoc) == 'SHUT' and orderType != 'H':
			return error.append('UNIT MAY ONLY BE ORDERED TO HOLD: ' + unit)
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
				status = 0
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
					return error.append(
						'SUPPORTED UNIT CANNOT REACH DESTINATION: %s ' %
						unit + order)
				#	----------------------------------
				#	Support across an adjacency listed
				#	in Map.abutRules['*'] is invalid.
				#	Ditto for abutRules['~'].
				#	----------------------------------
				elif ((unitLoc, dest) in map.abutRules.get('*', []) +
										 map.abutRules.get('~', [])):
					return error.append(
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
					return error.append(
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
			if 'FICTIONAL_OK' not in self.rules:
				self.checkLeague(owner, unit, order, word, orderText)
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
			and (orderType < 'C' or 'NO_RETURN' in self.rules)):
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
				if to in visit and 'NO_RETURN' in rules: return error.append(
					'CONVOYING UNIT USED TWICE IN SAME CONVOY: %s ' %
					unit + order)
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
			proxyTo = ''.join(word[1:])
			if proxyTo not in map.powers or proxyTo == power.name:
				return error.append('IMPROPER PROXY ORDER: %s ' % unit + order)
		else: return error.append('UNRECOGNIZED ORDER TYPE: %s ' % unit + order)
		#	--------
		#	All done
		#	--------
		return status
	#	----------------------------------------------------------------------
	def checkLeague(self, owner, unit, order, word, orderText):
		#	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
		#	At present, this method is not called during order input
		#	validation for games that use the FICTIONAL_OK rule.
		#	This is to assist Crystal Ball, in which we have no way
		#	of knowing whether any "owner" of a unit will be the same
		#	next turn.  Probably what should happen is this method
		#	should be called at adjudication time from somewhere
		#	in the XtalballGame object to drive whether an ordered
		#	unit should HOLD instead (of violate its league rules).
		#	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
		error = self.error
		if not owner or len(self.map.leagues.get(owner.name, [])) <= 1: return
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
	#	----------------------------------------------------------------------
	def expandOrder(self, word):
		#	---------------------------------
		#	Provide spacing around dashes and
		#	vertical bars; change -> into -
		#	---------------------------------
		error, result = self.error, ''
		for ch in ' '.join(word):
			if result and ((ch in '|-' and result[-1] != ' ')
			or (ch != ' ' and result[-1] in '|-')):
				result += ' '
				if result[-2] + ch == '->': continue
			result += ch
		#	------------------------------------
		#	Convert aliases to recognized tokens
		#	------------------------------------
		final, result, which = [], result.split(), 0
		if 'NO_CHECK' in self.rules: [error.append('AMBIGUOUS PLACENAME: ' + x)
			for x in result if x.upper() in self.map.unclear]
		while which < len(result):
			#	Don't convert anything after a proxy request
			if 'P' in final: item, parsed = result[which].upper(), 1
			else: item, parsed = self.map.alias(result[which:])
			if item: final += [item]
			which += parsed or 1
			if not parsed and 'NO_CHECK' in self.rules:
				error += ['UNRECOGNIZED DATA IN ORDER: ' + item]
		#	-------------------------------
		#	Remove the "H" from any order
		#	having the form "u xxx S xxx H"
		#	-------------------------------
		if len(final) > 5 and final[2] == 'S':
			if (len(final), final[5]) == (6, 'H'): del final[5]
			elif ('NO_CHECK' in self.rules
			and len(final) == 7 and '/' in final[6]):
				error += ['COAST NOT ALLOWED IN SUPPORT ORDER: ' + 
					' '.join(word)]
				#   --------------------------------------------
				#   Comment out the above error += command to
				#   allow coastal designation in a support order
				#   in a NO_CHECK game to be silently ignored.
				#   --------------------------------------------
				final[6] = final[6][:3]
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
			else:
				try:
					unit = [x for y in self.powers for x in y.units
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
	def loadMap(self, mapName = 'standard', lastPhase = 0):
		import Map
		self.map, phases = Map.Map(mapName), []
		self.error += self.map.error
		#	-------------------------------------------
		#	Have the Game process all lines in the map
		#	file that were in DIRECTIVES clauses (this
		#	includes any RULE lines).  Do this for all
		#	directives given without a variant and for
		#	those specified for this Game's variant.
		#	-------------------------------------------
		self.load(self.map.directives.get('ALL', []) +
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
	def setTimeZone(self, zone = 'GMT'):
		if not self.zones:
			self.zones = ['GMT']
			zoneFile = open(host.toolsDir + '/zone.tab')
			for line in zoneFile:
				word = line.strip().split()
				if word and word[0][0] != '#': self.zones.append(word[2])
			zoneFile.close()
		if zone in self.zones:
			self.zone = zone
			os.putenv('TZ', zone)
		else: self.error += ['BAD TIME ZONE: ' + zone]
	#	----------------------------------------------------------------------
	def load(self, fileName = 'status', includePersistent = 1, includeOrders = 1):
		self.reinit(includePersistent)
		error, power = self.error, None
		if type(fileName) is not list:
			try: file = open(self.file(fileName), encoding='latin-1')
			except: return setattr(self, 'name', 0)
		else: file = fileName
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
				continue
			if type(file) is list: self.directives += [' '.join(word)]
			upword = word[0].upper()
			if blockMode == 0:
				# Start of first block, the game data
				if upword != 'GAME':
					error += ['OTHER DATA PRECEDING GAME DECLARATION: ' + ' '.join(word)]
				else: 
					if word[1:] != [self.name]: error += ['GAME NAME MISMATCH']
					blockMode = 1
					self.mode = self.modeRequiresEnd = None
			elif blockMode == 1:
				# Game data
				if self.mode and upword == 'END' and len(word) == 2 and word[1].upper == self.mode:
					self.mode = self.modeRequiresEnd = None
				elif not self.parseGameData(self, word, includePersistent) and includePersistent:
					error += ['UNRECOGNIZED GAME DATA: ' + ' '.join(word)]
			elif blockMode == 2:
				# Power (or observer, etc.)
				power = self.determinePower(word)
				if not power:
					error += ['NOT A POWER DECLARATION: ' + ' '.join(word)]
				else:
					blockMode = 3
					self.mode = self.modeRequiresEnd = None
			else:
				# Power data
				if self.mode and upword == 'END' and len(word) == 2 and word[1].upper == self.mode:
					self.mode = self.modeRequiresEnd = None
				elif (not self.parsePowerData(self, power, word, includePersistent, includeOrders)
				and includePersistent and includeOrders):
					error += ['UNRECOGNIZED POWER DATA: ' + ' '.join(word)]
		if blockMode == 1:
			self.finishGameData() 
		elif blockMode == 3:
			self.finishPowerData(power)
		if type(fileName) is list: return
		self.validateStatus()
		self.setState()
	#	----------------------------------------------------------------------
	def parseGameData(self, word, includePersistent):
		error, upword = self.error, word[0].upper()
		#	-----
		#	Modes
		#	-----
		if self.mode:
			if not includePersistent: return 0
			#	--------------------------------------
			#	Game-specific information (persistent)
			#	--------------------------------------
			if self.mode == 'DESC':
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
		if upword in ('AWAIT', 'PHASE', 'SKIP'):
			if self.phase: error += ['TWO AWAIT/PHASE/SKIP STATEMENTS']
			elif len(word) > 1:
				self.phase = ' '.join(word[1:]).upper()
				if fileName == 'status':
					self.await = upword == 'AWAIT'
					self.skip = upword == 'SKIP'
				else: error += ['NO PHASE GIVEN']
		elif upword == 'RESULT':
			if len(word) > 1: self.outcome += word[1:]
		elif upword == 'FINISH':
			if self.end: error += ['TWO FINISH STATEMENTS']
			elif len(word) > 1: self.end = ' '.join(word[1:])
		elif upword == 'PROPOSAL':
			if self.proposal: error += ['TWO PROPOSALS']
			elif len(word) != 3: error += ['BAD PROPOSAL']
			else: self.proposal = word[1:]
		#	--------------------------------------
		#	Game-specific information (persistent)
		#	--------------------------------------
		elif not includePersistent:
			return 0
		elif upword == 'MASTER':
			if self.master: error += ['TWO MASTER STATEMENTS']
			elif len(word) == 1: error += ['NO MASTER SPECIFIED']
			else: self.master = word[1].split('|')
		if upword == 'PASSWORD':
			if len(word) != 2 or '<' in word[1] or '>' in word[1]:
				error += ['BAD PASSWORD: ' + ' '.join(word[1:]).
				replace('<', '&lt;').replace('>', '&gt;')]
			elif self.password: error += ['TWO MASTER PASSWORDS']
			else: self.password = word[1]
		elif upword == 'DESC':
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
		elif upword == 'RULE':
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
				if type(fileName) is list:
					if item not in self.map.rules: self.map.rules += [item]
					if item not in self.metaRules: self.metaRules += [item]
		elif upword == 'MAP':
			if self.map: error += ['TWO MAP STATEMENTS']
			elif len(word) == 2: self.loadMap(word[1])
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
		elif upword == 'DEADLINE':
			if self.deadline: error += ['TWO DEADLINES']
			elif (len(word) == 2 and word[1].isdigit()
			and len(word[1]) == 12): self.deadline = word[1]
			else: error += ['BAD DEADLINE: ' + ' '.join(word[1:])]
		elif upword == 'DELAY':
			if self.delay: error += ['TWO DELAYS']
			elif len(word) != 2: error += ['BAD DELAY']
			else:
				try:
					self.delay = int(word[1])
					if not (0 < self.delay < 73): raise
				except: error += ['BAD DELAY COUNT: ' + word[1]]
		elif upword == 'TIMING':
			try:
				for num in range(1, len(word), 2):
					key = word[num].upper()
					if key == 'NOT' and self.timing.get(key):
						self.timing[key] += ',' + word[num + 1].upper()
					elif key in self.timing:
						error += ['TWO %s SPECS IN TIMING' % key]
					elif key == 'DAYS': self.timing[key] = word[num + 1]
					else: self.timing[key] = word[num + 1].upper()
			except: error += ['BAD TIMING']
		elif upword == 'MORPH':
			if len(word) > 1: self.morphs += [' '.join(word[1:])]
			else: self.mode, self.modeRequiresEnd = upword, 1
		else: return 0
		return 1
	#	----------------------------------------------------------------------
	def finishGameData(self):
		self.mode = self.modeRequiresEnd = None
		#	-----------------------------
		#	Other lines require a map --
		#	default to standard if needed
		#	-----------------------------
		if not self.map: self.loadMap()
		if self.morphs:
			self.map.load(self.morphs)
			self.map.validate(force = 1)
		#	-------------------------
		#	Validate RULE consistency
		#	-------------------------
		self.validateRules()
	#	----------------------------------------------------------------------
	def determinePower(self, word):
		error, upword = self.error, word[0].upper()
		#	-----------------------
		#	Powers and other player
		#	types (observers, etc.)
		#	-----------------------
		if ((len(word) == 1 and upword in self.map.powers)
		or (len(word) == 2 and upword in (self.playerTypes +
				['POWER', 'OBSERVER', 'MONITOR'])
		and (upword == 'POWER'
		or word[1].upper() not in self.map.powers))):
			word.reverse()
			for power in self.powers:
				if word[0] == power.name: break
			else:
				if self.phase == 'FORMING':
					if len(word) == 1: word += ['POWER']
					elif word[-1] == 'POWER': del word[-1]
				word = [self] + [x.upper() for x in word]
				try: power = self.powerType(*word)
				except:
					error += ['BAD PARTICIPANT ' + line]
					return None
				if power.name in self.map.powers: power.abbrev = (
					self.map.abbrev.get(power.name, power.name[0]))
				else: power.abbrev = None
				self.powers += [power]
			return power
		return None
	#	----------------------------------------------------------------------
	def parsePowerData(self, power, word, includePersistent, includeOrders):
		error, upword = self.error, word[0].upper()
		#	-----
		#	Modes
		#	-----
		if self.mode:
			return 0
		#	-------------------------------
		#	Power-specific data (transient)
		#	-------------------------------
		if upword == 'CONTROL':
			if len(word) == 1:
				error += ['INVALID CONTROL FOR ' + power.name]
			elif power.password or power.ceo:
				error += ["TWO CONTROLS FOR " + power.name]
			else: power.ceo = [x.upper() for x in word[1:]]
		elif upword == 'FUNDS':
			if len(word) == 1: error += ['NO FUNDS DATA']
			else:
				try:
					for money in line.split()[1:]:
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
		elif upword in ('BUILD', 'REMOVE', 'RETREAT'):
			if not includeOrders: return -1
			power.adjust += [' '.join(word).upper()]
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
		elif upword == 'VOTE':
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
		elif upword in ('INHABITS', 'HOME'):
			power.home = self.map.home[power.name] = [x.upper() for x in word[1:]]
		elif upword == 'SEES':
			for sc in [x.upper() for x in word[1:]]:
				if sc in self.map.scs: power.sees += [sc]
				else: error += ['BAD SEEN CENTER: ' + sc]
		#	--------------------------------
		#	Power-specific data (persistent)
		#	--------------------------------
		elif not includePersistent:
			return 0
		elif upword == 'PASSWORD':
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
		elif upword == 'WAIT':
			power.wait = 1
		elif upword == 'MSG':
			power.msg += [' '.join(word[1:])]
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
		else: return 0
		return 1
	#	----------------------------------------------------------------------
	def finishPowerData(self, power):
		self.mode = self.modeRequiresEnd = None
	#	----------------------------------------------------------------------
	def validateStatus(self):
		#	----------------------------
		#	Make sure the game has a map
		#	----------------------------
		if not self.map: self.loadMap()
		if self.phase == 'FORMING': self.avail = [`len(self.map.powers) -
			len([1 for x in self.powers if x.type == 'POWER']) -
			len(self.map.dummies)`]
		rules, error = self.rules, self.error
		if self.phase not in ('FORMING', 'COMPLETED') and not self.deadline:
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
				and self.rotate[how + 1][0] in abbrev): continue
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
				win = self.map.victory[:]
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
						or	val[-1] not in 'MHDW'): raise
			except: error += ['BAD %s IN TIMING: ' % key + val]
		#	-------------------
		#	Validate power data
		#	-------------------
		for power in self.powers:
			#	------------------------------------------
			#	Set default player vote (solo for himself)
			#	------------------------------------------
			if not power.centers: power.vote = None
			elif power.vote is None and 'PROPOSE_DIAS' not in rules:
				power.vote = '1'
			#	--------------------
			#	Validate controllers
			#	--------------------
			for who in power.ceo:
				if (who != 'MASTER'
				and not ([1 for x in self.map.powers if x == who]
					or	 [1 for x in self.powers if x.name == who])):
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
			kind, goodOrders = None, []
			for order in power.adjust:
				word = order.split()
				if not kind:
					kind = word[0]
					if (kind == 'RETREAT') == (self.phaseType == 'A'):
						error += ['IMPROPER ORDER TYPE: ' + order]
						continue
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
				elif (not self.map.isValidUnit(unit) or len(word) > 3
				or unit[2:5] not in self.buildSites(power)):
					error += ['BAD BUILD FOR %s: ' % power.name + order]
	#	----------------------------------------------------------------------
	def validateRules(self):
		ruleData, rulesForced, rulesDenied = self.loadRules()
		rules, rulesAdded = self.rules[:], []
		while 1:
			addCopy, rulesAdded = rulesAdded[:], []
			for each in addCopy or rules:
				if each not in rules: continue
				if each not in ruleData:
					self.error += ['NO SUCH RULE: ' + each]
					continue
				if ruleData[each]['variant'] not in ('', self.status[0]):
					self.error += ['%sRULE %s REQUIRES %s VARIANT' %
						('MAP ' * (each in self.metaRules), each,
						ruleData[each]['variant'].upper())]
				for force in (ruleData[each].get('+', []) +
							  ruleData[each].get('=', [])):
					if (ruleData[force]['variant'] in ('', self.status[0])
					and force not in rules):
						rules.append(force)
						rulesAdded += [force]
						self.metaRules += [force]
				for deny in (ruleData[each].get('-', []) +
							 ruleData[each].get('!', [])):
					if deny in rules: rules.remove(deny)
			if not rulesAdded: break
		self.rules = [x for x in rules if x not in self.norules]
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
		self.mail = Mail(mailTo or host.dpjudge, subject,
			copy = copyFile and self.file(copyFile),
			mailAs = mailAs or self.master[1], header = 'Errors-To: ' +
				(self.master and self.master[1] or host.judgekeeper))
		if not mailAs:
			self.mail.write('SIGNON M%s %s\n' % (self.name, self.password), 0)
	#	----------------------------------------------------------------------
	def save(self, asBackup = 0):
		fileName = 'status'
		if asBackup: fileName += '.' + self.phaseAbbr()
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
	def fileResults(self, lines):
		file = open(self.file('results'), 'a')
		temp = ''.join(lines)
		file.write(temp.encode('latin-1'))
		del temp
		file.close()
		try: os.chmod(file.name, 0666)
		except: pass
		self.logAccess('TO', self.phase, 'ADVANCED')
	#	----------------------------------------------------------------------
	def fileSummary(self, reveal = 0):
		text, fileName = self.summary(reveal = reveal), self.file('summary')
		if 'NO_REVEAL' in self.rules and not reveal:
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
	def makePostScriptMap(self, viewer = 0, password = ''):
		import DPmap
		fileName = host.dpjudgeDir + '/maps/' + self.name + password
		for ext in ['.ps', '.pdf', '.gif', '_.gif', '_.pdf']:
			try: os.unlink(fileName + ext)
			except: pass
		DPmap.PostScriptMap(host.packageDir + '/maps/' + self.map.rootMap,
			self.file('results'),
			host.dpjudgeDir + '/maps/' + self.name + password + '.ps', viewer)
		os.chmod(fileName + '.ps', 0666)
	#	----------------------------------------------------------------------
	def makeGifMaps(self, password = ''):
		#	--------------------------------------------
		#	Make .gif files from the last page(s) of the
		#	.ps map for the game.  To do so, extract the
		#	target page using the psselect utility (from
		#	Andrew Duggan's "psutils" package), and mess
		#	with it until it is all converted to a .gif.
		#	--------------------------------------------
		root = host.dpjudgeDir + '/maps/' + self.name + password
		file = root + '.'
		upscale = host.imageResolution / 72.
		origin = size = None
		if self.map.bbox: 
			origin = [self.map.bbox[0] * upscale, self.map.bbox[1] * upscale]
			size = [(self.map.bbox[2] - self.map.bbox[0]) * upscale,
					(self.map.bbox[3] - self.map.bbox[1]) * upscale]
		if os.name == 'nt':
			inp = ('%sppm' % file, '< %sdat' % file,
				   '< %sdta' % file, '< %sdat' % file)
			outp = ('>%s;' % inp[1][1:], '>%s;' % inp[2][1:],
					'>%s;' % inp[1][1:])
		else: inp, outp = ('%sppm' % file, '2>/dev/null', '2>/dev/null', '2>/dev/null'), ('|', '|', '|')
		toolsDir = host.toolsDir
		chop = ('%s/psselect -p_%%d %sps %s %s'
				'%s/gs -q -r%d -dSAFER -sDEVICE=ppmraw -sOutputFile=%sppm %s;' %
				(toolsDir, file, inp[1] * (os.name != 'nt'), outp[0],
				toolsDir, host.imageResolution, file,
				(inp[1], '-')[os.name != 'nt']))
		#	----------------------------------------------------------
		#	All landscape maps must be rotated 270 degrees by pnmflip.
		#	----------------------------------------------------------
		make, idx = '', 0
		if self.map.rotation:
			make += '%s/pnmflip -r%d %s %s' % (toolsDir,
				self.map.rotation * 90, inp[idx], outp[idx])
			idx += 1
		if origin:
			make += '%s/pnmcut %d %d %d %d %s %s' % (toolsDir,
				origin[0], origin[1], size[0], size[1], inp[idx], outp[idx])
			idx += 1
		make += '%s/pnmcrop -white %s %s' % (toolsDir, inp[idx], outp[idx])
		idx += 1
		make +=	'%s/ppmtogif -interlace %s > %%s' % (toolsDir, inp[idx])
		for page in (1, 2):
			if page == 2 and self.phase == self.map.phase: break
			gif = root + '_'[page & 1:] + '.gif'
			try: os.unlink(gif)
			except: pass
			map(os.system, (chop % page + make % gif).split(';'))
			#	------------------------------------------------------------
			#	If the gif make fails, the file will be 0 bytes.  Remove it.
			#	------------------------------------------------------------
			if os.path.getsize(gif): os.chmod(gif, 0666)
			else: os.unlink(gif)
		try: map(os.unlink, (file + 'ppm', file + 'dat', file + 'dta'))
		except: pass
	#	----------------------------------------------------------------------
	def makePdfMaps(self, password = ''):
		#	---------------------------------------------------------
		#	Make a .pdf file with the final page(s) from the .ps file
		#	---------------------------------------------------------
		fileName, params = host.dpjudgeDir + '/maps/' + self.name + password, []
		outfileName = fileName + '.pdf'
		if self.map.papersize: params = ['-sPAPERSIZE=' + self.map.papersize]
		#	----------------------------------------
		#	Add more parameters before this comment.
		#	----------------------------------------
		if os.name == 'nt': params = ['"%s"' % x for x in params]
		params = ' '.join(params) + ' %s.ps ' % fileName + outfileName
		#	-----------------------------------------------------------------
		#	(We could run psselect -_2-_1 xx.ps 2>/dev/null > tmp.ps and then
		#	run the ps2pdf on the tmp.ps file, but we now pdf the full game.)
		#	-----------------------------------------------------------------
		os.system(host.toolsDir + '/ps2pdf ' + params)
		try:
			os.chmod(outfileName, 0666)
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
	def isValidPassword(self, power, pwd):
		if not power: return
		pwd = pwd.upper()
		#	---------------------------------------
		#	Find proper power to check his password
		#	---------------------------------------
		if type(power) in (str, unicode):
			try: power = [x for x in self.powers if x.name == power][0]
			except: return
		#	-------------------------------------------------------------------
		#	If power is run by controller, password is in the controller's data
		#	-------------------------------------------------------------------
		if not power.ceo: player = power
		else: player = [x for x in self.powers if x.name == power.ceo[0]][0]
		#	---------------------------
		#	Determine password validity
		#	---------------------------
		if (player.password and pwd == player.password.upper()
		or pwd == self.password.upper()): return 1
		#	----------------------------------------
		#	Check against omniscient power passwords
		#	----------------------------------------
		if [1 for x in self.powers if x.omniscient and player.name != 'MASTER'
			and x.password and pwd == x.password.upper()]: return 2
	#	----------------------------------------------------------------------
	def makeMaps(self):
		#	--------------------------------------------------------
		#	If the map is marked as text only, make no graphical map
		#	--------------------------------------------------------
		if self.map.textOnly: return
		#	----------------------------------------------------------
		#	Get a list of all the different powers for whom we need to
		#	make maps.  In a BLIND game, the powers see separate maps.
		#	----------------------------------------------------------
		if 'BLIND' in self.rules: maps = [(x, '.' + y + `hash(z)`)
			for x, y, z in [('MASTER', 'M', self.password)] +
			[(x.name, x.abbrev or 'O', (x.password or self.password) + x.name)
			for x in self.powers if (not x.type or x.omniscient)]]
		else: maps = [(None, '')]
		for viewer, pwd in maps:
			#	-------------------------------------------------
			#	Make a complete "season-by-season" PostScript map
			#	(putting the file into the maps subdirectory)
			#	-------------------------------------------------
			self.makePostScriptMap(viewer, pwd)
			#	--------------------------------------
			#	Make .gif files from the last pages of
			#	the PostScript map that was just made.
			#	--------------------------------------
			self.makeGifMaps(pwd)
			#	-------------
			#	Make .pdf map
			#	-------------
			self.makePdfMaps(pwd)
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
		try: homes = orig = self.map.home[power.name]
		except:
			error = 'DATA FOR NON-POWER: %s' % power.name
			if error not in self.error: self.error += [error]
			return
		if 'SC?' in power.centers or 'SC!' in power.centers: return homes
		if ('BUILD_ANY' in self.rules or 'REMOTE_BUILDS' in self.rules
		or '&SC' in homes): homes = power.centers
		if 'HOME_BUILDS' in self.rules:
			homes = [x for y,z in self.map.home.items() for x in z]
		if 'REMOTE_BUILDS' in self.rules:
			if not [1 for x in orig if x in power.centers]: return []
		revert = [y for x in self.powers for y in self.map.home.get(x.name, [])
			if 'SC?' in x.centers or 'SC!' in x.centers]
		return ([x for x in homes if x in power.centers and x not in
			[y[2:5] for z in self.powers for y in z.units] + revert] +
			[x for x in (self.map.factory.get(power.name, []) *
				('NO_FACTORIES' not in self.rules) +
			self.map.partisan.get(power.name, []) * ('SC*' in power.centers))
			if x[:3] not in [z[2:5] for y in self.powers for z in y.units]])
	#	----------------------------------------------------------------------
	def sortPowers(self):
		self.powers.sort(Power.compare)
	#	----------------------------------------------------------------------
	def begin(self, move1st = 0):
		self.phase = self.map.phase
		count = self.phase.endswith(' ADJUSTMENTS')
		if (('MOBILIZE' in self.rules or 'BLANK_BOARD' in self.rules)
		and (move1st or not count)):
			now, seq = self.phase.split(), self.map.seq[:]
			yr, when = int(now[1]), now[0] + ' ' + now[2]
			if not [x for x in seq if x[:7] == 'NEWYEAR']: seq += ['NEWYEAR']
			for item in reversed(seq + seq[:seq.index(when)]):
				count += item.endswith(' ADJUSTMENTS')
				if count and (not move1st or item.endswith(' MOVEMENT')): break
				if item[:7] == 'NEWYEAR': yr -= int(item[8:] or '0') or 1
			self.phase = item.replace(' ', ' %d ' % yr)
		self.avail, avail = [], self.map.powers[:]
		map(avail.remove, self.map.dummies)
		self.win = self.map.victory[0]
		self.setDeadline(firstPhase = 1)
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
		for starter in [x for x in self.map.dummies
			if x not in [y.name for y in self.powers]]:
			self.powers.append(self.powerType(self, starter))
			self.powers[-1].player = ['DUMMY']
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
		self.start = time.strftime('%d %B %Y', time.localtime())
		if self.start[0] == '0': self.start = self.start[1:]
		self.changeStatus('active')
		#	---------------------------------------------
		#	Generate and broadcast initial unit positions
		#	and make the initial PostScript and gif map.
		#	---------------------------------------------
		lines = self.mapperHeader() + ['Starting position for ' +
			self.phaseName()] + self.list() + [
			'\nThe deadline for the first orders is %s.\n' % self.timeFormat()]
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
			timing += ' ' + key.title() + ' ' + val
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
		win = self.map.victory
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
							self.visible(power, unit, 'H').items() if y & 8]
						if playing and playing.name not in shows: continue
					if not spaced: lines += ['']
					spaced = 1
					if 'BLIND' in self.rules and not playing:
						lines += ['SHOW ' + ' '.join(shows)]
					lines += [powerName + self.anglify(unit) +
						(option and (' can retreat to ' +
						' or '.join(map(self.anglify, option))) or '') + '.']
				if 'BLIND' in self.rules and not playing: lines += ['SHOW']
		if 'active' in self.status or 'waiting' in self.status: lines += (
			self.ownership(playing = (None, playing)['BLIND' in self.rules]))
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
		if (playing and playing.name in self.map.powers
		and (playing.units or playing.retreats or playing.centers)):
			lines += [self.powerOrders(playing)]
		self.mail.write('\n'.join(self.mapperHeader()) + '\n\n')
		self.mail.write('\n'.join(lines) + '\n')
		self.mail.close()
	#	----------------------------------------------------------------------
	def ownership(self, unowned = None, playing = None):
		self.includeOwnership = None
		rules = self.rules
		if unowned is None:
			homes = [x for y in self.map.home.values() for x in y]
			unowned = [x for x in self.map.scs if x not in homes]
		if self.phase != self.map.phase:
			for power in self.powers:
				if power.type: continue
				power.centers = [x for x in power.centers
								if x not in ('SC?', 'SC*')]
				homes = self.map.home[power.name]
				if ('GARRISON' in rules and not power.centers
				and not power.type and (power.ceo
				or power.player and not power.isResigned())
				and not [0 for x in self.powers for y in x.units
					if x is not power and y[2:5] in homes]):
						power.centers = ['SC?'] * (len(power.units) + 1)
				if 'NO_PARTISANS' not in self.rules:
					held = len([x for x in homes if x not in power.centers])
					if 0 < held < len(homes): power.centers += (['SC*'] *
						len(self.map.partisan.get(power.name, [])))
		lines = ['']
		if 'VASSAL_DUMMIES' in rules:
			lines += ['Vassal status of minor powers:', '']
			lines += ['%s is a vassal of %s.' %
				(self.anglify(x.name), self.anglify(x.ceo[0]))
				for x in self.powers if x.ceo]
			lines += [self.anglify(x.name) + ' is independent.'
				for x in self.powers if x.isDummy() and not x.ceo]
		blind = ('BLIND' in rules and not playing
				 and 'SEE_ALL_SCS' not in rules) 
		lines += ['\nOwnership of supply centers:\n']
		for power in self.powers + ['UNOWNED']:
			if playing and playing.name not in ('MASTER', power.name):
				continue
			if power != 'UNOWNED':
				powerName, centers = power.name, power.centers
				[unowned.remove(x) for x in centers if x in unowned]
			else: powerName, centers = power, unowned
			powerName = self.anglify(powerName) + ':'
			ceo = getattr(power, 'ceo', [])[:1]
			for who in self.powers + ['UNOWNED']:
				seen = 0
				if who is power:
					seen = [(x, 'Undetermined Home SC')[x == 'SC!']
						for x in centers if x[-1] not in '?*']
				elif (blind and who != 'UNOWNED'
				and not who.omniscient and [who.name] != ceo):
					who.sees += [x for x in centers
						if x not in who.sees and self.visible(power, x)[who.name] & 2]
					seen = [x for x in centers if x in who.sees]
				if not seen: continue
				if blind:
					if who is power: lines += ['SHOW MASTER ' +
						' '.join([x.name for x in self.powers
						if x is power or x.omniscient or [x.name] == ceo])]
					else: lines += ['SHOW ' + who.name]
				lines += [y.replace('\0377', '-') for y in textwrap.wrap(
					('%-11s %s.' % (powerName,
					', '.join(map(self.anglify, sorted(seen)))))
					.replace('-', '\0377'), 75, subsequent_indent = ' ' * 12)]
		if blind: lines += ['SHOW']
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
		#	--------------------------------------------------
		#	Add a mail-like header then file into results file
		#	--------------------------------------------------
		body[:0] = ['From %s %s\nSubject: %s\n\n' %
			(host.dpjudge, time.ctime(), subject)]
		self.fileResults(body)
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
		who = self.powers + ['MASTER', 'ALL']
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
					if self.validOrder(sendingPower, y, 'S ' + x, 0)
					or self.validOrder(power, x, 'S ' + y, 0)]):
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
				if power.type == 'MONITOR': continue
				if power.address:
					if (power.isResigned() or power.isDummy()
					or	sendingPower.ceo
					and sendingPower.ceo[0] == power.name): continue
				elif power.ceo:
					if power.ceo[0] in ('MASTER', sendingPower.name): continue
				elif 'HIDE_DUMMIES' not in self.rules: continue
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
		#					will be ['All'] for a broadcast or ['All!']
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
		#	-----------------------
		#	See who is listening in
		#	-----------------------
		omniscient, sentTo = ['MASTER'][:'EAVESDROP' in self.rules
									or 'EAVESDROP!' in self.rules], []
		omniscient += [x.name for x in self.powers if x.omniscient == 2]
		if private: omniscient = []
		#	----------------------------------------
		#	Now send the message to each destination
		#	----------------------------------------
		for reader in self.powers + ['MASTER'] + ['JUDGEKEEPER']:
			#	----------------------------------
			#	Get the recipient's e-mail address
			#	----------------------------------
			if reader == 'MASTER':
				if (sender and sender.name != reader and readers == ['All']
				and 'PRESS_MASTER' in self.rules): continue
				power, email = reader, self.master[1]
			elif reader == 'JUDGEKEEPER':
				if readers in (['All'], ['All!']): continue
				power, email = reader, host.judgekeeper
			else:
				if reader.type == 'MONITOR' and readers != ['All!']: continue
				power = reader.name
				if reader.address: email = reader.address[0]
				else:
					try: email = [x.address[0] for x in self.powers
						if x.name == reader.ceo[0]][0]
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
								  claimFrom, claimTo, subject = subject)
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
		if 'suspect' in self.status and host.judgekeeper not in sentTo:
			self.deliverPress(sender, 'MASTER', host.judgekeeper,
				readers, message, claimFrom, claimTo, subject = subject)
	#	---------------------------------------------------------------------
	def pressHeader(self, power, whoTo, reader, sender = 0):
		text = ('Message', 'Broadcast message')[whoTo == ['All']]
		if sender:
			if sender != '(ANON)': text += ' from ' + self.anglify(sender)
			if reader == 'MASTER' and sender != power.name:
				text += ' [%s %s]' % (('by', 'from')[sender == '(ANON)'],
					self.anglify(power.name))
		else: text += ' sent'
		return text + self.listReaders(whoTo)
	#	----------------------------------------------------------------------
	def listReaders(self, who):
		if who == ['All']: return ''
		who = map(self.anglify, who)
		if len(who) > 1: who[-1] = 'and ' + who[-1]
		return ' to ' + ', '[len(who) < 3:].join(who)
	#	----------------------------------------------------------------------
	def deliverPress(self, sender, reader, email, recipient, message,
					 claimFrom, claimTo, subject = None):
		#	------------------------------------------------------
		#	If email is not None, the press is going to a specific
		#	private e-mail address, so it will look like it came
		#	from the host.dpjudge address.
		#	------------------------------------------------------
		if email: mailAs = host.dpjudge
		elif sender.name == 'MASTER': mailAs = self.master[1]
		else: mailAs = sender.address[0].split(',')[0]
		#	--------------
		#	Begin the mail
		#	--------------
		if subject: topic = subject
		elif reader == sender.name:
			if recipient == ['All']: topic = 'Diplomacy broadcast sent'
			else: topic = 'Diplomacy press sent' + self.listReaders(recipient)
		elif claimFrom == '(ANON)': topic = 'Diplomacy press'
		else: topic = 'Diplomacy press from ' + self.anglify(claimFrom)
		self.openMail(topic, mailTo = email, mailAs = mailAs)
		mail = self.mail
		if not subject and email:
			#	---------------------------------------
			#	The message is being sent directly to a
			#	player e-mail.  So format it ourselves.
			#	---------------------------------------
			if reader == sender.name: mail.write(
				self.pressHeader(sender, recipient, reader) + ':\n\n')
			mail.write('%s in %s:\n\n' %
				(self.pressHeader(sender, claimTo, reader, claimFrom),
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
		if not subject:
			if not email: mail.write('ENDPRESS\nSIGNOFF\n')
			elif reader == sender.name: mail.write('\nEnd of message.\n')
		mail.close()
	#	----------------------------------------------------------------------
	#							ADJUDICATION METHODS
	#	----------------------------------------------------------------------
	def ready(self, process = 0):
		return process == 2 or ((self.deadline and self.deadline <= self.Time())
		or process or not ([1 for power in self.powers if power.wait]
		or 'ALWAYS_WAIT' in self.rules)) and not self.latePowers()
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
	def latePowers(self):
		lateList = []
		#	----------------------------------------------------
		#	Determine if any power's retreats would be fruitless
		#	----------------------------------------------------
		self.findGoners()
		#	------------------------------
		#	See who is late and who is not
		#	------------------------------
		for power in [x for x in self.powers if not x.type]:
			cd = power.isCD()
			if self.phaseType == 'A':
				if power.adjust: continue
				units, centers = len(power.units), len(power.centers)
				if [x for x in power.centers if x in self.map.home[power.name]]:
					centers += (self.map.reserves.count(power.name) +
						min(self.map.militia.count(power.name),
						len([0 for x in power.units
							if x[2:5] in self.map.home[power.name]])))
				if (cd or centers == 0 or units == centers
				or (units < centers and not self.buildSites(power))): continue
			elif self.phaseType == 'R':
				if power.adjust or not power.retreats: continue
				#	-----------------------------------------------------
				#	Disband all units with no future and no bounce-effect
				#	-----------------------------------------------------
				if cd or power.goner:
					if 'CD_RETREATS' not in self.rules or power.goner:
						power.adjust = ['RETREAT %s DISBAND' % x
							for x in power.retreats]
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
	def process(self, now = 0, email = None):
		if (now > 1 or self.ready(now) or self.preview
		or	self.graceExpired() and 'CIVIL_DISORDER' in self.rules):
			if not now:
				if self.deadline and 'REAL_TIME' not in self.rules:
					#	-------------------------------------------
					#	If this game has a deadline, the cron job
					#	will find it next time around.  Mark that
					#	it should delay one cycle before processing
					#	(if the deadline hasn't passed yet).
					#	-------------------------------------------
					self.delay = self.deadline > self.Time()
					return self.save()
				#	-----------------------------------------
				#	No deadline.  Process right away.
				#	Lock the game status file against changes
				#	and mail OURSELF to ask for processing.
				#	-----------------------------------------
				self.save(asBackup = 1)
				self.openMail('Process phase', mailTo = host.dpjudge)
				self.mail.write('PROCESS\nSIGNOFF\n')
				self.mail.close()
				self.mail = self.skip = None
				return
			#	---------------------------------------------
			#	We have received a PROCESS command via e-mail
			#	---------------------------------------------
			if self.deadline and not self.preview: self.save(asBackup = 1)
			self.delay = None
			if self.phaseType == 'M':
				self.determineOrders()
				self.addCoasts()
				if not self.preview and not self.preMoveUpdate(): return
			for power in self.powers: power.wait = None
			self.resolve(email = email)
		#	-------------------------------------------------
		#	Game not ready.  If we received a PROCESS command
		#	let the caller know we won't be honoring it.
		#	-------------------------------------------------
		elif now: return 'Game not ready for processing'
		#	---------------------------
		#	Update the game status file
		#	---------------------------
		if not self.preview: self.save()
	#	---------------------------------------------------------------------
	def rollback(self, phase, includePersistent = 0, includeOrders = 0):
		if self.status[1] != 'active': raise RollbackGameInactive
		lines = []
		if os.path.isfile(self.file('status.' + phase)):
			file = open(self.file('results'), 'r', 'latin-1')
			lines, start = file.readlines(), 0
			file.close()
			for num, text in enumerate(lines):
				if '%s ' % self.name + phase in text: break
				start |= 'Diplomacy results' in text
		else: raise RollbackPhaseInvalid
		file = open(self.file('results'), 'w')
		temp = lines[:num - 1]
		file.write(''.join(temp).encode('latin-1'))
		file.close()
		if start:
			[os.unlink(host.dpjudgeDir + '/maps/' + x)
				for x in os.listdir(host.dpjudgeDir + '/maps')
				if x.startswith(self.name.encode('latin-1'))
				and x.endswith('_.gif')]
			self.phase = self.map.phase
		self.makeMaps()
		# Load the phase.
		self.load('status.' + phase, includePersistent, includeOrders)
		self.changeStatus('active')
		try: os.unlink(self.file('summary'))
		except: pass
		self.setDeadline()
		os.rename(self.file('status'), self.file('status.rollback'))
		self.save()
		self.mailPress(None, ['All!'],
			"Diplomacy game '%s' has been rolled back to %s\n"
			'and all orders have been cleared.\n\n'
			'The new deadline is %s.\n' %
			(self.name, self.phaseName(form = 2), self.timeFormat()),
			subject = 'Diplomacy rollback notice')
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
	def checkDisruptions(self, mayConvoy, result):
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
			or 'DUMMY_FIRE' in self.rules and self.unitOwner(unit).isDummy)
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
			word = order.split()
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
				if 'SHOW_PHANTOM' in self.rules: self.result[unit] += ['void']
				else: self.command[unit] = 'H'
				continue
			word[1:where + 1] = guy.split()
			self.command[unit] = ' '.join(word)
			#	---------------------------------------------------
			#	See if the unit's order matches the supported order
			#	---------------------------------------------------
			coord = self.command[guy].split()
			if ((len(word) < 5 and coord[0] == '-')
			or (len(word) > 4 and (coord[0], coord[-1]) != ('-', word[4]))
			or 'no convoy' in self.result[guy]): self.result[unit] += ['void']
			else:
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
			self.checkDisruptions(mayConvoy, 'no convoy')
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
				self.result[loser] += ['dislodged']
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
				word = 'Builds'[:6 - (tokens[num + 1][0] == 'W')]
			elif word in ('C', 'S'):
				word = ('SUPPORT', 'CONVOY')[word == 'C']
				if 'SHOW_PHANTOM' not in self.rules:
					help = self.unitOwner(' '.join(tokens[num + 1:num + 3]))
					if help not in (None, power):
						word += ' ' + self.anglify(self.map.ownWord[help.name])
			else:
				try: word = {'REMOVE': 'Removes', 'WAIVED': 'waived',
							'-': '->', 'H': 'HOLD'}[word]
				except:
					for loc in [x.strip('_')
						for x,y in self.map.locName.items() +
						self.map.powName.items()
						if y.strip('_') == word.strip('_')]:
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
						if word in (['MASTER', 'UNOWNED'] +
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
	def advancePhase(self):
		self.phase = self.findNextPhase()
		self.phaseType = self.phase.split()[-1][0]
		return self.checkPhase()
	#	----------------------------------------------------------------------
	def morphMap(self, lastPhase = 0):
		text, map = [], self.map
		shut = [x for y in self.powers for x in y.units
			if not map.isValidUnit(x)]
		self.loadMap(map.name, lastPhase = lastPhase)
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
	def findNextPhase(self, phaseType = None, skip = 0):
		now = self.phase.split()
		if len(now) < 3: return self.phase
		year = int(now[1])
		which = ((self.map.seq.index(now[0] + ' ' + now[2]) + 1) %
			len(self.map.seq))
		while 1:
			year += (which == 0
				and 'NEWYEAR' not in [x.split()[0] for x in self.map.seq])
			new = self.map.seq[which].split()
			if new[0] == 'IFYEARDIV':
				if '=' in new[1]: div, mod = map(int, new[1].split('='))
				else: div, mod = int(new[1]), 0
				if year % div != mod: which = -1
			elif new[0] == 'NEWYEAR': year += len(new) == 1 or int(new[1])
			elif phaseType in (None, new[1][0]):
				if skip == 0: break
				skip -= 1
			which += 1
			which %= len(self.map.seq)
		return ' '.join([new[0], `year`, new[1]])
	#	----------------------------------------------------------------------
	def checkPhase(self):
		if self.phase in (None, 'FORMING', 'COMPLETED'): return []
		if self.phaseType == 'M': return ((self.includeOwnership or
				('BLIND' in self.rules) > ('NO_UNITS_SEE' in self.rules)
				+ ('SEE_NO_SCS' in self.rules) + ('SEE_ALL_SCS' in self.rules))
			and self.ownership() or [])
		if self.phaseType == 'R':
			if [1 for x in self.powers if x.retreats]: return []
			for power in self.powers: power.retreats, power.adjust = {}, []
			return self.advancePhase()
		if self.phaseType == 'A':
			text = self.captureCenters()
			if self.phase == 'COMPLETED': return text
			if self.phase.split()[1] in self.map.homeYears:
				for power in [x for x in self.powers if not x.type]:
					self.map.home[power.name] = power.home = power.centers
			for power in self.powers:
				units, centers = len(power.units), len(power.centers)
				if [x for x in power.centers if x in self.map.home[power.name]]:
					centers += (self.map.reserves.count(power.name) +
						min(self.map.militia.count(power.name),
						len([0 for x in power.units
							if x[2:5] in self.map.home[power.name]])))
				if (units > centers
				or (units < centers and self.buildSites(power))): return text
			for power in self.powers:
				while 'SC?' in power.centers: power.centers.remove('SC?')
				while 'SC*' in power.centers: power.centers.remove('SC*')
			return text + self.advancePhase()
		#	--------------------------------------
		#	Other phases.  For now take no action.
		#	--------------------------------------
		self.await = 1
		return ['The game is waiting for processing of the %s phase.\n' %
			self.phase.title()]
	#	----------------------------------------------------------------------
	def captureCenters(self, func = None):
		#	-----------------------------------------
		#	If no power owns centers, initialize them
		#	-----------------------------------------
		if not [1 for x in self.powers if x.centers]:
			for power in self.powers:
				power.centers = self.map.home.get(power.name, [])
		#	-------------------------------------------------------
		#	Remember the current center count for the various
		#	powers, for use in the victory condition check, then
		#	go through and see if any centers have been taken over.
		#	Reset the centers seen by each power.
		#	-------------------------------------------------------
		lastYear, unowned = {}, self.map.scs
		for power in self.powers:
			lastYear[power] = sum(map(len, [x.centers for x in self.powers
				if 'VASSAL_DUMMIES' in self.rules and x.ceo == [power.name]]),
				len(power.centers))
			[unowned.remove(x) for x in power.centers if x in unowned]
			power.sees = []
		for power in self.powers + [None]:
			if power: centers = power.centers
			else: centers = unowned
			for center in centers[:]:
				for owner in self.powers:
					if (owner is not power
					and center in [x[2:5] for x in owner.units]):
						self.transferCenter(power, owner, center)
						if not power: unowned.remove(center)
						break
		#	-----------------------------------
		#	Determine any vassal state statuses
		#	and the list of who owns what.
		#	-----------------------------------
		list = self.vassalship() + self.ownership(unowned)
		#	----------------------------------------------------------------
		#	See if we have a win.  Criteria are the ARMADA Regatta victory
		#	criteria (adapted from David Norman's "variable length" system).
		#	----------------------------------------------------------------
		victor, thisYear = None, [sum(map(len, [y.centers for y in self.powers
			if 'VASSAL_DUMMIES' in self.rules and y.ceo == [x.name]]),
			len(x.centers)) for x in self.powers]
		for power in self.powers:
			centers = sum(map(len, [x.centers for x in self.powers
				if 'VASSAL_DUMMIES' in self.rules and x.ceo == [power.name]]),
				len([x for x in power.centers if x != 'SC*']))
			#	FIRST, YOU MUST HAVE ENOUGH CENTERS TO WIN
			if	(centers >= self.win
			#	AND YOU MUST GROW (OR, IF "HOLD_WIN," MUST HAVE HAD A WIN)
			and (centers > lastYear[power], lastYear[power] >= self.win)
				['HOLD_WIN' in self.rules]
			#	AND YOU MUST BE ALONE IN THE LEAD
			and (centers, thisYear.count(centers)) == (max(thisYear), 1)):
				if not self.preview: self.finish([power.name])
				victor, func = power, None
		return list + self.powerSizes(victor, func)
	#	----------------------------------------------------------------------
	def vassalship(self):
		if 'VASSAL_DUMMIES' not in self.rules: return []
		#	------------------------------------------------------
		#	Determine vassal states (DUMMY powers whose homes are
		#	all controlled by a single great power or its vassals)
		#	------------------------------------------------------
		more, list, repeat = 0, [], 1
		while repeat:
			was, run, repeat = {}, {}, 0
			for power in [x for x in self.powers if x.isDummy()]:
				was[power], run[power] = power.ceo[:], []
				for home in self.map.home.get(power.name, []):
					owner = [y for y in self.powers if home in y.centers][0]
					run[power] += (owner.ceo + [owner.name])[:1]
			for power, runners in run.items():
				if (runners and runners[0] != power.name
				and runners == runners[:1] * len(runners)):
					del run[power]
					ceo = [x for x in self.powers if x.name == runners[0]]
					power.ceo = runners[:not ceo[0].isDummy()]
					if was[power] or not power.ceo: continue
					for guy in [x for x in run if power.name in run[x]]:
						run[guy], repeat = [(z, power.ceo[0])[z == power.name]
							for z in run[guy]], 1
		#	---------------------------------------------------------
		#	Determine torn allegiance destructions (vassal units on
		#	SC's now controlled by a different great power than they)
		#	---------------------------------------------------------
		while not repeat:
			repeat = 1
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
						else: repeat, other[0].ceo, more = 0, power.ceo, 1
		#	-----------------------------------------
		#	Return supply centers to and from vassals
		#	-----------------------------------------
		for power in [x for x in self.powers if x.isDummy()]:
			#	----------------------------------------
			#	Give the DUMMY powers back their centers
			#	----------------------------------------
			for home in self.map.home.get(power.name, []):
				owner = [y for y in self.powers if home in y.centers][0]
				self.transferCenter(owner, power, home)
			#	-----------------------------------------------------------
			#	Give the great powers back their centers from their vassals
			#	-----------------------------------------------------------
			if power.ceo:
				ceo = [y for y in self.powers if y.name == power.ceo[0]][0]
				[self.transferCenter(power, ceo, y)
					for y in power.centers if y in self.map.home[ceo.name]]
		if more: list += self.vassalship()
		return list
	#	----------------------------------------------------------------------
	def powerSizes(self, victor, func = None):
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
			if [x for x in power.centers if x in self.map.home[power.name]]:
				needs += (self.map.reserves.count(power.name) +
					min(self.map.militia.count(power.name),
					len([0 for x in power.units
						if x[2:5] in self.map.home[power.name]])))
			text = ('%-11s %2d Supply center%.2s %2d Unit%.2s  %s %2d unit%s.' %
				(self.anglify(power.name) + ':', owned, 's, '[owned == 1:],
				units, 's: '[units == 1:],
				('Builds ', 'Removes')[needs < units],
				abs(needs - units), 's'[abs(needs - units) == 1:]))
			#	------------------------------------------------------------
			#	Modify (if necessary) what we believe will be the next phase
			#	------------------------------------------------------------
			if power is victor: text += '  (* VICTORY!! *)'
			if self.phase == 'COMPLETED' or self.phaseType == 'A':
				if 'BLIND' in self.rules:
					if power is victor: list += ['SHOW ' +
						' '.join([x.name for x in self.powers
						if not (x.units or x.centers or x.omniscient)]),
						'\nOwnership of supply centers:\n', 'SHOW']
					else: list += ['SHOW MASTER ' + ' '.join([x.name
						for x in self.powers if x is power or x.omniscient])]
				list += [text]
			if func and self.phaseType != 'A': func(power, text.upper().split())
		return list + ['SHOW' * ('BLIND' in self.rules)]
	#	----------------------------------------------------------------------
	def phaseAbbr(self, phase = None):
		#	------------------------------------------
		#	Returns S1901M from "SPRING 1901 MOVEMENT"
		#	------------------------------------------
		phase = phase or self.phase
		try: return '%.1s%s%.1s' % tuple(phase.split()[:3])
		except: return '?????'
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
		word, season = phase.title().split(), ''
		for ch in word[0]:
			season += season and season[-1] == '.' and ch.upper() or ch
		return (season + ' ' +
			'of ' * (season in ('Spring', 'Fall', 'Winter', 'Summer', 'Autumn')
			and form != 2) + word[1] + (form != 2 and '.' or ' ' + word[2]) +
			'  (%s.%s)' % (self.name, self.phaseAbbr(phase)) * (not form))
	#	----------------------------------------------------------------------
	def visible(self, power, unit, order = None):
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
		if 'command' not in vars(self): self.command = {}
		shows, order = {'MASTER': 15}, order or self.command.get(unit, 'H')
		old = new = unit.split()[-1][:3]
		if order[0] == '-' and (self.phaseType != 'M'
		or not self.result.get(unit)): new = order.split()[-1][:3]
		rules = self.rules
		for seer in self.powers:
			shows[seer.name] = 15 * bool(power is seer or seer.omniscient
				or [seer.name] == getattr(power, 'ceo', [])[:1])
			if (shows[seer.name]
			or ('SEE_NO_SCS', 'SEE_NO_UNITS')[' ' in unit] in rules): continue
			#	--------------------------------------------------
			#	Get the list of the "seer"s sighted units (if any)
			#	with their positions before and after any movement
			#	--------------------------------------------------
			if 'NO_UNITS_SEE' in rules: before = after = []
			else:
				before = after = [x[2:]
					for x in seer.units + seer.retreats.keys()
					if ' ' not in unit
					or unit[0] != x[0] and 'UNITS_SEE_OTHER' in rules
					or unit[0] == x[0] and 'UNITS_SEE_SAME' in rules]
				if self.phaseType == 'M':
					after = []
					for his in seer.units:
						if (' ' in unit
						and ('UNITS_SEE_SAME' in rules and his[0] != unit[0]
						or	'UNITS_SEE_OTHER' in rules and his[0] == unit[0])):
							continue
						if (self.command.get(his, 'H')[0] != '-'
						or self.result.get(his)): after += [his[2:]]
						else: after += [self.command[his].split()[-1]]
			#	------------------------------------------------
			#	Get the list of the "seer"s sighted scs (if any)
			#	------------------------------------------------
			if 'NO_SCS_SEE' in rules: scs = []
			elif ('OWN_SCS_SEE' in rules
			or self.map.homeYears and not [x for x in self.powers if x.home]):
				#	------------------------------------
				#	The seer's owned centers are sighted
				#	------------------------------------
				scs = seer.centers[:]
				if 'SC!' in scs:
					scs = [x[8:11] for x in seer.adjust if x[:5] == 'BUILD']
			else:
				#	-----------------------------------
				#	The seer's home centers are sighted
				#	-----------------------------------
				scs = self.map.home.get(seer.name, [])[:]
				#	----------------------------------------------------------
				#	Also add locations where the power had units at game start
				#	(helping void variant games, where units start on non-SCs)
				#	----------------------------------------------------------
				if 'BLANK_BOARD' not in rules and 'MOBILIZE' not in rules:
					scs += [x[2:] for x in self.map.units.get(seer.name, [])]
			#	-------------------------------------------------------
			#	Set the bitmap for this "seer" if any unit or sc in the
			#	lists (before, after, scs) can see the site in question
			#	-------------------------------------------------------
			for his, place in [(x[:3], y) for x in before + after + scs
				for y in (old, new) if x == y or self.abuts('?', y, 'S', x)]:
				bit = (his in before and 1) | (his in after and 2) or 3
				if place == new: bit = bit * (place == old) | bit << 2
				shows[seer.name] |= bit
		return shows
	#	----------------------------------------------------------------------
	def showLines(self, power, unit, notes):
		if self.phaseType != 'M': unit, word = ' '.join(unit[1:3]), unit
		list, lost, found, gone, came, all = [], [], [], [], [], []
		if self.phaseType == 'M':
			if self.command.get(unit, 'H')[0] != '-' or self.result[unit]:
				there = unit
			else: there = unit[:2] + self.command[unit].split()[-1]
			cmd = None
		elif len(word) > 4 and word[2] not in notes:
			cmd, there = ' '.join(word[3:]), unit[:2] + word[-1]
			power.units += [unit]
			for who in (self.powers, [])['NO_UNITS_SEE' in self.rules]:
				if who is power: continue
				for what in who.units + who.adjust:
					if ('UNITS_SEE_OTHER' in self.rules and what[0] == unit[0]
					or	'UNITS_SEE_SAME' in self.rules and what[0] != unit[0]):
						continue
					if what in who.adjust:
						parse = what.split()
						if parse[2] in notes or parse[3] != '-': continue
						what, it = parse[1], parse[-1]
					else: it = what[2:]
					if (self.abuts('?', word[-1], 'S', it)
					and not self.visible(who, what, 'H').get(power.name, 0)):
						list += ['SHOW ' + power.name,
							'%-11s %s FOUND.' % (self.anglify(who.name) + ':',
							self.anglify(what[0] + ' ' + it))]
			power.units.remove(unit)
		elif unit == 'WAIVED': return ['SHOW ' + power.name]
		else: cmd, there = 'H', unit
		for who, how in self.visible(power, unit, cmd).items():
			if how & 8:
				if how & 1: all += [who]
				else: (found, came)[how & 4 > 0].append(who)
			elif how & 1: (lost, gone)[how & 2 > 0].append(who)
		if self.phaseType != 'M' and word[2] in notes: found = arrived = []
		for who, what in ((gone, ('LOST', 'DEPARTS')[self.phaseType == 'M']),
						  (lost, 'LOST'), (found, 'FOUND'), (came, 'ARRIVES')):
			if who:
				list += ['SHOW ' + ' '.join(who)]
				if self.phaseType == 'M': list += ['%s: %s %s.' %
					(self.anglify(power.name),
					self.anglify((unit, there)[what[0] in 'FA'], power), what) +
					'  (*dislodged*)' * ('dislodged' in notes)]
				else: list += ['%-11s %s %s.' % (self.anglify(power.name) + ':',
					self.anglify((unit, there)[what[0] != 'L'], power), what)]
		return list + ['SHOW ' + ' '.join(all)]
	#	----------------------------------------------------------------------
	def moveResults(self):
		self.resolveMoves()
		list = ['Movement results for ' + self.phaseName(), '']
		self.result[None], rules = 'invalid', self.rules
		for power in [x for x in self.powers if x.units]:
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
					#	-----------------------------------------------------
					#	If this is a BLIND game, add a line before the result
					#	text line specifying who should see result text.
					#	Also, show any partial results that should be seen.
					#	-----------------------------------------------------
					list += self.showLines(power, unit, notes)
				#	-------------------------------------------
				#	I know it's tempting to line up the orders,
				#	but David Norman's Mapper doesn't read the
				#	output right if it has more than a single
				#	space between the colon and the order.
				#	-------------------------------------------
				list += ['%s: %s.%s' % (self.anglify(power.name),
					self.anglify(unit + ' ' + self.command[unit], power),
					notes and '  (*%s*)' % ', '.join(notes) or '')]
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
		#	----------------------
		#	Determine any retreats
		#	----------------------
		for power in self.powers:
			for unit in filter(self.dislodged.has_key, power.units):
				attacker, site = self.dislodged[unit], unit[2:]
				if self.map.locAbut.get(site): pushee = site
				else: pushee = site.lower()
				for abut in self.map.locAbut[pushee]:
					abut = abut.upper()
					where = abut[:3]
					if ((self.abuts(unit[0], site, '-', abut)
					or	 self.abuts(unit[0], site, '-', where))
					and not self.combat.get(where) and where != attacker):
						power.retreats.setdefault(unit, [])
						#	----------------------------------------
						#	Armies cannot retreat to specific coasts
						#	----------------------------------------
						if unit[0] == 'F': power.retreats[unit] += [abut]
						elif where not in power.retreats[unit]:
							power.retreats[unit] += [where]
		#	--------------------------
		#	List all possible retreats
		#	--------------------------
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
						del self.dislodged[unit]
						try: del power.retreats[unit]
						except: pass
					elif toWhere: text += (' can retreat to %s.' %
						' or '.join(map(self.anglify, toWhere)))
					else:
						text += ' with no valid retreats was destroyed.'
						del self.dislodged[unit]
					#	-----------------------------------------------------
					#	If this is a BLIND game, add a line before the result
					#	text line specifying who should NOT see result text.
					#	-----------------------------------------------------
					if 'BLIND' in rules:
						show = [x for x,y in self.visible(power, unit, 'H').
							items() if y & 8 and x in self.map.powers]
						who += [x for x in show if x not in who]
						show.remove(power.name)
						if show: dis += ['SHOW ' + ' '.join(show), desc + '.']
						show = [x.name for x in self.powers if x.omniscient]
						who += [x for x in show if x not in who]
						dis += ['SHOW MASTER %s ' % power.name + ' '.join(show)]
					#	------------------------------------
					#	Make long lines wrap around politely
					#	------------------------------------
					dis += [y.replace('\0377', '-')
						for y in textwrap.wrap(text.replace('-', '\0377'), 75)]
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
		#	------------
		#	All finished
		#	------------
		if not self.preview: self.postMoveUpdate()
		return list
	#	----------------------------------------------------------------------
	def otherResults(self):
		conflicts, popped, owner, list = {}, [], 0, ['%s orders for ' %
			self.phase.split()[2][:-1].title() + self.phaseName(), '']
		for power in self.powers:
			#	---------------------------------------------------
			#	Supply CIVIL_DISORDER retreat and adjustment orders
			#	---------------------------------------------------
			if not power.adjust:
				if self.phaseType == 'A':
					diff = len(power.units) - len(power.centers)
					if [x for x in power.centers
						if x in self.map.home[power.name]]:
						diff -= (self.map.reserves.count(power.name) +
							min(self.map.militia.count(power.name),
							len([0 for x in power.units
								if x[2:5] in self.map.home[power.name]])))
					if diff > 0:
						pref = []
						for own, sc, home in (
							(0,0,0), (1,1,0), (1,1,1), (0,1,0), (0,1,1)):
							for kind in 'FA': pref.append(
								[x for x in power.units if x[0] == kind
								and (x[2:5] in self.map.scs) == sc
								and (x[2:5] in power.centers) == own])
						for unit in range(diff):
							pref = filter(None, pref)
							goner = random.choice(pref[0])
							pref[0].remove(goner)
							power.adjust += ['REMOVE ' + goner]
					elif diff:
						sites = self.buildSites(power)
						need = min(len(sites), -diff)
						power.adjust = ['BUILD WAIVED'] * need
						if 'CD_BUILDS' in self.rules:
							options = []
							for site in [x.upper() for x in self.map.locType]:
								if site[:3] in sites: options += filter(
									self.map.isValidUnit,
									('A ' + site, 'F ' + site))
							for build in range(need):
								if not options: break
								power.adjust[build] = ('BUILD ' +
									random.choice(options))
								options = [x for x in options
									if x[2:5] != power.adjust[build][8:11]]
				elif 'CD_RETREATS' in self.rules:
					taken = []
					for unit in power.retreats:
						sites = [x for x in power.retreats[unit]
							if x not in taken]
						for own, his in ((0,1), (0,0), (1,1), (1,0)):
							options = [x for x in sites
								if x[:3] in self.map.scs
								and (x[:3] in self.map.home[power.name]) == his
								and (x[:3] in power.centers) == own]
							if options: break
						else: options = sites
						if options:
							where = random.choice(options)
							taken.append(where)
							power.adjust += ['RETREAT %s - ' % unit + where]
						else: power.adjust += ['RETREAT %s DISBAND' % unit]
				else: power.adjust = [
					'RETREAT %s DISBAND' % x for x in power.retreats]
			#	-------------------------------------------------
			#	Determine multiple retreats to the same location.
			#	-------------------------------------------------
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
		#	When finished, "popped" will be a list of all
		#	retreaters who didn't make it.
		#	-------------------------------------------------
		for site, retreaters in conflicts.items():
			for weak in '~*':
				if len(retreaters) < 2: continue
				for retreater in retreaters[:]:
					if (retreater, site) in self.map.abutRules.get(weak, []):
						popped += [retreater]
						retreaters.remove(retreater)
			if len(retreaters) > 1: popped += retreaters
		#	----------------------------
		#	Add the orders to the output
		#	----------------------------
		for power in self.powers:
			for order in power.adjust or []:
				word = order.split()
				if 'BLIND' in self.rules:
					list += self.showLines(power, word, popped)
				list += ['%-11s %s.' %
					(self.anglify(power.name) + ':', self.anglify(order))]
				if word[0] == 'BUILD' and len(word) > 2:
					power.units += [' '.join(word[1:])]
					sc = word[2][:3]
					if 'SC!' in power.centers:
						power.centers.remove('SC!')
						if sc not in power.centers:
							power.centers += [sc]
							self.includeOwnership = 1
					if ('&SC' in self.map.home[power.name]
					and sc not in self.map.home[power.name]):
						self.map.home[power.name].remove('&SC')
						self.map.home[power.name] += [sc]
						power.home = self.map.home[power.name]
				elif word[0] == 'REMOVE': power.units.remove(' '.join(word[1:]))
				elif len(word) == 5:
					if word[2] in popped: list[-1] += '  (*bounce, destroyed*)'
					else: power.units += [word[1] + ' ' + word[-1]]
			if self.phaseType == 'A':
				count = len(power.centers) - len(power.units)
				if [x for x in power.centers if x in self.map.home[power.name]]:
					count += (self.map.reserves.count(power.name) +
						min(self.map.militia.count(power.name),
						len([0 for x in power.units
							if x[2:5] in self.map.home[power.name]])))
				if count:
					if 'BLIND' in self.rules: list += ['SHOW MASTER ' +
						' '.join([x.name for x in self.powers
						if x is power or x.omniscient])]
					list += ['%-12s%d unused build%s pending.' %
						(self.anglify(power.name) + ':', count,
						's'[count == 1:])]
				while 'SC?' in power.centers: power.centers.remove('SC?')
				while 'SC*' in power.centers: power.centers.remove('SC*')
			power.adjust, power.retreats = [], {}
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
		return [
			':: Judge: %s  Game: %s  Variant: %s ' %
				(host.dpjudgeID, self.name, self.map.name) + self.variant,
			':: Deadline: %s ' % phase + self.timeFormat(shortForm = 1),
			':: URL: %s%s?game=' % (host.dpjudgeURL,
				'/index.cgi' * (os.name == 'nt')) + self.name, ''] or []
	#	----------------------------------------------------------------------
	def resolvePhase(self):
		return ["The %s phase of '%s' has been completed." %
				(self.phase.title(), self.name), '']
	#	----------------------------------------------------------------------
	def resolve(self, email = None):
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
		broadcast += self.advancePhase()
		if self.phase != 'COMPLETED':
			#	---------------------------------------------------
			#	Make any unit changes based on upcoming map changes
			#	---------------------------------------------------
			if self.map.dynamic: broadcast += self.morphMap(lastPhase)
			phase = self.phase.title().split()
			broadcast += ['The next phase of %s will be %s for ' %
				(`self.name.encode('latin-1')`,
				phase[2]) + self.phaseName(form = 1)]
			if self.deadline:
				self.setDeadline()
				broadcast += ['The deadline for orders will be %s.' %
					self.timeFormat()]
			#	---------------------------------------------------------
			#	Rotate power control for any "BEFORE" and "FOR" rotations
			#	---------------------------------------------------------
			for how in range(0, len(self.rotate), 2):
				if self.rotate[how] != 'AFTER' and (len(self.rotate) == 1
				or phase[2].upper()[0] == self.rotate[how + 1][0]):
					self.rotateControl(self.rotate[how])
		else: broadcast += ['The game is over.  Thank you for playing.']
		self.await, text = 0, [x + '\n' for x in broadcast + ['']]
		if self.preview:
			if email: self.master[1] = email
			return self.mailPress(None, ['MASTER'],
				''.join(text), subject = 'PREVIEW ' + subject)
		self.mailResults(text, subject)
		self.finishPhase()
		self.makeMaps()
		self.save()
		if self.phase == 'COMPLETED': self.fileSummary()
	#	----------------------------------------------------------------------
	def endByAgreement(self):
		lines = [x + '\n' for x in self.mapperHeader()]
		result = self.proposal[0]
		if result in ('DIAS', 'NO_DIAS'):
			victors = sorted([x.name for x in self.powers
				if (x.vote > '0', x.centers)[result == 'DIAS']])
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
		self.mailResults(lines, "Diplomacy game '%s' complete" % self.name)
		self.finish(victors)
		self.fileSummary()
	#	----------------------------------------------------------------------
	def finish(self, victors):
		self.end = time.strftime('%d %B %Y', time.localtime())
		self.end = self.end[self.end[0] == '0':]
		self.outcome = [self.phaseAbbr()] + victors
		self.proposal, self.phase = None, 'COMPLETED'
		for power in self.powers: power.retreats, power.adjust = {}, []
		self.changeStatus('completed')
		self.save()
		if 'BLIND' in self.rules:
			for power in self.powers: power.removeBlindMaps()
			file = host.dpjudgeDir + '/maps/' + self.name
			for suffix in ('.ps', '.pdf', '.gif', '_.gif'):
				try: os.rename(file + `hash(self.password)` + suffix,
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
	def timeFormat(self, shortForm = None):
		when = self.deadline
		format = shortForm and ('a', 'b', '%Z') or ('A', 'B', '%Z')
		if hasattr(host, 'timeZone') and host.timeZone: 
			format = (format[0], format[1], host.timeZone)
		try: when = time.strftime('%%%s %%d %%%s %%Y %%H:%%M %s' % format,
			time.localtime(time.mktime(map(int,
			(when[:4], when[4:6], when[6:8], when[8:10], when[10:],
			0, 0, 0, -1))))).split()
		except:
			if self.phase == 'FORMING': return ''
			return 'Invalid Deadline! Notify Master!'
		when[1] = `int(when[1])`
		return ' '.join(when)
	#	----------------------------------------------------------------------
	def graceExpired(self):
		grace = self.timing.get('GRACE',
			'CIVIL_DISORDER' in self.rules and '0H')
		return grace and self.deadlineExpired(grace)
	#	----------------------------------------------------------------------
	def deadlineExpired(self, grace = '0H'):
		dict = { 'M': 60, 'H': 3600, 'D': 86400, 'W': 604800 }
		try: return time.localtime()[:5] >= time.localtime(time.mktime(tuple(
			map(int, (self.deadline[:4], self.deadline[4:6], self.deadline[6:8],
			self.deadline[8:10], self.deadline[10:], 0, 0, 0, -1)))) +
			int(grace[:-1]) * dict.get(grace[-1], 1))[:5]
		except: pass
	#	----------------------------------------------------------------------
	def setDeadline(self, firstPhase = 0):
		at, days = self.timing.get('AT'), self.timing.get('DAYS', '-MTWTF-')
		try: delay = [y for x,y in self.timing.items()
			if not self.phase.split()[-1].find(x)][0]
		except: delay = self.timing.get('NEXT',
			('3D', '1D')[self.phaseType in 'RA'])
		oneDay = 86400
		dict = { 'M': 60, 'H': 3600, 'D': oneDay, 'W': 604800 }
		secs = int(delay[:-1]) * dict.get(delay[-1], 1)
		#	-------------------------------------------------------
		#	Determine earliest deadline.  If the game allows press,
		#	double the usual length of time for the first deadline.
		#	-------------------------------------------------------
		next = time.time() + (secs << (firstPhase
			and 'NO_PRESS' not in self.rules
			and ('FTF_PRESS' not in self.rules or self.phaseType == 'M')))
		#	--------------------
		#	Advance the deadline
		#	the specified time.
		#	--------------------
		when = moved = time.localtime(next)
		if secs < oneDay / 2: at = 0
		elif at:
			#	-------------------------------------
			#	Pull the deadline back 20 minutes to
			#	provide fudge-time so that three days
			#	from 11:41, pushed to the next 11:40
			#	won't be four days away (for example)
			#	-------------------------------------
			next -= 1200
			at, when = tuple(map(int, at.split(':'))), time.localtime(next)
			if when[3:5] > at:
				next += oneDay
				when = time.localtime(next)
		while moved:
			#	---------------------------------
			#	Specific day-of-week setting (the
			#	DAYS option to the TIMING line)
			#	---------------------------------
			while 1:
				day = days[(when[6] + 1) % 7]
				if (day.isalpha(), day.isupper())[self.phaseType == 'M']: break
				next += oneDay
				when = time.localtime(next)
			#	--------------------------
			#	Vacation handling (the NOT
			#	option to the TIMING line)
			#	--------------------------
			outings, moved = self.timing.get('NOT', ''), 0
			vacations, now = filter(None, outings.split(',')), self.Time()
			while vacations:
				for vacation in vacations:
					if '-' in vacation: start, end = vacation.split('-')
					else: start = end = vacation
					while (start or now) <= self.Time(when)[:len(end)] <= end:
						next += oneDay
						when = moved = time.localtime(next)
					if end < now[:len(end)]:
						vacations.remove(vacation)
						break
				else: break
			if vacations: self.timing['NOT'] = ','.join(vacations)
			elif outings: del self.timing['NOT']
		#	------------------------------
		#	Specific time-of-day setting
		#	(AT option in the TIMING line)
		#	------------------------------
		if at: when = when[:3] + at + when[5:]
		#	--------------------------------------------------------------
		#	Set deadline to the nearest :00, :20, or :40 of the given hour
		#	--------------------------------------------------------------
		if secs > 1200: when = when[:4] + (when[4] / 20 * 20,) + when[5:]
		#	----------------------------------------------------------------
		#	Now set the deadline unless it's already set beyond the new time
		#	----------------------------------------------------------------
		self.deadline = max(self.deadline, self.Time(when))
	#	----------------------------------------------------------------------
	def canChangeOrders(self, oldOrders, newOrders):
		if self.deadline and self.deadline <= self.Time() and not self.avail:
			if not newOrders:
				return self.error.append('ORDERS REQUIRED TO AVOID LATE STATUS')
			if oldOrders and 'NO_LATE_CHANGES' in self.rules:
				return self.error.append(
					'ORDER RESUBMISSION NOT ALLOWED AFTER DEADLINE')
		if 'MUST_ORDER' in self.rules and oldOrders and not newOrders:
			return self.error.append('ORDERS REQUIRED AFTER SUBMISSION')
		return 1
	#	----------------------------------------------------------------------
	def updateOffPhases(self, power, adjust):
		if not adjust or '(NMR)' in adjust:
			if adjust and adjust.count('(NMR)') < len(adjust):
				self.error += ['ORDERS INCOMPLETE']
			adjust = []
		adjust.sort()
		if adjust == power.adjust: return self.process()
		if not self.canChangeOrders(power.adjust, adjust): return
		if not adjust:
			power.adjust = []
			return self.save()
###		if 'NO_CHECK' in self.rules:
###			power.adjust = power.adjusted = self.adjust
###			return self.process()
		orders = []
		#	------------------------------------------------------------------
		#	Check for duplicate orders (building/removing the same unit twice)
		#	------------------------------------------------------------------
		for order in adjust:
			if order == 'BUILD WAIVED': continue
			word = order.split()
			for other in orders:
				if word[2][:3] == other.split()[2][:3]:
					self.error += ['DUPLICATE ORDER: ' + order]
					break
			else: orders += [order]
		#	-----------------------------------------
		#	Process the phase if everything is ready.
		#	-----------------------------------------
		if not self.error:
			power.adjust = power.adjusted = adjust
			self.process()
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
		show, count, owner, reading, save, years = 1, {}, {}, 0, '', []
		year = last = None
		for line in [x.strip() for x in lines]:
			if not line:
				if reading and owner.get(year): reading = 0
			elif line[:26] == 'Subject: Diplomacy results':
				word = line.split()
				last, year = word[4], word[4][1:-1]
			elif year and line[:12] == 'Ownership of' and year not in years:
				years += [year]
				reading, owner[year], count[year] = 1, {}, {}
			elif reading:
				line = line.upper()
				if line[:4] == 'SHOW':
					if self.phase == 'COMPLETED': continue
					who = line.split()
					show = len(who) == 1 or not forPower or forPower.name in who
					continue
				if not show: continue
				if save: line = save + ' ' + line
				if line[-1] == '.':
					power, save = line[:line.find(':')], ''
					if power == 'UNOWNED': letter = '.'
					else: letter = self.map.abbrev.get(power, power[0])
					centers = ' '.join(line[:-1].split()[1:]).split(', ')
					for spot in centers: owner[year][self.map.aliases.
						get(spot.strip().replace(' ', '+'))] = letter
					count[year][power] = len(centers)
				else: save = line
		scs = []
		for yr in owner: scs += [sc for sc in owner[yr] if sc not in scs]
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
					'Historical Supply Center Summary\n%s\n   ' %
			(self.name, last, self.playerRoster(None, forPower, reveal)[:-1],
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
				if count[years[decade * 10]].get(power):
					results += '\n%-10s' % self.anglify(power)
					for year in years[decade * 10:][:10]:
						if count[year].get(power):
							results += '  %2d' % count[year][power]
			results += '\nIndex:    '
			for year in years[decade * 10:][:10]:
				if (forPower and forPower.name == 'MASTER'
				or 'BLIND' not in self.rules or self.phase == 'COMPLETED'):
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
			self.master[-1].replace('_', ' ') * (request != 'LIST'),
			self.master[1])
		for powerName in self.map.powers:
			try: power = [x for x in self.powers if x.name == powerName][0]
			except: continue
			results += '  %-15s ' % (self.anglify(powerName) + ':')
			if power.player: player = power.player[:]
			elif not power.address: player = ['|someone@somewhere|']
			else: player = ['|%s|' % power.address[0]]
			if request == 'LIST': del player[1:]
			elif (power.isResigned() and self.phase != self.map.phase
			and not power.units and not power.centers): del player[:2]
			for data in reversed(player):
				if '|' in data:
					late = 'late' * (self.deadline and data == player[-1]
						and self.phase not in ('COMPLETED', 'FORMING')
						and powerName in self.latePowers()
						and self.deadlineExpired()
						and ('HIDE_LATE_POWERS' not in self.rules
						or forPower.name in (powerName, 'MASTER')))
					if (self.phase != 'COMPLETED' or ('NO_REVEAL' in self.rules
					and not reveal)) and (forPower is None
					or forPower.name not in ('MASTER', powerName)
					or forPower.name == powerName and data != player[-1]):
						person = (None, 'someone@somewhere', late)
					else: person = data.split('|')
				elif data in ('RESIGNED', 'DUMMY'):
					late = ('vacant', 'dummy')[data[0] == 'D']
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
		power.adjust, places = [], []
		if not orders: return
		need = len(power.centers) - len(power.units)
		if [x for x in power.centers if x in self.map.home[power.name]]:
			need += (self.map.reserves.count(power.name) +
				min(self.map.militia.count(power.name),
				len([0 for x in power.units
					if x[3:5] in self.map.home[power.name]])))
		orderType, claim = ('BUILD', 'REMOVE')[need < 0], []
		if need > 0: needed = min(need, len(self.buildSites(power)))
		for order in orders:
			word = self.addUnitTypes(self.expandOrder([order]))
			if word[0] != orderType: word[:0] = [orderType]
			order = ' '.join(word)
			if need < 0:
				if len(word) == 3:
					if (' '.join(word[1:]) in power.units
					and order not in power.adjust): power.adjust += [order]
					else: self.error += ['INVALID REMOVE ORDER: ' + order]
				else: self.error += ['BAD ADJUSTMENT ORDER: ' + order]
			elif len(word) == 2 and word[1] in ('WAIVE', 'WAIVED'):
				if len(power.adjust) < need: power.adjust += ['BUILD WAIVED']
			elif len(word) == 3:
				site = word[2][:3]
				if ('&SC' in self.map.home[power.name]
				and site not in self.map.home[power.name]): claim += [site]
				if site not in self.buildSites(power):
					self.error += ['INVALID BUILD SITE: ' + order]
				elif site in places:
					self.error += ['MULTIPLE BUILDS IN SITE: ' + order]
				elif self.map.isValidUnit(' '.join(word[1:])):
					power.adjust += [order]
					places += [site]
				else: self.error += ['INVALID BUILD ORDER: ' + order]
			else: self.error += ['BAD ADJUSTMENT ORDER: ' + order]
		if len(claim) > self.map.home[power.name].count('&SC'):
			self.error += ['EXCESS HOME CENTER CLAIM']
		if self.error: return
		while 0 < need < len(power.adjust):
			try: power.adjust.remove('BUILD WAIVED')
			except: break
		if len(power.adjust) == abs(need): self.process()
		else: self.error += ['ADJUSTMENT ORDERS IGNORED (MISCOUNTED)']
	#	----------------------------------------------------------------------
	def updateRetreatOrders(self, power, orders):
		power.adjust, retreated = [], []
		if not orders: return
		for order in orders:
			word = self.addUnitTypes(self.expandOrder([order]))
			if word[0] == 'RETREAT': del word[0]
			unit = ' '.join(word[:2])
			try: unit = [x for x in power.retreats
				if x == unit or x.startswith(unit + '/')][0]
			except: return self.error.append('UNIT NOT IN RETREAT: ' + unit)
			if unit in retreated: return self.error.append(
				'TWO ORDERS FOR RETREATING UNIT: ' + unit)
			word[1] = unit[2:]
			if ((len(word) != 3 or word[2] != 'DISBAND')
			and (len(word) != 4 or word[2] != '-'
			or   word[3] not in power.retreats[unit])):
				return self.error.append('BAD RETREAT ORDER: ' + order)
			retreated += [unit]
			power.adjust += ['RETREAT ' + ' '.join(word)]
		if len(retreated) == len(power.retreats): self.process()
		else: self.error += ['RETREAT ORDERS IGNORED (INCOMPLETE)']
	#	----------------------------------------------------------------------
	def powerOrders(self, power):
		try:
			if self.phaseType in 'RA': orders = '\n'.join(power.adjust)
			else: orders = self.getOrders(power)
		except: orders = '(None)'
		return ('Current orders for %s:\n\n%s\n\nEnd of orders.\n' %
			(self.anglify(power.name), orders or '(NMR)'))
	#	----------------------------------------------------------------------
	def lateNotice(self):
		late, now = self.latePowers(), self.Time()
		#	-----------------------------
		#	Pre-deadline warning messages
		#	-----------------------------
		if not self.deadlineExpired():
			for power in late: self.mailPress(None, [power],
				"%s\n\nThe deadline for '%s' is approaching and\n"
				'orders for %s have not yet been submitted.\n\n'
				'The pending deadline is %s.\n' %
				('\n'.join(self.mapperHeader()),
				self.name, self.anglify(power), self.timeFormat()),
				subject = 'Diplomacy deadline reminder')
			return
		#	-------------------------------------
		#	Other notices (late and beyond grace)
		#	-------------------------------------
		text = ('Diplomacy Game:   %s (%s)\n'
				'Current Phase:    %s\n'
				'Missed Deadline:  %s\n' %
				(self.name, host.dpjudgeID, self.phaseName(form = 2),
				self.timeFormat()))
		receivers, who = ['MASTER'], '\n'.join(textwrap.wrap(
			', '.join(map(self.anglify, late or ['MASTER'])), 70,
			subsequent_indent = ' ' * 18))
		#	----------------------------
		#	Past grace -- resign anyone
		#	who is still late and say so
		#	----------------------------
		if late and self.graceExpired():
			self.mailPress(None, ['All'], '%s%-17s%s\n' %
				(text, 'Dismissed Power%-2s ' % 's:'[len(late) == 1:], who),
				subject = 'Diplomacy player dismissal')
			for power in [x for x in self.powers if x.name in late]:
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
			count = int(self.timing['GRACE'][:-1])
			penalty = ('\n\nPowers who are still late %d %s%s after the\n'
				'deadline above will be %s.' % (count,
				{'H': 'hour', 'D': 'day', 'M': 'minute', 'W': 'week'}.
				get(self.timing['GRACE'][-1], 'second'), 's'[count == 1:],
				('summarily dismissed', 'declared in civil disorder')
				['CIVIL_DISORDER' in self.rules]))
		else: penalty = ''
		#	-----------------------------------
		#	Send late notice.  If it's the same
		#	calendar hour as the deadline, send
		#	it to everyone.  Otherwise, only
		#	bother the late powers.
		#	-----------------------------------
		if late and 'HIDE_LATE_POWERS' in self.rules:
			for power in late: self.mailPress(None, [power],
				'%sLate Power:       %s%s\n' % (text, self.anglify(power),
				penalty), subject = 'Diplomacy deadline missed', private = 1)
		elif now[:10] != self.deadline[:10]: receivers += late
		else: receivers += [x.name for x in self.powers]
		for receiver in receivers: self.mailPress(
			None, [receiver], '%s%-18s%s\n' %
			(text, 'Late Power%-2s' % 's:'[len(late) == 1:], who + penalty),
			subject = ('Diplomacy late notice', 'Diplomacy deadline missed')
			[receiver in late], private = 1)
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
			variant, self.master[1].split('@')[0], ''.join(press)))
		indent = 20 + (len(need) == 1)
		if need: result += (' ' * indent + 'URL: %s%s?game=%s\n' %
			(host.dpjudgeURL, '/index.cgi' * (os.name == 'nt'), self.name))
		for line in need:
			result += ' ' * indent + line + '\n'
			indent += 1
		return result
	#	----------------------------------------------------------------------
	def reportOrders(self, power, email = None):
		whoTo = email = email or power.address[0]
		if (power.address
		and email.upper() not in power.address[0].upper().split(',')):
			whoTo += ',' + power.address[0]
		self.openMail('Diplomacy orders', mailTo = whoTo, mailAs = host.dpjudge)
		self.mail.write(self.powerOrders(power))
		self.mail.close()
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
			for x in (host.judgekeeper, self.master[1])]
		outsider = (jk[0] != gm[0]
			or jk[1].split('.')[-2:] != gm[1].split('.')[-2:])
		powers = [[x.name, x.password.upper()]
			for x in self.powers if x.password]
		if ([power, pwd.upper()] in ['MASTER', self.password.upper()] + powers
		and not self.private
		and origin != 'unknown'
		and '.proxy.aol.com' not in origin
		and '.mx.aol.com' not in origin):
			try: lines = open(access, encoding='latin-1').readlines()
			except: lines = []
			for line in lines:
				word = line.upper().strip().split()
				if len(word) < 8: continue
				if (word[5] == origin.upper() # and '@' not in word[5]
				and word[6] != power and word[6:] in powers
				and self.password.upper() not in (word[7], pwd.upper())):
					for addr in [self.master[1]] + host.detectives * outsider:
						self.openMail('Diplomacy suspicious activity',
							mailTo = addr, mailAs = host.dpjudge)
						self.mail.write('GameMaster:\n\n'
							"The login just made by '%s' in game '%s' is\n"
							"suspiciously similar to logins made by '%s'.\n\n"
							'This may need to be investigated at\n'
							'%s?game=%s&power=MASTER&password=%s\n' %
							(self.anglify(power), self.name,
							self.anglify(word[6]),
							host.dpjudgeURL, self.name, self.password))
						self.mail.close()
					break
		#	---------------------------
		#	End of cheater-catcher code
		#	---------------------------
		file = open(access, 'a')
		if pwd == self.password: pwd = '!-MASTER-!'
		temp = '%s %-16s %-10s %s\n' % (time.ctime(), origin, power, pwd)
		file.write(temp.encode('latin-1'))
		del temp
		file.close()
		try: os.chmod(access, 0666)
		except: pass
	#	----------------------------------------------------------------------
	def mailMap(self, email, mapType, power = None):
		fileName = (host.dpjudgeDir + '/maps/' + self.name +
			(power and 'BLIND' in self.rules
			and (power, self)[power.name == 'MASTER'].password or '')
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
	#	----------------------------------------------------------------------
	def setState(self):
		if self.status[1] == 'preparation': return
		if self.error and self.status[1] not in ('completed', 'terminated'):
			self.status[1] = 'error'
		self.state = {
						'MASTER':	self.password + ':' + self.master[0],
						'STATUS':	':'.join(self.status).upper(),
						'PHASE':	self.phaseAbbr(),
						'DEADLINE':	self.deadline,
						'ZONE':		self.zone or 'GMT',
						'PRIVATE':	self.private or '',
						'MAP':		self.map.name,
						'RULES':	':'.join(self.rules),
					}
		for power in self.powers:
			if power.player and power.password and power.player[0][0] == '#':
				if (self.status[1] == 'active' and self.deadlineExpired()
				and power.name in self.latePowers()): what = 'LATE'
				else: what = power.type or 'POWER'
				self.state[power.name] = ':'.join(
					(what, power.password, power.player[0].split('|')[0]))
	#	----------------------------------------------------------------------
	def updateState(self):
		# return # TEMP! BUT AS OF NEW YEARS MOMENT 2007, APACHE SEEMS WAY SICK
		if not host.dppdURL: return
		self.setState()
		header = '|'.join([x + ':' + (y or '') for x,y in self.state.items()])
		if self.outcome: result = '|RESULT:' + ':'.join(self.outcome)
		else: result = ''
		header = ('JUDGE:%s|GAME:%s%s|' %
			(host.dpjudgeID, self.name, result) + header)
		dict = urllib.urlencode({'status': header.encode('latin-1')})
		#	I don't know why, but we need to use the query string
		#	instead of a POST.  Something to look into.
		query = '?&'['?' in host.dppdURL]
		page = urllib.urlopen(host.dppdURL + query + 'page=update&' + dict)
		#print '<!--' + `page.readlines()` + '-->'
		page.close()
	#	----------------------------------------------------------------------
	def changeStatus(self, status):
		self.status[1] = status
		Status().changeStatus(self.name, status)
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
					data.setdefault(rule, {'group': group, 'variant': variant})
					for control in word[3:-1]:
						if control[0] in '-=+!': data[rule].setdefault(
							control[0],[]).append(control[1:])
		file.close()
		return data, forced, denied
	#	----------------------------------------------------------------------


import os
from codecs import open

import host

class Map:
	#	----------------------------------------------------------------------
	def __init__(self, name = 'standard', trial = 0):
		victory = phase = validated = textOnly = flowSign = None
		rootMap = rootMapDir = None
		homes, locName, locType, locAbut, abutRules = {}, {}, {}, {}, {}
		ownWord, abbrev, centers, units, powName, flag = {}, {}, {}, {}, {}, {}
		rules, files, powers, scs, owns, inhabits = [], [], [], [], [], []
		flow, size, homeYears, dummies, locs = [], [], [], [], []
		reserves, militia, flagDirs, error, notify = [], [], [], [], []
		dynamic, factory, partisan, alternative, hidden = {}, {}, {}, {}, {}
		controls, leagues, directives, phaseAbbrev, unclear = {}, {}, {}, {}, {}
		if host.notify and host.judgekeeper and (trial or host.notify > 1):
			notify = [host.judgekeeper]
		unitNames = {
			'A': 'ARMY',	'F': 'FLEET',	'W': 'WING'
		}
		#	-------------------------------------------------------------
		#	Keywords are always single words. Put any word combinations
		#	in aliases, where map locations and power names will be added
		#	later.
		#	Since 'East Coast' and 'West Coast' are actually spaces on
		#	the Empire map, adding 'OF' helps to distinguish.
		#	Aliases are only converted in a second pass, so if they
		#	contain a keyword, you should replace the keyword with its
		#	abbreviation (e.g. replace 'OF' with '\\').
		#	The reason to add 'A F' (stands for 'A FLEET') and the like
		#	instead of making 'A' a keyword mapping to '', is that 'A'
		#	already stands for 'ARMY'. Remember, longer word combinations
		#	get processed first.
		#	-------------------------------------------------------------
		keywords, aliases = {
			'>': '',		'-': '-',
			'ARMY': 'A',	'FLEET': 'F',	'WING': 'W',	'THE': '',	
			'NC': '/NC',	'SC': '/SC',	'EC': '/EC',	'WC': '/WC',
			'MOVE': '',		'MOVES': '',	'MOVING': '',
			'ATTACK': '',	'ATTACKS': '',	'ATTACKING': '',
			'RETREAT': 'R',	'RETREATS': 'R',	'RETREATING': 'R',
			'SUPPORT': 'S',	'SUPPORTS': 'S',	'SUPPORTING': 'S',	
			'CONVOY': 'C',	'CONVOYS': 'C',	'CONVOYING': 'C', 
			'HOLD': 'H',	'HOLDS': 'H',	'HOLDING': 'H',
			'BUILD': 'B',	'BUILDS': 'B',	'BUILDING': 'B',
			'DISBAND': 'D',	'DISBANDS': 'D',	'DISBANDING': 'D',
			'REMOVE': 'D',	'REMOVES': 'D',	'REMOVING': 'D',
			'WAIVE': 'V',	'WAIVES': 'V',	'WAIVING': 'V',	'WAIVED': 'V',
			'KEEP': 'K',	'KEEPS': 'K',	'KEEPING': 'K',
			'PROXY': 'P',	'PROXIES': 'P',	'PROXYING': 'P',
			'IS': '',		'WILL': '',
			'IN': '',		'AT': '',		'ON': '',	'TO': '',
			'OF': '\\',		'FROM': '\\',	'WITH': '?',	'TSR': '=',
			'VIA': '~',		'THROUGH': '~',	'OVER': '~',	'BY': '~',
			'AND': '',		'OR': '|',
			'BOUNCE': '|',	'CUT': '|',		'VOID': '?',
			'DISLODGED': '~',				'DESTROYED': '*',
		}, {
			'NORTH COAST \\': '/NC \\',		'SOUTH COAST \\': '/SC \\',
			'EAST COAST \\': '/EC \\',		'WEST COAST \\': '/WC \\',
			'AN A': 'A',	'A F': 'F',		'A W': 'W',
			'NO C': '?',	'~ C': '^',		'~ =': '=',		'? =': '=',
			'~ LAND': '_',	'~ WATER': '_',	'~ SEA': '_',
			'TRANS SIBERIAN RAILROAD': '=',	'V B': 'B V',
		}
		vars(self).update(locals())
		self.load()
		self.validate()
	#	----------------------------------------------------------------------
	def __repr__(self):
		return self.name
	#	----------------------------------------------------------------------
	def validate(self, phases = '', force = 0):
		if not force and not phases and self.validated: return
		for phase in phases:
			for when, what in self.dynamic.items():
				if ((when.isupper() and phase.startswith(when))
				or	(when.islower() and when.upper() == phase)): self.load(what)
		error, self.rootMap = self.error, self.rootMap or self.name
		self.powers, self.validated = self.homes.keys(), 1
		try: self.powers.remove('UNOWNED')
		except: pass
		self.powers.sort()
		if len(self.powers) < 2:
			error += ['MAP DOES NOT SPECIFY AT LEAST TWO POWERS']
		for place in self.locName.values():
			if place.upper() not in self.powers and not self.areatype(place):
				error += ['NAMED LOCATION NOT ON MAP: ' + place]
		for place, abuts in self.locAbut.items():
			upAbuts = [x.upper() for x in abuts]
			for abut in abuts:
				upAbut = abut.upper()
				if upAbuts.count(upAbut) > 1:
					error += ['SITES ABUT TWICE: %s-' % place.upper() + upAbut]
					while upAbut in upAbuts: upAbuts.remove(upAbut)
			if place.upper() not in self.locName.values():
				error += ['MAP LOCATION HAS NO FULL NAME: ' + place]
			[error.append('ONE-WAY ADJACENCY IN MAP: %s -> ' % place + x)
				for x in abuts if 'SHUT' not in map(self.areatype, (place, x))
				and not self.abuts('A', x, '-', place)
				and not self.abuts('F', x, '-', place)]
		for power, places in self.homes.items():
			for site in [x for x in places if x != '&SC']:
				if site not in self.scs: self.scs += [site]
				if not self.areatype(site):
					error += ['BAD HOME FOR %s: ' % power + site]
				#	------------------------------------------------------
				#	Remove home centers from unowned list.
				#	It's perfectly ok for 2 powers to share a home center,
				#	as long as no more than one owns it at the same time.
				#	------------------------------------------------------
				if power != 'UNOWNED':
					try: self.homes['UNOWNED'].remove(site)
					except: pass
		for scs in self.centers.values():
			self.scs.extend([x for x in scs if x not in self.scs])
		#	------------------------------------------------------------
		#	Validate factory and partisan sites (non-SC build locations)
		#	------------------------------------------------------------
		for power, places in self.factory.items():
			for site in places:
				if power == 'UNOWNED': error += ['UNOWNED FACTORY: ' + site]
				elif not self.areatype(site):
					error += ['BAD FACTORY FOR %s: ' % power + site]
				elif site in self.scs:
					error += ['FACTORY CANNOT BE SC: ' + site]
				for other, locs in self.factory.items():
					if locs.count(site) != (other == power):
						error += ['FACTORY MULTIPLY OWNED: ' + site]
		for power, places in self.partisan.items():
			for site in places:
				if power == 'UNOWNED':
					error += ['UNOWNED PARTISAN SITE: ' + site]
				elif not self.areatype(site):
					error += ['BAD PARTISAN SITE FOR %s: ' % power + site]
				elif site in self.scs:
					error += ['PARTISAN SITE CANNOT BE SC: ' + site]
				for other, locs in self.partisan.items():
					if locs.count(site) != (other == power):
						error += ['PARTISAN SITE MULTIPLY OWNED: ' + site]
				for other, locs in self.factory.items():
					if site in locs:
						error += ['PARTISAN SITE CANNOT BE FACTORY: ' + site]
		#	-------------------------------------
		#	Validate alternative home limitations
		#	-------------------------------------
		for power, alternatives in self.alternative.items():
			alts = [x[0] for x in alternatives]
			for altHomes in alternatives:
				for home in altHomes[1:]:
					if home not in self.homes.get(power, []):
						error += ['LIMITATION FOR ALTERNATIVE HOME CENTER '
							+ altHomes[0] + ' FOR POWER ' + power
							+ ' NOT A HOME CENTER: ' + home]
					elif home in alts:
						error += ['LIMITATION FOR ALTERNATIVE HOME CENTER '
							+ altHomes[0] + ' FOR POWER ' + power
							+ ' CANNOT ITSELF BE ALTERNATIVE HOME CENTER: '
							+ home]
		#	-----------------
		#	Validate RESERVES
		#	-----------------
		error += ['BAD RESERVES POWER: ' + x
			for x in self.reserves if x not in self.powers]
		#	----------------
		#	Validate MILITIA
		#	----------------
		error += ['BAD MILITIA POWER: ' + x
			for x in self.militia if x not in self.powers]
		#	----------------------------------
		#	Validate special abut restrictions
		#	----------------------------------
		for key in self.abutRules:
			if key[-1] == ')':
				if key[:-1] not in self.scs:
					error += ['BAD OWNERSHIP ABUT RESTRICTION: (' + key]
			elif key[-1] == ':':
				if key[0] not in [self.abbrev.get(x, x[0])
					for x in self.powers]:
					error += ['BAD POWER ABUT RESTRICTION: ' + key]
			elif key not in '~*':
				error += ['UNKNOWN SPECIAL ABUT RESTRICTION: ' + key]
			elif self.abutRules.get('~*'[key == '~']):
				error += ['ILLEGAL SPECIAL ABUT RESTRICTIONS: BOTH ~ AND *']
		#	-----------------
		#	Validate initial
		#	centers and units
		#	-----------------
		for power, places in self.centers.items(): [error.append(
			'BAD INITIAL OWNED CENTER FOR %s: ' % power + x) for x in places
			if x not in ('SC!', 'SC?') and not self.areatype(x)]
		for power in self.powers:
			if power not in self.owns: self.centers[power] = [
				x for x in self.homes[power] if x != '&SC']
			[error.append('BAD INITIAL UNIT FOR %s: ' % power + x)
				for x in self.units.get(power, []) if not self.isValidUnit(x)]
		for power, centers in self.centers.items():
			for site in [x for x in centers if x not in ('SC!', 'SC?')]:
				for other, locs in self.centers.items():
					if locs.count(site) != (other == power):
						error += ['CENTER MULTIPLY OWNED: ' + site]
		if 'UNOWNED' in self.homes: del self.homes['UNOWNED']
		#	----------------
		#	Ensure a default
		#	game-year FLOW
		#	----------------
		self.flow = self.flow or [
			'SPRING:MOVEMENT,RETREATS',
			'FALL:MOVEMENT,RETREATS',
			'WINTER:ADJUSTMENTS'	]
		#	------------------
		#	Validate game FLOW
		#	------------------
		self.phaseAbbrev = abbrev = {
			'M': 'MOVEMENT', 'R': 'RETREATS', 'A': 'ADJUSTMENTS' }
		try:
			self.seq, self.flowSign = [], 0
			for item in self.flow:
				if ':' not in item:
					if item == 'NEWYEAR':
						if self.flowSign < 0:
							error += ['THE %s FLOW DIRECTIVE CANNOT BE BOTH'
								' POSITIVE AND NEGATIVE' % item]
						else: self.flowSign = 1
						self.seq += [item]
					else:
						error += ['FLOW %s REQUIRES COLON (:)' % item]
					continue
				try: season, phases = item.split(':')
				except:
					error += ['MORE THAN ONE COLON (:) IN FLOW ' + item]
					continue
				if season == 'NEWYEAR':
					try: years = int(phases)
					except: 
						error += ['THE %s FLOW DIRECTIVE CAN ONLY HAVE A'
							' NUMBER AS PARAMETER' % season]
						continue
					if years == 0:
						error += ['THE %s FLOW DIRECTIVE CAN NOT BE 0' % season]
						continue
					if self.flowSign * years < 0:
						error += ['THE %s FLOW DIRECTIVE CANNOT BE BOTH'
							' POSITIVE AND NEGATIVE' % item]
					else: self.flowSign = years < 0 and -1 or 1
					self.seq += [season + ' ' + phases]
				elif season == 'IFYEARDIV':
					try:
						if '=' in phases:
							div, mod = map(int, phases.split('='))
						else:
							div, mod = int(phases), 0
					except: 
						error += ['THE %s FLOW DIRECTIVE SHOULD EITHER HAVE A'
							' SINGLE NUMBER, OR 2 NUMBERS SEPARATED BY AN'
							' EQUAL SIGN (=) INSTEAD OF %s' % (season, phases)]
						continue
					if div <= 0:
						error += ['THE %s FLOW DIRECTIVE REQUIRES A DIVISOR '
							'GREATER THAN 0 INSTEAD OF %s' % (season, div)]
						continue
					if mod < 0 or mod >= div:
						error += ['THE %s FLOW DIRECTIVE REQUIRES A'
							' POSITIVE MODULO SMALLER THAN THE DIVISOR %d'
							' INSTEAD OF %d' % (season, div, mod)]
						continue
					self.seq += [season + ' ' + phases]
					if not self.flowSign:
						self.seq[:0], self.flowSign = ['NEWYEAR'], 1
				else:
					for phase in phases.split(','):
						if abbrev.get(phase[0]) not in (None, phase):
							error += ['BAD PHASE TYPE IN FLOW (%s IS ALREADY'
								' %s)' % (`phase[0]`, `abbrev[phase[0]]`)]
							continue
						newPhase = season + ' ' + phase
						if newPhase in self.seq and season != 'NEWYEAR':
							error += ['PHASE IN FLOW TWICE: ' + newPhase]
							continue
						self.seq += [newPhase]
						abbrev[phase[0]] = phase
			if not self.flowSign:
				self.seq[:0], self.flowSign = ['NEWYEAR'], 1
		except: error += ['BAD FLOW SPECIFICATION']
		#	---------------------------
		#	Validate initial game phase
		#	---------------------------
		self.phase = self.phase or 'SPRING 1901 MOVEMENT'
		try:
			phase = self.phase.split()
			if len(phase) != 3: raise
			self.firstYear = int(phase[1])
		except: error += ['BAD PHASE IN MAP FILE: ' + self.phase]
		#	----------------------
		#	Load map specific info
		#	----------------------
		return self.loadInfo()
	#	----------------------------------------------------------------------
	def loadInfo(self):
		error = self.error
		#	-----------------
		#	Open ps info file
		#	-----------------
		for mapDir in ['trials', 'maps'][not self.trial:]:
			try: file = open(host.packageDir + '/' + mapDir + '/psinfo',
				encoding = 'latin-1')
			except:
				err = 'PSINFO FILE NOT FOUND'
				continue
			#	------------------------------------
			#	Assign default values
			#	Order: bbox papersize rotation blind
			#	------------------------------------
			self.bbox, self.papersize, self.rotation = None, '', 3
			defVals = [''] * 3
			curVals = defVals[:]
			#	-----------------------------------------------------------
			#	Parse the file, searching for the map name
			#	and determining its parameter values
			#	Missing values are replaced with the default values.
			#   Special values:
			#		'_': replace with the default value
			#		'-': copy the corresponding value for the preceding map
			#		'=': copy all remaining values from the preceding map
			#	-----------------------------------------------------------
			for line in file:
				word = line.split()
				if not word or word[0][0] == '#': continue
				curName = word.pop(0)
				for idx in range(len(defVals)):
					if len(word) <= idx or word[idx] == '_':
						curVals[idx] = defVals[idx]
					elif word[idx] == '-': pass
					elif word[idx] == '=': break
					else: curVals[idx] = word[idx]
				if curName == self.rootMap: break
			else:
				err = 'MAP NOT DEFINED IN PSINFO FILE: ' + self.rootMap
				continue
			#	------------------------------------------------------
			#	Determine bbox and pixel size of graphic map at 72 dpi
			#	after rotation (for .gif file creation and display)
			#	------------------------------------------------------
			if curVals[0] != '':
				try: 
					bbox = [eval(x) for x in curVals[0].split(',')]
					if len(bbox) == 4:
						self.bbox = bbox
						self.size = [bbox[2] - bbox[0], bbox[3] - bbox[1]]
					else: raise 
				except: error.append('BBOX NOT CORRECT IN PSINFO FOR MAP: ' +
					self.rootMap)
			#	-------------------
			#	Determine papersize
			#	-------------------
			if curVals[1] != '': self.papersize = curVals[1]
			#	-----------------------------------------
			#	Determine rotation from page orientation: 
			#		Portrait:	0 (No rotation)
			#		Landscape:	3 (270 degrees rotation)
			#		(Seascape:	1 (90 degrees rotation))
			#	-----------------------------------------
			if curVals[2] != '':
				try: 
					rotation = eval(curVals[2])
					if rotation in range(4): self.rotation = rotation
					else: raise
				except: error.append('ROTATION NOT 0 TO 3 IN PSINFO FOR MAP: ' +
					self.rootMap)
			break
		else: return error.append(err)
	#	----------------------------------------------------------------------
	def load(self, fileName = 0):
		error, flagDirsLen = self.error, len(self.flagDirs)
		if type(fileName) is not list:
			fileName, power = fileName or (self.name + '.map'), 0
			mapName = fileName.split('.')[0]
			for mapDir in ['trials', 'maps'][not self.trial:]:
				try: file = open(host.packageDir + '/' + mapDir + '/' +
					fileName, encoding = 'latin-1')
				except: continue
				if mapName == (self.rootMap or self.name):
					self.rootMapDir = mapDir
				break
			else: return error.append('MAP FILE NOT FOUND: ' + fileName)
			self.files += [fileName]
			if mapName not in self.flagDirs and os.path.isdir(
				host.dpjudgeDir + '/images/flags/' + mapName):
				self.flagDirs += [mapName]
		else: file = fileName
		phase = variant = 0
		for line in file:
			word = line.split()
			if not word or word[0][0] == '#': continue
			upword = word[0].upper()
			if word[-1].upper() in ('DIRECTIVE', 'DIRECTIVES'):
				if len(word) > 2: error += ['BAD VARIANT DIRECTIVE LINE IN MAP']
				elif len(word) == 1: variant = 'ALL'
				elif upword == 'END': variant = 0
				else:
					where = host.packageDir + '/variants'
					dirs = [x.upper() for x in os.listdir(where)
						if os.path.isdir(where + '/' + x)]
					if upword in dirs: variant = upword
					else: error += ['BAD VARIANT IN DIRECTIVE LINE IN MAP']
			elif variant: self.directives.setdefault(variant, []).append(line)
			#	----------------------------------------
			#	Dynamic map instructions to be processed
			#	by the game only in specific game phases
			#	----------------------------------------
			elif upword in ('FROM', 'IN'):
				data = [x.strip() for x in ' '.join(word[1:]).split(':')]
				if not data: error += ['BAD %s DIRECTIVE IN MAP' % upword]
				elif upword == 'IN': phase = data[0].upper()
				else: phase = data[0].lower()
				if phase == 'start': phase = 0
				elif (' ' in phase or phase[-1] != 'm'
				or not phase[1:-1].isdigit()): error += ['BAD FROM DIRECTIVE']
				if len(data) > 1:
					self.dynamic.setdefault(phase, []).append(data[1])
					phase = 0
			elif phase: self.dynamic.setdefault(phase, []).append(line)
			#	------------------------------------------
			#	Text-Only specification (no .ps available)
			#	------------------------------------------
			elif upword == 'TEXTONLY': self.textOnly = 1
			#	----------------------------------
			#	Centers needed to obtain a VICTORY
			#	----------------------------------
			elif upword == 'VICTORY':
				#if self.victory: error += ['TWO VICTORY LINES IN MAP']
				try: self.victory = map(int, word[1:])
				except: error += ['BAD VICTORY LINE IN MAP FILE']
			#	---------------------------------
			#	Inclusion of other base map files
			#	---------------------------------
			elif upword in ('USE', 'USES', 'MAP'):
				if upword == 'MAP':
					if len(word) != 2: error += ['BAD ROOT MAP LINE']
					elif self.rootMap: error += ['TWO ROOT MAPS']
					else: self.rootMap = word[1].split('.')[0]
				for newFile in word[1:]:
					if '.' not in newFile: newFile += '.map'
					if newFile not in self.files: self.load(newFile)
					else: error += ['FILE MULTIPLY USED: ' + newFile]
			#	----------------------------
			#	FLAGS directory for this map
			#	----------------------------
			elif upword == 'FLAGS':
				self.flagDirs = self.flagDirs[:flagDirsLen]
				for mapName in word[1:]:
					if mapName not in self.flagDirs and os.path.isdir(
						host.dpjudgeDir + '/images/flags/' + mapName):
						self.flagDirs += [mapName]
			#	----------------------------
			#	Game phase FLOW for this map
			#	----------------------------
			elif upword == 'FLOW': 
				if len(word) == 1: self.flow = []
				else: self.flow += word[1:]
			#	-----------------------------
			#	Person to NOTIFY on gamestart
			#	-----------------------------
			elif upword == 'NOTIFY': self.notify += word[1:]
			#	---------------
			#	Set BEGIN phase
			#	---------------
			elif upword == 'BEGIN': self.phase = ' '.join(word[1:]).upper()
			#	----------------------------------
			#	DPjudge RULEs specific to this map
			#	----------------------------------
			elif upword in ('RULE', 'RULES'):
				self.directives.setdefault(variant or 'ALL', []).append(line)
				#	----------------------------------------------
				#	Go ahead and add it to self.rules if this rule
				#	applies to all variants.  Any variant-specific
				#	rules will be added later by the Game object.
				#	Map.rules is only for display on GM's Webpage.
				#	----------------------------------------------
				if (variant or 'ALL') == 'ALL':
					self.rules += line.upper().split()[1:]
			#	----------------
			#	Other directives
			#	----------------
			elif upword == 'ROTATE':
				self.directives.setdefault(variant or 'ALL', []).append(line)
			#	---------------------------------------------------
			#	Year(s), if any, in which new home SC's are decided
			#	---------------------------------------------------
			elif upword == 'NEWHOMES': self.homeYears = word[1:]
			#	----------------------
			#	Placenames and aliases
			#	----------------------
			elif '=' in line:
				token = line.upper().split('=')
				if len(token) == 1:
					error += ['BAD ALIASES IN MAP FILE: ' + token[0]]
					token += ['']
				oldName, name, word = 0, token[0].strip(), token[1].split()
				parts = [x.strip() for x in name.split('->')]
				if len(parts) == 2: oldName, name = parts
				elif len(parts) > 2: error += ['BAD RENAME DIRECTIVE: ' + name]
				if (not (word[0][0] + word[0][-1]).isalnum()
				or word[0] != self.norm(word[0]).replace(' ', '')):
					error += ['INVALID LOCATION ABBREVIATION: ' + word[0]]
				if oldName: self.rename(oldName, word[0])
				if name in self.keywords:
					error += ['MAP LOCATION IS RESERVED KEYWORD:' + name]
					normed = name
				else: normed = self.norm(name)
				if name in self.locName or normed in self.aliases:
					error += ['DUPLICATE MAP LOCATION OR POWER: ' + name]
				self.locName[name] = self.aliases[normed] = word[0]
				for alias in word[1:]:
					unclear = alias[-1] == '?'
					#   --------------------------------
					#   For ambiguous place names, let's
					#   do just a minimal normalization,
					#   otherwise they might become
					#   unrecognizable (e.g. "THE")
					#   --------------------------------
					normed = unclear and alias[:-1].replace('+',
						' ').upper() or self.norm(alias)
					if unclear: self.unclear[normed] = word[0]
					elif normed in self.aliases:
						if self.aliases[normed] != word[0]:
							error += ['DUPLICATE MAP ALIAS OR POWER: ' + alias]
					else: self.aliases[normed] = word[0]
			#	----------------------
			#	Alternate flag graphic
			#	----------------------
			elif upword == 'FLAG':
				if not power: error += ['FLAG BEFORE POWER: ' + ' '.join(word)]
				elif len(word) != 2 or self.flag.has_key(power):
					error += ['INVALID FLAG: ' + ' '.join(word)]
				else: self.flag[power] = word[1]
			#	----------------
			#	Center ownership
			#	----------------
			elif upword in ('OWNS', 'CENTERS'):
				if not power:
					error += [upword + ' BEFORE POWER: ' + ' '.join(word)]
				else:
					if not power in self.owns: self.owns.append(power)
					if upword[0] == 'C' or not self.centers.has_key(power):
						self.centers[power] = line.upper().split()[1:]
					else: self.centers[power].extend([x for x in
						line.upper().split()[1:]
						if x not in self.centers[power]])
			#	--------------------------------------------------------------
			#	Home centers, overriding those from the power declaration line
			#	--------------------------------------------------------------
			elif upword == 'INHABITS':
				if not power:
					error += ['INHABITS BEFORE POWER: ' + ' '.join(word)]
				else:
					reinit = power not in self.inhabits
					if reinit: self.inhabits.append(power)
					self.addHomes(power, word[1:], reinit)
			elif upword in ('HOME', 'HOMES'):
				if not power:
					error += [upword + ' BEFORE POWER: ' + ' '.join(word)]
				else:
					if power not in self.inhabits: self.inhabits.append(power)
					self.addHomes(power, word[1:], 1)
			#	-----------------------------
			#	Clear known units for a power
			#	-----------------------------
			elif upword == 'UNITS':
				if power: self.units[power] = []
				else: error += ['UNITS BEFORE POWER']
			#	--------------------------------
			#	Establish reserves (extra units)
			#	and militia (home defense units)
			#	--------------------------------
			elif upword in ('RESERVES', 'MILITIA'):
				if power:
					try:
						if len(word) > 2: raise
						count = len(word) == 1 or int(word[1])
						if count < 0: raise
						if upword == 'RESERVES':
							self.reserves = [power] * count + [x
								for x in self.reserves if x != power]
						else: self.militia = [power] * count + [x
								for x in self.militia if x != power]
						self.reserves += [power] * count
					except: error += ['INVALID %s COUNT' % upword]
				else: error += ['%s BEFORE POWER' % upword]
			#	-------------
			#	Power control
			#	-------------
			elif upword == 'CONTROL':
				if not power: error += ['CONTROL BEFORE POWER']
				elif power not in self.dummies: error += [
					'CONTROLLED POWER %s NOT A DUMMY' % power]
				else:
					#	----------------------------------------------------
					#	To allow for non-map powers to control dummies,
					#	checking if the controller exists and is not a dummy
					#	is done in Game.validateStatus().
					#	----------------------------------------------------
					
					self.controls[power] = [self.normPower(x) for x in word[1:]]
			#	-------------------------------
			#	League affiliation and behavior
			#	-------------------------------
			elif upword == 'LEAGUE':
				if not power: error += ['LEAGUE BEFORE POWER']
				elif power not in self.leagues:
					self.leagues[power] = [x.upper() for x in word[1:]]
					if len(word) > 2:
						act = self.leagues[power][1]
						if act == 'STRICT':
							if len(word) > 3: error += ['BAD STRICT LEAGUE']
						elif act != 'BENIGN': error += ['BAD LEAGUE BEHAVIOR']
				else: error += ['POWER IN MULTIPLE LEAGUES']
			#	----------------
			#	Unit designation
			#	----------------
			elif upword in ('A', 'F'):
				unit = ' '.join(word).upper()
				if not power: error += ['UNIT BEFORE POWER: ' + unit]
				elif len(word) == 2:
					for units in self.units.values(): map(units.remove,
						[x for x in units if x[2:5] == unit[2:5]])
					self.units.setdefault(power, []).append(unit)
				else: error += ['INVALID UNIT: ' + unit]
			#	-------
			#	Dummies
			#	-------
			elif upword in ('DUMMY', 'DUMMIES'):
				if len(word) > 1: power = None
				if len(word) == 1:
					if upword == 'DUMMIES':
						error += ['DUMMIES REQUIRES LIST OF POWERS']
					elif not power: error += ['DUMMY BEFORE POWER']
					elif power not in self.dummies: self.dummies += [power]
				elif word[1].upper() != 'ALL':
					self.dummies.extend([x for x in [self.normPower(y)
						for y in word[1:]] if x not in self.dummies])
				elif len(word) == 2: self.dummies = [x for x in self.homes.keys() if x != 'UNOWNED']
				elif word[2].upper() != 'EXCEPT':
					error += ['NO EXCEPT AFTER %s ALL' % upword]
				elif len(word) == 3:
					error += ['NO POWER AFTER %s ALL EXCEPT' % upword]
				else: self.dummies = [x for x in self.homes.keys()
					if x not in (['UNOWNED'] + [self.normPower(y) for y in word[3:]])]
			#	-----------------------------------------------------------
			#	Teams, a way to create dummies controlled by a single power
			#	-----------------------------------------------------------
			elif upword in ('TEAM', 'TEAMS'):
				if len(word) == 1: error += ['%s REQUIRES LIST OF TEAMS']
				else:
					power = None
					teams = word[1:2]
					for team in word[2:]:
						if team.startswith('-') or teams[-1].endswith('-'):
							teams[-1] += team
						else: teams += [team]
					for team in teams:
						members = [self.normPower(x) for x in team.split('-')]
						if [1 for x in members if not x]:
							error += ['TOO MANY HYPHENS IN %s LINE' % upword]
							continue
						if len(members) < 2: continue
						#	-------------------------------------------------
						#	To allow for non-map powers to control dummies,
						#	checking if the leader exists and is not a dummy
						#	is done in Game.validateStatus().
						#	-------------------------------------------------
						leader = members[0]
						for member in members[1:]:
							if member not in self.homes.keys():
								error += ['CONTROLLED POWER %s IS NOT A MAP POWER'
									% member]
								break
						else:
							for member in members[1:]:
								if member not in self.dummies: self.dummies += [member]
								self.controls[member] = [leader]
			elif upword == 'DROP':
				for place in [x.upper() for x in word[1:]]: self.drop(place)
			#	----------------------------------------
			#	Dynamic map instructions to be processed
			#	by the game only in specific game phases
			#	----------------------------------------
			elif len(word) > 1 and upword == 'IN':
				data = [x.strip() for x in ' '.join(word[1:]).split(':')]
				if len(data) != 2: error += ['BAD DYNAMIC MAP INSTRUCTION']
				else: self.dynamic.setdefault(data[0], []).append(data[1])
			#	----------------------------------------
			#	Dynamic map instructions to be processed
			#	by the game only in specific game phases
			#	----------------------------------------
			elif len(word) > 1 and upword == 'IN':
				data = [x.strip() for x in ' '.join(word[1:]).split(':')]
				if len(data) != 2: error += ['BAD DYNAMIC MAP INSTRUCTION']
				else: self.dynamic.setdefault(data[0], []).append(data[1])
			#	------------------------------
			#	Terrain type and adjacencies
			#	(with special adjacency rules)
			#	------------------------------
			elif (len(word) > 1
			and upword in ('AMEND', 'WATER', 'LAND', 'COAST', 'PORT', 'SHUT')):
				place, other = word[1], word[1].swapcase()
				if other in self.locs:
					self.locs.remove(other)
					if upword == 'AMEND':
						self.locType[place] = self.locType[other]
						self.locAbut[place] = self.locAbut[other]
					del self.locType[other]
					del self.locAbut[other]
					if place.isupper(): [self.drop(x, 1) for x in self.locs
						if x.startswith(place + '/')]
				if place in self.locs: self.locs.remove(place)
				self.locs += [place]
				if upword != 'AMEND':
					self.locType[place] = word[0]
					if len(word) > 2: self.locAbut[place] = []
				elif place not in self.locType:
					error += ['NO DATA TO "AMEND" FOR ' + place]
				if len(word) > 2 and word[2].upper() != 'ABUTS':
					error += ['NO "ABUTS" FOR ' + place]
				for dest in word[3:]:
					if dest[0] == '-':
						for site in self.locAbut[place][:]:
							if site.upper().startswith(dest[1:].upper()):
								self.locAbut[place].remove(site)
						for rule, sites in self.abutRules.items():
							for tuple in sites:
								if dest[1:][:3].upper() in tuple:
									self.abutRules[rule].remove(tuple)
									if not self.abutRules[rule]:
										del self.abutRules[rule]
						continue
					rule = []
					#	----------------------------------------------
					#	Check for power restrictions of the form R:AEG
					#	meaning that only a Russian unit abuts AEG.
					#	----------------------------------------------
					if dest.count(':') == 1:
						who, dest = dest.split(':')
						rule = [who.upper() + ':']
					#	---------------------------------------
					#	Check for SC ownership restrictions of
					#	the form AEG(CON) meaning that only the
					#	player owning CON is adjacent to AEG
					#	---------------------------------------
					if dest.count('(') == 1 and dest[-1] == ')':
						dest, need = dest.split('(')
						rule += [need.upper()]
					#	---------------------------------------------
					#	Check for single-character (non-alphanumeric)
					#	special restrictions like CON* or *CON, which
					#	each mean something special.
					#	---------------------------------------------
					while dest and not dest[0].isalnum():
						rule += [dest[0]]
						dest = dest[1:]
					while dest and not dest[-1].isalnum():
						rule += [dest[-1]]
						dest = dest[:-1]
					if not dest:
						error += ['BAD SPECIAL ABUT FOR ' + place]
						break
					#	----------------------------------
					#	Add all the adjacency restrictions
					#	----------------------------------
					for code in rule:
						self.abutRules.setdefault(code, []).append(
							(place.upper(), dest[:3].upper()))
					#	---------------------
					#	Now add the adjacency
					#	---------------------
					self.locAbut[place] += [dest]
			#	----------------------------
			#	Removal of an existing power
			#	----------------------------
			elif upword == 'UNPLAYED':
				goners = []
				if len(word) == 1:
					if not power: error += ['UNPLAYED BEFORE POWER']
					else: goners = [power]
				elif word[1].upper() != 'ALL':
					goners = [self.normPower(x) for x in word[1:]]
				elif len(word) == 2: goners = [x for x in self.homes.keys()
					if x != 'UNOWNED']
				elif word[2].upper() != 'EXCEPT':
					error += ['NO EXCEPT AFTER UNPLAYED ALL']
				elif len(word) == 3:
					error += ['NO POWER AFTER UNPLAYED ALL EXCEPT']
				else: goners = [x for x in self.homes.keys() if x not in (
					['UNOWNED'] + [self.normPower(y) for y in word[3:]])]
				power = None

				for goner in goners:
					try:
						del self.powName[goner]
						del self.ownWord[goner]
						del self.homes[goner]
						self.dummies = [x for x in self.dummies if x != goner]
						self.inhabits = [x for x in self.inhabits if x != goner]
						if goner in self.centers: del self.centers[goner]
						self.owns = [x for x in self.owns if x != goner]
						if goner in self.abbrev: del self.abbrev[goner]
						if goner in self.factory: del self.factory[goner]
						if goner in self.partisan: del self.partisan[goner]
						if goner in self.hidden: del self.hidden[goner]
						if goner in self.alternative: del self.alternative[goner]
						if goner in self.units: del self.units[goner]
						self.powers = [x for x in self.powers if x != goner]
						self.reserves = [x for x in self.reserves if x != goner]
						self.militia = [x for x in self.militia if x != goner]
					except: error += ['NO SUCH POWER TO REMOVE: ' + goner]
				power = None
			#	----------------------
			#	Power name, ownership
			#	word, and home centers
			#	----------------------
			else:
				if upword in ('NEUTRAL', 'CENTERS'): upword = 'UNOWNED'
				power = (0, self.normPower(upword))[upword != 'UNOWNED']
				if len(word) > 2 and word[1] == '->': 
					oldPower = power
					word = word[2:]
					upword = word[0].upper()
					if upword in ('NEUTRAL', 'CENTERS'): upword = 'UNOWNED'
					power = (0, self.normPower(upword))[upword != 'UNOWNED']
					if not oldPower or not power:
						error += ['RENAMING UNOWNED DIRECTIVE NOT ALLOWED']
					elif not self.powName.get(oldPower):
						error += ['RENAMING UNDEFINED POWER ' + oldPower]
					else: self.renamePower(oldPower, power)
				if power and not self.powName.get(power):
					self.powName[power] = upword
					normed = self.norm(power)
					#	---------------------------------------
					#	Add power to aliases even if the normed
					#	form is identical. That way it becomes
					#	part of the vocabulary.
					#	---------------------------------------
					if not normed:
						error += ['POWER NAME IS EMPTY KEYWORD: ' + power]
						normed = power
					if normed not in self.aliases:
						if len(normed.split('/')[0]) in (1, 3):
							error += ['POWER NAME CAN BE CONFUSED WITH ' +
								'LOCATION ALIAS OR ORDER TYPE: ' + normed]
						self.aliases[normed] = power
					elif self.aliases[normed] != power:
						error += ['DUPLICATE POWER OR LOCATION: ' + normed]
				upword = power or upword
				if power and len(word) > 1 and word[1][0] == '(':
					self.ownWord[upword] = word[1][1:-1] or power
					normed = self.norm(self.ownWord[upword])
					if normed == power: pass
					elif normed not in self.aliases: self.aliases[normed] = power
					elif self.aliases[normed] != power:
						error += ['DUPLICATE POWER OR LOCATION: ' + normed]
					if ':' in word[1]:
						owner, abbrev = self.ownWord[upword].split(':')
						self.ownWord[upword] = owner or power
						self.abbrev[upword] = abbrev[:1].upper()
						if not abbrev or self.abbrev[upword] in 'M?':
							error += ['ILLEGAL POWER ABBREVIATION']
					del word[1]
				else: self.ownWord.setdefault(upword, upword)
				reinit = upword in self.inhabits
				if reinit: self.inhabits.remove(upword)
				self.addHomes(upword, word[1:], reinit)
	#	----------------------------------------------------------------------
	def addHomes(self, power, homes, reinit):
		if reinit:
			self.homes[power] = []
			if power in self.partisan: del self.partisan[power]
			if power in self.factory: del self.factory[power]
			if power in self.hidden: del self.hidden[power]
			if power in self.alternative: del self.alternative[power]
		else:
			self.homes.setdefault(power, [])
		for home in ' '.join(homes).upper().split():
			remove = partisan = factory = alternative = hidden = 0
			while home:
				if home[0] == '-': remove = 1
				elif home[0] == '*': partisan = 1
				elif home[0] == '+': factory = 1
				elif home[0] == '~': hidden = 1
				elif home[0] == '@': alternative = 1
				else: break;
				home = home[1:]
			if not home: continue
			if '(' in home and home[-1] == ')':
				idx = home.index('(')
				limits, home = home[idx + 1:-1].split(','), home[:idx]
			else: limits = []
			if not home: continue
			if power in self.alternative.keys():
				self.alternative[power] = [x for x in self.alternative[power]
					if x[0] != home]
			if home in self.hidden.get(power, []):
				self.hidden[power].remove(home)
			if home in self.factory.get(power, []):
				self.factory[power].remove(home)
			elif home in self.partisan.get(power, []):
				self.partisan[power].remove(home)
			else:
				try:
					self.homes[power].remove(home)
					if power != 'UNOWNED':
						self.homes['UNOWNED'].append(home)
				except: pass
			if not remove:
				if alternative:
					self.alternative.setdefault(power, []).append(
						[home] + limits)
				if hidden:
					self.hidden.setdefault(power, []).append(home)
				if partisan:
					self.partisan.setdefault(power, []).append(home)
				elif factory: 
					self.factory.setdefault(power, []).append(home)
				else: self.homes[power].append(home)
	#	----------------------------------------------------------------------
	def rename(self, old, new):
		old = old.upper()
		if old not in self.locName.values():
			return self.error.append('INVALID RENAME LOCATION: ' + `old`)
		[x.pop(y) for x in (self.locName, self.aliases)
			for y,z in x.items() if z == old]
		if old == new: return
		for site in [x for x in self.locs if x.upper() == old]:
			self.locs.remove(site)
			self.locs.append((new.lower(), new)[site == old])
		for data in (self.homes, self.centers,
			self.factory, self.partisan, self.hidden):
			for sites in [x for x in data.values() if old in x]:
				sites.remove(old)
				sites.append(new)
		for alternatives in self.alternative.values():
			for sites in [x for x in alternatives if old in x]:
				sites[sites.index(old)] = new
		for units in self.units.values():
			for unit in [x for x in units if x.endswith(old)]:
				units.remove(unit)
				units.append(unit[:2] + new)
		for data in (self.locAbut, self.locType):
			gone = (old.lower(), old)[old in data]
			data[(new.lower(), new)[old in data]] = data[gone]
			del data[gone]
		for one, two in [(x,y) for z in self.abutRules.values()
						for x,y in z if old in (x.upper(), y.upper())]:
			self.abuts.remove((one, two))
			self.abuts.append((	one == old and new
						or  one == old.lower() and new.lower()
						or  one == old.title() and new.title() or one,
							two == old and new
						or  two == old.lower() and new.lower()
						or  two == old.title() and new.title() or two))
		for sites in self.locAbut.values():
			for attr in ('', '.lower()', '.title()'):
				try:
					sites.remove(eval('old' + attr))
					sites.append(eval('new' + attr))
				except: pass
	#	----------------------------------------------------------------------
	def renamePower(self, old, new):
		self.powName.pop(old, None)
		[x.pop(old, None) for x in (self.ownWord, self.abbrev)]
		[self.aliases.pop(x, None) for x in self.aliases
			if self.aliases[x] == old]
		if old == new: return
		for data in (self.homes, self.units, self.centers,
		self.factory, self.partisan, self.alternative, self.hidden):
			try:
				data[new] = data[old]
				del data[old]
			except: pass
		for data in (self.flag, ):
			try:
				data[new] = data[old]
				del data[old]
			except: data[new] = old
		for data in (self.militia, self.reserves, self.powers, self.dummies):
			try:
				data.remove(old)
				data.append(new)
			except: pass
	#	----------------------------------------------------------------------
	def drop(self, place, deCoast = 0):
		[self.locs.remove(x) for x in self.locs if x.upper().startswith(place)]
		[x.pop(y) for x in (self.locName, self.aliases)
			for y,z in x.items() if z.startswith(place)]
		[x.remove(place) for x in self.homes.values() if place in x]
		[y.remove(x) for y in self.units.values()
					 for x in y if x[2:5] == place[:3]]
		for sites in self.locAbut.values():
			for site in [x for x in sites if x.upper().startswith(place)]:
				sites.remove(site)
				if deCoast and place[:3] not in sites: sites += [place[:3]]
		for rule, abuts in self.abutRules.items():
			for one, two in abuts[:]:
				if (one.upper().startswith(place)
				or	two.upper().startswith(place)): abuts.remove((one, two))
			if not abuts: del self.abutRules[rule]
		[y.pop(x) for y in (self.locType, self.locAbut) for x in y.keys()
			if x.startswith(place) or x.startswith(place.lower())]
	#	----------------------------------------------------------------------
	def normPower(self, power):
		return self.norm(power).replace(' ', '')
	#	----------------------------------------------------------------------
	def norm(self, phrase):
		#	--------------------------------------
		#	Replace commas, pluses and dashes
		#	with spaces; remove dots and colons;
		#	provide spacing in front of slashes
		#	around brackets, asterisks, vertical
		#	bars and other punctuation marks.
		#	--------------------------------------
		phrase = phrase.upper().replace('/', ' /').replace(' / ', '')
		for x in '.:': phrase = phrase.replace(x, '')
		for x in '-+,': phrase = phrase.replace(x, ' ')
		for x in '/': phrase = phrase
		for x in '|*?!~()[]=_^': phrase = phrase.replace(x, ' ' + x + ' ')
		#	--------------------------------------------
		#	Replace keywords which, contrary to aliases,
		#	all consist of a single word
		#	--------------------------------------------
		return ' '.join(
			[self.keywords.get(x, x) for x in phrase.strip().split()])
	#	----------------------------------------------------------------------
	def compact(self, phrase):
		word, result = self.norm(phrase).split(), []
		while word:
			alias, i = self.alias(word)
			if alias: result += alias.split()
			word = word[i:]
		return result
	#	----------------------------------------------------------------------
	def alias(self, word):
		#	------------------------------------------------
		#	Assume that word already was subjected to norm()
		#	------------------------------------------------
		alias = word[0]
		if alias in '([':
			for j in range(1, len(word)):
				if word[j] == '])'[alias == '(']: break
			else: return alias, 1
			if j == 1: return '', 2
			if word[1] + word[j-1] == '**':
				word2 = word[2:j-1]
			else:
				word2 = word[1:j]
				alias2 = self.aliases.get(' '.join(word2) + ' \\', '')
				if alias2[-2:] == ' \\': return alias2[:-2], j+1
			result = []
			while word2:
				alias2, i = self.alias(word2)
				if alias2: result += [alias2]
				word2 = word2[i:]
			return ' '.join(result), j+1
		for i in range(len(word), 0, -1):
			key = ' '.join(word[:i])
			if key in self.aliases:
				alias = self.aliases[key]
				break
		else: i = 1
		#	------------------
		#	Concatenate coasts
		#	------------------
		if i == len(word): return alias, i
		if alias[:1] != '/' and ' ' not in alias:
			alias2, j = self.alias(word[i:])
			if alias2[:1] != '/' or ' ' in alias2: return alias, i
		elif alias[-2:] == ' \\':
			alias2, j = self.alias(word[i:])
			if alias2[:1] == '/' or ' ' in alias2: return alias, i
			alias, alias2 = alias2, alias[:-2]
		else: return alias, i
		#	---------------------------------------------
		#	Check if the location is also an ambiguous
		#	power name and replace with its alternative
		#	if that's the case
		#	---------------------------------------------
		if alias in self.powers and alias in self.unclear:
			alias = self.unclear[alias]
		#	---------------------------------------------
		#	Check if the coast is mapped to another coast
		#	---------------------------------------------
		if alias + ' ' + alias2 in self.aliases:
			return self.aliases[alias + ' ' + alias2], i + j
		return alias + alias2, i + j
	#	----------------------------------------------------------------------
	def vet(self, word, strict=0):
		#	---------------------------------------------------------
		#	Determines type of every word in a compacted order phrase
		#	0: Undetermined
		#	1: Power
		#	2: Unit
		#	3: Location
		#	4: Coastal location
		#	5: Order
		#	6: Move separator (-=_^)
		#	7: Non-move separator (|\?~) or result (*!?~+)
		#	Separators are between other types of words, results
		#	are at the end (or the start?)
		#	Strict means verifying that the words actually exist,
		#	instead of merely resembling a certain type
		#	If they don't exist, the numbers become negative
		#	---------------------------------------------------------
		result = []
		for thing in word:
			if ' ' in thing: type = 0
			elif len(thing) == 1:
				if thing in self.unitNames: type = 2
				elif thing.isalnum(): type = 5
				elif thing in '-=_': type = 6
				else: type = 7
			elif '/' in thing:
				if thing.find('/') == 3: type = 4
				else: type = 1
			elif len(thing) == 3: type = 3
			else: type = 1
			if strict and thing not in (self.aliases.values() +
				self.keywords.values()): type = -type
			result += [(thing, type)]
		return result
	#	----------------------------------------------------------------------
	def rearrange(self, word):
		#	--------------------------------------------------
		#	Surround with vertical bars to simplify edge cases
		#	--------------------------------------------------
		result = self.vet(['|'] + word + ['|'])
		#	------------------------------------------
		#	Remove result tokens at the start and end,
		#	as they are similar to separators, which
		#	might generate confusion
		#	------------------------------------------
		result[0] = ('|', 0)
		while result[-2][1] == 7: del result[-2]
		if len(result) == 2: return []
		result[0] = ('|', 7)
		while result[1][1] == 7: del result[1]
		#	------------------------------------------
		#	Move "with" unit and location to the start
		#	There should only be one, ignore the rest
		#	------------------------------------------
		found = 0
		while ('?', 7) in result:
			i = result.index(('?', 7))
			del result[i]
			if found: continue
			for j in range(i, len(result)):
				if result[j][1] in (1, 2): continue
				if result[j][1] in (3, 4): j += 1
				break
			if j != i:
				found = 1
				for k in range(1, i):
					if result[k][1] not in (1, 2): break
				if k < i:
					result[k:k] = result[i:j]
					result[j:2*j-i] = []
		#	----------------------------------------------------
		#	Move "from" location before any preceding locations.
		#	----------------------------------------------------
		while ('\\', 7) in result:
			i = result.index(('\\', 7))
			del result[i]
			if result[i][1] not in (3, 4): continue
			for j in range(i-1, -1, -1):
				if result[j][1] not in (3, 4) and result[j][0] != '~': break
			if j+1 != i:
				result[j+1:j+1] = result[i:i+1]
				del result[i+1]
		#	---------------------------------------------------------
		#	Move "via" locations between the two preceding locations.
		#	---------------------------------------------------------
		while ('~', 7) in result:
			i = result.index(('~', 7))
			del result[i]
			if (result[i][1] not in (3, 4) or result[i-1][1] not in (3, 4)
			or result[i-2][1] not in (3, 4)): continue
			for j in range(i+1, len(result)):
				if result[j][1] not in (3, 4): break
			result[j:j] = result[i-1:i]
			del result[i-1]
		#	---------------------------------
		#	Move order beyond first location.
		#	---------------------------------
		i = 0
		for j in range(1, len(result)):
			if result[j][1] in (3, 4):
				if i:
					result[j+1:j+1] = result[i:i+1]
					del result[i]
				break
			elif result[j][1] == 5: i = j
			elif result[j][0] == '|': break
		#	--------------------------------------------
		#	Put the power before the unit, or replace it
		#	with a location if there's ambiguity.
		#	--------------------------------------------
		vet = 0
		for i in range(0, len(result)):
			if result[i][1] == 1:
				if vet > 0 and result[i][0] in self.unclear:
					result[i] = (self.unclear[result[i][0]], 3)
				elif vet == 1:
					result[i+1:i+1] = result[i-1:i]
					del result[i-1]
				vet = 2
			elif not vet and result[i][1] == 2: vet = 1
			elif result[i][1] == 5: vet = 0
			else: vet = 2
		#	--------------------------------------------
		#	Insert hyphens between subsequent locations.
		#	--------------------------------------------
		for i in range(len(result)-1, 1, -1):
			if result[i][1] in (3, 4) and result[i-1][1] in (3, 4):
				result[i:i] = [('-', 6)]
		#	--------------------------------------
		#	Remove vertical bars at start and end.
		#	--------------------------------------
		return [x for x, y in result[1:-1]]
	#	----------------------------------------------------------------------
	def areatype(self, loc):
		return self.locType.get(loc.upper()) or self.locType.get(loc.lower())
	#	----------------------------------------------------------------------
	def defaultCoast(self, word):
		#	----------------------------------------
		#	Returns the coast for a fleet move order
		#	that can only be to a single coast.  For
		#	example, F GRE-BUL returns F GRE-BUL/SC
		#	----------------------------------------
		if len(word) == 4 and word[0] + word[2] == 'F-' and '/' not in word[3]:
			unitLoc, newLoc, singleCoast = word[1], word[3], None
			for place in self.abutList(unitLoc):
				upPlace = place.upper()
				if newLoc == upPlace: break
				if newLoc == upPlace[:3]:
					if singleCoast: break
					singleCoast = upPlace
			else: word[3] = singleCoast or newLoc
		return word
	#	----------------------------------------------------------------------
	def abuts(self, unitType, unitLoc, orderType, otherLoc):
		#	----------------------------------------
		#	If looking at adjacencies for support,
		#	remove any coast to check the adjacency.
		#	Armies cannot otherwise affect a coast.
		#	----------------------------------------
		unitLoc, otherLoc = unitLoc.upper(), otherLoc.upper()
		if '/' in otherLoc:
			if orderType == 'S': otherLoc = otherLoc[:3]
			elif unitType == 'A': return
		#	------------------------------
		#	See if the list of adjacencies
		#	works from unitLoc to otherLoc
		#	------------------------------
		for place in self.abutList(unitLoc):
			upPlace = place.upper()
			locale = upPlace[:3]
			if otherLoc in (upPlace, locale): break
		else: return
		#	------------------------------------
		#	Okay, the place is adjacent ... but
		#	see what terrain type is at otherLoc
		#	------------------------------------
		otherLocType = self.areatype(otherLoc)
		if otherLocType == 'SHUT': return
		#	---------------------------------
		#	If the unit type is unknown, then
		#	assume that the adjacency is okay
		#	---------------------------------
		if unitType == '?': return 1
		#	--------------------------------------------
		#	Fleets cannot affect LAND and fleets are not
		#	adjacent to any location listed in lowercase
		#	(except when offering support into such an
		#	area, as in F BOT S A MOS-STP), or listed in
		#	the adjacency list in lower-case (F VEN-TUS)
		#	--------------------------------------------
		if unitType == 'F':
			if (otherLocType == 'LAND' or place[0] != locale[0]
			or orderType != 'S' and otherLoc not in self.locType): return
		#	------------------------------------------------------
		#	Armies cannot move to water (unless this is a convoy).
		#	Note that the caller is responsible for determining if
		#	a fleet exists at the adjacent spot to convoy the army
		#	Also, armies can't move to spaces listed in Mixed case
		#	------------------------------------------------------
		elif orderType != 'C' and (otherLocType == 'WATER'
		or place == place.title()): return
		#	--------------------------
		#	Good news.  It's adjacent.
		#	--------------------------
		return 1
	#	----------------------------------------------------------------------
	def isValidUnit(self, unit, noCoastOK = 0, shutOK = 0):
		unit, locale = unit.upper().split()
		type = self.areatype(locale)
		if unit == '?': return not not type
		if shutOK and type == 'SHUT': return 1
		if unit == 'A': return ('/' not in locale
			and type in ('LAND', 'COAST', 'PORT'))
		return (unit == 'F' and type in ('WATER', 'COAST', 'PORT')
			and (noCoastOK or locale.lower() not in self.locAbut))
	#	----------------------------------------------------------------------
	def parseAlias(self, words):
		result = []
		del words[:words[0] == 'THE']
		for word in words:
			if word[-1] in ',.': word = word[:-1]
			if (word in ('->', 'NO', 'SUPPORT', 'HOLD',
						 'CONVOY', 'DISBAND', 'WITH')
			or len(word) > 1 and word[1] == '*'): break
			result += [word]
		return self.locName.get(' '.join(result))
	#	----------------------------------------------------------------------
	def abutList(self, site):
		return self.locAbut.get(site, self.locAbut.get(site.lower(), []))
	#	----------------------------------------------------------------------
	def findNextPhase(self, phase, phaseType = None, skip = 0):
		now = phase.split()
		if len(now) < 3: return phase
		year = int(now[1])
		which = ((self.seq.index(now[0] + ' ' + now[2]) + 1) %
			len(self.seq))
		n = len(self.seq)
		while n:
			n -= 1
			new = self.seq[which].split()
			if new[0] == 'IFYEARDIV':
				if '=' in new[1]: div, mod = map(int, new[1].split('='))
				else: div, mod = int(new[1]), 0
				if year % div != mod: which = -1
			elif new[0] == 'NEWYEAR': year += len(new) == 1 or int(new[1])
			elif phaseType in (None, new[1][0]):
				if skip == 0: return ' '.join([new[0], `year`, new[1]])
				skip -= 1
				n = len(self.seq)
			which += 1
			which %= len(self.seq)
	#	----------------------------------------------------------------------
	def findPreviousPhase(self, phase, phaseType = None, skip = 0):
		now = phase.split()
		if len(now) < 3: return phase
		year = int(now[1])
		which = self.seq.index(now[0] + ' ' + now[2])
		n = len(self.seq)
		while n:
			n -= 1
			which -= 1
			if which == -1:
				for new in [x.split() for x in self.seq]:
					if new[0] == 'IFYEARDIV':
						if '=' in new[1]: div, mod = map(int, new[1].split('='))
						else: div, mod = int(new[1]), 0
						if year % div != mod: break
					which += 1
			new = self.seq[which].split()
			if new[0] == 'IFYEARDIV': pass
			elif new[0] == 'NEWYEAR': year -= len(new) == 1 or int(new[1])
			elif phaseType in (None, new[1][0]):
				if skip == 0: return ' '.join([new[0], `year`, new[1]])
				skip -= 1
				n = len(self.seq)
	#	----------------------------------------------------------------------
	def comparePhases(self, phase1, phase2):
		if len(phase1.split()) == 1:
			phase1 = self.phaseLong(phase1, phase1.upper())
		if len(phase2.split()) == 1:
			phase2 = self.phaseLong(phase2, phase2.upper())
		if phase1 == phase2: return 0
		now1, now2 = phase1.split(), phase2.split()
		if len(now1) < 3 or len(now2) < 3: 
			order1 = (len(now1) > 2 and 2 or phase1 == 'FORMING' and 1 or
				phase1 == 'COMPLETED' and 3 or 0)
			order2 = (len(now2) > 2 and 2 or phase2 == 'FORMING' and 1 or
				phase2 == 'COMPLETED' and 3 or 0)
			return order1 > order2 and 1 or order1 < order2 and -1 or 0
		year1, year2 = int(now1[1]), int(now2[1])
		if year1 != year2:
			return (year1 > year2 and 1 or -1) * (self.flowSign or 1)
		which1, which2 = (self.seq.index(now1[0] + ' ' + now1[2]), 
			self.seq.index(now2[0] + ' ' + now2[2]))
		if which1 > which2:
			return ('NEWYEAR' in [x.split()[0] 
				for x in self.seq[which2 + 1:which1]]) and -1 or 1
		elif which1 < which2:
			return ('NEWYEAR' in [x.split()[0] 
				for x in self.seq[which1 + 1:which2]]) and 1 or -1
		else: return 0
	#	----------------------------------------------------------------------
	def phaseAbbr(self, phase, default = '?????'):
		#	------------------------------------------
		#	Returns S1901M from "SPRING 1901 MOVEMENT"
		#	------------------------------------------
		try: return '%.1s%s%.1s' % tuple(phase.split()[:3])
		except: return default
	#	----------------------------------------------------------------------
	def phaseLong(self, phaseAbbr, default = '?????'):
		#	------------------------------------------
		#	Returns "SPRING 1901 MOVEMENT" from S1901M
		#	------------------------------------------
		try: 
			year = int(phaseAbbr[1:-1])
			return [' '.join([new[0], `year`, new[1]]) for new in 
				[x.split() for x in self.seq] 
				if new[0] not in ('NEWYEAR', 'IFYEARDIV') 
				and new[0][0] == phaseAbbr[0] and new[1][0] == phaseAbbr[-1]][0]
		except: return default
	#	----------------------------------------------------------------------

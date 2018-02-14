# -*- coding: utf-8 -*-

from unicodedata import normalize

class Lang:
	#	----------------------------------------------------------------------
	def __init__(self, name, parent = None):
		self.name, self.error = name, []
		self.units, self.coasts = {}, {}
		self.keywords, self.keycombos = {}, {}
		self.maxKeywords = self.maxKeycombos = 0
		self.aliases, self.nicks = {}, {}
		self.maxAliases = self.maxNicks = 0
		self.unclear = {}
		self.reinit()
		if parent: self.inherit(parent)
	#	----------------------------------------------------------------------
	def reinit(self):
		self.keywords.update({
			'M': '-',		'NMR': '*',
		})
		self.keycombos.update({
			'- >': '-',		'= >': '=',		'< -': '<',		'< =': '<',
			'& &': '&',		'| |': '|',		'& |': '|',		'| &': '|',
			'~ C': '^',		'~ =': '=',		'? =': '=',
			'V B': 'B V',
		})
		self.error = []
		for x, y in self.units.iteritems():
			self.keywords[self.normAlias(y)] = x
		for x, y in self.coasts.iteritems():
			self.keywords[self.normAlias(y)] = '/' + x
			self.keywords[x] = '/' + x
		self.maxKeywords = max([len(x.split()) for x in self.keywords])
		self.maxKeycombos = max([len(x.split()) for x in self.keycombos])
	#	----------------------------------------------------------------------
	def inherit(self, lang):
		self.error += lang.error[:]
		[x.setdefault(z, w) for x, y in [(self.aliases, lang.aliases),
			(self.nicks, lang.nicks), (self.unclear, lang.unclear)]
			for z, w in y.items()]
		self.maxAliases = max([len(x.split()) for x in self.aliases])
		self.maxNicks = max([len(x.split()) for x in self.nicks])
	#	----------------------------------------------------------------------
	def scan(self, words, terms, maxTerms):
		if not words: return []
		for i in range(min(maxTerms, len(words)), 0, -1):
			key = ' '.join(words[:i])
			if key in terms:
				alias = terms[key].split()
				break
		else: alias, i = words[:1], 1
		return alias + self.scan(words[i:], terms, maxTerms)
	#	----------------------------------------------------------------------
	def norm(self, phrase):
		#	---------------------------------------------
		#	Uppercase the phrase;
		#	Provide spacing around or in front of various
		#	punctuation marks and remove some of them
		#	---------------------------------------------
		phrase = phrase.upper().replace('/', ' /')
		while '/ ' in phrase: phrase = phrase.replace('/ ', '/')
		for x in '"': phrase = phrase.replace(x, '')
		for x in ',;': phrase = phrase.replace(x, '&')
		for x in '.|&%$@#*:?!~()[]<>+-=_^\\\'':
			phrase = phrase.replace(x, ' ' + x + ' ')
		return phrase
	#	----------------------------------------------------------------------
	def normAlias(self, alias):
		#	-----------------------------------------
		#	Replace pluses with spaces before norming
		#	-----------------------------------------
		if '%' in alias: return self.error.append(
			'INVALID COMMENT CHARACTER IN ALIAS: ' + alias)
		words = self.norm(alias.replace('+', ' ')).replace(' /',
			'/').strip().split()
		#	----------------
		#	Replace keywords
		#	----------------
		if ' '.join(words) in self.keywords: return self.error.append(
			'ALIAS MATCHES EXISTING KEYWORD: ' + alias)
		words = self.scan(words, self.keywords, self.maxKeywords)
		if ' '.join(words) in self.keycombos: return self.error.append(
			'ALIAS MATCHES EXISTING KEYCOMBO: ' + alias)
		words = self.scan(words, self.keycombos, self.maxKeycombos)
		if not words: return self.error.append(
			'EMPTY ALIAS: ' + alias)
		if words[0][0] in '&|-\\/<?~': return self.error.append(
			'BAD FIRST PART OF ALIAS: ' + alias)
		if words[-1] in ':': return self.error.append(
			'BAD LAST PART OF ALIAS: ' + alias)
		return ' '.join(words)
	#	----------------------------------------------------------------------
	def normNick(self, nick):
		normed = self.normAlias(nick)
		if normed is not None: return normed
		self.error[-1] = self.error[-1].replace('ALIAS', 'NICK', 1)
	#	----------------------------------------------------------------------
	def normPower(self, power):
		normed = self.normNick(power)
		if normed is None: return
		normed = normed.replace(' ', '').replace('-', '').replace('.', '')
		if normed: return normed
		self.error += ['BAD POWER NAME: ' + power]
	#	----------------------------------------------------------------------
	def addAlias(self, alias, loc):
		if loc not in self.aliases.values():
			if loc in self.aliases: return self.error.append(
				'LOCATION ABBREVIATION MATCHES OTHER ALIAS: ' + loc)
			normed = self.normAlias(loc)
			if not normed: return
			elif normed != loc: return self.error.append(
				'INVALID LOCATION ABBREVIATION: ' + loc)
		#   --------------------------------
		#   For ambiguous place names, let's
		#   do just a minimal normalization,
		#   otherwise they might become
		#   unrecognizable (e.g. "THE")
		#   --------------------------------
		if alias[-1] == '?':
			self.unclear[alias[:-1].replace('+', ' ').upper()] = loc
			return
		normed = self.normAlias(alias)
		if not normed: return
		if normed in self.aliases: return self.error.append(
			'DUPLICATE MAP ALIAS: ' + alias)
		elif normed != loc and normed in self.aliases.values():
			return self.error.append(
				'ALIAS MATCHES OTHER LOCATION ABBREVIATION: ' + alias)
		self.aliases[normed] = loc
		self.maxAliases = max(self.maxAliases, len(normed.split()))
		#   -------------------------------
		#   If it contains hyphens or dots,
		#	add another entry without those
		#   -------------------------------
		if '.' in normed or '-' in normed:
			normed = (' ' + normed).replace(' .', '').replace(' -', '')[1:]
			if normed in self.aliases: return self.error.append(
				'DUPLICATE MAP ALIAS: ' + alias)
			elif normed != loc and normed in self.aliases.values():
				return self.error.append(
					'ALIAS MATCHES OTHER LOCATION ABBREVIATION: ' + alias)
			self.aliases[normed] = loc
	#	----------------------------------------------------------------------
	def addNick(self, nick, power):
		if power not in self.nicks.values():
			if power in self.nicks: return self.error.append(
				'POWER NAME MATCHES OTHER NICK: ' + power)
			normed = self.normNick(power)
			if not normed: return
			elif normed != power: return self.error.append(
				'INVALID POWER NAME: ' + power)
			if '/' in normed: return self.error.append(
				'POWER NAME CONTAINS "/": ' + power)
			elif len(normed) == 1: return self.error.append(
				'POWER NAME CAN BE CONFUSED WITH ' +
				'ORDER TYPE OR UNIT TYPE: ' + normed)
		normed = self.normNick(nick)
		if not normed: return
		if normed in self.nicks: return self.error.append(
			'DUPLICATE POWER NICKNAME: ' + nick)
		elif normed != power and normed in self.nicks.values():
			return self.error.append(
				'NICK MATCHES OTHER POWER NAME: ' + nick)
		self.nicks[normed] = power
		self.maxNicks = max(self.maxNicks, len(normed.split()))
		#   -------------------------------
		#   If it contains hyphens or dots,
		#	add another entry without those
		#   -------------------------------
		if '.' in normed or '-' in normed:
			normed = (' ' + normed).replace(' .', '').replace(' -', '')[1:]
			if not normed: return self.error.append(
				'BAD POWER NICKNAME: ' + nick)
			elif normed in self.nicks: return self.error.append(
				'DUPLICATE POWER NICKNAME: ' + nick)
			elif normed != power and normed in self.nicks.values():
				return self.error.append(
					'NICK MATCHES OTHER POWER NAME: ' + nick)
			self.nicks[normed] = power
		#   ----------------------
		#   Do the same for spaces
		#   ----------------------
		if ' ' in normed:
			normed = normed.replace(' ', '')
			if normed in self.nicks: return self.error.append(
				'DUPLICATE POWER NICKNAME: ' + nick)
			elif normed != power and normed in self.nicks.values():
				return self.error.append(
					'NICK MATCHES OTHER POWER NAME: ' + nick)
			self.nicks[normed] = power
	#	----------------------------------------------------------------------
	def removeAliases(self, loc):
		[x.pop(y) for x in [self.aliases, self.unclear]
			for y, z in x.items() if z == loc]
		self.maxAliases = max([len(x.split()) for x in self.aliases])
	#	----------------------------------------------------------------------
	def removeNicks(self, power):
		[x.pop(y) for x in [self.nicks]
			for y, z in x.items() if z == power]
		self.maxNicks = max([len(x.split()) for x in self.nicks])
	#	----------------------------------------------------------------------
	def parseNick(self, words):
		nick = ' '.join(words)
		if nick in self.nicks: return '[' + self.nicks[nick] + ']'
		elif len(words) == 1 and nick in self.nicks.values():
			return '[' + nick + ']'
	#	----------------------------------------------------------------------
	def parseAlias(self, words):
		#	------------------------------------------------
		#	Assume that words already was subjected to norm()
		#	------------------------------------------------
		alias = words[0]
		if alias in '([':
			for j in range(1, len(words)):
				if words[j] == '])'[alias == '(']: break
			else: return alias, 1
			if j == 1: return '', 2
			if j > 2 and words[1] + words[j-1] == '**':
				word2 = words[2:j-1]
			elif j == 2 and words[1][0] == '/': return words[1], 3
			else:
				word2 = words[1:j]
				power = self.parseNick(word2)
				if power: return power, j+1
			result = []
			while word2:
				alias2, i = self.parseAlias(word2)
				if alias2: result += [alias2]
				word2 = word2[i:]
			return ' '.join(result), j+1
		#	------------------------------------------
		#	Find the longest stretch that has an alias
		#	------------------------------------------
		for i in range(min(len(words),
			max(self.maxAliases, self.maxNicks + 1)), 0, -1):
			if words[i-1] == ':':
				if i == 1: return '', 1
				power = self.parseNick(words[:i-1])
				if power: return power, i
				key = ' '.join(words[:i-1])
				if key in self.aliases:
					alias = self.aliases[key]
					break
			else:
				key = ' '.join(words[:i])
				if key in self.aliases:
					alias = self.aliases[key]
					break
				elif i == 1 and (len(key) == 1 or key in self.aliases.values()
				or key in self.keywords.values()): pass
				else:
					power = self.parseNick(words[:i])
					if power: return power, i
		else: i = 1
		return alias, i
	#	----------------------------------------------------------------------
	def distribute(self, power, orders):
		powers, distributor = [power], {}
		blocker = power
		for order in orders:
			vets = self.compact(order)
			if not vets: continue
			pets, start, liner, loner = [], 1, blocker, 1
			for vet in vets + ['S&']:
				if vet != 'S&':
					if start:
						start = 0
						if vet[0] == 'P':
							liner = who = vet[2:-1]
							if who not in powers: powers += [who]
							continue
						who, loner = liner, 0
					pets += [vet]
				else:
					start = 1
					if not pets: continue
					if pets[0][0] not in 'RFS': loner = 0
					#	----------------------------------------------
					#	Ignore any comment after a power, as these get
					#	automatically appended to display some status
					#	info to the Master, e.g. a power's treasury
					#	----------------------------------------------
					if loner and pets[0] == 'S%': pass
					elif pets[0][1] == '*' and (len(pets) == 1
					or pets[1][0] in 'RSF'):
						distributor[who] = []
					else:
						distributor.setdefault(who, []).append(self.unvet(pets))
					pets = []
			if loner: blocker = liner
		return [(x, distributor[x]) for x in powers if x in distributor]
	#	----------------------------------------------------------------------
	def compact(self, phrase):
		if '%' in phrase:
			order, comment = phrase.split('%', 1)
		else: order, comment = phrase, None
		words, result = self.norm(order).split(), []
		words = self.scan(words, self.keywords, self.maxKeywords)
		words = self.scan(words, self.keycombos, self.maxKeycombos)
		if words:
			if len(words) > 1 or len(words[0]) > 1:
				power = self.parseNick(words)
				if power: result = [power]
			if not result:
				while words:
					alias, i = self.parseAlias(words)
					if alias: result += alias.split()
					words = words[i:]
		if comment: result += ['%', comment.strip()]
		return self.rearrange(self.vet(result))
	#	----------------------------------------------------------------------
	def vet(self, words, strict=0):
		#	---------------------------------------------------------
		#	Determines type of every word in a compacted order phrase
		#	P: Power
		#	A: Betting amount
		#	B: Betting operator (!:>@*#+)
		#	U: Unit
		#	L: Location
		#	C: Coastal location
		#	O: Order
		#	M: Move separator (-=_^)
		#	R: Result (.!*|~?+)
		#	S: Non-move separator (|&%\<?~)
		#	K: Comment
		#	F: Phase
		#	Separators are between other types of words
		#	Given the overlap between operators, separators and
		#	results, those near the end need to be reevaluated
		#	Strict means verifying that the words actually exist,
		#	instead of merely resembling a certain type
		#	If they don't exist, the characters are lowercased
		#	---------------------------------------------------------
		result, comment = [], 0
		for thing in words:
			if comment: type = 'K'
			elif thing == '%':
				type, comment = 'S', len(result) + 1
			elif thing.isdigit(): type = 'A'
			elif len(thing) == 1:
				if thing in self.units: type = 'U'
				elif thing.isalpha(): type = 'O'
				elif thing in '|&\\<?~': type = 'S'
				elif thing in '-=_^': type = 'M'
				elif thing in '$!:>@*#+': type = 'B'
				else: type = 'R'
			elif thing[0] + thing[-1] in ('[]', '()'): type = 'P'
			elif (thing[0] + thing[-1]).isalpha() and thing[1:-1].isdigit():
				type = 'F'
			elif '/' in thing: type = 'C'
			else: type = 'L'
			if strict and (type in 'LC' and thing not in self.aliases.values()
			or type == 'P' and thing[1:-1] not in self.nicks.values()
			or type == 'O' and thing not in 'HSCDRBVPK'):
				type = type.lower()
			result += [type + thing]
		#	----------------------------------------
		#	Reevaluate separators near the end of
		#	each branch as results and validate them
		#	----------------------------------------
		end = 1
		for i in range(len(result)-1, 0, -1):
			if not end:
				end = result[i] in ('S&', 'S|', 'S%')
			elif result[i] in ('S&', 'S%'): pass
			elif result[i][0] in 'KF': pass
			elif result[i][0] not in 'SBR': end = 0
			elif result[i][0] == 'B' and result[i-1][0] == 'A': end = 0
			elif strict and result[i][1] not in '.!*|~?+':
				result[i] = 'r' + result[i][1]
			else: result[i] = 'R' + result[i][1]
		return result
	#	----------------------------------------------------------------------
	def unvet(self, vets):
		return ' '.join([x[1:] for x in vets])
	#	----------------------------------------------------------------------
	def revet(self, vets, strict = 1):
		return self.vet([x[1:] for x in vets], strict)
	#	----------------------------------------------------------------------
	def rearrange(self, vets):
		#	--------------------------------------------------
		#	Surround with ampersands to simplify edge cases
		#	--------------------------------------------------
		vets = ['S&'] + vets + ['S&']
		#	--------------------------------
		#	Swap words before and after "of"
		#	--------------------------------
		while 'S\\' in vets:
			i = vets.index('S\\')
			del vets[i]
			if vets[i-1][0] in 'PULC' and vets[i][1] in 'PULC':
				vets[i-1:i+1] = [vets[i], vets[i-1]]
		#	---------------------------------------
		#	Concatenate coasts with their territory
		#	and negative signs with numbers
		#	---------------------------------------
		for i in range(len(vets)-2, 1, -1):
			if vets[i][:2] == 'C/':
				if vets[i-1][0] == 'L':
					vets[i-1] = 'C' + vets[i-1][1:] + vets[i][1:]
					del vets[i]
			elif vets[i][0] == 'A':
				if vets[i-1] == 'M-':
					vets[i-1] = 'A-' + vets[i][1:]
					del vets[i]
		#	----------------------------------------
		#	Replace every ">" that is preceded by a
		#	territory (so it's not a bet) with a "-"
		#	----------------------------------------
		for i in range(2, len(vets)-1):
			if vets[i] == 'B>' and vets[i-1][0] in 'LC': vets[i] = 'M-'
		#	--------------------------------------
		#	Remove every "and" or "or" in front of
		#	a result or other "and" or "or"
		#	--------------------------------------
		for i in range(len(vets)-2, 0, -1):
			if vets[i][0] == 'S' and vets[i+1][0] in 'RS':
				del vets[i]
		#	--------------------------------------
		#	Remove every "and" that is followed by
		#	a single territory
		#	--------------------------------------
		for i in range(len(vets)-2, 0, -1):
			if vets[i] == 'S&' and vets[i+1][0] in 'LC' and (
				vets[i+2][0] == 'S' or
				vets[i+2][0] == 'M' and vets[i+3][0] == 'S'):
				del vets[i]
		#	---------------------------------------------
		#	Remove every move operator, but keep track of
		#	the primary type per "and" and "or" phrase
		#	---------------------------------------------
		move, moves = '-', []
		for i in range(len(vets)-2, -1, -1):
			if vets[i][0] == 'M':
				if move == '=': pass
				elif vets[i][1] == '=': move = '='
				elif vets[i][1] != '-': move = vets[i][1]
				del vets[i]
			elif vets[i] in ('S|', 'S&'):
				moves += [move]
				move = '-'
		#	-------------------------------------------------
		#	Move every bet to the front of each "and" branch, 
		#	preceded only by the power if already in place
		#	-------------------------------------------------
		j, k = 0, 1
		for i in range(1, len(vets)-1):
			if vets[i][0] in 'AB':
				if i > k:
					vets[k:i+1] = vets[i:i+1] + vets[k:i]
				k = k+1
			elif vets[i] == 'S&' or vets[i][0] == 'P' and i == j+1:
				j, k = i, i+1
		#	-------------------------------------
		#	Insert a colon if a bet amount is not
		#	followed by an operator
		#	Remove if it concerns waived builds
		#	-------------------------------------
		for i in range(len(vets)-2, 0, -1):
			if vets[i][0] == 'A':
				if vets[i+1] in ('OB', 'OV'):
					del vets[i]
				elif vets[i+1][0] != 'B':
					vets[i+1:i+1] = ['B:']
		#	------------------------------------------
		#	Move every phase to the end, followed only
		#	by a comment if present
		#	------------------------------------------
		j, k = len(vets)-1, len(vets)-2
		for i in range(len(vets)-2, 0, -1):
			if vets[i][0] == 'F':
				if i < k:
					vets[i:k+1] = vets[i+1:k+1] + vets[i:i+1] 
				k = k-1
			elif vets[i] == 'S%':
				j, k = i, i-1
		#	------------------------------------------
		#	Move "with" unit and location to the start
		#	There should only be one per "and" phrase,
		#	ignore the rest
		#	------------------------------------------
		found = 0
		while 'S?' in vets:
			i = vets.index('S?')
			del vets[i]
			if 'S&' not in vets[found:i]: continue
			for j in range(i, len(vets)):
				if vets[j][0] in 'PU': continue
				if vets[j][0] in 'LC': j += 1
				break
			if j != i:
				while 'S&' in vets[found+1:i]:
					found = vets.index('S&', found+1)
				for k in range(found+1, i):
					if vets[k][0] not in 'PU': break
				if k < i:
					vets[k:k] = vets[i:j]
					vets[j:2*j-i] = []
				found = i
		#	---------------------------------------------------
		#	Move "from" location before any preceding locations
		#	---------------------------------------------------
		while 'S<' in vets:
			i = vets.index('S<')
			del vets[i]
			if vets[i][0] not in 'LC': continue
			for j in range(i-1, -1, -1):
				if vets[j][0] not in 'LC' and vets[j] != 'S~': break
			if j+1 != i:
				vets[j+1:j+1] = vets[i:i+1]
				del vets[i+1]
		#	--------------------------------------------------------
		#	Move "via" locations between the two preceding locations
		#	--------------------------------------------------------
		while 'S~' in vets:
			i = vets.index('S~')
			del vets[i]
			if (vets[i][0] not in 'LC' or vets[i-1][0] not in 'LC'
			or vets[i-2][0] not in 'LC'): continue
			for j in range(i+1, len(vets)):
				if vets[j][0] not in 'LC': break
			vets[j:j] = vets[i-1:i]
			del vets[i-1]
		#	--------------------------------
		#	Move order beyond first location
		#	--------------------------------
		i = 0
		for j in range(1, len(vets)):
			if vets[j][0] in 'LC':
				if i:
					vets[j+1:j+1] = vets[i:i+1]
					del vets[i]
				break
			elif vets[j][0] == 'O': i = j
			elif vets[j] in ('S|', 'S&'): break
		#	-----------------------------------------
		#	Put the power before the unit and the bet
		#	-----------------------------------------
		j = 0
		for i in range(1, len(vets)-1):
			if vets[i][0] == 'P':
				if j > 0:
					vets[j:i+1] = vets[i:i+1] + vets[j:i]
				j = -1
			elif not j and vets[i][0] in 'UAB': j = i
			elif vets[i][0] in 'OS': j = 0
			else: j = -1
		#	----------------------------------------
		#	Insert the primary move operator between
		#	subsequent locations
		#	----------------------------------------
		for i in range(len(vets)-2, 1, -1):
			if vets[i][0] in 'LC' and (vets[i-1][0] in 'LC'
			or vets[i-1] == 'S|'):
				vets[i:i] = ['M' + moves[0]]
			elif vets[i] in ('S|', 'S&'):
				moves = moves[1:]
		#	----------------------------------
		#	Remove ampersands at start and end
		#	----------------------------------
		return vets[1:-1]

class EnglishLang(Lang):
	#	----------------------------------------------------------------------
	def __init__(self, name = 'English'):
		Lang.__init__(self, name)
	#	----------------------------------------------------------------------
	def reinit(self):
		#	-------------------------------------------------------------
		#	Define the standard names for units and coasts. These will be
		#	automatically added to the list of keywords. Non-standard
		#	terms (like BOAT for GUNBOAT) must be added manually with
		#	key and value reversed. Note that coast abbreviations in the
		#	keywords list have a '/' prepended.
		#	-------------------------------------------------------------
		self.units = {
			'A': 'ARMY',
			'F': 'FLEET',
			'G': 'GUNBOAT',
			'W': 'WING',
		}
		self.coasts = {
			'NC': 'NORTH COAST',
			'SC': 'SOUTH COAST',
			'EC': 'EAST COAST',
			'WC': 'WEST COAST',
		}
		#	---------------------------------------------------------------
		#	Norming occurs in two phases, first replacing all keywords
		#	with characters based on the English language, followed by a
		#	further reduction of certain character combinations.
		#	The reason to add 'A FLEET' (used in build orders) and the like
		#	instead of making 'A' a keyword mapping to '', is that 'A'
		#	already stands for 'ARMY'. Remember, longer word combinations
		#	get processed first.
		#	---------------------------------------------------------------
		self.keywords = {
			'AN ARMY': 'A',	'A FLEET': 'F',	'A WING': 'W',	'THE': '',
			'BOAT': 'G',	'A BOAT': 'G',	'A GUNBOAT': 'G',	
			'MOVE': '',		'MOVES': '',	'MOVING': '',
			'ATTACK': '-',	'ATTACKS': '-',	'ATTACKING': '-',
			'GO': '',		'GOES': '',		'GOING': '',
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
			'CLEAR': '*',	'UNUSED': '',	'PENDING': 'V',
			'ORDER': '',	'ORDERS': '',	'RESULT': '',	'RESULTS': '',
			'IS': '',		'WILL': '',
			'IN': '',		'AT': '',		'ON': '',		'TO': '-',
			'OF': '\\',		'FROM': '<',	'\' S': '',		'WITH': '?',
			'VIA': '~',		'THROUGH': '~',	'OVER': '~',	'BY': '~',
			'AND': '',		'OR': '|',
			'BOUNCE': '|',	'CUT': '|',
			'VOID': '?',	'NO CONVOY': '?',
			'DISLODGED': '~',				'DESTROYED': '*',
			'TRANS - SIBERIAN RAILROAD': '=',				'TSR': '=',
			'TRANS SIBERIAN RAILROAD': '=',	'TRANS SIBERIAN': '=',
			'TRANS - SIBERIAN': '=',		'RAILROAD': '=',
		}
		self.keycombos = {
			'~ LAND': '_',	'~ WATER': '_',	'~ SEA': '_',
			'* ALL': '*',	'* ANY': '',	'* EVERY': '',
		}
		#	----------------------------------
		#	Standard nicks
		#	Note that '-' is 'M' after keyword
		#	transformation
		#	----------------------------------
		self.nicks = {
			'-': 'MASTER',	'?': 'NEUTRAL',
			'JK': 'JUDGEKEEPER',
		}
		#	-------------------------------------
		#	Call this after initializing the rest
		#	-------------------------------------
		Lang.reinit(self)

class FrenchLang(Lang):
	#	----------------------------------------------------------------------
	def __init__(self, name = 'French'):
		Lang.__init__(self, name)
	#	----------------------------------------------------------------------
	def reinit(self, name = 'french'):
		self.units = {
			'A': 'ARMÉE',
			'F': 'FLOTTILLE',
			'G': 'CANONNIÈRE',
			'W': 'AILE',
		}
		self.coasts = {
			'CN': 'CÔTE NORD',
			'CS': 'CÔTE SUD',
			'CE': 'CÔTE EST',
			'CO': 'CÔTE OUEST',
		}
		Lang.reinit(self)
	#	----------------------------------------------------------------------
	def norm(self, phrase):
		#	---------------
		#	Remove accents.
		#	---------------
		return Lang.norm(self, normalize('NFKD', unicode(phrase,
			'utf-8')).encode('ascii', 'ignore'))

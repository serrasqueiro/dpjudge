import random, os

from DPjudge import Game, host, Map

from PayolaPower import PayolaPower

class PayolaGame(Game):
	#	----------------------------------------------------------------------
	class Key:
		#	------------------------------------------------------------------
		def __init__(self, power, unit, order):
			total, seqs = 0, [None] * (len(power.game.map.powers) + 1)
			cost, plateau = {}, {}
			vars(self).update(locals())
		#	------------------------------------------------------------------
		def __repr__(self):
			return ' '.join((self.power.name, self.unit, self.order,
							`self.total`, `self.seqs`))
		#	------------------------------------------------------------------
		def __cmp__(self, key):
			#	--------------------------------------------------------------
			#	Decide all bribe winners.  High bribe wins, and if two or more
			#	bribes are tied, the winner is that with the more acceptable
			#	bribes (from bribe positions, put in acceptance list order).
			#	--------------------------------------------------------------
			return (cmp(key.total, self.total)
				or cmp([(x, os.sys.maxint)[x is None] for x in self.seqs],
					   [(x, os.sys.maxint)[x is None] for x in key.seqs]))
		#	------------------------------------------------------------------
		def add(self, offer):
			#	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
			#	Determine the spot in the acceptance list to place the "position
			#	in list" data (in the seqs attribute).  The "".find() call could
			#	result in -1, which is okay (actually, this is the case for all
			#	non-map powers) -- all investors, etc., are relegated to the
			#	rearmost (extra) spot.  See NOTE in PayolaGame.bestOffer() for
			#	an important caution about the effect this can have.
			#
			#	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
			if offer.power.type: which = -1
			else: which = self.power.fullAccept.find(offer.power.abbrev)
			if self.seqs[which] is None: self.seqs[which] = offer.num
			else: self.seqs[which] = min(self.seqs[which], offer.num)
			self.total += offer.amt
			self.cost.setdefault(offer.power, 0)
			self.cost[offer.power] += offer.amt
			self.plateau.setdefault(offer.power, 0)
			if 'PUBLIC_TOTALS' not in self.power.game.rules:
				self.plateau[offer.power] += offer.plateau
		#	------------------------------------------------------------------
		def format(self, power = 0, blind = 0, hide = 0):
			if power: flag, self.amt = ' ', self.cost.get(power, 0)
			else:
				pay = self.power.fullAccept.index(self.power.abbrev)
				flag = ' *'[self.seqs[pay] is None and not hide]
				self.amt = self.total
			return ' %s %3d : %s %s\n' % (flag, self.amt, self.unit,
				blind and ('%s(%s)' % ((' ' * 9)[len(self.unit):],
				self.power.game.map.ownWord[self.power.name])) or self.order)
	#	----------------------------------------------------------------------
	def __init__(self, gameName):
		variant, rules, powerType = 'payola', ['ORDER_ANY'], PayolaPower
		offers, orders, taxes, tax, cap = {}, {}, {}, 0, 0
		vars(self).update(locals())
		Game.__init__(self, gameName)
	#	----------------------------------------------------------------------
	def __repr__(self):
		text = Game.__repr__(self).decode('latin-1')
		if self.taxes:
			for center, value in self.taxes.items():
				text += '\nTAX %s %d' % (center, value)
		if self.tax: text += '\nTAX %d' % self.tax
		if self.cap: text += '\nCAP %d' % self.cap
		return '\n'.join([x for x in text.split('\n')
						if x not in self.directives]).encode('latin-1')
	#	----------------------------------------------------------------------
	def load(self, fileName = 'status'):
		Game.load(self, fileName)
		for power in self.powers:
			power.liquid = power.balance
			for offer in power.sheet: self.parseOffer(power, offer)
			self.validateOffers(power)
	#	----------------------------------------------------------------------
	def parseData(self, power, word):
		if not word: return
		upline = ' '.join(word)
		#	----------------------------------------------
		#	Center tax income values (completely optional)
		#	----------------------------------------------
		if word[0] == 'TAX':
			self.tax = -1
			if len(word) == 3 and self.map.areatype(word[1]) or len(word) < 3:
				try: self.tax = int(word[-1])
				except: pass
			if self.tax < 0: self.error += ['BAD TAX: ' + upline]
			elif len(word) == 3: self.taxes[word[1]] = self.tax
		elif word[0] == 'CAP':
			try:
				self.cap = int('$'.join(word[1:]))
				if self.cap < 1: raise
			except: self.error += ['BAD CAP: ' + upline]
		#	----------
		#	Power data
		#	----------
		elif not power: self.error += ['DATA BEFORE POWER: ' + upline]
		elif word[0] == 'ACCEPT':
			if power.accept: self.error += ['TWO ACCEPTS FOR ' + power.name]
			elif len(word) != 2:
				self.error += ['BAD ACCEPT FOR ' + power.name]
			else: power.accept = word[1]
		elif word[0] == 'SENT':		# (one_transfer)
			try: power.sent += [word[1]]
			except: self.error += ['BAD SENT FOR ' + power.name]
		elif word[0] == 'ELECT':	# (exchange)
			for item in word[1:]:
				company, candidate = item.split(':')
				power.elect[company] = candidate
		elif word[0] == 'STATE':		# (exchange, undocumented?)
			if len(word) == 2: power.state = word[1]
			else: error += ['BAD STATE FOR ' + power.name]
		#	-------------------
		#	Offers and comments
		#	-------------------
		elif word[0][0] in '0123456789%':
			power.sheet += [upline]
			if word[0][0] != '%': power.held = 1
		else: self.error += ['UNRECOGNIZED PAYOLA DATA: ' + upline]
	#	----------------------------------------------------------------------
	def processExchangeReportsPhase(self):
		for power in self.powers:
			if power.type or not power.accept: continue
			shareholders = [x.name for x in self.powers
				if x.funds.get(power.abbrev)]
			self.mailPress(None, shareholders,
				'Status of %s for the beginning of fiscal year %s.\n\n'
				'Current treasury balance: %d AgP\n'
				'List of stockholders:%s\n' %
				(power.name.title(), self.phase.split()[1],
				power.balance, '\n    '.join(shareholders)),
				subject = 'Annual stockholder report for ' + power.name.title())
		return ['Annual stockholder reports have been sent.\n']
	#	----------------------------------------------------------------------
	def processExchangeElectionsPhase(self):
		results = {}
		for power in self.powers:
			for corp in self.powers:
				vote = power.elect.get(corp)
				if not vote: continue
				results.setdefault(corp, {}).setdefault(vote, 0)
				results[corp][vote] += power.funds[corp[0]]
		#	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
		#	Need to make a list of who won (what are the rules?)
		#	and act on it, and return it instead of just doing this:
		#
		#	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
		return []
	#	----------------------------------------------------------------------
	def processExchangeDividendsPhase(self):
		for power in self.powers:
			div, shareholders = power.funds.get('/share'), []
			if div is None: continue
			prevBal = power.balance
			for player in self.powers:
				shares = player.funds.get(power.abbrev)
				if player is power or not shares: continue
				if div:
					self.transferCash(power, player, shares * div, receipt = 0)
				else: shareholders += [player.name]
			del power.funds['/share']
			if shareholders:
				self.mailPress(None, shareholders,
					'%s has elected to withhold dividends for %d.' %
					(power.name.title(), self.year),
					subject = 'Dividends withheld by ' + power.name.title())
				continue
			mailTo = host.dpjudge
			self.openMail('Payola dividend distribution', 'ledgers', mailTo)
			if mailTo:
				self.mail.write('OFFICIAL Payola dividend distribution\n', 0)
				template = ('PRESS TO %s' +
					' QUIET' * ('EAVESDROP' not in self.rules))
			else: template = 'PRESS TO %.1s'
			self.mail.write(template % power.name +
				'\nACCOUNT ACTIVITY FOR %s\n%s\n'
				'BALANCE FORWARD            %4d AgP\n'
				'DIVIDEND DISTRIBUTION      %4d AgP\n'
				'CURRENT BALANCE            %4d AgP\n'
				'ENDPRESS\n' %
				(power.name, '=' * (21 + len(power.name)),
				prevBal, prevBal - power.balance, power.balance))
			self.mail.write('SIGNOFF\n', 0)
			self.mail.close()
			self.mail = None
		return ['Corporate dividends have been disbursed.\n']
	#	----------------------------------------------------------------------
	def processIncomePhase(self):
		if self.findNextPhase().endswith('ADJUSTMENTS'):
			list = Game.captureCenters(self, self.parseSupplyCount)
		else:
			Game.powerSizes(self, None, self.parseSupplyCount)
			list = []
		return (list + [self.phase.title() + ' has been distributed.\n']
			['NO_LEDGERS' in self.rules or self.phase in (None, 'COMPLETED'):])
	#	----------------------------------------------------------------------
	def resolvePhase(self):
		if self.phaseType == 'I': return self.processIncomePhase()
		if self.phaseType == 'D': return self.processExchangeDividendsPhase()
		if self.phaseType == 'Y': return self.processExchangeReportsPhase()
		return Game.resolvePhase(self)
	#	----------------------------------------------------------------------
	def checkPhase(self):
		if self.phase in ('FORMING', 'COMPLETED'): return []
		if self.phaseType == 'I':
			return self.processIncomePhase() + self.advancePhase()
		if self.phaseType == 'D':
			for power in self.powers:
				if not (power.funds.get('/share') or power.dividendLimit()):
					return []
			return self.processExchangeDividendsPhase() + self.advancePhase()
		if self.phaseType == 'Y':
			return self.processExchangeReportsPhase() + self.advancePhase()
		return Game.checkPhase(self)
	#	----------------------------------------------------------------------
	def checkAccept(self, power, accept = 0):
		accept = accept and accept.upper() or power.accept
		if len(accept) > len(self.map.powers):
			return self.error.append('BAD ACCEPTANCE LIST FOR ' + power.name)
		accept += '?'[len(accept) == len(self.map.powers) or '?' in accept:]
		powers = [x.abbrev for x in self.powers if x.abbrev] + ['?']
		for letter in accept:
			if letter not in powers or accept.count(letter) > 1:
				return self.error.append('BAD ACCEPT LIST FOR ' + power.name)
		power.accept = accept
	#	----------------------------------------------------------------------
	def parseOffer(self, power, offer):
		#	-----------------------------------------------
		#	Comments are signified by leading percent-marks
		#	-----------------------------------------------
		both = offer.split('%')
		word, comment = both[0].upper().split(), '%'.join(both[1:])
		if not word: return offer
		#	-----------------------------
		#	Provide 0 : default if needed
		#	-----------------------------
		if word[0][0] in '!:>@': word[0] = '0' + word[0]
		elif word[0][0].isalpha(): word = ['0', ':'] + word
		#	-----------------------------------------------------------
		#	Format bribe amount and plateau without embedded whitespace
		#	-----------------------------------------------------------
		for ch in '*#+':
			if len(word) > 1 and word[1][0] == ch:
				if len(word[1]) > 1: word[:2] = [''.join(word[:2])]
				else: word[:3] = [''.join(word[:3])]
		#	--------------------
		#	Segregate bribe type
		#	--------------------
		if not word[0][0].isdigit():
			return self.error.append('INVALID OFFER AMOUNT:&nbsp;' + word[0])
		for ch, char in enumerate(word[0]):
			if not (char.isdigit() or char in '#*+'):
				word[0:1] = [word[0][:ch], word[0][ch:]]
				break
		if len(word[1]) > 1: word[1:2] = [word[1][0], word[1][1:]]
		#	---------------------------------------------------
		#	Convert all words in the offer to recognized tokens
		#	---------------------------------------------------
		word, detail = self.expandOrder(word), []
		#	-----------------------------------------------------------------
		#	Now finish normalizing the offer by adding all missing unit types
		#	-----------------------------------------------------------------
		word = word[:2] + self.addUnitTypes(word[2:])
		#	-----------------------------------------
		#	Validate the bribe amount, which may have
		#	the format rep*max#plateau+(another)+...
		#	-----------------------------------------
		for each in word[0].split('+'):
			if not each: return self.error.append(
				'ADDITIONAL BRIBE NOT GIVEN:&nbsp;' + word[0])
			try:
				if '*' in each:
					rep, rest = each.split('*')
					if rep == '1': each = rest
				else: rep, rest = 1, each
				if '#' not in rest: amt, plateau = int(rest), 0
				elif 'NO_PLATEAU' in self.rules or 'NO_SAVINGS' in self.rules:
					return self.error.append('PLATEAUS NOT ALLOWED')
				elif rest[-1] == '#': amt = plateau = int(rest[:-1])
				else: amt, plateau = map(int, rest.split('#'))
				if amt == 0: rep, each = 1, '0'
			except: rep, amt, plateau = 0, 0, 1
			if amt < plateau or amt > 9999 or not (0 < int(rep) < 100):
				return self.error.append('INVALID OFFER AMOUNT:&nbsp;' + each)
			detail += [(rep, amt, plateau)]
		#	------------------------------------
		#	Figure out what to do with the offer
		#	First see if it is a savings request
		#	------------------------------------
		if word[1] == '$':
			if 'NO_SAVINGS' in self.rules:
				return self.error.append('SAVINGS NOT ALLOWED IN THIS GAME')
			if '#' in word[0]:
				return self.error.append('PLATEAU AMOUNT ON SAVINGS REQUEST')
			for rep, amt, plateau in detail: power.reserve(rep * amt)
		#	-----------------------------
		#	Now see if it is a bribe line
		#	-----------------------------
		elif word[1] in list(':!@>&'):
			#	---------------------------------------------------
			#	Validate the unit and check for disallowed wildcard
			#	orders and and for 0 AgP bribes to foreign units.
			#	---------------------------------------------------
			if len(word) < 4:
				return self.error.append('INCOMPLETE OFFER: ' + ' '.join(word))
			unit, orders, newline = ' '.join(word[2:4]), [], word[:4]
			#	---------------------------------------
			#	Check for 'Payola Classic' restrictions
			#	---------------------------------------
			if 'DIRECT_ONLY' in self.rules:
				if [x for x in power.offers if x.unit == unit]:
					return self.error.append(
						'MULTIPLE OFFERS TO A SINGLE UNIT FORBIDDEN: ' + unit)
				if word[1] != ':' or '|' in offer: return self.error.append(
					'WILDCARD BRIBES NOT ALLOWED')
				if '*' in word[0] or '+' in word[0]: return self.error.append(
					'REPETITION AND AUGMENTATION NOT ALLOWED')
				if ('LIMIT_OFFERS' in self.rules
				and sum([x.amt for x in power.offers]) > power.liquid):
					return self.error.append(
						'TOTAL OFFERS EXCEED AMOUNT AVAILABLE')
			#	---------------------------
			#	Check for dummy-only Payola
			#	---------------------------
			if 'PAY_DUMMIES' in self.rules:
				if unit in power.units:
					for rep, amt, plateau in detail:
						if ((amt, word[1]) != (0, ':') or '|' in offer
						or [x for x in power.offers if x.unit == unit]):
							return self.error.append(
								'BRIBE TO DOMESTIC UNIT: ' + unit)
				else:
					whose = self.unitOwner(unit)
					if whose and whose.player and not whose.isDummy():
						return self.error.append('BRIBE TO OWNED UNIT: ' + unit)
			#	---------------------------------------------------
			#	Check for zero silver piece bribes to foreign units
			#	---------------------------------------------------
			for rep, amt, plateau in detail:
				if (amt == 0 and unit not in power.units
				and ('BLIND' in self.rules or self.unitOwner(unit))
				and 'ZERO_FOREIGN' not in self.rules): return self.error.append(
					'ZERO AgP OFFER TO FOREIGN UNIT: ' + unit)
			#	--------------------------------------------------
			#	Go through all bribes (separated by vertical bars)
			#	--------------------------------------------------
			for order in [x.strip() for x in ' '.join(word[4:]).split('|')]:
				#	--------------------------------------------------
				#	The Payola Mailing List voted to outlaw duplicate
				#	orders in offers (i.e. "5 : F TYS - ION | - ION").
				#	Note that this form DOES have meaning, though --
				#	rather than a single bribe of 10 AgP, which would
				#	be reduced to 9 on overspending, two bribes of 5
				#	would be reduced each to four, for a total of 8.
				#	However, to achieve quicker reduction like this,
				#	players must use separate offers.  The best
				#	reason to for this rule is to provide semantics
				#	consistent with that required for negative offers.
				#	--------------------------------------------------
				if not order: return self.error.append('NO %sORDER GIVEN: ' %
					('|' in ' '.join(word) and 'ALTERNATIVE ' or '') + unit)
				if order in orders: return self.error.append(
					'DUPLICATE ORDER IN OFFER: %s ' % unit + order)
				#	---------------------------------------------------
				#	Add any missing coasts (RUM-BUL becomes RUM-BUL/EC)
				#	---------------------------------------------------
				order = ' '.join(self.map.defaultCoast(
					unit.split() + order.split())[2:])
				if len(newline) > 4: newline += ['|']
				newline += order.split()
				#	--------------------------------------------------
				#	Validate and (if valid) add the order to the offer
				#	--------------------------------------------------
				valid = self.validOrder(power, unit, order)
				if valid is None: return
				if not valid and 'FICTIONAL_OK' not in self.rules:
					return self.error.append(
						'NON-EXISTENT UNIT IN ORDER: %s ' % unit + order)
				whose = self.unitOwner(unit)
				if (('TOUCH_BRIBE' in self.rules
				or   'REMOTE_BRIBE' in self.rules)
				and not ('CD_DUMMIES' in self.rules
				and whose and whose.player and whose.isDummy())):
					owner = whose or power
					if power is not owner:
						bad = [x for x in power.units
							if self.validOrder(power, x, 'S ' + unit, report=0)
							or self.validOrder(owner, unit, 'S ' + x, report=0)]
						if 'TOUCH_BRIBE' in self.rules: bad = not bad
						if bad: return self.error.append(
							'BRIBED UNIT M%sT BE ADJACENT: ' %
							('AY NO', 'US')['TOUCH_BRIBE' in self.rules] + unit)
				orders += [order]
			#	-----------------------------------------------------
			#	Add the offer repeatedly (according to the "*" count)
			#	-----------------------------------------------------
			word = newline
			for rep, amt, plateau in detail:
				for repeat in range(int(rep)):
					power.addOffer(word[1], unit, orders, amt, plateau)
		else: return self.error.append('BAD OFFER TYPE: ' + offer)
		return ' '.join(word) + (comment and (' %' + comment) or '')
	#	----------------------------------------------------------------------
	def bestOffer(self, power, unit):
		orders = {}
		#	-----------------------------------------
		#	Determine direct payment for each : order
		#	-----------------------------------------
		while not orders:
			for offerer in self.powers:
				for offer in offerer.offers:
					if (offer.unit == unit and offer.code == ':'
					and self.validOrder(power, unit, offer.order)):
						orders.setdefault(offer.order,
							self.Key(power, offer.unit, offer.order)).add(offer)
			#	---------------------------------------------------
			#	In BLIND games, all the offers a unit gets MIGHT be
			#	invalid.  If so, we'll have no order yet, and we'll
			#	need to add another (default hold) bribe to get one
			#	---------------------------------------------------
			if not orders: power.addOffer(':', unit, 'H')
		#	----------------------
		#	Now add wildcard money
		#	----------------------
		for offerer in self.powers:
			for offer in offerer.offers:
				if offer.unit != unit or offer.code == ':': continue
				for order, key in orders.items():
					if ((offer.code == '!' and order not in offer.order)
					or  '@>'.find(offer.code) == (order[0] == '-')
					or	offer.code == '&'): key.add(offer)
		#	---------------------------------------------
		#	Sort the offers and pick the first (best) one
		#	---------------------------------------------
		self.offers[unit] = sorted(orders.values())
		#	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
		#	NOTE -- in games with investors, we still could be "randomly"
		#	choosing one of the bids involved in an unresolvable tie.  This
		#	could happen if two (or more) investors all offer the same
		#	high-bid amount to a unit for separate orders, and no power's
		#	money is involved.  All investors appear at the same location
		#	in all acceptance lists, meaning the "num" attribute of the two
		#	Keys could be identical if each power listed its contending
		#	bid at the same position down their list.
		#
		#	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
		self.orders[unit] = best = self.offers[unit][0]
		#	--------------------------------------------------------
		#	If the eBayola rule is being used, the winning briber(s)
		#	will only be charged the sum of the highest NON-winning
		#	bribe amount plus one.  Any resulting rebates will be
		#	given to the most-preferred contributing powers first
		#	(uncomment in the if clause to rebate the most-preferred
		#	contributing power among those offering the most gold).
		#	--------------------------------------------------------
		if 'EBAYOLA' in self.rules:
			for other in self.offers[unit][1:]:
				for who, amt in other.cost.items():
					other.cost[who] -= min(amt, best.cost.get(who, 0))
			pref, obs, over = {}, [], best.total - 1
			try: over -= max(sorted(self.offers[unit][1:])[0].total, 0)
			except: pass
			for who, amt in best.cost.items():
				if amt: # == max(best.cost.values()):
					try: pref[power.fullAccept.index(who.abbrev)] = who
					except: obs += [who]
			obs.sort(lambda x,y: cmp(best.cost[y], best.cost[x]))
			for saver in [pref[x] for x in sorted(pref)] + obs:
				rebate = min(best.cost[saver] - best.plateau[saver], over)
				best.cost[saver] -= rebate
				best.total -= rebate
				over -= rebate
		#	--------------------------------------------------------------
		#	When a DUMMY unit is bribed, all ties involving bribes offered
		#	by a different power or set of powers are decided by having
		#	the unit HOLD.  Find and accept the unit's HOLD offer, and set
		#	its total (for appearances) to one AgP better than the best.
		#	--------------------------------------------------------------
		if power.isDummy() and power.accept == '?':
			id = [not x for x in self.orders[unit].seqs]
			for guy in self.offers[unit][1:]:
				if self.orders[unit].total != guy.total: return
				if [not x for x in guy.seqs] != id: break
			else: return
			tops = self.offers[unit][0].total + 1
			try:
				hold = [x for x in self.offers[unit] if x.order == 'H'][0]
				self.offers[unit].remove(hold)
			except: hold = self.Key(power, unit, 'H')
			hold.total, self.orders[unit] = tops, hold
			self.offers[unit].insert(0, hold)
	#	----------------------------------------------------------------------
	def determineOrders(self):
		#	------------------------------------------------------------------
		#	All vassal states use the same acceptance list as their controller
		#	------------------------------------------------------------------
		if 'VASSAL_DUMMIES' in self.rules:
			for power in self.powers:
				for vassal in [x for x in self.powers if x.ceo == [power.name]]:
					vassal.accept = power.accept
		#	---------------------------------
		#	Provide default hold offers and
		#	expand apathetic acceptance lists
		#	---------------------------------
		#	Note -- initially, all apathetic lists were expanded every time
		#	any unit decided on an order.  This caused problems, though, in
		#	that a second or subsequent order in a group of alternatives
		#	(separated by vertical bars) would often sort higher than the
		#	first order in the list, in direct contradiction of Rule 3.3.
		#	So then I made it so that the expansion occurred for all lists
		#	only before each run through all of the bribes -- including
		#	before any re-run-throughs caused by player overexpenditure.
		#	This made good sense to me, but proved too difficult to explain
		#	in the rules and could lead to players wondering why an
		#	overexpenditure had even occurred, because with the acceptance
		#	list expansion that was finally used, one would not have been
		#	necessary.  So I decided it was cleaner all around to just do
		#	it up front, and the same expansion will hold true for all
		#	adjudication done in a particular movement phase.
		#	---------------------------------------------------------------
		for power in self.powers:
			power.addDefaults()
			if power.accept:
				others = [x.abbrev for x in self.powers
					if x.abbrev and x.abbrev not in power.accept]
				random.shuffle(others)
				power.fullAccept = power.accept.replace('?', ''.join(others))
		#	-------------------------------
		#	Determine the orders to be sent
		#	-------------------------------
		self.await = 1
		while 1:
			self.orders, self.offers, overspent = {}, {}, 0
			for power in self.powers:
				power.left = power.liquid
				if not power.accept: continue
				others = [x.abbrev for x in self.powers
					if x.abbrev and x.abbrev not in power.accept]
				random.shuffle(others)
				power.fullAccept = power.accept.replace('?', ''.join(others))
			for power in self.powers:
				for unit in power.units:
					self.bestOffer(power, unit)
					for payer, amount in self.orders[unit].cost.items():
						payer.spend(amount)
						overspent |= payer.left < 0
			if not overspent: break
			[x.reduce() for x in self.powers if x.left < 0]
	#	----------------------------------------------------------------------
	def writeChart(self):
		header, num, dash, bribers = '%35s', '%4d ', '   - ', self.map.powers
		powers, balance, liquid, left, overpaid, total = [], {}, {}, {}, {}, 0
		for player in bribers:
			for power in self.powers:
				if power.name == player:
					balance[player], left[player] = power.balance, power.left
					liquid[player] = power.liquid
					if power.overpaid: overpaid[player] = power.overpaid
					if power.units: powers += [power]
					break
		if 'PAY_DUMMIES' in self.rules:
			bribers = [x.name for x in self.powers
				if x.name in self.map.powers and not x.isDummy()]
			powers = [x for x in powers if x.isDummy()]
		line = '-' * (39 + 5 * len(bribers))
		try: file = open(self.file('chart'), 'a')
		except: return self.error.append('CANNOT WRITE CHART: INFORM MASTER')
		temp = '\n%s\n%s\n%s\n%35s' % (line, self.phase, line, '')
		file.write(temp.encode('latin-1'))
		for player in bribers: file.write('  %.3s' % player)
		if 'PAY_DUMMIES' not in self.rules:
			for power in powers:
				file.write('\nACCEPTANCE LIST FOR %-15s' % power.name)
				others = [x.abbrev for x in self.powers
					if x.abbrev and x.abbrev not in power.accept]
				accept = power.accept.replace('?', '?' * len(others))
				for each in self.powers:
					if each.abbrev:
						if each.abbrev in others: file.write('   ? ')
						else: file.write(num % (accept.index(each.abbrev) + 1))
		file.write('\n' + line.encode('latin-1'))
		for power in powers:
			file.write('\n')
			for unit in power.units:
				for offer in self.offers[unit]:
					temp = '%-35s' % (unit + ' ' + offer.order)
					file.write(temp.encode('latin-1'))
					for payer in bribers:
						player = [x for x in self.powers if x.name == payer]
						if player:
							temp = (player[0] in offer.cost
							and num % offer.cost[player[0]] or dash)
							file.write(temp.encode('latin-1'))
					temp = (unit[0] == ' ' and dash or num % offer.total) + '\n'
					file.write(temp.encode('latin-1'))
					unit = ' ' * len(unit)
		file.write(line.encode('latin-1'))
		if overpaid:
			file.write('\n%-35s' % 'OVERBIDDING REDUCTIONS')
			for power in bribers: file.write(
				overpaid.get(power) and num % overpaid[power] or dash)
		file.write('\n%-35s' % 'TREASURY BEFORE OFFERS')
		for power in bribers:
			balance[power] = balance.get(power, 0)
			liquid[power] = liquid.get(power, 0)
			left[power] = left.get(power, 0)
			file.write(num % balance[power])
			total += balance[power]
		temp = num % total + '\n%-35s' % 'TOTAL PRICES PAID'
		file.write(temp.encode('latin-1'))
		total = 0
		for power in bribers:
			file.write(num % (liquid[power] - left[power]))
			total += liquid[power] - left[power]
		temp = num % total + '\n%-35s' % 'NEW TREASURY BALANCES'
		file.write(temp.encode('latin-1'))
		total = 0
		for power in bribers:
			temp = num % (balance[power] - liquid[power] + left[power])
			file.write(temp.encode('latin-1'))
			total += balance[power] - liquid[power] + left[power]
		temp = num % total + '\n%s\n' % line
		file.write(temp.encode('latin-1'))
		file.close()
		try: os.chmod(file.name, 0666)
		except: pass
	#	----------------------------------------------------------------------
	def sendLedgers(self):
		mailTo = host.dpjudge
		self.openMail('Payola orders', 'ledgers', mailTo = mailTo)
		if mailTo: self.mail.write(
			'OFFICIAL Payola bribe results %s %.1s%s%.1s\n' %
			tuple([self.name] + self.phase.split()), 0)
		blind = 'BLIND' in self.rules
		for power in self.powers:
			if not power.offers and (not power.balance
			or power.isDummy() and not power.ceo): continue
			if mailTo: self.mail.write('PRESS TO %s %s\n' %
				(power.name, 'EAVESDROP' not in self.rules and 'QUIET' or ''))
			elif power.name not in self.map.powers: self.mail.write(
				'PRESS TO M\nACCOUNT ACTIVITY FOR %s\n' % power.name)
			else: self.mail.write('PRESS TO %s\n' % power.abbrev)
			self.mail.write(
				'%s ACCOUNT STATEMENT FOR %s\n%s\n' %
				(self.phase.upper(), power.name,
				'=' * (len(self.phase + power.name) + 23)))
			if power.units and 'PAY_DUMMIES' not in self.rules:
				gain = 0
				self.mail.write(
					'YOUR UNITS WERE %sORDERED AS FOLLOWS:\n' %
					('PAID AND ' * ('HIDE_COST' not in self.rules)))
				for unit in power.units:
					if 'HIDE_COST' not in self.rules:
						self.mail.write(self.orders[unit].format(
							hide = 'HIDE_OFFERS' in self.rules))
					gain += self.orders[unit].total
				if 'ZEROSUM' in self.rules:
					self.mail.write(
						'TOTAL NET INCOME FOR YOUR UNITS WAS:%5d AgP\n' % gain)
					power.funds['+'] = power.funds.get('+', 0) + gain
			if not power.offers: self.mail.write('YOU OFFERED NO BRIBES\n')
			elif 'HIDE_OFFERS' not in self.rules:
				status = 1
				for key in [x for x in self.orders.values() if power in x.cost]:
					off = key.format(power, blind)
					if not key.amt:
						if self.unitOwner(key.unit) == power:
							if 'PAY_DUMMIES' in self.rules: continue
						elif blind and 'ZERO_FOREIGN' not in self.rules:
							continue
					self.mail.write('YOUR ACCEPTED BRIBES WERE:\n' * status +
						off)
					status = 0
				if status:
					self.mail.write('NONE OF YOUR BRIBES WERE ACCEPTED\n')
				self.mail.write('YOUR OFFER SHEET WAS:\n')
				for offer in power.sheet:
					if 'PAY_DUMMIES' in self.rules and offer[:1] == '0':
						continue
					self.mail.write(
						'%*s%s\n' % (6 - offer.find(' '), '', offer))
				self.mail.write(
				'THE PREVIOUS BALANCE OF YOUR BANK ACCOUNT WAS:%7d AgP\n' %
					power.balance)
				if power.overpaid: self.mail.write(
				'EACH OFFER WAS SUBJECT TO BRIBE REDUCTION RULES %5d TIME%s\n'
					% (power.overpaid, 'S'[power.overpaid < 2:]))
				self.mail.write(
				'TOTAL COST TO YOU OF THE BRIBES YOU OFFERED WAS:%5d AgP\n' %
					(power.liquid - power.left))
			power.balance -= power.liquid - power.left
			self.mail.write(
				'THE REMAINING BALANCE IN YOUR BANK ACCOUNT IS:%7d AgP\n'
				'ENDPRESS\n' % power.balance)
		self.mail.write('SIGNOFF\n', 0)
		self.mail.close()
		self.mail = None
	#	----------------------------------------------------------------------
	def preMoveUpdate(self):
		if 'BLIND' in self.rules or 'FICTIONAL_OK' in self.rules:
			self.error = [x for x in self.error
				if not x.startswith('IMPOSSIBLE ORDER')]
		if self.error:
			print 'ERRORS IMPEDING RESOLUTION:', self.error
			return
		self.writeChart()
		if 'NO_LEDGERS' not in self.rules: self.sendLedgers()
		#	----------------------
		#	Empty the offer sheets
		#	----------------------
		for power in self.powers: power.sheet = power.offers = []
		return Game.preMoveUpdate(self)
	#	----------------------------------------------------------------------
	def postMoveUpdate(self):
		if 'NO_DONATIONS' in self.rules:
			self.findGoners(phase = 0)
			for power in self.powers:
				if power.goner: power.balance = 0
		return Game.postMoveUpdate(self)
	#	----------------------------------------------------------------------
	def validateStatus(self):
		self.map = self.map or Map.Map()
		#	-------------------------------------------------
		#	If the map's flow already holds any INCOME phase,
		#	leacve it alone.  Otherwise, add a single INCOME
		#	phase into the flow after the first ADJUSTMENTS.
		#	-------------------------------------------------
		if self.map.flow:
			for item in [x.split(':')[1] for x in self.map.flow]:
				if 'INCOME' in item.split(','): break
			else:	
				for flow, item in enumerate(self.map.flow):
					if 'ADJUSTMENTS' in item.split(':')[1].split(','):
						self.map.flow[flow] = item.replace(
							'ADJUSTMENTS', 'ADJUSTMENTS,INCOME')
						break
				(where, what) = [(x+1,y) for (x,y) in enumerate(self.map.seq)
					if y.endswith('ADJUSTMENTS')][0]
				self.map.seq.insert(where, what.replace('ADJUSTMENTS','INCOME'))
		if self.rotate: self.error += ['CONTROL ROTATION IS INVALID IN PAYOLA']
		self.error += [rule + ' RULE IS INVALID IN PAYOLA'
			for rule in ('PROXY_OK', 'NO_CHECK') if rule in self.rules]
		for apple, orange in	(	('ZERO_FOREIGN',	'BLIND'),
									('PUBLIC_TOTALS',	'BLIND'),
									('REMOTE_BRIBE',	'TOUCH_BRIBE'),
									('REMOTE_BRIBE',	'PAY_DUMMIES'),
									('TOUCH_BRIBE',		'PAY_DUMMIES'),
								):
			if apple in self.rules and orange in self.rules:
				self.error += ['INCOMPATIBLE RULES: %s/' % apple + orange]
		for power in self.powers:
			if power.centers:
				if type(power.accept) not in (str, unicode): power.initAccept()
				else: self.checkAccept(power)
			if power.balance is None and (power.centers or power.units):
				self.error += ['NO BALANCE FOR ' + power.name]
#		for subvar in ('ZEROSUM', 'EXCHANGE', 'FLAT_TAX'):
#			if subvar in self.rules:
#				self.variant = subvar.lower() + ' ' + self.variant
		Game.validateStatus(self)
	#	----------------------------------------------------------------------
	def transferCenter(self, loser, gainer, sc):
		if 'ZEROSUM' in self.rules:
			#	--------------------------------------
			#	Add to the "gained" and "lost" lists.
			#	Each entry is an SC and an amount that
			#	is to be moved from one treasury to
			#	another.  The amount is the current
			#	(pre-income) balance of the losing
			#	power divided by the number of SC's he
			#	held AT THE BEGINNING OF THE YEAR.
			#	--------------------------------------
			if loser:
				amt = ((loser.balance + loser.funds.get('+', 0)) /
					(len(loser.centers) - len(loser.gained) + len(loser.lost)))
				loser.lost += [(sc, amt)]
			else: amt = 10
			gainer.gained += [(sc, amt)]
		Game.transferCenter(self, loser, gainer, sc)
	#	----------------------------------------------------------------------
	def captureCenters(self):
		return Game.captureCenters(self, self.parseSupplyCount)
	#	----------------------------------------------------------------------
	def parseSupplyCount(self, power, word):
		if not self.phase: return
		if 'PAY_DUMMIES' in self.rules and not [x for x in self.powers
			if x.isDummy() and x.centers]:
			if 'NO_HOARDING' in self.rules: power.balance = 0
			return
		prev = 'NO_HOARDING' not in self.rules and power.balance
		bal = prev + power.income(int(word[1]))
		power.balance = (bal + sum([x[1] for x in power.gained])
							 - sum([x[1] for x in power.lost]))
		if 'NO_LEDGERS' in self.rules: return
		if not (bal or power.gained or power.lost): return
		mailTo = host.dpjudge
		subject = 'Payola income report ' + self.phase.split()[1]
		desc = ('TAX INCOME', 'BRIBE PROFITS')['ZEROSUM' in self.rules]
		self.openMail(subject, 'ledgers', mailTo = mailTo)
		if mailTo: self.mail.write('OFFICIAL %s\n' % subject, 0)
		if mailTo: self.mail.write('PRESS TO %s %s\n' %
			(power.name, 'EAVESDROP' not in self.rules and 'QUIET' or ''))
		else: self.mail.write('PRESS TO %.1s\n' % power.name)
		self.mail.write(
			'INCOME FOR %s FOR YEAR END %s\n%s\n'
			'BALANCE FORWARD%9d AgP\n'
			'%-15s%9d AgP\n' %
			(power.name, self.phase.split()[1],
			'=' * (25 + len(power.name + self.phase.split()[1])),
			prev, desc, bal - prev))
		#	-------
		#	ZeroSum
		#	-------
		for sc, amt in power.gained:
			self.mail.write('CAPTURE OF %s %9d AgP\n' % (sc, amt))
		for sc, amt in power.lost:
			self.mail.write('LOSS OF %s    %9d AgP\n' % (sc, -amt))
		self.mail.write(
			'CURRENT BALANCE%9d AgP\n'
			'ENDPRESS\n' % power.balance)
		self.mail.write('SIGNOFF\n', 0)
		self.mail.close()
		self.mail = None
	#	----------------------------------------------------------------------
	def finishPhase(self):
		if 'ONE_TRANSFER' in self.rules:
			for power in self.powers: power.sent = []
	#	----------------------------------------------------------------------
	def transferCash(self, giver, receiver, amount, sc = None, receipt = 1):
		for (who, where) in ((receiver, giver), (giver, receiver)):
			if not who: continue
			send = (who is receiver) or receipt
			#	----------------------------------------------------------
			#	Start the mail.  The master signon is put in automatically
			#	----------------------------------------------------------
			if send:
				mailTo = host.dpjudge
				self.openMail('Payola transfer', 'ledgers', mailTo)
				if mailTo:
					self.mail.write('OFFICIAL Payola funds transfer\n', 0)
					template = ('PRESS TO %%s%s\n' %
						('EAVESDROP' not in self.rules and ' QUIET' or ''))
				elif who.name in self.map.powers: template = 'PRESS TO %.1s\n'
				else: template = 'PRESS TO M\nACCOUNT ACTIVITY FOR %s\n'
				self.mail.write(template % who.name)
				#	------------------------------
				#	Format and compose the message
				#	------------------------------
				if receiver is who:
					if sc:
						what = 'CAPTURE OF ' + sc
						if where: what += ' FROM ' + where.name
					elif 'ANON_TRANSFER' in self.rules:
						what = 'TRANSFER FROM SOMEONE'
					else: what = 'TRANSFER FROM ' + where.name
				elif sc: what = 'LOSS OF %s TO ' % sc + receiver.name
				else: what = 'TRANSFER TO ' + receiver.name
				self.mail.write(
					'ACCOUNT ACTIVITY FOR %s\n%s\n'
					'BALANCE FORWARD            %4d AgP\n'
					'%-27s%4d AgP\n' % (who.name, '=' * (21 + len(who.name)),
					who.balance, what, amount))
			#	---------------------
			#	Update player balance
			#	---------------------
			if receiver is who: who.balance += amount
			else: who.balance -= amount
			if send:
				self.mail.write(
					'CURRENT BALANCE            %4d AgP\n'
					'ENDPRESS\n' % who.balance)
				self.mail.write('SIGNOFF\n', 0)
				self.mail.close()
				self.mail = None
	#	----------------------------------------------------------------------
	def updateOrders(self, power, offers):
		hadOffers = power.offers
		power.offers, power.sheet = [], []
		for line in filter(None, offers):
			offer = self.parseOffer(power, line)
			if offer: power.sheet += [offer]
		self.validateOffers(power)
		if self.canChangeOrders(hadOffers, power.offers) and not self.error:
			self.process()
	#	----------------------------------------------------------------------
	def getOrders(self, power):
		if self.phaseType in 'RA': return '\n'.join(power.adjust)
		return '\n'.join([x['PAY_DUMMIES' in self.rules and x.startswith('0 :')
			<< 2:] for x in power.sheet])
	#	----------------------------------------------------------------------
	def validateOffers(self, power):
		if 'PAY_DUMMIES' not in self.rules: return
		if power.isDummy(): return
		if (power.offers and [x for x in power.units
			if x not in [y.unit for y in power.offers]]
			and 'DEFAULT_UNORDERED' not in self.rules):
			self.error += ['ALL OWNED UNITS NOT ORDERED FOR %s' % power.name]
	#	----------------------------------------------------------------------


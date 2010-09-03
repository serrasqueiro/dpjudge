#!/usr/bin/env python -SO

import sys
from codecs import open

class PostScriptMap:
	#	----------------------------------------------------------------------
	def __init__(self, mapFile, inFile = 0, outFile = 0, viewer = 0):
		try: input = (inFile and open(inFile) or sys.stdin).readlines()
		except: raise CannotOpenResultsFile
		lines = [unicode(x, 'latin-1') for x in input]
		self.outFileName = outFile
		try: self.outFile = outFile and open(outFile, 'w') or sys.stdout
		except: raise CannotOpenOutputFile
		if viewer: viewer = viewer.upper()
		self.pages, self.sc, show = 0, '', 1
		self.started = self.scBefore = section = lastSection = lastLine = None
		power = season = year = None
		self.map, self.orders, self.retreats, self.ownerOrder = [], [], [], []
		self.vassals, dislodgements, successes, retractions = {}, {}, {}, {}
		self.owner, self.adj, self.units = {}, {}, {}
		self.startDoc(mapFile)
		for line in lines:
			word = line.upper().split()
			if not word or line[0] in ' \t' and section != 'O': 
				lastLine = None
				continue
			if lastLine:
				line = lastLine.rstrip() + ' ' + line
				word = line.upper().split()
				lastLine = None
			if word[0] == 'SHOW':
				show = not (word[1:] and viewer) or viewer in word[1:]
				continue
			if not show: continue
			copy = ' '.join(word)

			if 'VASSAL' in word:
				if 'STATUS' not in word:
					vassal, master = line.upper().split(' IS A VASSAL OF')
					self.vassals[vassal] = master.strip()[:-1]
				continue
			if 'INDEPENDENT.' in word:
				vassal = line.upper().split(' IS ')[0]
				if vassal in self.vassals: del self.vassals[vassal]
				continue

			#	-------------------------------------------
			#	Check if this is the beginning of a section
			#	-------------------------------------------
			if ' '.join(word[:2]) in (	'STARTING POSITION', 'STATUS OF',
										'ADJUSTMENT ORDERS', 'RETREAT ORDERS',
										'MOVEMENT RESULTS'):
				where, section = word[1] == 'OF' and 5 or 2, word[0][0]
				lastSection = section
			elif word[0] == 'OWNERSHIP':
				section, self.sc, where = 'OWN', '', 0
				self.ownerOrder, self.owner = [], {}
			elif ' '.join(word[:2]) == 'THE FOLLOWING': where, section = 0, 'D'
			elif section: where = 0
			else: continue

			if where:
				#	--------------------------------------------------------
				#	Determine the page title (game name, season, year, etc.)
				#	--------------------------------------------------------
				lastSeason, lastYear = season, year
				graphics, lowWord = [], line.split()
				scList = season = ''
				if lowWord[where] == 'for':
					name = lowWord[-1][1:-1].split('.')[0]
					title = name + ', '
					if section == 'S' and not self.pages:
						if lowWord[-1][0] + lowWord[-1][-1] != '()': title = ''
						title += 'Game Start'
					else:
						season, year = lowWord[where + 1:where + 3]
						if year == 'of': year = lowWord[where + 3]
						year = int(float(year))  # "year" has a period at end
						if lowWord[-1][0] == '(' and lowWord[-1][-1] == ')':
							title += season + ' ' + `year`
				#	------------
				#	Prepare page
				#	------------
				if section in 'MSA':
					if self.started: self.endPage()
					self.scBefore = self.pages
					self.startPage(title)
					if section == 'A': self.positions()
					else: self.units = {}
					dislodgements, successes, retractions = {}, {}, {}
				#	-----------------------------
				#	Page begun.  Go to next line.
				#	-----------------------------
				continue

			#	-------------------
			#	Lines to be ignored
			#	-------------------
			if ('PENDING' in copy or 'INVALID' in copy
			or	'REORDER' in copy or 'INCOME HAS' in copy
			or  'SUBJECT' in copy or copy[:2] == '::'): continue

			#	-------------------------------------------
			#	See if we're reading orders for a new power
			#	-------------------------------------------
			if word[0][-1] == ':':
				thisPower = word[0][:-1].replace('.', '')
				if power != thisPower:
					powerOrder = powerDecl = power = thisPower
					if power in self.vassals:
						powerDecl += ' ControlledBy ' + self.vassals[power]
						powerOrder += ' (' + self.vassals[power] + ')'
					if section not in 'OU':
						if section != 'R': self.outFile.write(
							(powerDecl + '\n').encode('latin-1'))
						if section in 'MS': 
							self.orders += [powerOrder]
					else: self.sc += powerDecl + '\n'

			#	--------------------------------------------
			#	Lines signaling the end of the phase results
			#	--------------------------------------------
			if filter(line.upper().startswith,
				('THE DEADLINE ', 'THE NEXT PHASE ', 'DEADLINE ', 'THE GAME IS ', 
				'ORDERS ', 'END')): section = None

			#	------------------------------
			#	Check if the section has ended
			#	------------------------------
			if section in ('OWN', None):
				#	Write the information
				#	---------------------
				for graphic in graphics:
					self.outFile.write((graphic + '\n').encode('latin-1'))
				power = None
				if section: section = 'O'
				continue

			#	----------------
			#	Center ownership
			#	----------------
			if section == 'O':
				if 'SUPPLY' in word:
					# Reset order and change section 
					self.ownerOrder = []
					section = 'U'
				else:
					if power not in self.ownerOrder: self.ownerOrder.append(power)
					scList += ' ' + ' '.join(word[line[0] != ' ':])
					if scList[-1] == '.':
						self.owner[power], scList = [], scList[:-1]
						for loc in scList.split(','):
							if loc.strip()[-2:] != 'SC':
								where = self.lookup(loc.strip())
								if where['nick'] not in self.owner[power]:
									self.owner[power] += [where['nick']]
									self.sc += where['nick'] + ' supply\n'
						scList = ''
					continue

			#	----------------
			#	Unit allotment
			#	----------------
			if section == 'U':
				if power not in self.ownerOrder: self.ownerOrder.append(power)
				continue

			#	--------------------------------------------------------
			#	Unit destructions.  Destroyed units are indicated by
			#	The ___ ___ in ___ with no valid retreats was destroyed.
			#	The ___ ___ in ___ was destroyed.
			#	The ___ ___ in ___ with torn allegiance was destroyed.
			#	These are possibly split across more than one line.
			#	--------------------------------------------------------
			if word[0] == 'THE' and ('FLEET' in word or 'ARMY' in word):
				if word[-1][-1] != '.':
					lastLine = line
					continue
				if word[-1] == 'DESTROYED.':
					which, upto = word.index('IN') + 1, -2
					if 'WITH' in word: upto = -word[::-1].index('WITH') - 1
					loc = ' '.join(word[which + (word[which] == 'THE'):upto])
					where = self.lookup(loc)
					if 'ALLEGIANCE' in word[upto:]:
						# no drawing for this one, simply remove
						for power in self.units:
							for piece in self.units[power]:
								if piece['loc']['nick'] == where['nick']:
									self.units[power].remove(piece)
						if where['nick'] in successes:
							idx = successes[where['nick']]
							self.orders[idx] = ('%-22s %s' %
								(self.orders[idx][:22], 'TORN'))
						elif where['nick'] in retractions:
							idx = retractions[where['nick']]
							self.retreats[idx] += ' TORN'
						continue
					graphics += [('%d %d DestroyUnit' %
						(where['x'], where['y']))]
					if where['nick'] in dislodgements:
						idx = dislodgements[where['nick']]
						self.orders[idx] = ('%-22s %s' %
							(self.orders[idx][:22], 'DESTROYED'))
					continue

			#	---------------------------------------------------
			#	Dislodgements (all lines that matter are handled by
			#	the unit destruction code above, so nothing to do).
			#	---------------------------------------------------
			if section == 'D': continue

			#	-------------------------------------------------------
			#	Adjustment orders (modify the units list for final map)
			#	-------------------------------------------------------
			if word[1] in ('DEFAULTS,', 'REMOVES', 'BUILDS', 'BUILD'):
				self.adj.setdefault(power,
					[word[1][0] == 'B' and 'BUILDS ' or 'REMOVES'])
				if word[2][:5] == 'WAIVE':
					self.adj[power] += ['WAIVED']
					continue
				which = 3 + (word[1][0] == 'D')
				unit = word[which][0]
				which += 2
				where = ' '.join(word[which + (word[which] == 'THE'):])
				where = self.lookup(where.split('.')[0])
				temp = ('\t%d %d Draw%s\n' %
					(where['x'], where['y'], ('Fleet', 'Army')[unit == 'A']))
				if word[1][0] != 'B':
					temp += ('\t%d %d RemoveUnit\n' % (where['x'], where['y'])) 
					for piece in self.units.get(power, [])[:]:
						if piece['loc']['nick'] == where['nick']:
							self.units[power].remove(piece)
				else:
					temp += ('\t%d %d BuildUnit\n' % (where['x'], where['y'])) 
					self.addUnit(power, unit, where, 1)
				self.outFile.write(temp.encode('latin-1'))
				self.adj[power] += [unit + ' ' + where['nick']]
				continue
				
			#	------------------------------------------------------
			#	Determine if the order failed (presence of annotation)
			#	------------------------------------------------------
			message, msg = copy.split('(*'), ''
			if len(message) > 1:
				copy, msg = message[0], message[1].split('*)')[0]
				word = copy.split()
			copy, word[-1] = copy.strip()[:-1], word[-1][:-1]

			#	--------------------------------------------------------
			#	Find the order type (and where in the order it is given)
			#	Detect the word 'NO' from "NO ORDER PROCESSED" ==> HOLD.
			#	--------------------------------------------------------
			for order in (	'SUPPORT', 'CONVOY', '->', 'HOLD', 'DISBAND', 'NO',
							'ARRIVES', 'DEPARTS', 'FOUND', 'LOST'	):
				try: orderWord = word.index(order)
				except: continue
				if order == 'NO': word[orderWord - 1] = word[orderWord - 1][:-1]
				break
			else: order, orderWord = '.', len(word)

			#	-----------------------
			#	Determine unit location
			#	-----------------------
			unit, si = word[1][0], self.lookup(' '.join(word[2:orderWord]))
			di = None
			
			#	----------------------------------------------------
			#	Dislodged units will not be listed in the unit list.
			#	----------------------------------------------------
			if 'DISLODGED' in msg: msg = 'DISLODGED'
			elif order[0] not in 'DL': 
				self.addUnit(power, unit, si)
				di = si
			submsg = ''

			#	-------------
			#	Draw the unit
			#	-------------
			if (section not in 'RD' and order[0] != 'A') or order[0] == 'F':
				temp = ("\t%d %d Draw%s\n" %
					(si['x'], si['y'], ('Fleet', 'Army')[unit == 'A']))
				self.outFile.write(temp.encode('latin-1'))

			#	--------------------------------------------
			#	Determine order text and graphical depiction
			#	--------------------------------------------

			#	----
			#	HOLD
			#	----
			if order[0] in 'NH': order, graph = 'H', ''
			#	------
			#	CONVOY
			#	------
			elif order[0] == 'C':
				mover, which = word.index('->'), ('ARMY', 'FLEET')[unit == 'A']
				di1 = self.lookup(' '.join(word[word.index(which) + 1:mover]))
				di2 = self.lookup(' '.join(word[mover + 1:]))
				order = "C %.3s - %-6.6s" % (di1['nick'], di2['nick'])
				graph = ("%d %d %d %d ArrowConvoy" %
					(di1['x'], di1['y'], di2['x'], di2['y']))
			#	-------
			#	SUPPORT
			#	-------
			elif order[0] == 'S':
				if 'ARMY' in word[orderWord:] or 'FLEET' in word[orderWord:]:
					try: where = word[orderWord:].index('ARMY')
					except: where = word[orderWord:].index('FLEET')
				else: continue
				where += orderWord + 1
				mover = None
				try:
					move = word.index('->')
					mover, where = ' '.join(word[where:move]), move + 1
				except: pass
				di = self.lookup(' '.join(word[where:]))
				if not mover:
					order = "S %.3s" % di['nick']
					graph = '%d %d ArrowHold' % (di['x'], di['y'])
				else:
					di2 = self.lookup(mover)
					order = "S %.3s - %-6.6s" % (di2['nick'], di['nick'])
					graph = ("%d %d %d %d ArrowSupport" %
						(di2['x'], di2['y'], di['x'], di['y']))
			#	----
			#	MOVE
			#	----
			elif order[0] == '-':
				where = 0
				while 1:
					try: where += word[where:].index('->') + 1
					except: break
				di = self.lookup(' '.join(word[where:]))
				order = "- %-6.6s" % di['nick']
				graph = ("%d %d Arrow" %
					(di['x'], di['y']) + ('Move', 'Retreat')[section == 'R'])
				if section == 'R': 
					self.retreats += ['%-10s %s %s - ' %
						(power, unit, si['nick']) + di['nick']]
					if msg:
						graph = 'FailedOrder %s OkOrder' % graph
						self.retreats[-1] += ' DESTROYED'
						del self.units[power][-1]
					else: retractions[di['nick']] = len(self.retreats) - 1
				if not msg: self.units[power][-1]['loc'] = di
			#	-------
			#	Disband
			#	-------
			elif order[:2] == 'DI':
				order, graph = '', 'DisbandUnit'
				self.retreats += ['%-10s %s %s DISBAND' %
					(power, unit, si['nick'])]
			#	-------
			#	Arrives
			#	-------
			elif order[0] == 'A':
				order = '- %.3s' % si['nick']
				graph = 'Arrow' + (section == 'R' and 'Retreat' or '') + 'Arrive'
				if section == 'R': self.retreats += ['%-10s %s ??? - ' %
					(power, unit) + si['nick']]
				if di: si = None
			#	-------
			#	Departs
			#	-------
			elif order[:2] == 'DE':
				order = '- ???'
				graph = 'Arrow' + (section == 'R' and 'Retreat' or '') + 'Depart'
				if section == 'R': self.retreats += ['%-10s %s %.3s - ???' %
					(power, unit, si['nick'])]
				
			#	-----
			#	Found
			#	-----
			elif order[0] == 'F':
				order, graph, submsg = '', 'FindUnit', 'FOUND'
				if section == 'R': self.retreats += ['%-10s %s %.3s !' %
					(power, unit, si['nick'])]
			#	----
			#	Lost
			#	----
			elif order[0] == 'L':
				order, graph, submsg = '', 'LoseUnit', 'LOST'
				if section == 'R': self.retreats += ['%-10s %s %.3s ?' %
					(power, unit, si['nick'])]
			#	---------------------
			#	Simple order position
			#	---------------------
			else:
				order, graph = '', ''
				if section == 'R':
					self.retreats += ['%-10s %s ' % (power, unit) + si['nick']]

			#	----------------------------------------------------
			#	Add information (order and graphic arrow) to the map
			#	----------------------------------------------------
			if section in 'MSA': 
				if msg == 'DISLODGED' and si: 
					dislodgements[si['nick']] = len(self.orders)
				elif di:
					successes[di['nick']] = len(self.orders)
				self.orders += [' %c %.3s %-15s ' %
					(unit, si and si['nick'] or '???', order) + (msg and msg or submsg)]
			if graph and section in 'MRA': graphics += ['%s%d %d ' %
				(msg and 'FailedOrder ' or '', (si or di)['x'],
				(si or di)['y']) + graph + (msg and ' OkOrder' or '')]

		#	------------------------------------------------------
		#	Finished reading the map.  Display any unfinished page
		#	------------------------------------------------------
		if self.pages:
			#	---------------------------
			#	Display any unfinished page
			#	---------------------------
			if self.started: self.endPage()
			#	---------------------------------------------------------------
			#	If the last page was movement, add final page showing positions
			#	---------------------------------------------------------------
			if lastSection != 'S' and self.units:
				self.positions(name, season, year)
			#	-------------------
			#	Finish the document
			#	-------------------
			self.endDoc()
	#	----------------------------------------------------------------------
	def addUnit(self, power, unit, where, built = None):
		self.units.setdefault(power, []).append(
			{'type': unit, 'loc': where, 'built': built})
	#	----------------------------------------------------------------------
	def reportSCOwner(self):
		fmt = '(%-11s %-7s %s) WriteOwner\n'
		#	-------------------
		#	SC ownership report
		#	-------------------
		if self.owner:
			self.outFile.write('OwnerReport\n')
			#	-------------------------------------------------
			#	Copy all powers in ownerOrder to seq, and reorder
			#	vassals below their masters, removing all vassals
			#	with no units or SCs.  We assume that vassals
			#	cannot have vassals themselves.
			#	-------------------------------------------------
			seq = self.ownerOrder[:]
			for power in [x for x in self.vassals if x in seq]:
				if not power in self.units and not power in self.owner:
					seq.remove(power)
					continue
				controller = self.vassals[power]
				if not controller in seq:
					#	Insert controller in ownerOrder
					#	before any dummies (attempt).
					seq.append(controller)
					prevOwner = ''
					for owner in [x for x in seq if x[0] != ' ']:
						if (owner == 'UNOWNED' or owner > controller
						or owner < prevOwner):
							seq.pop()
							seq.insert(seq.index(owner), controller)
							break
						prevOwner = owner
				seq.remove(power)
				seq.insert(seq.index(controller) + 1, ' ' + power)
			# Remove all powers with no units, SCs or vassals.
			for owner, idx in [(x, seq.index(x) + 1) for x in seq if x[0] != ' '
			and not self.units.get(x, 0)]:
				if idx >= len(seq) or seq[idx][0] != ' ': seq.remove(owner)
			for owner in seq:
				power = owner.lstrip()
				status = power == 'UNOWNED' and ' ' or ('(%d/%d)' %
					(len(self.units.get(power, [])),
					len(self.owner.get(power, []))))
				temp = (fmt %
					(owner, status, ' '.join(self.owner.get(power, []))))
				self.outFile.write(temp.encode('latin-1'))
		#	-------------
		#	SC coloration
		#	-------------
		self.outFile.write(self.sc.encode('latin-1'))
	#	----------------------------------------------------------------------
	def startDoc(self, mapFile):
		try: file = open(mapFile + '.ps', 'rU', encoding = 'latin-1')
		except: 
			try: file = open(mapFile, 'rU', encoding = 'latin-1')
			except: raise CannotOpenPostScriptFile
		info = 0
		for line in file.readlines():
			word = line.strip().upper().split()
			if word[:2] == ['%', 'MAP']: info = 0
			elif word[:2] == ['%', 'INFO']: info = 1
			elif info:
				try: self.map += [{	'x': int(word[1]), 'y': int(word[2]),
									'nick': word[3], 'name': ' '.join(word[4:])
								 }]
				except: raise BadSiteInfoLine
			else: self.outFile.write(line.encode('latin-1'))
		file.close()
		self.outFile.write('/DrawNames {\n')
		for data in [x for x in self.map if '/' not in x['nick']]:
			temp = '%(x)d %(y)d (%(nick)s) DrawName\n' % data
			self.outFile.write(temp.encode('latin-1'))
		self.outFile.write('} bind def\n')
		self.pages, self.started = 0, None
	#	----------------------------------------------------------------------
	def endDoc(self):
		temp = (
			'%%%%Trailer\n'
			'%%%%Pages: %d 1\n' % self.pages)
		self.outFile.write(temp.encode('latin-1'))
		self.outFile.close()
		try: os.chmod(self.outFileName, 0666)
		except: pass
	#	----------------------------------------------------------------------
	def startPage(self, title = None):
		self.pages += 1
		self.started = 1
		temp = ("%%%%Page: %d %d\n" 
				"DrawMap\nDrawNames\n" % (self.pages, self.pages))
		self.outFile.write(temp.encode('latin-1'))
		if title:
			self.outFile.write(('(%s) DrawTitle\n' % title).encode('latin-1'))
		#	-------------------------------------
		#	SC ownership report and SC coloration
		#	-------------------------------------
		if self.scBefore:
			self.reportSCOwner()
	#	----------------------------------------------------------------------
	def endPage(self):
		#	--------------
		#	Order report
		#	--------------
		if self.orders:
			self.outFile.write('OrderReport\n')
			for order in self.orders:
				temp = '(%s) WriteOrder\n' % order
				self.outFile.write(temp.encode('latin-1'))
			self.orders = []
		#	--------------
		#	Retreat report
		#	--------------
		if self.retreats:
			self.outFile.write('RetreatReport\n')
			for order in sorted(self.retreats):
				temp = '(%s) WriteRetreat\n' % order
				self.outFile.write(temp.encode('latin-1'))
			self.retreats = []
		#	-----------------
		#	Adjustment report
		#	-----------------
		if self.adj:
			self.outFile.write('AdjustReport\n')
			for power in [x for x in sorted(self.adj)
				if x not in self.ownerOrder]: self.ownerOrder.append(power)
			for power in [x for x in self.ownerOrder if x in self.adj]:
				temp = ('(%-10s %s %s) WriteAdjust\n' %
					(power, self.adj[power][0], ', '.join(self.adj[power][1:])))
				self.outFile.write(temp.encode('latin-1'))
			self.adj = {}
		#	-------------------------------------
		#	SC ownership report and SC coloration
		#	-------------------------------------
		if not self.scBefore: 
			self.reportSCOwner()
		#	---------------
		#	Page terminator
		#	---------------
		temp = ("\nBlack\n"
				"ShowPage\n"
				"%%%%PageTrailer\n")
		self.outFile.write(temp.encode('latin-1'))
		self.started = 0
	#	----------------------------------------------------------------------
	def lookup(self, name):
		for loc in self.map:
			#	----------------------------------------------------------
			#	Check for "XXX" and also for "THE XXX" in case a placename
			#	starts with the word "THE" (all the "THE"s are taken out).
			#	----------------------------------------------------------
			if name in loc.values() or 'THE ' + name in loc.values():
				return loc
		sys.stdout.write(('CANNOT LOOKUP %s\n' % name).encode('latin-1'))
		raise OhCrap 
	#	----------------------------------------------------------------------
	def positions(self, name = None, season = None, year = None):
		complete = not self.started
		if complete: self.startPage('%s, After %s %d' % (name, season, year))
		temp = ''
		[self.ownerOrder.append(x) for x in sorted(self.units)
			if x not in self.ownerOrder]
		for time in ('', 'OrderReport\n'):
			temp += time
			for power in [x for x in self.ownerOrder
				if x in self.units and self.units[x]]:
				if power in self.vassals:
					temp += (time and '(%s (%s)) WriteOrder\n'
					or '%s ControlledBy %s\n') % (power, self.vassals[power])
				else: temp += (time and '(%s) WriteOrder\n' or '%s\n') % power
				for unit in self.units[power]:
					if time: temp += '( %c %s) WriteOrder\n' % (unit['type'],
						unit['loc']['nick'])
					else: temp += '\t%d %d Draw%s\n' % (unit['loc']['x'],
						unit['loc']['y'],
						('Fleet', 'Army')[unit['type'] == 'A'])
		self.outFile.write(temp.encode('latin-1'))
		if complete: self.endPage()
	#	----------------------------------------------------------------------

if __name__ == '__main__':
	if len(sys.argv) == 1:
		sys.argv += [os.path.dirname(sys.argv[0]) + '/maps/standard']
	if len(sys.argv) == 2: sys.argv += [0]
	if len(sys.argv) > 3 or sys.argv[1] == '-?':
		temp = ('Usage: %s [.../mapDir/mapName] [viewer] '
				'< resultsFile > outputPSfile\n' %
			os.path.basename(sys.argv[0]))
		sys.stderr.write(temp.encode('latin-1'))
	else: PostScriptMap(sys.argv[1], 0, 0, sys.argv[2])

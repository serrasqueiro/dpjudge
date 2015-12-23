#!/usr/bin/env python -SO

import sys
import os
from codecs import open

class PostScriptMap:
	#	----------------------------------------------------------------------
	#	Parameters:
	#		split: Display minor phases on separate pages or not
	#		 0: Merge retreat and adjustment with movement
	#		 1: Display adjustment on separate page
	#		 2: Display retreat and adjustment together on separate page
	#		 3: Display retreat and adjustment on separate pages
	#	----------------------------------------------------------------------
	def __init__(self, mapFile, inFile = 0, outFile = 0, viewer = 0, split = 1):
		try: 
			if inFile:
				input = open(inFile, 'r', 'latin-1')
				lines = input.readlines()
				input.close()
			else: lines = [unicode(x, 'latin-1') for x in sys.stdin.readlines()]
		except: raise CannotOpenResultsFile
		self.outFileName = outFile
		try: self.outFile = outFile and open(outFile, 'w') or sys.stdout
		except: raise CannotOpenOutputFile
		if viewer: viewer = viewer.upper()
		self.pages, self.sc, show = 0, '', 1
		self.started = self.scBefore = section = lastSection = lastLine = None
		power = powerDecl = powerRedecl = powerOrder = season = year = None
		self.map, self.lang, self.LANG = [], dict(), dict()
		self.orders, self.retreats, self.ownerOrder = [], [], []
		self.owner, self.adj, self.units, self.discoveries = {}, {}, {}, {}
		self.vassals, self.error, self.errorPhase = {}, [], None
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
				show = not word[1:] or (viewer or 'MASTER') in word[1:]
				continue
			if not show: continue
			copy = ' '.join(word)

			if 'VASSAL' in word:
				participants = line.upper().split(' IS A VASSAL OF')
				if len(participants) == 2:
					self.vassals[participants[0]] = participants[1].strip()[:-1]
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
				self.owner = {}
			elif ' '.join(word[:2]) == 'THE FOLLOWING':
				where, section = 0, 'D'
				continue
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
						title += self.translate('Game Start', 1)
					else:
						season, year = lowWord[where + 1:where + 3]
						if year == 'of': year = lowWord[where + 3]
						year = int(float(year))  # "year" has a period at end
						if lowWord[-1][0] == '(' and lowWord[-1][-1] == ')':
							title += season + (' ' + self.translate(
								'Retreat', 1)) * (split > 1 and
								section == 'R') + ' ' + `year`
							self.errorPhase = lowWord[-1][1:-1].split('.')[-1]
							if viewer:
								self.errorPhase = viewer + '.' + self.errorPhase
				#	------------
				#	Prepare page
				#	------------
				if section in 'MS' + 'A' * (split % 2) + 'R' * (split > 1):
					if self.started: self.endPage()
					self.scBefore = self.pages
					self.startPage(title)
					if section in 'RA': self.positions()
					else: self.units = {}
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
						powerDecl = (self.vassals[power] + ' Controls ' +
							powerDecl)
						powerOrder += ' (' + self.vassals[power] + ')'
					powerRedecl = powerDecl

			#	--------------------------------------------
			#	Lines signaling the end of the phase results
			#	--------------------------------------------
			if filter(line.upper().startswith,
				('THE DEADLINE ', 'THE NEXT PHASE ', 'DEADLINE ',
				'THE GAME IS ', 'ORDERS ', 'END')): section = None

			#	------------------------------
			#	Check if the section has ended
			#	------------------------------
			if section in ('OWN', None):
				#	---------------------
				#	Write the information
				#	---------------------
				for graphic in graphics:
					self.outFile.write((graphic + '\n').encode('latin-1'))
				power = powerDecl = powerRedecl = powerOrder = None
				if section: section = 'O'
				continue

			#	----------------
			#	Center ownership
			#	----------------
			if section == 'O':
				if 'SUPPLY' in word or 'LOST.' in word or 'FOUND.' in word:
					# Reset order and change section - Not good, as in blind
					# games not all visible powers are listed.
					section = 'U'
				else:
					if power not in self.ownerOrder: raise PowerNotInPS
					scList += ' ' + ' '.join(word[line[0] != ' ':])
					if scList[-1] == '.':
						self.owner[power], scList = [], scList[:-1]
						if powerDecl:
							self.sc += powerDecl + '\n'
							powerDecl = None
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
				if 'SUPPLY' in word:
					if power not in self.ownerOrder: raise PowerNotInPS
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
					torn = 'ALLEGIANCE' in word[upto:]
					for pow in self.units:
						piece = self.findUnit(pow, where, torn,
							'D' * (not torn))
						if piece:
							piece['state'] = 'X'; break
					else:
						self.addError('NO UNIT TO DESTROY IN ' + where['name'])
						continue
					if 'line' in piece:
						idx, res = piece['line'], ('DESTROYED', 'TORN')[torn]
						if piece['phase'] in 'MP':
							self.orders[idx] = ('%-22s %s' %
								(self.orders[idx][:22], self.translate(res)))
						elif piece['phase'] == 'R':
							self.retreats[idx] += (' ' + self.translate(res))
					graphics += [('%d %d DestroyUnit' %
						(piece['loc']['x'], piece['loc']['y']))]
				continue

			#	-------------------------------------------------------
			#	Adjustment orders (modify the units list for final map)
			#	-------------------------------------------------------
			if word[1] in ('DEFAULTS,', 'REMOVES', 'BUILDS', 'BUILD'):
				if power not in self.adj: self.adj[power] = [
				self.translate(word[1][0] == 'B' and 'BUILDS' or 'REMOVES',
				0, ['BUILDS', 'REMOVES'])]
				if word[2][:5] == 'WAIVE':
					self.adj[power] += [self.translate('WAIVED')]
					continue
				elif word[2][:6] == 'HIDDEN':
					self.adj[power] += [self.translate('HIDDEN')]
					continue
				which = 3 + (word[1][0] == 'D')
				unit = word[which][0]
				which += 2
				where = ' '.join(word[which + (word[which] == 'THE'):])
				where = self.lookup(where.split('.')[0])
				temp = ''
				if word[1][0] != 'B':
					piece, draw = self.findUnit(power, where, 1 - split % 2), 0
					if piece: 
						if piece['type'] != unit:
							self.addError('UNIT MISMATCH: %s %s %s BECAME %s' %
								(power, piece['type'], where['name'], unit))
					else:
						piece, draw = self.addUnit(power, unit, where, 'A'), 1
				else:
					draw = 1
					if split % 2 == 0:
						for pow in self.units:
							if self.findUnit(pow, where, split == 2):
								draw = 0; break
					piece = self.addUnit(power, unit, where, 'A')
				where = piece['loc']
				if draw:
					if powerDecl:
						temp += powerDecl + '\n'
						powerDecl = None
					temp += ('\t%d %d Draw%s\n' % (where['x'], where['y'],
						('Fleet', 'Army')[unit == 'A']))
				if word[1][0] != 'B':
					temp += ('\t%d %d RemoveUnit\n' % (where['x'], where['y'])) 
					piece['state'] = 'X'
				else:
					temp += ('\t%d %d BuildUnit\n' % (where['x'], where['y'])) 
					piece['state'] = 'B'
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
			
			#	---------------------------------
			#	Find the unit or add if not found
			#	---------------------------------
			draw, state, submsg = 0, 'H', ''
			phase = section == 'R' and 'R' or 'M'
			if order[0] == 'D': state = 'X'
			elif order[0] == 'L': state = 'L'
			elif order[0] == 'A': di, si, state = si, None, 'A'
			elif order[0] != '-': di = si
			else:
				where = 0
				while 1:
					try: where += word[where:].index('->') + 1
					except: break
				di = self.lookup(' '.join(word[where:]))
				if not msg: state = 'M' 
			if 'DISLODGED' in msg: msg, state = 'DISLODGED', 'D'
			if not si:
				piece, draw = self.addUnit(power, unit, None, phase, state), 0
			elif split > 1 and section == 'R':
				piece, draw = self.addUnit(power, unit, si, 'R', state), -1
			else:
				after = section in 'RDU' and state != 'M'
				piece = self.findUnit(power, si, after)
				if piece: 
					if piece['type'] != unit:
						self.addError('UNIT MISMATCH: %s %s %s BECAME %s' %
							(power, piece['type'], si['name'], unit))
						piece['type'] = unit
					piece['state'] = state
					if after:
						di = di or si
						si = piece.get('loc')
					#if piece['state'] not in 'HD':
						#piece, draw = self.addUnit(power, unit, si, phase,
						#	state), 1 - after
				else:
					#self.addError('UNIT NOT FOUND: %s %s %s' %
					#	(power, unit, si['name']))
					piece, draw = self.addUnit(power, unit, si, phase, state), 1
			if state in 'MA': piece['dest'] = di

			#	-------------
			#	Draw the unit
			#	-------------
			if draw:
				if draw == 1: pi = si
				else: pi = di
				if pi:
					temp = ''
					if powerDecl:
						temp += powerDecl + '\n'
						powerDecl = None
					temp += ("\t%d %d Draw%s\n" %
						(pi['x'], pi['y'], ('Fleet', 'Army')[unit == 'A']))
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
				di1 = self.lookup(' '.join(word[where:]))
				if not mover:
					order = "S %.3s" % di1['nick']
					graph = '%d %d ArrowHold' % (di1['x'], di1['y'])
				else:
					di2 = self.lookup(mover)
					order = "S %.3s - %-6.6s" % (di2['nick'], di1['nick'])
					graph = ("%d %d %d %d ArrowSupport" %
						(di2['x'], di2['y'], di1['x'], di1['y']))
			#	----
			#	MOVE
			#	----
			elif order[0] == '-':
				order = "- %-6.6s" % di['nick']
				graph = ("%d %d Arrow" %
					(di['x'], di['y']) + ('Move', 'Retreat')[section == 'R'])
				if not msg: piece['dest'] = di
			#	-------
			#	Disband
			#	-------
			elif order[:2] == 'DI':
				order, graph, submsg = '', 'DisbandUnit', 'DISBAND'
			#	-------
			#	Arrives
			#	-------
			elif order[0] == 'A':
				order = '- %.3s' % (di or si)['nick']
				graph = 'Arrow' + ('Arrive', 'Refuge')[section == 'R'] + (
					'Fleet', 'Army')[unit == 'A']
				if powerRedecl:
					graphics += [powerRedecl]
					powerRedecl = None
			#	-------
			#	Departs
			#	-------
			elif order[:2] == 'DE':
				order = '- ???'
				graph = 'Arrow' + ('Depart', 'Flee')[section == 'R']
				
			#	-----
			#	Found
			#	-----
			elif order[0] == 'F':
				order, graph, submsg = '', 'FindUnit', 'FOUND'
				if section in 'DRA': 
					self.discoveries.setdefault(section, {}).setdefault(
						power + ' F', []).append(unit + ' ' + si['nick'])
			#	----
			#	Lost
			#	----
			elif order[0] == 'L':
				order, submsg = '', 'LOST'
				graph = 'Lose' + 'Arrive' * (not si) + 'Unit'
				if section in 'DRA': 
					self.discoveries.setdefault(section, {}).setdefault(
						power + ' L', []).append(unit + ' ' +
						(di or si)['nick'])
			#	---------------------
			#	Simple order position
			#	---------------------
			else:
				order, graph = '', ''

			#	----------------------------------------------------
			#	Add information (order and graphic arrow) to the map
			#	----------------------------------------------------
			if section in 'MS': 
				if powerOrder:
					self.orders += [powerOrder]
					powerOrder = None
				piece['line'] = len(self.orders)
				self.orders += [' %c %.3s %-15s ' %
					(unit, si and si['nick'] or '???', order) + 
					self.translate(msg and msg or submsg)]
			elif section == 'R':
				if msg:
					msg = 'DESTROYED'
					piece['state'] = 'X'
				piece['line'] = len(self.retreats)
				if not submsg or submsg[0] not in 'FL':
					self.retreats += ['%-10s %c %.3s ' %
						(power, unit, si and si['nick'] or '???') +
						(order and order + ' ' or '') + 
						self.translate(msg and msg or submsg)]
			if graph and section in 'MDRA': graphics += ['%s%d %d ' %
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
			if lastSection != 'S':
				self.positions(name, season, year)
			#	-------------------
			#	Finish the document
			#	-------------------
			self.endDoc()
	#	----------------------------------------------------------------------
	def addUnit(self, power, unit, where, phase, state = 'H'):
		piece = {'type': unit, 'loc': where, 'phase': phase, 'state': state} 
		self.units.setdefault(power, []).append(piece)
		return piece
	#	----------------------------------------------------------------------
	def findUnit(self, power, where, after = 0, state = None):
		for piece in self.units.get(power, [])[:]:
			loc = after and piece.get('dest') or piece.get('loc')
			if loc and loc['nick'] == where['nick'] and (not state
				or state == piece['state']): return piece
		else: return None
	#	----------------------------------------------------------------------
	def reportSCOwner(self):
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
			for owner in [x for x in seq if x[0] != ' ']:
				if not len(self.units.get(owner, [])) and not len(self.owner.get(owner, [])):
					idx = seq.index(owner)
					if idx + 1 == len(seq) or seq[idx + 1][0] != ' ':
						seq.remove(owner)
			for owner in seq:
				power = owner.lstrip()
				status = ' '
				if power == 'UNOWNED':
					status = '%-18s' % self.translate('UNOWNED')
				else:
					status = ('(%d/%d)' % (len(self.units.get(power, [])),
						len(self.owner.get(power, []))))
					status = '%-10s %-7s' % (owner, status)
				temp = ('(%s %s) WriteOwner\n' %
					(status, ' '.join(self.owner.get(power, []))))
				self.outFile.write(temp.encode('latin-1'))
		#	-------------
		#	SC coloration
		#	-------------
		self.outFile.write(self.sc.encode('latin-1'))
	#	----------------------------------------------------------------------
	#	Searches the ps-file for all procedures required for DPmap.
	#	If one is not found, it will be replaced by a stub.
	#	This will normally consist of popping off its parameters.
	#	In the array of tuples below, the first parameter is the name, the 
	#	second is the number of parameters (0 by default).
	#	Note that tuples that only consist of 1 parameter still require a ','
	#	at the end, otherwise they will be parsed as mere strings.
	#	For a different stub behavior, write out the stub at the end of this 
	#	method.
	#	Furthermore extracts the territory coordinates from the INFO section
	#	and the language terms from the LANG section at the start of the file.
	#	In addition tries to find all powers to get an idea of the power order
	#	to use.
	#	----------------------------------------------------------------------
	def startDoc(self, mapFile):
		try: file = open(mapFile + '.ps', 'rU', encoding = 'latin-1')
		except: 
			try: file = open(mapFile, 'rU', encoding = 'latin-1')
			except: raise CannotOpenPostScriptFile

		self.procs = [];
		# Basic procedures
		# Note: The stub for ShowPage executes showpage.
		self.procs += [
			('ShowPage',),
		]
		# Text procedures
		self.procs += [
			('DrawTitle', 1), 
			('OrderReport',), ('RetreatReport',), ('OwnerReport',), ('AdjustReport',), 
			('WriteOrder', 1), ('WriteRetreat', 1), ('WriteOwner', 1), ('WriteAdjust', 1), 
		]
		# Basic map draw procedures
		# Note: The stub for DrawNames calls DrawName on every province name.
		self.procs += [
			('DrawMap',),
			('DrawNames',), ('DrawName', 3),
			('DrawArmy', 2), ('DrawFleet', 2), 
		]
		# Basic orders
		self.procs += [
			('OkOrder',), ('FailedOrder',), 
			('ArrowMove', 4), ('ArrowHold', 4),
			('ArrowSupport', 6), ('ArrowConvoy', 6), 
			('ArrowRetreat', 2), 
		]
		# Supply centers
		#	Note: For the procedure supply, it's not possible to judge how many
		#	parameters are on the stack. The bigger problem is that the supply
		#	center procs themselves might not be defined, so a more thorough
		#	solution might be not to generate these lines at all.
		self.procs += [
			('supply',), 
		]
		# Build/destroy orders 
		self.procs += [
			('BuildUnit', 2),
			('DestroyUnit', 2), ('DisbandUnit', 2), ('RemoveUnit', 2),  
		]
		# Blind orders 
		self.procs += [
			('ArrowArriveArmy', 2), ('ArrowArriveFleet', 2), ('ArrowDepart', 2),
			('ArrowRefugeArmy', 2), ('ArrowRefugeFleet', 2), ('ArrowFlee', 2),
			('ArrowSupportArrive', 4), ('ArrowSupportDepart', 4),
			('ArrowConvoyArrive', 4), ('ArrowConvoyDepart', 4),
			('FindUnit', 2),
			('LoseUnit', 2), ('LoseArriveUnit', 2), ('LoseRefugeUnit', 2),
		]
		# Vassal orders 
		self.procs += [
			('Controls',),
		]

		procsNeeded = dict.fromkeys([p[0] for p in self.procs])

		info, blank, visit, endSetup, self.ownerOrder = 0, 0, 0, None, []
		for line in file.readlines():
			word = line.split()
			upWord = [x.upper() for x in word]
			if upWord[:2] == ['%', 'MAP']: info = 0; blank *= 2
			elif upWord[:2] == ['%', 'INFO']: info = 1
			elif upWord[:2] == ['%', 'LANG']: info = 2
			elif info == 1:
				try: self.map += [{	'x': int(upWord[1]), 'y': int(upWord[2]),
									'nick': upWord[3], 'name': ' '.join(upWord[4:])
								 }]
				except: raise BadSiteInfoLine
			elif info == 2:
				word = map(lambda x: x.strip(), ' '.join(word[1:]).split('='))
				try: self.lang[word[0]], self.LANG[word[0].upper()] = word[1], word[1].upper()
				except: raise BadLangLine
			elif visit == 1:
				if not word: pass
				elif word[0][0] == '/': 
					power = word[0][1:]
					if power == power.upper(): self.ownerOrder.append(power)
				elif word[0][0] == '}': visit = 0
				self.outFile.write(line.encode('latin-1'))
			elif not word:
				if endSetup: endSetup += '\n'
				elif blank < 2: self.outFile.write('\n')
				blank = 1
			elif word[0] == '%%EndSetup':
				blank = 0
				if endSetup:
					self.outFile.write(endSetup.encode('latin-1'))
				endSetup = line
			elif word[0][0] == '%':
				blank = 0
				if endSetup: endSetup += '\n' + line
				else: self.outFile.write(line.encode('latin-1'))
			else:
				blank = 0
				if endSetup:
					self.outFile.write(endSetup.encode('latin-1'))
					endSetup = None
				if word[0][0] == '/':
					proc = word[0][1:]
					if proc == 'VisitPowers' or proc == 'Powers': visit = 1
					elif proc == proc.upper() and (word[-1] == 'AddCountry' 
						or 'set_country' in word or 'set_country}' in word): 
						self.ownerOrder.append(proc)
					else:
						try: del procsNeeded[proc]
						except: pass
				self.outFile.write(line.encode('latin-1'))
		file.close()
		
		if not self.ownerOrder: raise NoPowersFoundInPS
		self.ownerOrder.remove('UNOWNED'); self.ownerOrder.append('UNOWNED')

		if procsNeeded.keys():
			self.outFile.write('% Stubs\n')
			for p in self.procs:
				if not p[0] in procsNeeded: continue
				self.outFile.write('/%s where {pop} { /%s {' % (p[0], p[0]))
				if len(p) == 2:
					self.outFile.write(' '.join(['pop'] * p[1]))
				elif p[0] == 'ShowPage':
					self.outFile.write('showpage')
				elif p[0] == 'DrawNames':
					self.outFile.write('\n')
					for data in [x for x in self.map if '/' not in x['nick']]:
						temp = '\t%(x)d %(y)d (%(nick)s) DrawName\n' % data
						self.outFile.write(temp.encode('latin-1'))
				self.outFile.write('} bind def } ifelse\n')
		if endSetup:
			self.outFile.write(endSetup.encode('latin-1'))
			
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
		#	----------------------------------------------------------
		#	First move the units to their new positions or remove them
		#	----------------------------------------------------------
		for power, units in self.units.items():
			units = [x for x in units if x['state'] not in 'XDL']
			for piece in units:
				if piece['state'] in 'MA':
					piece['loc'] = piece['dest']
					del piece['dest']
				piece['state'] = 'H'
			self.units[power] = units
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
		if self.retreats or 'R' in self.discoveries or 'D' in self.discoveries:
			self.outFile.write('RetreatReport\n')
		if self.retreats:
			for order in sorted(self.retreats):
				temp = '(%s) WriteRetreat\n' % order
				self.outFile.write(temp.encode('latin-1'))
			self.retreats = []
		for sect in 'DR':
			for powered in sorted(self.discoveries.get(sect, [])):
				temp = ('(%-10s %s %s) WriteRetreat\n' %
					(powered[:-2], ', '.join(self.discoveries[sect][powered]),
					self.translate(powered[-1] == 'F' and 'FOUND' or 'LOST')))
				self.outFile.write(temp.encode('latin-1'))
		#	-----------------
		#	Adjustment report
		#	-----------------
		if self.adj or 'A' in self.discoveries:
			self.outFile.write('AdjustReport\n')
		if self.adj:
			for power in [x for x in self.ownerOrder if x in self.adj]:
				temp = ('(%-10s %s %s) WriteAdjust\n' %
					(power, self.adj[power][0], ', '.join(self.adj[power][1:])))
				self.outFile.write(temp.encode('latin-1'))
			self.adj = {}
		if 'A' in self.discoveries:
			for powered in sorted(self.discoveries['A']):
				temp = ('(%-10s %s %s) WriteAdjust\n' %
					(powered[:-2], ', '.join(self.discoveries['A'][powered]),
					self.translate(powered[-1] == 'F' and 'FOUND' or 'LOST')))
				self.outFile.write(temp.encode('latin-1'))
		self.discoveries = {}
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
	def translate(self, term, case = 0, alternatives = None):
		altLen = 0
		if alternatives:
			altLen = max(map(lambda x: len(self.translate(x, case)), alternatives))
		if case: return ('%-' + str(altLen) + 's') % (self.lang.get(term, term))
		else: return ('%-' + str(altLen) + 's') % (self.LANG.get(term.upper(),
			term.upper()))
	#	----------------------------------------------------------------------
	def addError(self, err):
		self.error.append('%s: %s' % (self.errorPhase, err))
	#	----------------------------------------------------------------------
	def positions(self, name = None, season = None, year = None):
		complete = not self.started
		if complete: self.startPage('%s, After %s %d' % (name, season, year))
		self.orders, graphics = [], ''
		for power in [x for x in self.ownerOrder
			if x in self.units and self.units[x]]:
			if power in self.vassals:
				self.orders += ['%s (%s)' % (power, self.vassals[power])]
				graphics += '%s Controls %s\n' % (self.vassals[power], power)
			else:
				self.orders += [power]
				graphics += power + '\n'
			for unit in self.units[power]:
				unit['phase'], unit['line'] = 'P', len(self.orders) 
				self.orders += [' %c %s' % (unit['type'], unit['loc']['nick'])]
				graphics += '\t%d %d Draw%s\n' % (unit['loc']['x'],
					unit['loc']['y'], ('Fleet', 'Army')[unit['type'] == 'A'])
		self.outFile.write(graphics.encode('latin-1'))
		if complete: self.endPage()
		
	#	----------------------------------------------------------------------

if __name__ == '__main__':
	if len(sys.argv) == 1:
		sys.argv += [os.path.dirname(sys.argv[0]) + '/maps/standard']
	if len(sys.argv) == 2: sys.argv += [0]
	if len(sys.argv) == 3: sys.argv += [1]
	if len(sys.argv) == 4: sys.argv += [0]
	if len(sys.argv) == 5: sys.argv += [0]
	if len(sys.argv) > 6 or sys.argv[1] == '-?':
		temp = ('Usage: %s [.../mapDir/mapName]'
			' [viewer] [split] [resultsFile] [outputPSfile]'
			' < resultsFile > outputPSfile\n' %
			os.path.basename(sys.argv[0]))
		sys.stderr.write(temp.encode('latin-1'))
	else:
		map = PostScriptMap(sys.argv[1],
			sys.argv[4], sys.argv[5], sys.argv[2], int(sys.argv[3]))
		if map.error: sys.stderr.write('\n'.join(map.error).encode('latin-1') + '\n')

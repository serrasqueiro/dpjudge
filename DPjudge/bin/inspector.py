import re, sys, urllib
from DPjudge import *
from DPjudge.bin.check import Check
from DPjudge.variants.dppd import *

class Inspector(object):
	"""
	Supporter class for inspect
	"""
	#	----------------------------------------------------------------------
	def __init__(self):
		self.updateVars()
	#	----------------------------------------------------------------------
	def __repr__(self):
		if self.game: return self.game.__repr__()
		return super(Inspector, self).__repr__()
	#	----------------------------------------------------------------------
	def load(self, gameName = None):
		import re
		game = None
		if gameName:
			game = Status().load(gameName)
		elif gameName is None:
			if not self.game:
				print 'No game name specified or loaded.'
				return
			gameName = self.game.name
			game = Status().load(gameName)
		if game:
			if game.error: print '\n'.join(game.error)
			self.__class__ = type(game.__class__.__name__ + 'Inspector',
				(Inspector, game.__class__), {})
			self.__dict__ = game.__dict__
			self.updateVars(game)
			print('Loaded game %s' % gameName)
		else:
			self.__class__ = type('Inspector', (Inspector,), {})
			self.__dict__ = dict()
			self.updateVars()
			print('Loaded no game')
	#	----------------------------------------------------------------------
	def process(self, now = 0, email = None):
		if not self.game: return 'No game loaded'
		result = self.game.process(now, email)
		self.updateVars(self.game)
		return result
	#	----------------------------------------------------------------------
	def rollback(self, phase = None, includeFlags = 0):
		if not self.game: return 'No game loaded'
		result = self.game.rollback(phase, includeFlags)
		self.updateVars(self.game)
		return result
	#	---------------------------------------------------------------------
	def rollforward(self, phase = None, includeFlags = 4):
		if not self.game: return 'No game loaded'
		result = self.game.rollforward(phase, includeFlags)
		self.updateVars(self.game)
		return result
	#	----------------------------------------------------------------------
	def check(self, gameNames = None):
		if gameNames is None:
			if not self.game:
				print 'No game loaded'
				return
			gameNames = [self.game.name]
		argv = ['inspect.check', '-a'] + gameNames
		Check(argv)
	#	----------------------------------------------------------------------
	def purge(self, gameName = None):
		if gameName is None:
			if not self.game:
				print 'No game loaded'
				return
			gameName = self.game.name
		errors = Status().purgeGame(gameName, 1)
		if not errors: print('Game %s purged.' % gameName)
		else: print('\n'.join(errors))
	#	----------------------------------------------------------------------
	def rename(self, gameName, toGameName = None):
		if toGameName is None:
			if not self.game:
				print 'No game loaded'
				return
			gameName, toGameName = self.game.name, gameName
		errors = Status().renameGame(gameName, toGameName, 1)
		if errors: print('\n'.join(errors))
		else:
			print('Game %s renamed to %s.' % (gameName, toGameName))
			self.load(toGameName)
	#	----------------------------------------------------------------------
	def connect(self):
		dppd = DPPD()
		db = dppd.db
		self.makeGlob(locals(), 2)
	#	----------------------------------------------------------------------
	def visit(self, game = None, power = 'MASTER', password = None):
		if not game:
			if not self.game:
				print 'No game loaded'
				return
			game = self.game
		elif not isinstance(game, Game):
			game = Status().load(game)
			if not game:
				print 'No such game'
				return
		query = {'game': game.name}
		if power: 
			powerName = power
			if isinstance(power, Power): powerName = power.name
			elif power.upper() != 'MASTER' and not [1 for x in game.powers
				if x.name in (power.upper(), '_' + power.upper())]:
				print 'No such power'
				return
			if not password: password = game.gm.password
			query.update({'power': powerName, 'password': password})
		self.browse(query, host.dpjudgeURL, 2)
	#	----------------------------------------------------------------------
	def query(self, query = None):
		self.browse(query, host.dppdURL.split(',')[0], 2)
	#	----------------------------------------------------------------------
	def browse(self, query = None, address = None, depth = 1):
		if not address: address = host.dpjudgeURL
		if isinstance(query, dict): query = urllib.urlencode(query)
		if query: address += ('?', '&')['?' in address] + query
		page = urllib.urlopen(address)
		result = page.read()
		page.close()
		if 'DPjudge Error' in result:
			try:
				trace = result[result.rindex('<!--') + 4:result.rindex('-->')
					].strip('\n\t')
				print trace
			except: print result
		else: print result
		self.makeGlob(locals(), depth + 1)
	#	----------------------------------------------------------------------
	def eval(self, expr, depth = 1):
		for name, var in self.varNames.items():
			expr = re.sub(r'\b%s\b' % re.escape(name), var, expr)
		return eval(expr, sys._getframe(depth).f_globals)
	#	----------------------------------------------------------------------
	def updateVars(self, game = None, depth = 2):
		self.game, self.vars, self.varNames = game, dict(), dict()
		if game:
			self.vars[self.makeVar(game.name, 'G')] = self
			self.vars['game'] = game
			self.vars['gm'] = self.gm
			self.vars['jk'] = self.jk
			for power in game and game.powers or []:
				self.vars[self.makeVar(power.name, 'P')] = power
		elif 'jk' not in self.vars:
			jk = Power(self, 'JUDGEKEEPER')
			jk.omniscient = 4
			jk.password = host.judgePassword
			jk.address = host.judgekeepers
			self.vars['jk'] = jk
		else: return
		self.makeGlob(self.vars, depth + 1)
	#	----------------------------------------------------------------------
	def makeVar(self, name, initial):
		var = name.lower()[name[0] == '_':]
		var = initial * var[0].isdigit() + re.sub(
			r'\W', '_', var.lower())
		if var != name: self.varNames[name] = var
		return var
	#	----------------------------------------------------------------------
	def makeGlob(self, vars, depth = 1):
		#	-------------------------------------------------------------
		#	The function globals() would just return this module's global
		#	variables. To change the globals in the interpreter, we need
		#	to access the top stack.
		#	-------------------------------------------------------------
		sys._getframe(depth).f_globals.update(vars)
	#	----------------------------------------------------------------------
	def findChain(self, map = None, locs = None, open = 0, report = 0):
		#	-------------------------------------------------------------
		#	Find the longest chain of provinces on a map such that every
		#	province is adjacent to exactly two other provinces, except
		#	(in an open chain) on the extremes.
		#	Parameters:
		#	* map: Map name or Map object
		#	* locs: List of starting locations.
		#	* open: Search for open or closed chain
		#	* report: Report statistics (1), solutions (2) and/or
		#	    intermediate results (3)
		#	Returns the length of the longest chains.
		#	The solutions are stored in self.chains.
		#	For a closed chain it's best to give a list of locations that
		#	divide the board in two by drawing a line through the center
		#	of the board.
		#	For an open chain all locations could potentially be starting
		#	locations, so it's better to leave as is and let the program
		#	sort them from least number of neighbors to most.
		#	-------------------------------------------------------------
		if isinstance(map, Map.Map): pass
		elif map: map = Map(map)
		elif self.game: map = self.game.map
		else: map = Map('standard')
		xlocs = [x.upper() for x in map.locs if len(x) == 3]
		abuts = {x: list(set([y[:3].upper() for y in map.locAbut.get(x, map.locAbut.get(x.lower()))])) for x in xlocs}
		avail = [x for x in xlocs if map.locType.get(x, map.locType.get(x.lower())) != 'SHUT']
		tail = []
		if not locs:
			locs = avail[:]
			locs.sort(key = lambda x: len(abuts[x]))
		elif [1 for x in locs if x not in avail]:
			return 'Error in starting locations list'
		xlen, self.chains, xtime = 0, [], Time.Time()
		for loc in locs:
			xlen = self.launchChain(loc, avail, tail, xlen, xtime, abuts, open, report)
		if report > 1: print('\n'.join(['-'.join(p) for p in self.chains]))
		if report:
			print('Final: max=%d, count=%d, elapsed: %d min.' % (xlen, len(self.chains), xtime.diff(Time.Time(), 60)))
		return xlen
	#	----------------------------------------------------------------------
	def launchChain(self, loc, avail, tail, xlen, xtime, abuts, open, report):
		if report:
			print('Before %s: max=%d, count=%d, elapsed=%d min.' % (loc, xlen, len(self.chains), xtime.diff(Time.Time(), 60)))
		path = [loc]
		avail[:] = [x for x in avail if x != loc]
		if open: tail += [loc]
		avas = [x for x in abuts[loc] if x in avail]
		if open: avail[:] = [x for x in avail if x not in avas]
		else: avas[:1] = []
		for l in avas:
			if not open: avail[:] = [x for x in avail if x != l]
			xlen = self.recurseChain(l, path, avail, tail, xlen, abuts, open, report)
		avail += avas
		if open: avail += [loc]
		return xlen
	#	----------------------------------------------------------------------
	def recurseChain(self, loc, path, avail, tail, xlen, abuts, open, report):
		path += [loc]
		if not open and len(path) > 2 and path[0] in abuts[loc]:
			xlen = self.improveChain(path, xlen, report)
		else:
			avas = [x for x in abuts[loc] if x in avail]
			if not avas:
				if open and loc not in tail:
					xlen = self.improveChain(path, xlen, report)
			else:
				avail[:] = [x for x in avail if x not in avas]
				if open and not [x for x in avail if x not in tail]:
					if loc not in tail:
						xlen = self.improveChain(path, xlen, report)
				else:
					for l in avas:
						xlen = self.recurseChain(l, path, avail, tail, xlen, abuts, open, report)
				avail += avas
		path[-1:] = []
		return xlen
	#	----------------------------------------------------------------------
	def improveChain(self, path, xlen, report):
		if len(path) > xlen:
			xlen, self.chains = len(path), [path[:]]
			if report > 2: print('Max: %d, path = %s' % (xlen, '-'.join(path)))
		elif len(path) == xlen: self.chains += [path[:]]
		return xlen

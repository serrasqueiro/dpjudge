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
	def process(self, now = 0, email = None, roll = 0):
		if not self.game: return 'No game loaded'
		result = self.game.process(now, email, roll)
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
		argv = ['inspect.check', '-a', '-r'] + gameNames
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
			if not password: password = game.password
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
			for power in game and game.powers or []:
				self.vars[self.makeVar(power.name, 'P')] = power
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

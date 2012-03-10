import re, sys
from DPjudge import *
from DPjudge.variants.dppd import *

class Inspector:
	"""
	Supporter class for inspect
	"""
	def __init__(self):
		self.varNames = dict()
	def load(self, gameName):
		import re
		self.vars = dict()
		game = Status().load(gameName)
		if game and game.error: print '\n'.join(game.error)
		self.vars[self.makeVar(gameName, 'G')] = self.vars['self'] = game
		for power in game.powers or []:
			self.vars[self.makeVar(power.name, 'P')] = power
		print 'Loaded', ('game %s' % gameName, 'no game')[not game]
		self.makeGlob(self.vars)
	def loadDb(self):
		dppd = DPPD()
		db = dppd.db
		self.makeGlob(locals())
	def eval(self, expr):
		for name, var in self.varNames.items():
			expr = re.sub(r'\b%s\b' % re.escape(name), var, expr)
		return `expr`
	def makeVar(self, name, initial):
		var = initial * name[0].isdigit() + re.sub(
			r'\W', '_', name.lower())
		if var != name: self.varNames[name] = var
		return var
	def makeGlob(self, vars, depth = 2):
		#	-------------------------------------------------------------
		#	The function globals() would just return this module's global
		#	variables. To change the globals in the interpreter, we need
		#	to access the top stack.
		#	-------------------------------------------------------------
		sys._getframe(depth).f_globals.update(vars)

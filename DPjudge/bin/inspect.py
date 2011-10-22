import os, sys
import host

class Inspect:
	"""
	This class allows for maintenance of any DPjudge game, through invoking
	the Python interpreter to run any specific command or set of commands.
	For example:
		inspect
			will leave you in the Python interpreter, with the DPjudge
			module imported
		inspect denarius
			will leave you in the Python interpreter with variables
			named "denarius" and "self" set to the Game object for the
			game named denarius.  If the game name starts with a digit,
			the variable will have a capital G prepended to it.
			Furthermore there are local variables for each power in the
			game, with names in lower case and all punctuation, including
			spaces and '+'s, replaced by underscores. If the power name 
			starts with a digit, the variable will have a capital P 
			prepended to it.
		inspect "denarius.makeMaps()"
			will make maps for the game "denarius" and will NOT leave
			you in the Python interpreter
		inspect denarius "denarius.makeMaps()"
			will make maps for the game "denarius" and WILL NOT leave you
			in the Python interpreter for further commands
		inspect denarius. "self.makeMaps()"
			will make maps for the game "denarius" and WILL leave you
			in the Python interpreter for further commands
		inspect . host.dpjudge
			will print the dpjudge address and WILL NOT leave you
			in the Python interpreter for further commands
		inspect @ host.dpjudge
			will print the dpjudge address and WILL leave you
			in the Python interpreter for further commands
	"""
	command, interp = ['from DPjudge import *'], 'i'
	if len(sys.argv) > 1:
		arg1 = sys.argv[1]
		game = arg1.split('.')[0].split('@')[0]
		interp = interp * ('.' not in arg1 and len(sys.argv) == 2)
		if game:
			gameVar = game
			if game[0].isdigit():
				gameVar = 'G' + gameVar
				sys.argv = [x.replace(game, gameVar) for x in sys.argv]
			command.extend([
				'import re',
				'%s = self = Status().load(%s)' % (gameVar, `game`),
				"_x_ = locals().update(dict([['%s%s' % ("
				"'P'*_x_.name[0].isdigit(), re.sub("
				"r'\W', '_', _x_.name.lower())), _x_"
				"] for _x_ in self and self.powers or []]))",
				"del locals()['_x_']",
				"print '\n'.join(self and self.error or [])",
				"print 'Loaded', ('game %s','no game')[not self]" % gameVar])
		command.extend([
			'print ' + ' '.join(sys.argv[(
			'.' not in arg1 or not arg1.split('.')[1]) + 1:])])
	os.system("%sPYTHONPATH=%s %s python -%sOc %s" %
		('set '*(os.name == 'nt'), os.path.dirname(host.packageDir),
		('/usr/bin/env', '&')[os.name == 'nt'], interp,
		'"' + `';'.join(command)`[1:-1] + '"'))
	raise SystemExit

#	-----------------------
#	Examine/Update any game
#	-----------------------
Inspect()

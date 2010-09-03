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
		inspect "denarius.makeMaps()"
			will make maps for the game "denarius" and will NOT leave
			you in the Python interpreter
		inspect denarius "denarius.makeMaps()"
			will make maps for the game "denarius" and WILL NOT leave you
			in the Python interpreter for further commands
		 nspect denarius. "self.makeMaps()"
			will make maps for the game "denarius" and WILL leave you
			in the Python interpreter for further commands
	"""
	command, interp = ['from DPjudge import *'], 'i'
	if len(sys.argv) > 1:
		arg1 = sys.argv[1]
		game = arg1.split('.')[0]
		interp = interp * ('.' not in arg1 and len(sys.argv) == 2)
		command.extend(['%s%s = self = Status().load(%s)' %
						('G'*game[0].isdigit(), game, `game`),
						"print 'Loaded', ('game %s%s','no game')[not self]" %
						('G'*game[0].isdigit(), game),
						'print ' + ' '.join(sys.argv[('.' not in arg1) + 1:])])
	os.system("%sPYTHONPATH=%s %s python -%sOc %s" %
		('set '*(os.name == 'nt'), os.path.dirname(host.packageDir), ('/usr/bin/env', '&')[os.name == 'nt'], interp, '"' + `';'.join(command)`[1:-1] + '"'))
	raise SystemExit

#	-----------------------
#	Examine/Update any game
#	-----------------------
Inspect()

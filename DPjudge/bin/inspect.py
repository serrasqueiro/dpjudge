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
			will make maps for the game "denarius" and WILL leave you
			in the Python interpreter for further commands
		inspect denarius. "self.makeMaps()"
			will make maps for the game "denarius" and WILL NOT leave you
			in the Python interpreter for further commands
		inspect . host.dpjudge
			will print the dpjudge address and WILL NOT leave you
			in the Python interpreter for further commands
		inspect @ host.dpjudge
			will print the dpjudge address and WILL leave you
			in the Python interpreter for further commands
	"""
	def __init__(self, argv = None):
		if argv is None: argv = sys.argv
		interp, command  = 'i', [
			'from DPjudge import *',
			'from DPjudge.variants.dppd import *',
			'import host',
			'from DPjudge.bin.inspector import Inspector',
			'inspect = Inspector()']
		if len(argv) > 1:
			arg1 = argv[1]
			gameName = arg1.split('.')[0].split('@')[0]
			interp = interp * ('.' not in arg1)
			if gameName:
				command.extend([
					"inspect.load('%s')" % gameName])
			command.extend([
				'print ' + ' '.join([
				"inspect.eval('%s')" % x.replace("'", "\\'") for x in argv[(
				'.' not in arg1 or not arg1.split('.')[1]) + 1:]])])
		os.system("%sPYTHONPATH=%s %s python -%sOc %s" %
			('set '*(os.name == 'nt'), os.path.dirname(host.packageDir),
			('/usr/bin/env', '&')[os.name == 'nt'], interp,
			'"' + `';'.join(command)`[1:-1] + '"'))

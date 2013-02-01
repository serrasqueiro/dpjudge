import os, sys
import random, string
from codecs import open

import host

class Scramble:
	"""
	Usage:
		scramble
			Returns the current judgekeeper password
		scramble -n
			Returns a random string that can be used as a password
		scramble -o
			Overwrites the JK password with a random one
		scramble -o password
			Overwrites the JK password with the password provided
	"""
	def __init__(self, argv = None):
		if argv is None: argv = sys.argv
		help = 0
		if len(argv) == 1:
			password = host.judgePassword
		elif argv[1] == '-n':
			if len(argv) == 2:
				password = self.scramble()
			else: help = 1
		elif argv[1] == '-o':
			if len(argv) == 2:
				password = self.override(self.scramble())
			elif len(argv) == 3:
				password = self.override(argv[2])
			else: help = 1
		else: help = 1
		if help: pass
		else: print(password)

	def scramble(self):
		letters, digits = string.lowercase, string.digits
		cipher = [random.choice(x) for x in
			[letters] * 2 + [digits] * 2 + [digits + letters + digits] * 4]
		random.shuffle(cipher)
		return ''.join(cipher)

	def override(self, password):
		for dir in os.sys.path:
			hostFileName = os.path.join(dir, 'host.py')
			if os.path.exists(hostFileName): break
		else: raise NoHostFileInSystemPath
		hostFile = open(hostFileName, encoding = 'latin-1')
		lines, nr = [], 0
		for line in hostFile:
			word = line.split()
			if word[:2] == ['judgePassword', '=']:
				nr += 1
				line = line.replace(word[2], ("'%s'" % password))
			lines += [line]
		hostFile.close()
		if not nr: lines += ["judgePassword = '%s'" % password]
		hostFile = open(hostFileName, 'w', encoding = 'latin-1')
		hostFile.writelines(lines)
		hostFile.close()
		return password

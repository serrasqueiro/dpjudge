import os, sys, shutil, glob
from codecs import open

import host, Game, Mail

class Status:
	#	----------------------------------------------------------------------
	def __init__(self):
		self.dict, self.file = {}, host.gameDir + '/status'
		try: file = open(self.file, encoding='latin-1')
		except: return
		for line in file:
			word = line.lower().split()
			if word: self.dict[word[0]] = word[1:]
		file.close()
	#	----------------------------------------------------------------------
	def __getitem__(self, game):
		return self.dict.get(game, [''])
	#	----------------------------------------------------------------------
	def save(self):
		file = open(self.file, 'w')
		for game, data in self.dict.items():
			temp = '%32s %s\n' % (game, ' '.join(data))
			file.write(temp.encode('latin-1'))
		file.close()
		try: os.chmod(self.file, 0666)
		except: pass
	#	----------------------------------------------------------------------
	def load(self, gameName):
		try: variant = self.dict[gameName][0]
		except: return
		return vars(__import__('DPjudge.variants.' + variant,
			globals(), locals(), `variant`))[variant.title() + 'Game'](gameName)
	#	----------------------------------------------------------------------
	def listGames(self, criteria, unlistedOk = 0):
		if type(criteria) != list: criteria = [criteria]
		statuses, variants, private, unlisted = [], [], None, None
		for crit in criteria:
			if not crit: continue
			key = crit.lower()
			if key in ('preparation', 'forming', 'active', 'waiting',
				'completed', 'terminated', 'error'): statuses += [key]
			elif key in ('public', 'private'):
				if private == None: private = key == 'private'
				elif private != (key == 'private'): private = None
			elif key in ('unlisted', 'listed'):
				if unlisted == None: unlisted = key == 'unlisted'
				elif unlisted != (key == 'unlisted'): unlisted = None
			elif os.path.isdir(host.packageDir + '/variants/' + key):
				variants += [key]
			else: return 'Unrecognized parameter: ' + crit
		if not unlistedOk:
			if unlisted: return 'Searching unlisted games not allowed'
			else: unlisted = 0
		games = self.dict.keys()
		if statuses:
			games = [x for x in games if [1 for y in statuses if y in self[x]]]
			if not games: return []
		if variants:
			games = [x for x in games if [1 for y in variants if y in self[x]]]
			if not games: return []
		if private is not None:
			games = [x for x in games if private == ('private' in self[x])]
			if not games: return []
		if unlisted is not None:
			games = [x for x in games if unlisted == ('unlisted' in self[x])]
			if not games: return []
		games.sort()
		return games
	#	----------------------------------------------------------------------
	def update(self, gameName, data, newVariant = 0):
		if type(data) != list: data = [data]
		if not newVariant: newVariant = self.dict.get(gameName, ['STANDARD'])[0]
		self.dict[gameName] = [newVariant] + data
		self.save()
	#	----------------------------------------------------------------------
	def changeStatus(self, game, status):
		self.dict[game][1] = status
		self.save()
	#	----------------------------------------------------------------------
	def list(self, email, subject='', criteria = None):
		import Mail
		results, openings = '', criteria is None
		if openings: criteria = ['forming', 'waiting', 'public']
		subject = ('DPjudge %s list (%s)' % (openings and 'openings' or
			'games', host.dpjudgeID), 'RE: ' + subject)[subject != '']
		games, error = self.listGames(criteria), ''
		if type(games) != list: error = games
		else:
			for gameName in games:
				try:
					game = self.load(gameName)
					results += game.shortList()
				except: pass
		mail = Mail.Mail(email, subject, mailAs = host.openingsAddress)
		mail.write((':: Judge: %s\n:: URL: %s%s\n\n' %
			(host.dpjudgeID, host.dpjudgeURL,
			'/index.cgi' * (os.name == 'nt'))) +
			(error or results or openings and 'No Openings!' or 'No such games!'))
		mail.close()
	#	----------------------------------------------------------------------
	def createGame(self, email = None, gameName = None, gamePass = None, gameVar = 'standard'):
		from variants.dppd.DPPD import RemoteDPPD
		error = []
		if not gameName: error += ['No game name to CREATE']
		if not gamePass: error += ['No game password given']
		if not email:    error += ['No registered email found']
		if host.createLimit and len([1 for x in self.dict.values()
			if 'forming' in x or 'preparation' in x]) > host.createLimit:
				error += ['CREATE is disabled -- ' + \
					'too many games currently need players']
		dppd = '|'.join(RemoteDPPD().whois(email).split()) or '|%s|' % email + email
		if dppd[0] == 'P': error += 'DPPD registration still pending'
		error += self.checkGameName(gameName)
		if '<' in gamePass or '>' in gamePass:
			error += ["Password cannot contain '<' or '>'"]
		dir, desc, onmap = host.gameDir + '/' + gameName, 0, ''
		if not error:
			os.mkdir(dir)
			os.chmod(dir, 0777)
			file = open(dir + '/status', 'w')
			temp = 'GAME %s\nPHASE FORMING\nMASTER %s\n' \
				'PASSWORD %s\n' % (gameName, dppd, gamePass)
			file.write(temp.encode('latin-1'))
			del temp
			file.write('DESC A Web-created Game')
			mode = 'preparation'
			file.close()
			os.chmod(file.name, 0666)
			self.dict[gameName] = [gameVar.lower(), mode]
			self.save()
			# Send mail
			game = Game.Game(gameName)
			self.announce(game, 'Game creation', 
				"Game '%s' has been created.  Finish preparation at:\n  %s"
				'\n\nWelcome to the %s.' %
				(gameName, self.gameLink(game), host.dpjudgeNick))
		return error
	#	----------------------------------------------------------------------
	def renameGame(self, gameName, toGameName, forced = 1, gamePass = None):
		from variants.dppd.DPPD import RemoteDPPD
		error = []
		if gameName not in self.dict:
			return ["No such game '%s' exists on this judge" % gameName]
		game = Game.Game(gameName)
		if not forced and (
			not host.judgePassword or gamePass != host.judgePassword):
			if not gamePass or game.password != gamePass:
				error += ['No match with the master password']
		error += self.checkGameName(toGameName)
		if error: return error
		# Remove game maps
		mapRootName = os.path.join(host.gameMapDir, gameName)
		mapRootRename = os.path.join(host.gameMapDir, toGameName)
		for suffix in ('.ps', '.pdf', '.gif', '_.gif'):
			try: os.rename(mapRootName + suffix, mapRootRename + suffix)
			except: pass
			for mapFileName in glob.glob(mapRootName + '.*' + suffix):
				try: os.rename(mapFileName, mapRootRename + os.path.splitext(
					os.path.splitext(mapFileName)[0])[1] + suffix)
				except: pass
		# Rename game dir
		if os.path.exists(game.gameDir) and os.path.isdir(
			game.gameDir):
			toGameDir = os.path.join(os.path.split(game.gameDir)[0],
				toGameName)
			try:
				os.rename(game.gameDir, toGameDir)
				game.gameDir = toGameDir
			except: error += ['Failed to rename the game directory']
		# Purge from dppd
		try: RemoteDPPD().deleteGame(gameName, game.gm.password)
		except: error += ['Failed to delete the game records from the DPPD'] 
		# Rename game and update dppd
		game.name = toGameName
		game.save()
		# Update status
		self.dict[toGameName] = self.dict[gameName]
		del self.dict[gameName]
		self.save()
		# Reload game with the appropriate variant class.
		game = self.load(toGameName)
		# Propagate name to all results and status files and remake the maps
		error += [game.reprocess(1, 16)]
		# Send mail
		self.announce(game, 'Game name change', 
			"Game '%s' has been renamed to '%s'.  The new link is:\n  %s" %
			(gameName, toGameName, self.gameLink(game)))
		return filter(None, error)
	#	----------------------------------------------------------------------
	def purgeGame(self, gameName, forced = 1, gamePass = None):
		from variants.dppd.DPPD import RemoteDPPD
		error = []
		if gameName not in self.dict:
			return ["No such game '%s' exists on this judge" % gameName]
		game = Game.Game(gameName)
		if not forced and (
			not host.judgePassword or gamePass != host.judgePassword):
			status = self.dict[gameName][1]
			if status == 'preparation': pass
			elif status == 'forming':
				if [1 for x in game.powers if not x.isDummy()]:
					error += ['Please inform your players and make them resign '
						'first']
			else: error += ['Please contact the judgekeeper to purge a game '
				'that has already started']
			if not gamePass or game.password != gamePass:
				error += ['No match with the master password']
			if error: return error
		# Remove game maps
		mapRootName = os.path.join(host.gameMapDir, game.name)
		for suffix in ('.ps', '.pdf', '.gif', '_.gif'):
			try: os.unlink(mapRootName + suffix)
			except: pass
			for mapFileName in glob.glob(mapRootName + '.*' + suffix):
				try: os.unlink(mapFileName)
				except: pass
		# Remove game dir
		if os.path.exists(game.gameDir) and os.path.isdir(
			game.gameDir):
			try: shutil.rmtree(game.gameDir)
			except: error += ['Failed to remove the game directory']
		# Purge from dppd
		try: RemoteDPPD().deleteGame(gameName, game.gm.password)
		except: error += ['Failed to delete the game records from the DPPD'] 
		# Purge from status
		del self.dict[gameName]
		self.save()
		# Send mail
		self.announce(game, 'Game purged', 
			"Game '%s' has been purged." % gameName)
		return error
	#	----------------------------------------------------------------------
	def checkGameName(self, gameName):
		error = []
		if gameName in self.dict:
			error += ["Game name '%s' already used" % gameName]
		if gameName[:0] == ['-']:
			error += ["Game name can not begin with '-'"]
		for ch in gameName:
			if not (ch.islower() or ch in '_-' or ch.isdigit()):
				error += ["Game name cannot contain '%s'" % ch]
		return error
	#	----------------------------------------------------------------------
	def announce(self, game, subject, message):
		if game.tester or 'SOLITAIRE' in game.rules: return
		groups = [game.map.notify]
		if not host.observers: pass
		elif type(host.observers) is list: groups += [host.observers]
		else: groups += [[host.observers]]
		groups += [x.address for x in [game.gm] + game.powers if x.address]
		for addresses in groups:
			if not addresses: continue
			mail = Mail.Mail(', '.join(addresses), subject,
				('', game.gameDir + '/mail')[host.copy], host.dpjudge, '')
			mail.write(message)
			mail.close()
	#	----------------------------------------------------------------------
	def gameLink(self, game):
		return '%s%s?game=%s' % (host.dpjudgeURL,
			'/index.cgi' * (os.name == 'nt'), game.name)
	#	----------------------------------------------------------------------

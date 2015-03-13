import os, sys, urllib, shutil, glob
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
	def listGames(self, criteria, unlisted = 0):
		if type(criteria) != list: criteria = [criteria]
		games = sorted([x for x,y in self.dict.items()
			if not [1 for z in criteria if z and z.lower() not in y]
			and ('unlisted' in y) <= unlisted])
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
	def list(self, email, subject=''):
		import Mail
		results = ''
		subject = ('DPjudge openings list (%s)' % host.dpjudgeID,
			'RE: ' + subject)[subject != '']
		for gameName in self.listGames('waiting') + self.listGames('forming'):
			if 'unlisted' not in self.dict[gameName]:
				try:
					game = self.load(gameName)
					if not game.private: results += game.shortList()
				except: pass
		mail = Mail.Mail(email, subject)
		mail.write((':: Judge: %s\n:: URL: %s%s\n\n' %
			(host.dpjudgeID, host.dpjudgeURL,
			'/index.cgi' * (os.name == 'nt'))) + (results or 'No Openings!'))
		mail.close()
	#	----------------------------------------------------------------------
	def createGame(self, email = None, gameName = None, gamePass = None, gameVar = 'standard'):
		import urllib
		error = []
		if not gameName: error += ['No game name to CREATE']
		if not gamePass: error += ['No game password given']
		if not email:    error += ['No registered email found']
		if host.createLimit and len([1 for x in self.dict.values()
			if 'forming' in x or 'preparation' in x]) > host.createLimit:
				error += ['CREATE is disabled -- ' + \
					'too many games currently need players']
		if host.dppdURL:
			#	--------------------------------------------------------------
			#	Need to use query string rather than POST it.  Don't know why.
			#	--------------------------------------------------------------
			dppdURL = host.dppdURL.split(',')[0]
			query = '?&'['?' in dppdURL]
			page = urllib.urlopen(dppdURL + query +
				'page=whois&email=' + urllib.quote(email, '@'))
			dppd = unicode(page.read(), 'latin-1').strip().split()
			page.close()
			dppd = '|'.join(dppd)
		else:
			#	-------------------------------------------------------
			#	Running without a DPPD.  Shame on the judgekeeper.  :-)
			#	-------------------------------------------------------
			dppd = '|%s|' % email + email
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
			self.game = Game.Game(gameName)
			self.announce('Game creation', 
				"Game '%s' has been created.  Finish preparation at:\n  %s"
				'\n\nWelcome to the DPjudge.' %
				(gameName, self.gameLink()))
		return error
	#	----------------------------------------------------------------------
	def renameGame(self, gameName, toGameName, forced = 1, gamePass = None):
		error = []
		if gameName not in self.dict:
			return ['No such game exists on this judge']
		self.game = Game.Game(gameName)
		if not forced and (
			not host.judgePassword or gamePass != host.judgePassword):
			if not gamePass or self.game.password != gamePass:
				error += ['No match with the master password']
		error += self.checkGameName(toGameName)
		if error: return error
		# Rename game maps
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
		if os.path.exists(self.game.gameDir) and os.path.isdir(
			self.game.gameDir):
			toGameDir = os.path.join(os.path.split(self.game.gameDir)[0],
				toGameName)
			try:
				os.rename(self.game.gameDir, toGameDir)
				self.game.gameDir = toGameDir
			except: error += ['Failed to rename the game directory']
		# Purge from dppd
		if host.dppdURL:
			dict = urllib.urlencode({
				'judge': host.dpjudgeID.encode('latin-1'),
				'name': gameName.encode('latin-1'),
				'password': self.game.password.encode('latin-1')})
			for dppdURL in host.dppdURL.split(','):
				query = '?&'['?' in dppdURL]
				page = urllib.urlopen(dppdURL + query + 'page=delete&' + dict)
		#   --------------------------------------------------------------------
		#   Check for an error report and raise an exception if that's the case.
		#   --------------------------------------------------------------------
		lines = page.readlines()
		page.close()
		if [1 for x in lines if 'DPjudge Error' in x]:
			if not [1 for x in lines if 'NoGameToDelete' in x]:
				error += ['Failed to delete the game records from the DPPD'] 
		# Rename game and update dppd
		self.game.name = toGameName
		self.game.save()
		# Update status
		self.dict[toGameName] = self.dict[gameName]
		del self.dict[gameName]
		self.save()
		# Send mail
		self.announce('Game name change', 
			"Game '%s' has been renamed to '%s'.  The new link is:\n  %s" %
			(gameName, toGameName, self.gameLink()))
		return error
	#	----------------------------------------------------------------------
	def purgeGame(self, gameName, forced = 1, gamePass = None):
		error = []
		if gameName not in self.dict:
			return ['No such game exists on this judge']
		self.game = Game.Game(gameName)
		if not forced and (
			not host.judgePassword or gamePass != host.judgePassword):
			status = self.dict[gameName][1]
			if status == 'preparation': pass
			elif status == 'forming':
				if [1 for x in self.game.powers if not x.isDummy()]:
					error += ['Please inform your players and make them resign '
						'first']
			else: error += ['Please contact the judgekeeper to purge a game '
				'that has already started']
			if not gamePass or self.game.password != gamePass:
				error += ['No match with the master password']
			if error: return error
		# Remove game maps
		mapRootName = os.path.join(host.gameMapDir, self.game.name)
		for suffix in ('.ps', '.pdf', '.gif', '_.gif'):
			try: os.unlink(mapRootName + suffix)
			except: pass
			for mapFileName in glob.glob(mapRootName + '.*' + suffix):
				try: os.unlink(mapFileName)
				except: pass
		# Remove game dir
		if os.path.exists(self.game.gameDir) and os.path.isdir(
			self.game.gameDir):
			try: shutil.rmtree(self.game.gameDir)
			except: error += ['Failed to remove the game directory']
		# Purge from dppd
		if host.dppdURL:
			dict = urllib.urlencode({
				'judge': host.dpjudgeID.encode('latin-1'),
				'name': gameName.encode('latin-1'),
				'password': self.game.password.encode('latin-1')})
			for dppdURL in host.dppdURL.split(','):
				query = '?&'['?' in dppdURL]
				page = urllib.urlopen(dppdURL + query + 'page=delete&' + dict)
		#   --------------------------------------------------------------------
		#   Check for an error report and raise an exception if that's the case.
		#   --------------------------------------------------------------------
		lines = page.readlines()
		page.close()
		if [1 for x in lines if 'DPjudge Error' in x]:
			if not [1 for x in lines if 'NoGameToDelete' in x]:
				error += ['Failed to delete the game records from the DPPD'] 
		# Purge from status
		del self.dict[gameName]
		self.save()
		# Send mail
		self.announce('Game purged', 
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
	def announce(self, subject, message):
		groups = [self.game.map.notify]
		if not host.observers: pass
		elif type(host.observers) is list: groups += [host.observers]
		else: groups += [[host.observers]]
		groups += [[self.game.master[1]]]
		groups += [x.address for x in self.game.powers if x.address]
		for addresses in groups:
			if not addresses: continue
			mail = Mail.Mail(', '.join(addresses), subject,
				('', self.game.gameDir + '/mail')[host.copy], host.dpjudge, '')
			mail.write(message)
			mail.close()
	#	----------------------------------------------------------------------
	def gameLink(self):
		return '%s%s?game=%s' % (host.dpjudgeURL,
			'/index.cgi' * (os.name == 'nt'), self.game.name)
	#	----------------------------------------------------------------------

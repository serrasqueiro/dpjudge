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
		if len([1 for x in self.dict.values()
			if 'forming' in x or 'preparation' in x]) > 20:
				error += ['CREATE is disabled -- ' + \
					'too many games currently need players']
		if host.dppdURL:
			#	Need to use query string rather than POST it.  Don't know why.
			query = '?&'['?' in host.dppdURL]
			page = urllib.urlopen(host.dppdURL + query +
				'page=whois&email=' + urllib.quote(email, '@'))
			dppd = unicode(page.read(), 'latin-1').strip().split()
			page.close()
			dppd = '|'.join(dppd)
		else:
			#	-------------------------------------------------------
			#	Running without a DPPD.  Shame on the judgekeeper.  :-)
			#	-------------------------------------------------------
			dppd = '|%s|' % email + email
		if gameName[:0] == ['-']:
			error += ["Game name can not begin with '-'"]
		for ch in gameName:
			if not (ch.islower() or ch in '_-' or ch.isdigit()):
				error += ["Game name cannot contain '%s'" % ch]
		if '<' in gamePass or '>' in gamePass:
			error += ["Password cannot contain '<' or '>'"]
		if gameName in self.dict:
			error += ["Game name '%s' already used" % gameName]
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
			self.game, self.message = Game.Game(gameName), []
			observers = host.observers
			if type(observers) is not list: observers = [observers]
			observers += self.game.map.notify
			observers.append(self.game.master[1])
			observers = [x for x in observers if x is not None]
			mail = Mail.Mail(', '.join(observers), 'Game creation', ('', dir + '/mail')[host.copy], 
				host.dpjudge, '')
			mail.write("Game '%s' has been created.  Finish preparation at:\n"
				'  %s%s?game=%s\n\nWelcome to the DPjudge.' %
				(gameName, host.dpjudgeURL, '/index.cgi' * (os.name == 'nt'),
				gameName))
			mail.close()
		return error
	#	----------------------------------------------------------------------
	def purgeGame(self, gameName, forced = 0, gamePass = None):
		error = []
		if gameName not in self.dict:
			return ['No such game exists on this judge']
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
		if os.path.exists(game.gameDir) and os.path.isdir(game.gameDir):
			try: shutil.rmtree(game.gameDir)
			except: error += ['Failed to remove the game directory']
		# Purge from dppd
		dict = urllib.urlencode({'judge': host.dpjudgeID.encode('latin-1'),
			'name': gameName.encode('latin-1')})
		query = '?&'['?' in host.dppdURL]
		page = urllib.urlopen(host.dppdURL + query + 'page=delete&' + dict)
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
		return error

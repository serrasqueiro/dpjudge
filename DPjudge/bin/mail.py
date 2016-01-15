#!/usr/bin/env python -O

import urllib, email
from codecs import open

from DPjudge import *

class Procmail:
	#	-------------------------------------------------------------
	"""
	This class is instantiated on all e-mail coming into the dpjudge.
	It detects email commands, processes them, and responds to them.
	"""
	#	-------------------------------------------------------------
	def __init__(self):
		self.game = power = password = joiner = None
		self.message = self.email = self.power = self.pressSent = None
		self.response, msg = [], []
		lineNo = joining = 0
		part = input = email.message_from_file(os.sys.stdin)
		addy = part.get('reply-to', part['from']) or ''
		if '@' in addy: self.email = ([x for x in addy.split() if '@' in x][0]
							.lower().strip('<",>'))
		self.subject = part.get('subject', '')
		self.dppd = None #part.get('DPPD','').split()
		ip = [x for x in part.get_all('received',[]) if x[:4] == 'from'] or ['']
		word = ip[0].split()
		if len(word) > 2 and '.' in word[2] and '[' in word[2]:
			self.ip = word[2].strip('([])')
		elif len(word) > 1 and '@' not in word[1]:
			ip = word[1].strip('[]')
			if '.' not in ip: ip = 'localhost'
			if max(map(ip.find, (
				'localhost', '127.0.0.1',
				'.proxy.aol.com', '.mx.aol.com',
				'fastmail.fm'))) == -1: self.ip = ip
		else: self.ip = self.email
		ip = part.get('x-originating-ip', input['x-originating-server'])
		if ip: self.ip = ip.split()[0]
		if part.is_multipart():
			for part in input.walk():
				if part.get_content_type() == 'text/plain': break
			else: self.respond('DPjudge requires a text/plain MIME part')
		lines = unicode(part.get_payload(decode=1), 'latin-1').split('\n')
		lines = [x for x in lines if x.strip()[:2] != '//']
		#	----------------------------------------
		#	Alternate line ending character (mostly
		#	for pager/cell-phone e-mailers who don't
		#	know how to send newline characters)
		#	----------------------------------------
		for line in lines:
			if line.strip()[:2] == r'\\':
				eol = line[2:].strip()[:1] or '\n'
				if eol.isalnum(): eol = '\n'
				msg.extend(line.split(eol)[1:])
			else: msg += [line]
		#	----------------------------------------
		#	Some mailers try to be html compliant by
		#	ending all lines with <br>. Strip them.
		#	----------------------------------------
		for line in msg:
			if line.rstrip() and line.rstrip()[-4:].lower() != '<br>': break
		else:
			msg = [x.rstrip()[:-4] for x in msg]
		self.message = msg[:]
		#file = open(host.gameDir + '/message', 'w')
		#file.write('\n'.join(self.message).encode('latin-1'))
		#file.close()
		for line in msg:
			word = line.split()
			lineNo += 1
			#	------------------
			#	Ignore empty lines
			#	------------------
			if not word:
				del self.message[:lineNo]
				lineNo = 0
				continue
			upword = word[0].upper()
			#	----------------------------------------
			#	Detect game creation or deletion message
			#	----------------------------------------
			if upword in ('CREATE', 'PURGE', 'RENAME'):
				if len(word) < 2: self.respond('No game name to %s' % upword)
				if upword[0] != 'R': word = word[:2] + ['X'] + word[2:]
				elif len(word) < 3:
					self.respond('No new game name to %s to' % upword)
				if len(word) < 4: self.respond('No Master password given')
				if len(word) < 5: word += ['standard']
				elif len(word) > 5:
					self.respond('Unrecognized %s data' % upword)
				game, toGame, password, variant = ' '.join(word[1:]).lower().split()
				password, variant = self.sanitize(password), self.sanitize(variant)
				for name in [toGame, game][upword[0] != 'R':]:
					if name[:0] == ['-']:
						self.respond("Game name can not begin with '-'")
					for ch in name:
						if not (ch.islower() or ch in '_-' or ch.isdigit()):
							self.respond("Game name cannot contain '%s'" % ch)
				if '<' in password or '>' in password:
					self.respond("Password cannot contain '<' or '>'")
				if upword[0] == 'P':
					response = Status().purgeGame(game, 0, password)
					if not response: 
						del self.message[:lineNo - 1]
						response = ['Game %s purged from this DPjudge' % game]
					self.response += response
					self.respond()
				elif upword[0] == 'R':
					response = Status().renameGame(game, toGame, 0, password)
					if not response: 
						del self.message[:lineNo - 1]
						response = ['Game %s renamed to %s' % (game, toGame)]
					self.response += response
					self.respond()
				else:
					games, mode, unlisted = Status(), 'preparation', 0
					#if len([1 for x in games.dict.values()
					#	if 'forming' in x or 'preparation' in x]) > 20:
					#	self.respond('CREATE is disabled -- '
					#		'too many games currently need players')
					if game in games.dict:
						self.respond("Game name '%s' already used" % game)
					try: desc = __import__('DPjudge.variants.' + variant,
						globals(), locals(), `variant`).VARIANT
					except: self.respond('Unrecognized rule variant: ' +
						variant)
					self.dppdMandate(upword)
					dir, onmap = host.gameDir + '/' + game, ''
					os.mkdir(dir)
					os.chmod(dir, 0777)
					file = open(dir + '/status', 'w')
					temp = ('GAME %s\nPHASE FORMING\nMASTER %s\n' +
						'PASSWORD %s\n') % (game, self.dppd, password)
					file.write(temp.encode('latin-1'))
					for info in self.message[1:]:
						word = ''.join(info.upper().split()[:1])
						if word == 'DESC': break
						if word in ('MAP', 'TRIAL'):
							onmap = ' on the %s%s map' % (
								''.join(info.split()[1:2]).title(),
								('', ' trial')[word == 'TRIAL'])
					else:
						temp = 'DESC A %s game%s.\n' % (desc, onmap)
						file.write(temp.encode('latin-1'))
					for info in self.message[1:]:
						word = ''.join(info.upper().split()[:1])
						if word == 'SIGNOFF': break
						if word in ('GAME', 'PHASE', 'MASTER'): pass
						elif word == 'FORM': mode = 'forming'
						# elif word == 'UNLISTED': unlisted = 1
						else: file.write((info + '\n').encode('latin-1'))
					file.close()
					os.chmod(file.name, 0666)
					games.dict[game] = [variant, mode]
					if unlisted: games.dict[game] += ['unlisted']
					games.save()
					self.game, self.message = Game(game), []
					if 'SOLITAIRE' in self.game.rules:
						if not self.game.private:
							self.game.private = 'SOLITAIRE'
							self.game.save()
					if self.game.private:
						games.dict[game] += ['private']
						games.save()
					if (mode == 'forming' and not game.available()
					and 'START_MASTER' not in self.game.rules):
						self.game.begin()
						mode = 'active'
					observers = host.observers or []
					if type(observers) is not list: observers = [observers]
					self.respond("Game '%s' has been created.  %s at:\n"
						'   %s%s?game=%s\n\nWelcome to the %s' %
						(game, mode[0] == 'p' and 'Finish preparation'
						or mode[0] == 'f' and 'Game is now forming'
						or 'Game has started', host.dpjudgeURL,
						'/index.cgi' * (os.name == 'nt'), game,
						host.dpjudgeNick),
						copyTo = observers + self.game.map.notify)
			#	---------------------------------------------------
			#	Detect player message (SIGNON, RESIGN, or TAKEOVER)
			#	---------------------------------------------------
			elif upword in ('SIGNON', 'RESIGN', 'TAKEOVER'):
				self.dppdMandate(upword)
				if len(word) == 1: power = game = ''
				elif list(word[1]).count('@') == 1:
					power, game = word[1].split('@')
				else: power, game = word[1][0], word[1][1:]
				power, game = power[power[0] == '_':].upper(), game.lower()
				try: password = self.sanitize(word[2])
				except: password = ''
				if upword == 'TAKEOVER':
					if '<' in password or '>' in password:
						self.respond("Password cannot contain '<' or '>'")
				if upword[0] != 'S': joiner = word[0].upper()
				del self.message[:lineNo - 1]
				break
			#	---------------------------------------------
			#	Detect LIST, SUMMARY, HISTORY, or MAP request
			#	---------------------------------------------
			elif upword in ('LIST', 'SUMMARY', 'HISTORY', 'MAP'):
				if upword == 'MAP':
					mapType = word[-1].lower()
					if mapType in ('ps', 'pdf', 'gif'): del word[-1]
					else: mapType = 'gif'
				self.pressSent = None
				if len(word) != 2 and upword != 'LIST': self.respond(
					'A single game must be specified to ' + upword)
				if len(word) == 1: Status().list(self.email, self.subject)
				else:
					gameName = word[1].lower()
					dataGame = Status().load(gameName)
					if not dataGame:
						self.respond("No game '%s' active" % gameName)
					if (dataGame.phaseAbbr() != '?????'
					and 'BLIND' in dataGame.rules): self.respond(
						"Must SIGNON to get '%s' of active BLIND game " %
						upword + gameName)
					if upword[0] == 'S': dataGame.summary(self.email)
					elif upword[0] == 'L':
						dataGame.list(self.email, subject=self.subject)
					elif upword[0] == 'H': dataGame.history(self.email)
					elif not dataGame.mailMap(self.email, mapType):
						self.respond("No '%s' MAP is available for game " %
							mapType.upper() + gameName)
				del self.message[:lineNo]
				lineNo = 0
			#	-------------------------
			#	Detect new player joining
			#	-------------------------
			elif self.email and len(word) > 2 and len(word[0]) > 2:
				if upword != 'MONITOR': self.dppdMandate(upword)
				game, joiner = None, upword
				if word[1].count('@') == 1:
					power, game = word[1].split('@')
				elif joiner == 'JOIN': power, game = 'POWER', word[1]
				if game:
					power, game = power[power[0] == '_':].upper(), game.lower()
					password = self.sanitize(word[2])
					if '<' in password or '>' in password:
						self.respond("Password cannot contain '<' or '>'")
					del self.message[:lineNo - 1]
				break
			#	------------------------------
			#	Detect SIGNOFF (usable without
			#	SIGNON; stops reading message)
			#	------------------------------
			elif upword == 'SIGNOFF': return
			#	-----------------
			#	Unrecognized line
			#	-----------------
			else: break
		#	----------------------------------
		#	If the message was just LIST, etc.
		#	commands, we've processed it all.
		#	----------------------------------
		if not self.message: return
		#	-------------
		#	Load the game
		#	-------------
		self.power = self.pressSent = None
		if 'game' not in locals(): game = ''
		if not game and self.email:
			#	---------------------------------------------------
			#	Somehow, the DPjudge seems to get into a pattern of
			#	sending mail to itself complaining that what it has
			#	received (from itself) doesn't start right.  So, to
			#	make this stop -- and hopefully prevent the process
			#	from running away -- I added the following lines:
			#	---------------------------------------------------
			user, domain = self.email.split('@')
			domain = '.'.join(domain.split('.')[-2:])
			if host.dppd:
				dppdUser, dppdDomain = host.dppd.split('@')
				dppdDomain = '.'.join(dppdDomain.split('.')[-2:])
				if (user, domain) == (dppdUser, dppdDomain): os._exit(os.EX_OK)
			self.respond(('Expected SIGNON, JOIN, CREATE, PURGE, RENAME, '
				'RESIGN, TAKEOVER, SUMMARY, HISTORY, or LIST,\n'
				'or a valid non-map-power join '
				'command (e.g., OBSERVE playerName@gameName)', 'No playerName '
				'given. Use "OBSERVE playerName@gameName password"')
				['OBSERVER'.startswith(upword)])
		self.game = Status().load(game)
		if not self.game:
			if not self.email: raise NoSuchGame, game
			self.respond("No game '%s' active" % game)
		#	---------------------------
		#	Handle newly joining player
		#	---------------------------
		if joiner: self.updatePlayer(power, password, joiner, word)
		#	---------------------
		#	Handle player message
		#	---------------------
		elif self.email:
			self.handleEmail(power, password)
			self.respond()
	#	----------------------------------------------------------------------
	def dppdMandate(self, command):
		if self.dppd: return
		if not host.dppdURL:
			#	-------------------------------------------------------
			#	Running without a DPPD.  Shame on the judgekeeper.  :-)
			#	-------------------------------------------------------
			self.dppd = '|%s|' % self.email + self.email
			return
		#	---------------------------------------------------------
		#	We're here for a JOIN (or similar) or CREATE command that
		#	requires registration -- need to ask the DPPD for an ID.
		#	---------------------------------------------------------
		#	Need to use query string rather than POST it.  Don't know why.
		dppdURL = host.dppdURL.split(',')[0]
		query = '?&'['?' in dppdURL]
		page = urllib.urlopen(dppdURL + query +
			'page=whois&email=' + urllib.quote(self.email, '@'))
		response = unicode(page.read(), 'latin-1')
		page.close()
		self.ip, self.dppd = self.email, '|'.join(response.strip().split())
		if self.dppd[:1] != '#': self.respond(
			'Your e-mail address (%s) is\nnot registered with the DPPD, '
			'or your DPPD status does\nnot allow you to use the %s command.'
			'\n\nVisit the DPPD at %s\nfor assistance' %
			(self.email, command, dppdURL))
	#	----------------------------------------------------------------------
	def updatePlayer(self, power, password, command, word):
		game, self.power, playerType = self.game, None, None
		if command != 'JOIN':
			self.locatePower(power, password,
				command in ('RESIGN', 'TAKEOVER'), command == 'TAKEOVER')
			if self.power: power, playerType = self.power.name, self.power.type
		#	---------------------------------------------
		#	The line below looks like a candidate to be
		#	an "else" but it's not, due to a coming elif!
		#	---------------------------------------------
		if command == 'JOIN':
			#	-------------------------------------------
			#	Make sure it's okay for a new power to join
			#	-------------------------------------------
			if game.phase != 'FORMING':
				self.respond("Game '%s' already full" % game.name)
			if power == 'POWER':
				taken = [x.name for x in game.powers]
				for count in range(1, len(game.map.powers) + 1):
					if 'POWER#' + `count` not in taken: break
				power += '#' + `count`
			elif 'POWER_CHOICE' not in game.rules:
				self.respond('Power selection is not allowed')
			elif power not in [x[x[0] == '_':] for x in game.map.powers]:
				self.respond("No power '%s' in game '%s'" % (power, game.name))
			elif power in [x[x[0] == '_':] for x in game.map.dummies]:
				self.respond("Power '%s' cannot be played" % power)
			elif power in [x.name for x in game.powers]: self.respond(
				'Power %s is already being played' % game.anglify(power))
			if game.groups:
				exclude = 1
				groupList = [x.group.name.upper()
					for x in Groups.userClass(self.email).groups()]
				for group in game.groups:
					if group in groupList:
						exclude = 0
						break
				if exclude:
					self.respond('You are not in a group allowed in this game.')
			playerType = 'POWER'
		elif command == 'RESIGN':
			if not self.power:
				self.respond("Player ID '%s' does not exist" % power)
			if self.power.player[0] in ('RESIGNED', 'DUMMY'):
				self.respond("Cannot RESIGN '%s' -- no current PLAYER" % power)
		elif command == 'TAKEOVER':
			try:
				if not self.isMaster(power) and self.power.player[0] != 'RESIGNED': 1/0
			except: self.respond("Cannot TAKEOVER the ID '%s'" % power)
		else:
			#	------------------------------------------------------
			#	Make sure it's okay for a new "something else" to join
			#	and that this "something else" chooses a unique name.
			#	------------------------------------------------------
			for playerType in ['OBSERVER', 'MONITOR'] + game.playerTypes:
				if playerType.startswith(command): break
			else: self.respond("Player type '%s' not allowed" % command)
			if self.power and self.email != self.power.address[0]:
				self.respond("Player ID '%s' already exists" % power)
			elif self.isMaster(power):
				self.respond("A Master already exists in '%s'" % game.name)
			#	-------------------------------
			#	Invalidate any name that could
			#	be a sequence of power abbrev's
			#	-------------------------------
			letters = ['M'] + [game.map.abbrev.get(x, x[0])
				for x in game.map.powers]
			if (not [1 for x in power if x not in letters or power.count(x) > 1]
			or power.startswith('POWER#')):
				self.respond("Invalid player ID: '%s'" % power)
		if command not in ('RESIGN', 'MONITOR'): self.dppdMandate(command)
		#	-----------------------------------
		#	If this e-mail address is already
		#	(just) observing the game or is an
		#	awaiting POWER, silently delete him
		#	-----------------------------------
		for num, existing in enumerate(game.powers):
			existing = game.powers[num]
			if ((command, power) == ('RESIGN',
			existing.name[existing.name[0] == '_':])
			or existing.address and self.email == existing.address[0]
			or self.dppd and self.dppd[0] != '|' and existing.player
			and self.dppd.split('|')[0] == existing.player[0].split('|')[0]):
				if (existing.type not in ('OBSERVER', 'MONITOR', 'POWER')
				and command != 'RESIGN'): self.respond(
					"You are already playing game '%s'" % game.name)
			else: continue
			if existing.isValidPassword(password) != 1:
				self.respond("Incorrect password to modify player ID '%s'" %
					existing.name)
			if command != 'RESIGN': del game.powers[num]
			break
		if (playerType == 'POWER' and game.available() <= 0 and
			command != 'RESIGN'):
			self.respond("The game is already full. " +
				"Try to join another game or take over an abandoned position")
		if (self.dppd and game.master[0] == self.dppd.split('|')[0]
		or self.email.lower() in game.master[1].lower().split(',')):
			if command != 'RESIGN': self.respond(
				"You are already Mastering game '%s'" % game.name)
			if self.isMaster(power): self.respond('The Master may not resign')
		#	----------------------
		#	Check for private game
		#	----------------------
		if command != 'RESIGN':
			if not game.private or command == 'MONITOR':
				if len(word) != 3: self.respond('Invalid %s command' % command)
			elif (len(word) != 4
			or self.sanitize(word[3]).upper() != game.private):
				self.respond(
					"Game '%s' is a private game for invited players only.\n"
					'You may %s only by specifying (after your password)\n'
					'the privacy keyword that was given to you by the '
					'GameMaster.\n'
					'A privacy password usually indicates that a game is\n'
					'exclusively for a group of players in a specific club\n'
					'or organization or who know each other personally and\n'
					'can communicate outside the confines of the judge (for\n'
					'example, face-to-face or by telephone).' %
					(game.name, command))
		#	---------------
		#	Player TAKEOVER
		#	---------------
		if command == 'TAKEOVER':
			if self.isMaster(power):
				oldGM, game.master = game.master[1], self.dppd.split('|')
				game.save()
				game.openMail('Diplomacy Master TAKEOVER notice',
					mailTo = oldGM, mailAs = host.dpjudge)
				game.mail.write(
					"You are no longer the Master of game '%s'.\n\n"
					'The new Master is %s (%s).\n\n'
					'Thank you for your service.' % (game.name,
					game.master[2].replace('_', ' '), game.master[1]))
				game.mail.close()
				self.respond('You are now the Master of game ' + game.name)
			response = self.power.takeover(self.dppd, self.email, password)
			if response: self.respond(response)
		#	-------------------------------------------------------
		#	Add the new power, then process the rest of the message
		#	-------------------------------------------------------
		elif command != 'RESIGN':
			self.power = game.powerType(game, power, playerType)
			self.power.address, self.power.password = [self.email], password
			#	--------------------
			#	Add DPPD player info
			#	--------------------
			if playerType != 'MONITOR': self.power.player[:0] = [self.dppd]
			if command != 'JOIN': self.power.initialize(game)
			game.powers += [self.power]
			game.sortPowers()
			game.save()
			responding = ''
			if command == 'JOIN':
				avail = game.available()
				if not avail:
					if 'START_MASTER' not in game.rules:
						responding = game.begin()
						if responding: game.mailPress(None, ['MASTER'],
							'The game cannot start yet because ' + (self.error
							and 'the following error%s exist%s:\n\t' %
							[('s', ''), ('', 's')][len(self.error) == 1] +
							'\n\t'.join(self.error) +
							'\n\nResolve this first, then ' or
							'the status is not forming. To begin ') +
							'change the game status to active.',
							subject = 'Diplomacy game %s full' % game.name)
					if responding is not None:
						game.mailPress(None, ['All!'],
							'All positions are filled, but you need to wait ' +
							'for the Master to activate the game.',
							subject = 'Diplomacy game %s full' % game.name)
				elif playerType == 'POWER' and not 'SILENT_JOIN' in game.rules:
					game.mailPress(None, ['All!'],
						'%s has joined the game. %s %d position%s left.' %
						(game.anglify(power), ('Only', 'Still')[2 * avail >
						len(game.map.powers) - len(game.map.dummies)], avail,
						's'[:avail != 1]))
			if responding is not None: self.response += [
				"You are now %s'%s' in game '%s'.\n\n"
				'Welcome to the %s' % (command not in ('JOIN', 'TAKEOVER')
				and ('a%s %s with ID ' % ('n'[:playerType[0] in 'AEIOU'],
				playerType.title())) or '', game.anglify(power), game.name,
				host.dpjudgeNick)]
		#	----------------------------------------------------
		#	Process the rest of the message for press to be sent
		#	----------------------------------------------------
		self.handleEmail(power, password)
		#	---------------
		#	Resign a player
		#	---------------
		if command == 'RESIGN':
			game.powers[num].resign()
		else: self.message, self.pressSent = [], 1
		self.respond()
	#	----------------------------------------------------------------------
	def powerID(self, abbrev, asName = True):
		"""
		Procmail.powerID(abbrev, asName = True):
			Given a power name or abbreviation, returns either the full power
			name (the default) or the Power object (if the "asName" parameter
			passed in is False).  If the "abbrev" does not identify a power,
			None is returned.
		"""
		if abbrev in ('M', 'MASTER'): return 'MASTER'
		if abbrev in ('JK', 'JUDGEKEEPER'): return 'JUDGEKEEPER'
		for who in self.game.powers:
			if (abbrev in
				(who.name, who.name[who.name[0] == '-':],
				self.game.map.abbrev.get(who.name, who.name[0]))
			or who.type == 'POWER' and abbrev == who.name.split('#')[-1]):
				return asName and who.name or who
	#	----------------------------------------------------------------------
	def respond(self, error = 0, copyTo = []):
		self.game = self.game or Game()
		if not self.power: rightEmail = self.email
		elif self.power.name == 'MASTER': rightEmail = self.game.master[1]
		elif self.power.name == 'JUDGEKEEPER': rightEmail = host.judgekeeper
		elif self.power.address: rightEmail = self.power.address[0]
		else: rightEmail = self.email
		wrongMail = 0
		if rightEmail.upper() not in (self.email.upper(), 'RESIGNED', 'DUMMY'):
			user, domain = self.email.upper().split('@')
			for u, d in [x.split('@') for x in rightEmail.upper().split(',')]:
				if u == user and d.endswith(domain): break
			else: wrongEmail = 1
		if error: self.response += [error]
		elif not self.response:
			if not wrongMail or not self.pressSent: return
			self.response = ['Message processed; press echoed to %s\n'
				 '(you sent from %s)' % (rightEmail, self.email)]
			self.message = None
		if type(copyTo) != list: copyTo = [copyTo]
		emails = []
		for email in [self.email] + copyTo:
			#	--------------------
			#	Prevent e-mail loops
			#	--------------------
			if email in emails: continue
			elif email == host.dpjudge:
				self.game.openMail('DPjudge e-mail reply' +
					' (redirected from %s)' % email,
					mailTo = host.judgekeeper, mailAs = host.dpjudge)
			else:
				self.game.openMail('DPjudge e-mail reply', mailTo = email,
					mailAs = host.dpjudge)
			mail = self.game.mail
			for line in self.response: mail.write(line + '.\n\n')
			if error and self.message:
				if self.pressSent and wrongMail: mail.write(
					'Message partially processed; press echoed to %s.\n\n' %
					rightEmail)
				mail.write('Unprocessed portion of message follows:\n\n' +
					'\n'.join(self.message))
			mail.close()
			emails += [email]
		os._exit(os.EX_OK)
	#	----------------------------------------------------------------------
	def locatePower(self, powerName, password, mustBe = 1, newPass = 0):
		if not password: self.respond('No password specified')
		if ' ' in password: self.respond('Multiple passwords given')
		powerName = self.powerID(powerName)
		if powerName == 'MASTER':
			power = Power(self.game, 'MASTER')
			if password.upper() not in (self.game.password.upper(),
				host.judgePassword.upper()):
				self.respond('Invalid Master password specified')
		elif powerName == 'JUDGEKEEPER':
			power = Power(self.game, 'JUDGEKEEPER')
			if password.upper() != host.judgePassword.upper():
				self.respond('Invalid Judgekeeper password specified')
		else:
			try: power = [x for x in self.game.powers
				if x.name[x.name[0] == '_':].replace('+', '') == powerName
				and (newPass or x.isValidPassword(password))][0]
			except:
				if mustBe: self.respond('Invalid power or password specified')
				power = None
		self.power = power
	#	----------------------------------------------------------------------
	def handleEmail(self, powerName, password):
		game, orders = self.game, []
		if game.phase in ('FORMING', 'COMPLETED'): rules = ['PUBLIC_PRESS']
		else: rules = game.rules
		official = press = deathnote = None
		if not self.power: self.locatePower(powerName, password)
		power, self.message = self.power, self.message[1:] + ['SIGNOFF']
		try: self.ip = socket.gethostbyaddr(self.ip)[0]
		except: pass
		game.logAccess(power.name, password, self.ip or self.email)
		for line in self.message[:]:
			word = line.upper().split()
			command = word and word[0] or None
			#	-------------------------------------
			#	See if we're building a press message
			#	-------------------------------------
			if press != None:
				msgLines += 1
				#	----------------------------
				#	Yes; if we're not at the end
				#	of the message, add to it.
				#	----------------------------
				if command not in ('SIGNOFF', 'ENDPRESS', 'ENDBROADCAST'):
					press += line + '\n'
					continue
				#	------------------------------------------------
				#	End of message reached.  Time to send the press.
				#	First, make sure the listed options are kosher.
				#	------------------------------------------------
				if not readers: self.respond('No press recipient specified')
				if claimFrom == '(WHITE)': claimFrom = None
				if not self.isMaster(power):
					late = game.latePowers()
					if (game.deadline and game.deadline <= game.getTime()
					and ('LATE_SEND' not in game.rules
					or	'NO_LATE_RECEIVE' in game.rules
					or	'FTF_PRESS' in game.rules)
					and late and readers not in (['All'], ['MASTER'])):
						if 'FTF_PRESS' in game.rules: self.respond(
							'Private press not allowed after deadline')
						if 'LATE_SEND' not in game.rules and power.name in late:
							self.respond('Private press not allowed while late')
						if 'NO_LATE_RECEIVE' in game.rules:
							for reader in readers:
								if reader in late: self.respond(
									'Private press may not be sent to late '
									'power (%s)' % game.anglify(reader))
					if ('MUST_ORDER' in game.rules
					and power.name in late and readers != ['MASTER']):
						self.respond('Press disallowed before order submission')
					if 'TOUCH_PRESS' in rules or 'REMOTE_PRESS' in rules:
						if 'PUBLIC_PRESS' not in rules and readers == ['All']:
							self.respond('Broadcast press not allowed')
					elif ('PUBLIC_PRESS' in rules
					and (claimTo or readers not in (['All'], ['MASTER']))):
						self.respond('Private press not allowed')
					if 'NO_PRESS' in rules and readers != ['MASTER']:
						self.respond('Private press allowed only to Master')
					if 'FAKE_PRESS' not in rules:
						if claimTo or claimFrom not in (None, '(ANON)'):
							self.respond('Fake press not allowed')
					elif claimFrom == 'MASTER' or (claimTo
					and 'MASTER' in claimTo
					and 'MASTER' not in readers and (
					'PRESS_MASTER' in rules or readers != ['All'])):
						self.respond('Cannot fake press to or from the Master')
					if (('YELLOW_PRESS' in rules and readers == ['All'])
					or 'GREY_PRESS' in rules): claimFrom = '(ANON)'
					elif claimFrom and ('WHITE_GREY' not in rules
					and 'FAKE_PRESS' not in rules):
						self.respond('Grey press not allowed')
					eligible = game.eligiblePressRecipients(power, 1)
					[self.respond('Press to %s impossible' % game.anglify(x))
						for x in readers if x.upper() not in eligible]
					if ('FTF_PRESS' in rules
					and (game.phaseType != 'M' or game.await)
					and readers != ['MASTER']): self.respond(
						'Press disallowed until next movement phase')
				#	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				#	Check for postage funds, etc. -- maybe do this in
				#	mailPress(), have it return an error code if insuf
				#	funds and then do a "if" and "self.respond" below.
				#	~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
				#	-----------------------------
				#	All is well; send the message
				#	-----------------------------
				game.mailPress(power, readers, press,
					claimFrom, claimTo, receipt = receipt, subject = official)
				del self.message[:msgLines]
				self.pressSent = self.pressSent or receipt
			if command == 'SIGNOFF': break
			if press is not None: press = None
			#	-------------------------------------
			#	See if we're starting a press message
			#	-------------------------------------
			elif command in ('BROADCAST', 'PRESS'):
				readers = [self.isMaster(power) and 'All!' or 'All'][
					:command[0] == 'B']
				which = claimFrom = claimTo = None
				wordNum = receipt = 1
				while wordNum < len(word):
					item = word[wordNum]
					if which:
						while item[-1] == ',':
							wordNum += 1
							item += word[wordNum]
						powers, guy = item.split(','), []
						if len(powers) == 1:
							player = self.powerID(item, asName = False)
							if player: powers, guy = [], [player == 'MASTER'
								and player or player.name]
							else: powers = item
						for who in powers:
							player = self.powerID(who)
							if not player:
								self.respond('Unknown power for press: ' + who)
							guy += [player]
						if which == 'FROM':
							if len(guy) != 1: self.respond(
								'Press must come FROM single power only')
							if player == 'MASTER': self.respond(
								'Press may not be sent as if FROM the MASTER')
							if player.type == 'MONITOR': self.respond(
								'Press may not be sent as if FROM a MONITOR')
							claimFrom = guy[0]
						elif which == 'TO': readers = guy
						else: claimTo = guy
						which = None
					elif item == 'QUIET':
						if not receipt: self.respond('QUIET given twice')
						receipt = 0
					elif item == 'TO' or item[0] == '+':
						if readers:
							self.respond('Press recipients listed twice')
						which = 'TO'
						if item not in ('TO', '+'):
							word[wordNum] = item[1:]
							continue
					elif item == 'FAKE':
						try:
							command = word[wordNum + 1]
							if command[0] == '+' and command != '+':
								which, word[wordNum + 1] = item, command[1:]
								continue
						except: command = None
						if command in ('TO', '+', None):
							if not readers: self.respond(
								item + ' must appear after TO option')
							which = item
							wordNum += 1
						elif command == 'BROADCAST':
							claimTo = ['All']
							wordNum += 1
						elif command != 'FROM': self.respond(
							item + ' must be followed by FROM or TO')
					elif item in ('FROM', 'WHITE', 'GRAY', 'GREY'):
						if claimFrom:
							self.respond('More than one FROM option given')
						if item == 'FROM': which = item
						elif item == 'WHITE': claimFrom = '(WHITE)'
						else: claimFrom = '(ANON)'
					else: self.respond('Unrecognized press option: ' + item)
					wordNum += 1
					if which and wordNum >= len(word):
						self.respond('Incomplete press specification')
				if not readers: self.respond('No press recipient specified')
				press, msgLines = '', 1
			#	-----------------------------------
			#	See if this is to be official press
			#	-----------------------------------
			elif command == 'OFFICIAL':
				if not self.isMaster(power):
					self.respond('Only the Master can send OFFICIAL press')
				official = ' '.join(line.split()[1:])
				del self.message[0]
			#	---------------------
			#	Change the game state
			#	---------------------
			elif command in ('FORM', 'ACTIVATE', 'WAIT', 'TERMINATE'):
				if not self.isMaster(power):
					self.respond('Only the Master can change the game state')
				mode = {'F': 'forming', 'A': 'active', 'W': 'waiting',
					'T': 'terminated'}[command[0]]
				if game.status[1] == mode:
					self.response += ['The game is already in the %s state' %
						mode]
				else:
					if (game.status[1] == 'preparation' and mode == 'forming'
					and not (game.available() or 'START_MASTER' in game.rules)):
						mode = 'active'
					reply = game.setState(mode)
					if reply: self.respond(reply)
					self.response += ['The game state has been changed to %s' %
						game.status[1]]
			#	------------------------------
			#	See if we are to do a ROLLBACK
			#	------------------------------
			elif command == 'ROLLBACK':
				if not self.isMaster(power):
					self.respond('Only the Master can ROLLBACK the game')
				phase, flags = '', 0
				for param in [x.upper() for x in word[1:]]:
					if param in ('RESTORE', 'RECOVER'): flags |= 1
					elif param == 'FULL': flags |= 2
					else: phase = param
				error = game.rollback(phase, flags)
				if error: self.respond(error)
				self.response += ['Game rolled back to ' + game.phase]
			#	---------------------------------
			#	See if we are to do a ROLLFORWARD
			#	---------------------------------
			elif command == 'ROLLFORWARD':
				if not self.isMaster(power):
					self.respond('Only the Master can ROLLFORWARD the game')
				phase, flags = '', 4
				for param in [x.upper() for x in word[1:]]:
					if param in ('RESTORE', 'RECOVER'): flags |= 1
					elif param == 'FULL': flags |= 2
					else: phase = param
				error = game.rollforward(phase, flags)
				if error: self.respond(error)
				self.response += ['Game rolled forward to ' + game.phase]
			#	--------------------------------------------------------
			#	See if we are trying to RESIGN, DUMMY or REVIVE a player
			#	--------------------------------------------------------
			elif command in ('RESIGN', 'DUMMY', 'REVIVE'):
				#Only the master can do these things
				if not self.isMaster(power):
					self.respond('Only the Master can %s a player' % command)
				#Must have a power to work with
				if len(word) == 1:
					self.respond('No power specified to ' + command)
				#Power must exist
				goner = [x for x in game.powers if x.name == word[1]]
				if goner: goner = goner[0]
				#Cannot RESIGN, DUMMY or REVIVE the MASTER
				elif target == 'MASTER':
					self.respond('Cannot %s the MASTER' % command)
				else: self.respond('Could not find power to ' + command)
				#Power must be resigned to be revived
				if command == 'REVIVE':
					if not goner.isResigned() and not goner.isDummy():
						self.respond('Cannot REVIVE a non-resigned power')
				#Power must not be already resigned or dummied
				elif goner.player[0].startswith(command):
					self.respond('Cannot %s a %s player' %
						(command, goner.player[0]))
				#copied from RESIGN signon format
				if command == 'RESIGN': response = goner.resign(1)
				#modified TAKEOVER format
				elif command == 'REVIVE':
					response = goner.takeover(password = len(word) > 2 and
						self.sanitize(word[2]) or None)
				else: response = goner.dummy()
				if response: self.respond(response)
			#	--------------------------
			#	SET ADDRESS, SET PASSWORD,
			#	and SET DEADLINE handling.
			#	--------------------------
			elif (len(word) > 1 and word[0] == 'SET'
			and word[1] in ('ADDRESS', 'PASSWORD', 'DEADLINE', 'ZONE',
							'NOZONE', 'WAIT', 'NOWAIT', 'ABSENCE')):
				nok = word[1][:2] == 'NO' and 2 or 0
				if len(word) == 2:
					if word[1][:2] == 'AD': word += [self.email]
					elif word[1][nok] == 'Z' and power.name == 'MASTER':
						word += [host.timeZone or 'GMT']
					elif word[1][nok] not in 'WZ': 
						self.respond('No new %s given' % word[1])
				elif word[1][nok] == 'W':
					self.respond('Bad %s directive' % word[1])
				if word[1][:2] == 'DE':

					#	------------
					#	SET DEADLINE
					#	------------
					if 'NO_DEADLINE' in game.rules:
						self.respond('No deadlines can be set in this game')
					elif (not self.isMaster(power)
					and 'PLAYER_DEADLINES' not in game.rules):
						self.respond('Only the Master can SET %s' % word[1])
					if game.phase in ('FORMING', 'COMPLETED'): self.respond(
						'DEADLINE cannot be set on an inactive game')
					if word[2] in ('TO', 'ON'): del word[2]
					now, date = game.getTime(npar=6), word[2:]
					try:
						if ':' not in date[-1]:
							date += [game.timing.get('AT', '0:00')]
						newline = now.next(' '.join(date))
					except: self.respond('Bad %s specified' % word[1])
					if now > newline: self.respond(
						'DEADLINE has already past: ' + ' '.join(word[2:]))
					if (not self.isMaster(power)
					and newline < game.deadline): self.respond(
						'Only the Master may shorten a deadline')
					game.deadline, game.delay = newline, None
					if not deathnote: deathnote = (
						"The deadline for game '%s' has been changed "
						'by %s.\n' % (game.name,
						self.isMaster(power) and ('the ' +
						game.anglify(power.name))
						or 'HIDE_EXTENDERS' in game.rules and 'a power'
						or game.anglify(power.name)))
				elif word[1][:2] == 'AB':
					#	-----------
					#	SET ABSENCE
					#	-----------
					if 'NO_ABSENCES' in game.rules and not self.isMaster(power):
						self.respond('Only the Master is allowed to ' +
							'SET ABSENCE in this game')
					if word[2] in ('ON', 'FROM'): del word[2]
					now, dates, oldline = game.getTime(npar=6), [word[2:]], None
					where = ('TO' in word and word.index('TO') or
						'UNTIL' in word and word.index('UNTIL'))
					if where == 2: dates = [None, word[3:]]
					elif where: dates = [word[2:where], word[where + 1:]]
					for date in dates:
						if not date: continue
						try:
							newline = (oldline or now).next(' '.join(date))
							if not oldline: oldline = newline
						except: self.respond('Bad %s specified' % word[1])
					if len(dates) < 2: nope, oldline = '', newline
					elif dates[0]: nope = str(oldline)  + '-'
					else: nope, oldline = '-', None
					nope += str(newline)
					if oldline:
						if oldline < now: oldline = None
						else: oldline = oldline.adjust(5)
					if newline.npar() < 4: newline = newline.offset('1D')
					newline = newline.adjust(5)
					if newline == oldline:
						self.respond('One minute ABSENCE too short')
					if (newline < (oldline or now) or not self.isMaster(power)
					and newline > (oldline or now).offset('2W')):
						self.respond('Invalid ABSENCE duration')
					dates = (oldline and oldline.format(0) or None,
						newline.format(0))
					game.setAbsence(power, nope)
				elif len(word) > 3: self.respond('Bad %s syntax' % word[1])
				#	-------------------
				#	SET ZONE and NOZONE
				#	-------------------
				elif word[1][nok] == 'Z':
					if len(word) == 2: power.zone = None
					else:
						zoneInfo = Time.TimeZone(word[2])
						if not zoneInfo:
							self.respond("Bad time zone '%s'" % word[2])
						zone = zoneInfo.__repr__()
						if self.isMaster(power):
							game.setTimeZone(zone)
							deathnote = ("The Master has changed the time zone for game " +
								"'%s'\nto %s (%s).\n" % (game.name, zone,
								zoneInfo.gmtlabel()))
						else: power.zone = zone
				#	-------------------
				#	SET WAIT and NOWAIT
				#	-------------------
				elif word[1][nok] == 'W':
					if self.isMaster(power):
						self.respond('MASTER has no WAIT flag')
					if game.await or game.deadline < game.getTime():
						self.respond('WAIT unavailable after deadline')
					if power.isEliminated():
						self.respond('WAIT unavailable; no orders required')
					if ('NO_MINOR_WAIT' in game.rules
					and game.phaseType != 'M'):
						self.respond('WAIT not available in this phase')
					if power.name in game.map.powers:
						power.wait = not nok
				else:
					#	----------------------------
					#	SET ADDRESS and SET PASSWORD
					#	----------------------------
					word[2] = word[2].lower()
					if word[1][0] == 'A':
						try:
							for addr in word[2].split(','):
								who, where = addr.split('@')
								if (not who or '.' not in where
								or not where.split('.')[-1].isalpha()
								or '.' in (where[0], where[-1])): raise
						except: self.respond('Bad ADDRESS: ' + addr)
					if self.isMaster(power):
						if word[1][0] == 'A': game.master[1] = word[2]
						else: game.password = self.sanitize(word[2])
					elif word[1][0] == 'A':
						power.address = power.address or ['']
						power.address[0] = word[2]
					else:
						if 'BLIND' in game.rules: power.removeBlindMaps()
						power.password = word[2]
						if 'BLIND' in game.rules: game.makeMaps()
				game.save()
				if word[1][:2] == 'AB':
					self.response += ['No deadlines will be set ' +
						('from %s to %s' % dates,
						'until after %s' % dates[1])[not dates[0]]]
				elif word[1][0] in 'AP':
					self.response += [word[1].title() + ' set to ' + word[2]]
				elif word[1][0] in 'NW': self.response += [
					'Wait status %sset' % ('re' * (word[1][0] == 'N'))]
				del self.message[0]
			#	-------------------------------
			#	LIST, SUMMARY, HISTORY, and MAP
			#	-------------------------------
			elif command in ('LIST', 'SUMMARY', 'HISTORY', 'MAP'):
				if command == 'MAP':
					mapType = word[-1].lower()
					if mapType in ('ps', 'pdf', 'gif'): del word[-1]
					else: mapType = 'gif'
				if len(word) > 2:
					self.respond('Must specify single game for ' + command)
				if len(word) > 1 and word[1].lower() != game.name: self.respond(
					'May only get %s of current game after SIGNON' % command)
				if command[0] == 'S': game.summary(self.email, power)
				elif command[0] == 'L':
					game.list(self.email, power, subject=self.subject)
				elif command[0] == 'H': game.history(self.email, power)
				elif not game.mailMap(self.email, mapType, power):
					self.respond("No '%s' map is available for game " %
						mapType.upper() + game.name)
			#	----------------
			#	CLEAR and STATUS
			#	----------------
			elif command == 'CLEAR': orders += [command]
			elif command == 'STATUS': game.reportOrders(power, self.email)
			#	----------------------------
			#	REVEAL the game if requested
			#	----------------------------
			elif command == 'REVEAL':
				if not self.isMaster(power):
					self.respond('Only the Master can REVEAL the game')
				if game.phase != 'COMPLETED':
					self.respond('Only a COMPLETED game can be REVEALed')
				if 'NO_REVEAL' in game.rules: game.fileSummary(reveal = 1)
				self.response += ["Game '%s' REVEALed" % game.name]
				del self.message[0]
			#	----------------------------------------
			#	PROCESS or PREVIEW the game if requested
			#	----------------------------------------
			elif command in ('PROCESS', 'PROCESS!', 'PREVIEW'):
				if not self.isMaster(power):
					self.respond('Only the Master can PROCESS/PREVIEW the game')
				game.preview = command == 'PREVIEW'
				error = game.process(1 + ('!' in command), self.email)
				if error: self.respond(error)
			#	-------------------------------
			#	Remove any press ending command
			#	-------------------------------
			elif command in (None, 'ENDPRESS', 'ENDBROADCAST'):
				if self.message: del self.message[0]
			else:
				orders += [line.strip()]
				del self.message[0]
		#	--------------------------------
		#	If the deadline or the time zone
		#	was changed, broadcast it.
		#	--------------------------------
		if deathnote: game.mailPress(None, ['All!'], deathnote +
			'The new deadline is %s.\n' % game.timeFormat(), subject = 'Diplomacy deadline changed')
		if orders: self.setOrders(orders)
	#	----------------------------------------------------------------------
	def sanitize(self, password):
		if password.upper().endswith('SIGNOFF') and len(password) > 7:
			return password[:-7]
		return password
	#	----------------------------------------------------------------------
	def setOrders(self, orders):
		game = self.game
		if not orders and 'MUST_ORDER' in game.rules:
			game.error += ['ORDERS MAY NOT BE CLEARED AFTER SUBMISSION']
		elif game.phaseType == 'R':
			game.updateRetreatOrders(self.power, orders)
		elif game.phaseType == 'A':
			game.updateAdjustOrders(self.power, orders)
		else:
			try: game.updateOrders(self.power, orders)
			except:
				self.message = orders + ['']
				self.respond('Improper e-mail order submission')
		text = '\n'.join(game.error)
		if text:
			if orders: text += ('\n\nErroneous orders:\n\n%s\n\n'
				'End of erroneous orders' % '\n'.join(orders))
			self.respond(text)
		else: game.reportOrders(self.power, self.email)
	#	----------------------------------------------------------------------
	def isMaster(self, power):
		try: return power.name in ('MASTER', 'JUDGEKEEPER')
		except: return power in ('MASTER', 'JUDGEKEEPER')
	#	----------------------------------------------------------------------

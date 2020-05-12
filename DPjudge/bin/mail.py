#!/usr/bin/env python -O

import email
from codecs import open

from DPjudge import *
from DPjudge.dppd.DPPD import RemoteDPPD

class Procmail:
	#	-------------------------------------------------------------
	"""
	This class is instantiated on all e-mail coming into the dpjudge.
	It detects email commands, processes them, and responds to them.
	"""
	#	-------------------------------------------------------------
	def __init__(self):
		self.message = self.msgLines = self.email = self.signOff = None
		part = input = email.message_from_file(os.sys.stdin)
		addy = part.get('reply-to', part['from']) or ''
		if '@' in addy:
			self.email = [x for x in addy.split() if '@' in x][0]
			pre, post = self.email.split('@')[:2]
			pre, post = pre.split('<')[-1], post.split('>')[0]
			self.email = (pre + '@' + post).lower().strip('<",>')
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
		lines, msg = [x for x in lines if x.strip()[:2] != '//'], []
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
		self.message = msg
		#file = open(host.gameDir + '/message', 'w')
		#file.write('\n'.join(self.message).encode('latin-1'))
		#file.close()
		#	---------------------------------------
		#	Process each SIGNON, CREATE, JOIN, etc.
		#	command separately.
		#	---------------------------------------
		while self.message and not self.signOff:
			self.parseMessage()
	#	----------------------------------------------------------------------
	def parseMessage(self):
		self.game = self.power = self.pressSent = None
		self.response = []
		game = power = password = joiner = nopower = None
		lineNo = 0
		for line in self.message[:]:
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
			unrecognized = 0
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
				game, toGame, password, variant = ' '.join(
					word[1:]).lower().split()
				password = self.sanitize(password)
				variant = self.sanitize(variant)
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
					del self.message[:lineNo]
					if not response: 
						response = ['Game %s purged from this DPjudge' % game]
					self.response += response
					return self.respond()
				elif upword[0] == 'R':
					response = Status().renameGame(game, toGame, 0, password)
					del self.message[:lineNo]
					if not response: 
						response = ['Game %s renamed to %s' % (game, toGame)]
					self.response += response
					return self.respond()
				else:
					del self.message[:lineNo]
					self.handleGameCreation(upword, game, password, variant)
					return
			#	---------------------------------------------------
			#	Detect player message (SIGNON, RESIGN, or TAKEOVER)
			#	---------------------------------------------------
			elif upword in ('SIGNON', 'RESIGN', 'TAKEOVER'):
				self.dppdMandate(upword)
				nopower = ''
				if len(word) == 1: power = game = ''
				elif list(word[1]).count('@') == 1:
					power, game = word[1].split('@')
					power, game = power[power[:1] == '_':].upper(), game.lower()
				else:
					power, game = word[1][0].upper(), word[1][1:].lower()
					nopower = word[1].lower()
				try: password = self.sanitize(word[2])
				except: password = ''
				if upword[0] == 'T':
					if '<' in password or '>' in password:
						self.respond("Password cannot contain '<' or '>'")
				if upword[0] != 'S': joiner = word[0].upper()
				del self.message[:lineNo - 1]
				break
			#	----------------------------------------------------
			#	Detect LIST, SUMMARY, HISTORY, SEARCH or MAP request
			#	----------------------------------------------------
			elif upword in ('LIST', 'SUMMARY', 'HISTORY', 'SEARCH', 'MAP'):
				if upword == 'MAP':
					mapType = word[-1].lower()
					if mapType in ('ps', 'pdf', 'gif'): del word[-1]
					else: mapType = 'gif'
				self.pressSent = None
				if upword == 'SEARCH':
					Status().list(self.email, self.subject, word[1:])
				elif upword == 'LIST' and len(word) == 1:
					Status().list(self.email, self.subject)
				elif len(word) != 2: self.respond(
					'A single game must be specified to ' + upword)
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
				game = nopower = None
				joiner = upword
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
			elif upword == 'SIGNOFF':
				self.signOff = 1
				return
			#	-----------------
			#	Unrecognized line
			#	-----------------
			else:
				unrecognized = 1
				break
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
			if 'OBSERVER'.startswith(upword):
				self.respond('No playerName given. Use '
					'"OBSERVE playerName@gameName password"')
			elif unrecognized:
				self.respond('Expected SIGNON, JOIN, CREATE, PURGE, RENAME, '
					'RESIGN, TAKEOVER, SUMMARY, HISTORY, or LIST,\n'
					'or a valid non-map-power join '
					'command (e.g., OBSERVE playerName@gameName)')
			else:
				self.respond('No gameName specified for %s command' % upword) 
		self.game = Status().load(game)
		if not self.game:
			if not self.email: raise NoSuchGame, game
			if nopower:
				self.game = Status().load(nopower)
				if self.game:
					self.respond("No power specified for game '%s'" % nopower)
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
			return self.respond()
	#	----------------------------------------------------------------------
	def handleGameCreation(self, upword, game, password, variant):
		games, mode, unlisted = Status(), 'preparation', 0
		#if len([1 for x in games.dict.values()
		#	if 'forming' in x or 'preparation' in x]) > 20:
		#	self.respond('CREATE is disabled -- '
		#		'too many games currently need players')
		if game in games.dict:
			self.respond("Game name '%s' already used" % game)
		try: desc = __import__('DPjudge.variants.' + variant,
			globals(), locals(), repr(variant)).VARIANT
		except: self.respond('Unrecognized rule variant: ' +
			variant)
		self.dppdMandate(upword)
		temp, onmap = ('GAME %s\nPHASE FORMING\nMASTER %s\n' +
			'PASSWORD %s\n') % (game, self.dppd, password), ''
		lineNo, block = 0, None
		for line in self.message[:]:
			lineNo += 1
			word = line.split()
			if self.checkEnd(line, block):
				if block:
					temp += line + '\n'
					block = None
				else:
					del self.message[:lineNo - 1]
					break
			elif block: temp += line + '\n'
			elif not len(word):
				if desc:
					temp += 'DESC A %s game%s.\n' % (desc, onmap)
					desc = None
				temp += '\n'
			else:
				upword = word[0].upper()
				if upword in ('DESC', 'DESCRIPTION'):
					desc = None
					if len(word) == 1: block = ['DESC', 'DESCRIPTION']
				elif upword in ('MAP', 'TRIAL'):
					onmap = ' on the %s%s map' % (
						''.join(word[1:2]).title(),
						('', ' trial')[word == 'TRIAL'])
				elif len(word) == 1 and upword in ('NAME', 'MORPH'):
					block = [upword]
				if upword in ('GAME', 'PHASE', 'MASTER'): pass
				elif (len(word) == 1
				and upword in ('FORM', 'ACTIVATE')): mode = 'forming'
				elif (len(word) == 2 and upword == 'SET'
				and word[1].upper() in ('LISTED', 'UNLISTED')):
					unlisted = upword[1] == 'U'
				else: temp += line + '\n'
		else: self.message = []
		if desc:
			temp += 'DESC A %s game%s.\n' % (desc, onmap)
		games.dict[game] = [variant, mode]
		if unlisted: games.dict[game] += ['unlisted']
		games.save()
		dir = host.gameDir + '/' + game
		try:
			os.mkdir(dir)
			os.chmod(dir, 0777)
		except: pass
		try:
			file = open(dir + '/status', 'w')
			file.write(temp.encode('latin-1'))
			file.close()
			os.chmod(file.name, 0666)
		except: self.respond('Unable to create status file')
		self.game = Game(game)
		if 'SOLITAIRE' in self.game.rules:
			if self.game.private is None: self.game.private = 'SOLITAIRE'
			self.game.save()
		if self.game.private:
			games.dict[game] += ['private']
			games.save()
		if (mode == 'forming' and not self.game.available()
		and 'START_MASTER' not in self.game.rules):
			self.game.begin()
			mode = 'active'
		observers = host.observers or []
		if type(observers) is not list: observers = [observers]
		self.response += ["Game '%s' has been created.  %s at:\n" %
			(game, mode[0] == 'p' and 'Finish preparation'
			or mode[0] == 'f' and 'Game is now forming'
			or 'Game has started') +
			'   %s%s?game=%s\n\n' % (host.dpjudgeURL,
			'/index.cgi' * (os.name == 'nt'), game) +
			'Welcome to the %s' % host.dpjudgeNick]
		self.respond(copyTo = observers + self.game.map.notify)
	#	----------------------------------------------------------------------
	def handleEmail(self, powerName, password):
		game, orders, proposal = self.game, [], None
		if game.phase in ('FORMING', 'COMPLETED'): rules = ['PUBLIC_PRESS']
		else: rules = game.rules
		official = press = deathnote = vote = None
		if not self.power: self.locatePower(powerName, password)
		power = self.power
		try: self.ip = socket.gethostbyaddr(self.ip)[0]
		except: pass
		game.logAccess(power.name, password, self.ip or self.email)
		del self.message[0]
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
				if not self.checkEnd(line, ['PRESS', 'BROADCAST'], 1):
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
						self.respond('Private press not allowed' +
							' before the start of the game' *
							(game.phase == 'FORMING') +
							' after the end of the game' *
							(game.phase == 'COMPLETED'))
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
			if self.checkEnd(line): break
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
			#	---------------------------------------
			#	SET ADDRESS, SET PASSWORD, SET DEADLINE
			#	and other SET command handling.
			#	---------------------------------------
			elif len(word) > 1 and word[0] == 'SET':
				if word[1] == 'NO' and len(word) > 2:
					word[1] += word[2]
					del word[2]
				if word[1] not in ('ADDRESS', 'PASSWORD', 'DEADLINE', 'ABSENCE',
					'ZONE', 'NOZONE', 'WAIT', 'NOWAIT',
					'DRAW', 'NODRAW','CONCEDE', 'NOCONCEDE',
					'LISTED', 'UNLISTED'):
					self.respond('SET %s directive not recognized' % word[1])
				nok = word[1][:2] in ('NO', 'UN') and 2 or 0
				if len(word) == 2:
					if word[1][:2] == 'AD': word += [self.email]
					elif word[1][nok] == 'Z' and power.name == 'MASTER':
						word += [host.timeZone or 'GMT']
					elif word[1][:2] in ('PA', 'DE', 'AB'): 
						self.respond('No new %s given' % word[1])
				elif word[1][:2] not in ('AD', 'PA', 'DE', 'AB', 'ZO'): 
					self.respond('Bad %s directive' % word[1])
				#	------------
				#	SET DEADLINE
				#	------------
				if word[1][:2] == 'DE':
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
							at = game.timing.get('AT', '0:00')
							if ',' not in at: date += [at]
							elif game.deadline:
								date += [game.deadline.formatTime(1)]
							else: date += ['00:00']
						newline = now.next(' '.join(date),
							'REAL_TIME' in game.rules and 1 or 1200)
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
				#	-----------
				#	SET ABSENCE
				#	-----------
				elif word[1][:2] == 'AB':
					if 'NO_ABSENCES' in game.rules and not self.isMaster(power):
						self.respond('Only the Master is allowed to ' +
							'SET ABSENCE in this game')
					if word[2] in ('ON', 'FROM', 'FOR'): del word[2]
					now, dates, oldline = game.getTime(npar=6), [word[2:]], None
					where = ('TO' in word and word.index('TO') or
						'UNTIL' in word and word.index('UNTIL'))
					if where == 2: dates = [None, word[3:]]
					elif where: dates = [word[2:where], word[where + 1:]]
					for date in dates:
						if not date: continue
						try:
							newline = (oldline or now).next(' '.join(date), 1)
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
					dates = (oldline and oldline.format() or None,
						newline.format())
					msg = game.setAbsence(power, nope)
					if msg: self.respond(msg.replace('Absence', 'ABSENCE'))
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
							deathnote = ("The Master has changed the time zone "
								"for game '%s'\nto %s (%s).\n" %
								(game.name, zone, zoneInfo.gmtlabel()))
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
				#	-------------------------
				#	SET DRAW and NODRAW
				#	SET CONCEDE and NOCONCEDE
				#	-------------------------
				elif word[1][nok] in 'DC':
					if vote is not None:
						self.respond('Please submit one vote only')
					if not power.canVote():
						self.respond('%s has no right to vote' % power.name)
					if 'PROPOSE_DIAS' in game.rules:
						self.respond('Please respond with VOTE YES or ' +
							'VOTE NO when there is a proposal')
					elif 'NO_DRAW' in game.rules and word[1][0] == 'D':
						self.respond('No draws are allowed in a NO_DRAW game')
					vote = nok and 1 or word[1][0] == 'D' and -1 or 0
				#	-----------------------
				#	SET LISTED and UNLISTED
				#	-----------------------
				elif word[1][nok] == 'L':
					if not self.isMaster(power):
						self.respond('Only the MASTER may UNLIST a game')
					gameMode = game.status[1:]
					if 'unlisted' in gameMode == (nok and 1):
						self.respond('Game already ' + word[2])
					if nok: gameMode += ['unlisted']
					else: gameMode.remove('unlisted')
					game.status[1:] = gameMode
					games.update(game.name, gameMode, game.status[0])
				#	----------------------------
				#	SET ADDRESS and SET PASSWORD
				#	----------------------------
				else:
					word[2] = word[2].lower()
					if word[1][0] == 'A':
						try:
							for addr in word[2].split(','):
								who, where = addr.split('@')
								if (not who or '.' not in where
								or not where.split('.')[-1].isalpha()
								or '.' in (where[0], where[-1])): raise
						except: self.respond('Bad ADDRESS: ' + addr)
					if word[1][0] == 'A':
						power.address = power.address or ['']
						power.address[0] = word[2]
					elif self.isMaster(power):
						power.password = self.sanitize(word[2])
					else:
						if 'BLIND' in game.rules: power.removeBlindMaps()
						power.password = self.sanitize(word[2])
						if 'BLIND' in game.rules: game.makeMaps()
				game.save()
				if word[1][:2] == 'AB':
					self.response += ['No deadlines will be set ' +
						('from %s to %s' % dates,
						'until after %s' % dates[1])[not dates[0]]]
				elif word[1][0] in 'AP':
					self.response += [word[1].title() + ' set to ' + word[2]]
				elif word[1][nok] == 'W': self.response += [
					'Wait status %sset' % ('re' * (word[1][0] == 'N'))]
				del self.message[0]
			#	----------------
			#	PROPOSE and VOTE
			#	----------------
			elif command == 'PROPOSE':
				if not 'PROPOSE_DIAS' in game.rules:
					self.respond('Not a PROPOSE_DIAS game')
				elif not power.canVote():
					self.respond('%s has no right to vote' % power.name)
				elif game.proposal and vote != 0:
					self.respond('You will first need to veto the current '
						'proposal')
				if len(word) != 2 or word[1] not in ['DIAS'] + [
					x.name for x in game.powers if x.canVote()]:
					self.respond('Invalid PROPOSE command')
				proposal = [word[1], power.name]
			elif command == 'VOTE':
				if vote is not None:
					self.respond('Please submit one vote only')
				if not power.canVote():
					self.respond('%s has no right to vote' % power.name)
				if len(word) > 2 and word[2] == 'WAY':
					word[1] += word[2]
					del word[2]
				if len(word) != 2:
					self.respond('Bad VOTE syntax')
				if 'PROPOSE_DIAS' in game.rules:
					if word[1] == 'YES': vote = 1
					elif word[1] == 'NO': vote = 0
					else:
						self.respond('Please respond with VOTE YES or ' +
							'VOTE NO when there is a proposal')
				elif word[1] == 'LOSS': vote = 0
				elif word[1] == 'SOLO': vote = 1
				elif 'NO_DRAW' in game.rules:
					self.respond('No draws are allowed in a NO_DRAW game')
				elif word[1] in ('DIAS', 'DRAW'): vote = -1
				elif word[1][-3:] != 'WAY':
					self.respond('Bad VOTE syntax')
				elif 'BLIND' in game.rules and 'NO_DIAS' not in game.rules:
					self.respond('A partial draw is not allowed in a DIAS game')
				else:
					vote = word[1][:-3]
					if vote[-1:] == '-': vote = vote[:-1]
					if not vote.isdigit():
						self.respond('Bad VOTE syntax')
					vote = int(vote)
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
			'The new deadline is %s.\n' % game.timeFormat(),
			subject = 'Diplomacy deadline changed')
		if orders: self.setOrders(orders)
		if vote is not None:
			if 'PROPOSE_DIAS' in game.rules:
				if not game.proposal:
					self.respond('No draw proposal has yet been submitted '
						'to vote on')
				self.response += ['You have %s the proposal%s for a %s' %
					(('vetoed', 'agreed to')[vote],
					(' by ' + game.anglify(game.proposal[1])) *
					(not 'HIDE_PROPOSER' in game.rules),
					('concession to ' + game.anglify(game.proposal[0]),
					'draw including all survivors')[game.proposal[0] ==
					'DIAS'])]
			elif vote == 0:
				self.response += ['Your goal is now a concession to ' +
					('another player', 'one or more of the other players')
					['NO_DIAS' in game.rules]]
			elif vote == 1:
				self.response += ['Your goal is now a solo victory for ' +
					game.anglify(power.name)]
			else:
				voters = len([1 for x in game.powers if x.canVote()])
				if 'BLIND' not in game.rules:
					if vote == -1: vote = voters
					elif vote > voters:
						self.respond('There are only %d powers left '
							'to include in the draw' % voters)
					elif vote != voters and 'NO_DIAS' not in game.rules:
						self.respond('A partial draw is not allowed'
							' in a DIAS game')
				self.response += ['Your goal is now a %sdraw'
					' including %s%s' % (('%d-way ' % vote) * (vote > -1),
					game.anglify(power.name), ' (DIAS)' * (vote == voters))]
			power.vote = str(vote)
			game.save()
			game.checkVotes()
		if proposal:
			game.proposal = proposal
			game.save()
			self.response += ['You submitted a proposal for a ' +
				('concession to ' + game.anglify(proposal[0]),
				'draw including all survivors (DIAS)')[proposal[0] == 'DIAS']]
#	----------------------------------------------------------------------
	def checkEnd(self, line, commands = None, concat = 0):
		word = line.upper().split()
		if not word: return
		#	------------------------------------------
		#	A SIGNOFF ends everything. If you want
		#	to do more than one action, like signing
		#	on to multiple games in the same e-mail,
		#	make sure there's no SIGNOFF before the
		#	next SIGNON, but only one at the very end.
		#	------------------------------------------
		if word == ['SIGNOFF']: 
			self.signOff = 1
			return 1
		for command in commands or []:
			if (concat and word[0] == 'END' + command
			or word == ['END', command]): return 1
		if word[0] in ['CREATE', 'RENAME', 'PURGE', 'SIGNON', 'RESIGN',
			'TAKEOVER', 'JOIN', 'MONITOR', 'OBSERVE']:
			if not commands: return 1
			#	-----------------------------------------------
			#	Since most of these commands contain passwords,
			#	be very careful about including them in press
			#	messages or other block commands.
			#	-----------------------------------------------
			if len(word) in (3, 4, 5):
				self.respond('%s command inside a %s block. Did you forget an '
					'%s statement? If not, put something in front like '
					'a quote or another word' % (word[0],
					' or '.join(commands), ' or '.join(['END' +
					' ' * (not concat) + x for x in commands])))
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
		self.dppd = RemoteDPPD().whois(self.email)
		if self.dppd is None: self.respond(
			'Your e-mail address (%s) is\nnot registered with the DPPD, '
			'or your DPPD status does\nnot allow you to use the %s command.'
			'\n\nVisit the DPPD at %s\nfor assistance' %
			(self.email, command, host.dppdURL.split(',')[0]))
		elif self.dppd[0][:1] == 'P': self.respond(
			'Please finish your DPPD registration first\n'
			'by following the instructions written in\nthe mail sent to\n'
			'your e-mail address (%s)' % self.email)
		self.ip, self.dppd = self.email, '|'.join(self.dppd.split())
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
			if existing.isValidPassword(password) < 3:
				self.respond("Incorrect password to modify player ID '%s'" %
					existing.name)
			if command != 'RESIGN': del game.powers[num]
			break
		if (playerType == 'POWER' and game.available() <= 0 and
			command != 'RESIGN'):
			self.respond("The game is already full. " +
				"Try to join another game or take over an abandoned position")
		if (self.dppd and game.gm.player and game.gm.player[0].split('|')[0]
			== self.dppd.split('|')[0] or [1 for x in game.gm.address
			if self.email.lower() in x.lower().split(',')]):
			if command != 'RESIGN': self.respond(
				"You are already Mastering game '%s'" % game.name)
			if self.isMaster(power): self.respond('The Master may not resign')
		#	----------------------
		#	Check for private game
		#	----------------------
		if command != 'RESIGN':
			if not game.private or command == 'MONITOR':
				if len(word) != 3: self.respond('Invalid %s command' % command)
			elif (len(word) == 3 or len(word) == 4
			and self.sanitize(word[3]).upper() != game.private):
				self.respond(
					"Game '%s' is a private game for invited players only.\n"
					'You may %s only by specifying (after your password)\n'
					'the privacy keyword that was given to you by the '
					'GameMaster.\n'
					'A privacy password usually indicates that a game is\n'
					'exclusively for a group of players in a specific club\n'
					'or organization or who know each other personally and\n'
					'can communicate outside the confines of the judge (for\n'
					'example, face-to-face or by telephone)' %
					(game.name, command))
			elif len(word) != 4: self.respond('Invalid %s command' % command)
		#	---------------
		#	Player TAKEOVER
		#	---------------
		if command == 'TAKEOVER':
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
		else: self.pressSent = 1
		return self.respond()
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
		elif self.power.address: rightEmail = self.power.address[0]
		else: rightEmail = self.email
		wrongMail = 0
		if rightEmail.upper() not in (self.email.upper(), 'RESIGNED', 'DUMMY'):
			user, domain = self.email.upper().split('@')
			for u, d in [x.split('@') for x in rightEmail.upper().split(',')]:
				if u == user and d.endswith(domain): break
			else: wrongEmail = 1
		if not error:
			if self.msgLines == len(self.message):
				error = ('Repeating the same response. Please contact '
					'the JudgeKeeper %s with a copy of this message.' %
					host.judgekeeper)
			else: self.msgLines = len(self.message)
		if error: self.response += [error]
		elif not self.response:
			if not wrongMail or not self.pressSent: return
			self.response = ['Message processed; press echoed to %s\n'
					 '(you sent from %s)' % (rightEmail, self.email)]
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
		if error: os._exit(os.EX_OK)
	#	----------------------------------------------------------------------
	def locatePower(self, powerName, password, mustBe = 1, newPass = 0):
		if not password: self.respond('No password specified')
		if ' ' in password: self.respond('Multiple passwords given')
		powerName = self.powerID(powerName)
		if powerName == 'MASTER':
			power = self.game.gm
			if password.upper() not in (power.password.upper(),
				self.game.jk.password.upper()):
				self.respond('Invalid Master password specified')
		elif powerName == 'JUDGEKEEPER':
			power = self.game.jk
			if password.upper() != power.password.upper():
				self.respond('Invalid Judgekeeper password specified')
		else:
			try: power = [x for x in self.game.powers
				if x.name[x.name[0] == '_':].replace('+', '') == powerName
				and (newPass or x.isValidPassword(password) > 2)][0]
			except:
				if mustBe: self.respond('Invalid power "%s" or password "%s" specified' % (powerName, password))
				power = None
		self.power = power
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
		try: return power.omniscient > 2
		except: return power in ('MASTER', 'JUDGEKEEPER')
	#	----------------------------------------------------------------------

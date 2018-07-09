import os, urllib

import host

class DPPD(dict):
	#	----------------------------------------------------------------------
	class DB:
		#	-----------------------------------------------------------------
		#	MySQL connection parameters. Note the absence of the passwd
		#	For security reasons this should be stored in host.py.
		#	All other parameters may be changed in there as well (see below).
		#	-----------------------------------------------------------------
		db		=	None
		mysql	=	{
						'db':	'dpjudge',	'host':		'localhost',
						'user': 'dpjudge',	'passwd':	'',
						'port': 3306
					}
		#	------------------------------------------------------------------
		def __init__(self):
			import MySQLdb, host
			if DPPD.DB.db is None:
				#	----------------------------------------------------
				#	At the very minimum provide a dbPassword in host.py.
				#	----------------------------------------------------
				for (sqlVar, hostVar) in [
					('db', 'dbName'), ('host', 'dbHost'), ('user', 'dbUser'),
					('passwd', 'dbPassword'), ('port', 'dbPort')]:
					if hostVar in vars(host):
						self.mysql[sqlVar] = vars(host)[hostVar]
				DPPD.DB.db = MySQLdb.connect(**self.mysql)
			self.cursor = DPPD.DB.db.cursor(MySQLdb.cursors.DictCursor)
		#	------------------------------------------------------------------
		def __getattr__(self, attr):
			return getattr(vars(self)['cursor'], attr)
		#	------------------------------------------------------------------
	#	----------------------------------------------------------------------
	def __init__(self):
		self.db = self.DB()
	#	----------------------------------------------------------------------
	def __getitem__(self, id):
		return dict.get(self, id, {})
	#	----------------------------------------------------------------------
	def allUsers(self):
		self.db.execute('select * from User')
		for data in self.db.fetchall(): self[data['id']] = data
	#	----------------------------------------------------------------------
	def register(self, name, email, password, status = 'PENDING'):
	#	self.allUsers()
		self.db.execute('select max(id)+1 next_id from User')
		next_id = self.db.fetchall()[0]['next_id']
		self.db.execute(
			"""
			insert into User (id, name, password, status)
						values (%s, %s, %s, %s)
			""", (next_id, name.encode('latin-1'),
			password.encode('latin-1'), status))
		user, domain = email.split('@')
		domain = domain.split('.')
		# IGNORE machinename.domain.com, but KEEP domain.com.au
		domain = '.'.join(domain[-2 - (len(domain[-1]) == 2):])
		self.db.execute(
			"""
			insert into Email (userId, address, status)
						values (%s, %s, "PRIMARY")
			""", (next_id, "%s@%s" % (user, domain)))
		ipAddress = os.environ.get('REMOTE_ADDR', '')
		if ipAddress:
			self.db.execute(
				"""
				insert into IP (userId, address)
							values (%s, %s)
				""", (next_id, ipAddress))
	#	----------------------------------------------------------------------
	def update(self, id):
		self.db.execute(
			"""
			update User set password = %s, status = %s
			where id = %s
			""", (self[id]['password'], self[id]['status'], self[id]['id']))
	#	----------------------------------------------------------------------
	def lookup(self, email = '', name = '', id = None, exact = 0):
		if name: name = ' '.join(name.upper().split())
		if email: email = email.strip()
		results = []
		if id is not None: self.db.execute(
			"""
			select * from User where id = %s
			""", [id])
		elif name:
			if exact: self.db.execute(
				"""
				select * from User
				where name = %s
				""", [name.encode('latin-1')])
			else: self.db.execute(
				"""
				select * from User
				where name like %s or name like %s
				""", map(lambda x: x % name.encode('latin-1'),
				('%s%%', '%% %s')))
		elif email:
			if exact:
				self.db.execute(
					"""
					select * from User, Email
					where address = %s
					and id = userID
					""", [email.lower().split()])
			else:
				if email.count('@') == 1:
					user, domain, at = email.lower().split('@') + ['@%']
					where = 2 + (domain[-6:-2] == '.co.') # .co.uk, .co.nz, etc.
					domain = '.'.join(domain.split('.')[-where:])
				else: user, domain, at = email, '', ''
				self.db.execute(
					"""
					select * from User, Email
					where address like %s
					and id = userID
					""", ['%%%s%s%s%%' % (user, at, domain)])
		else: return
		for x in self.keys(): del self[x]
		for data in self.db.fetchall(): self[data['id']] = data
		results = self.keys()
		if len(results) == 1: return self[data['id']]
		return results or None
	#	----------------------------------------------------------------------
	def whois(self, email):
		#	------------------------------------------------
		#	Check membership status of email and pack into a
		#			DPPD: #idNum email1,email2 First_Last
		#	header that we return to the requesting judge
		#	(it will then fulfill the request).
		#	------------------------------------------------
		data, name = self.lookup(email), ''
		if data is None or data.get('id') is None: return
		status = data.get('status', 'ACTIVE')
		#	check for sponsor request
		if status[0].isdigit() or status == 'ACTIVE': status = ''
		name = data.get('name', '').replace(' ', '_')
		id = status or ('#%s' % data['id'])
		return ' '.join([id, email, name])
	#	----------------------------------------------------------------------
	def address(self, name = '', id = None, active = 2, dict = 0):
		#	-----------------------------------------
		#	Name has to be in full.
		#	Values for active:
		#	0: Inactive addresses only
		#	1: Primary e-mail address
		#	2: All active addresses, including primary
		#	3: All e-mail addresses
		#	-----------------------------------------
		if name: name = ' '.join(name.upper().split())
		results = []
		if active == 0:
			cond = ' and status = "INACTIVE"'
		elif active == 1:
			cond = ' and status = "PRIMARY"'
		elif active == 2:
			cond = ' and status <> "INACTIVE"'
		else: cond = ''
		if name:
			name = ' '.join(name.upper().split())
			self.db.execute(
				"""
				select address, Email.status from User, Email
				where name = %s and id = userId
				""" + cond, [name.encode('latin-1')])
		elif id is not None: self.db.execute(
			"""
			select address, status from Email
			where userId = %s
			""" + cond, [id])
		else: return None
		results = self.db.fetchall()
		if dict: return results
		return [data['address'] for data in results]
	#	----------------------------------------------------------------------
	def verify(self, password, email = '', name = '', id = None):
		if not password: return 'No password'
		if id is not None:
			key = 'ID: %d' % id
			nr = self.db.execute("""
				select password from User
				where id = %s
				""", [id])
		elif name:
			key = 'Name: ' + name
			nr = self.db.execute("""
				select password from User
				where name = %s
				""", [name])
		elif email:
			key = 'Email: ' + email
			nr = self.db.execute("""
				select password from User, Email
				where address = %s
				and id = userId
				""", [email])
		else: return 'Empty key'
		if not nr: return 'Not registered' + ' with ' + key
		elif nr > 1: return 'Multiple registrations'
		if password != self.db.fetchone()['password']:
			return 'No password match'
	#	----------------------------------------------------------------------
	def updateGame(self, data):
		#	-----------------------------------------------------------------
		#	DON'T PRINT THE STATUS! It may show up as an error page in the
		#	browser of an unsuspecting player if the update for some reason
		#	fails, revealing the whole game status.
		#	Any non-ascii character in the data can make this print statement
		#	fail, unless the environment variable PYTHONIOENCODING is set to
		#	something suitable, like utf-8.
		#	Anyway, DON'T PRINT IT!
		#	-----------------------------------------------------------------
		#try: print 'UPDATING', data
		#except: pass
		game = oldgame = gameType = result = 0
		newrules, newroles = set(), []
		for info in [x.split(':') for x in data.split('|')]:
			key, value = info[0], info[1:]
			if not key: pass
			elif key == 'JUDGE':
				self.db.execute("select id from Judge where id = %s",
					[value[0]])
				try: judgeId = self.db.fetchone()['id']
				except: raise UnknownJudge
			elif key == 'GAME':
				while not game:
					self.db.execute("select * from Game where judgeId = %s "
									"and name = %s", (judgeId, value[0]))
					game = self.db.fetchone()
					if game: break
					self.db.execute("insert into Game (judgeId, name) "
						"values (%s, %s)", (judgeId, value[0]))
				oldgame = dict(game)
			elif key == 'RESULT': game['endPhase'], result = value[0], value[1:]
			elif key == 'STATUS': gameType, game['status'] = value[:2]
			elif key == 'MAP': game['map'] = value[0]
			elif key == 'ZONE': game['zone'] = value[0]
			elif key == 'PHASE': game['phase'] = value[0]
			elif key == 'DEADLINE': game['deadline'] = value[0]
			elif key == 'PRIVATE': game['private'] = value[0]
			elif key == 'RULES': newrules = set(filter(None, value))
			else:
				try: userId = int(value[-1][1:])
				except: userId = None
				newroles += [{'gameId': game['id'], 'userId': userId,
					'type': (value[0], 'MASTER')[key == 'MASTER'],
					'name': key, 'password': value[-2]}]
		#	-------------------
		#	Update Rule records
		#	-------------------
		self.db.execute("select name from Rule where gameId = %s", [game['id']])
		oldrules = set([x['name'] for x in self.db.fetchall()])
		if gameType: newrules.add(gameType)
		[self.db.execute("delete from Rule where gameId = %s and name = %s",
			(game['id'], x)) for x in oldrules - newrules]
		[self.db.execute("insert into Rule (gameId, name) values (%s, %s)",
			(game['id'], x)) for x in newrules - oldrules]
		#	-------------------
		#	Update Role records
		#	-------------------
		self.db.execute("select * from Role where gameId = %s", [game['id']])
		oldroles = self.db.fetchall()
		[self.db.execute(
			"delete from Role "
			"where gameId = %s and userId = %s", (game['id'], x['userId']))
			for x in oldroles if x not in newroles]
		[self.db.execute(
			"insert into Role (gameId, userId, type, password, name) "
			"values (%s, %s, %s, %s, %s)",
			(game['id'], x['userId'], x['type'], x['password'], x['name']))
			for x in newroles if x not in oldroles]
		#	------------------
		#	Update Game record
		#	------------------
		newparams = [(x, y) for (x,y) in game.items()
			if y != oldgame.get(x)]
		if newparams: self.db.execute("update Game set %s where id = %%s" %
			', '.join(["%s = %%s" % x for (x, y) in newparams]),
			[y for (x,y) in newparams] + [game['id']])
	#	----------------------------------------------------------------------
	def deleteGame(self, gameName, gamePass, judgeId = None):
		#	------------------------------------------------------------
		#	Deletes a game from the database.
		#	Returns True if no game records were found.
		#	Note that a call to Game.updateState() can restore the game,
		#	as long as the game folder is still on the server.
		#	------------------------------------------------------------
		if not self.db.execute(
			"select id from Game where judgeId = %s and name = %s",
			(judgeId or host.dpjudgeID, gameName)): return True
		gameId = self.db.fetchone()['id']
		if host.judgePassword and host.judgePassword != gamePass:
			if not self.db.execute(
				"select password from Role where gameId = %s and "
				"name = 'MASTER'", [gameId]): raise NoGamePassword
			if gamePass != self.db.fetchone()['password']:
				raise WrongGamePassword
		self.db.execute("delete from Role where gameId = %s", [gameId])
		self.db.execute("delete from Rule where gameId = %s", [gameId])
		self.db.execute("delete from Game where id = %s", [gameId])
	#	----------------------------------------------------------------------

class RemoteDPPD():
	#	----------------------------------------------------------------------
	def __init__(self):
		self.localMain, self.dppd = False, None
		if host.dppdLocal is not None and host.dbUser:
			self.dppd = DPPD()
			self.localMain = True
		self.urls = host.dppdURL.split(',')
		if self.dppd is not None and self.urls:
			self.localMain = not host.dppdLocal
			del self.urls[host.dppdLocal]
#	----------------------------------------------------------------------
	def updateGame(self, data):
		if self.dppd is not None: self.dppd.updateGame(data)
		if not self.urls: return
		dict = urllib.urlencode({'status': data.encode('latin-1')})
		for dppdURL in urls:
			#   -----------------------------------------------------
			#	I don't know why, but we need to use the query string
			#	instead of a POST.  Something to look into.
			#   -----------------------------------------------------
			query = '?&'['?' in dppdURL]
			page = urllib.urlopen(dppdURL + query + 'page=update&' + dict)
			#   ----------------------------------------------------------
			#   Check for an error report and raise an exception if that's
			#   the case. Double check the DPPD code for any print
			#   statements, as it may reveal the whole game status info to
			#   the unsuspecting player.
			#   ----------------------------------------------------------
			lines = page.readlines()
			page.close()
			if [1 for x in lines if 'DPjudge Error' in x]:
				#	Make absolutely sure it doesn't print the game status!!
				print '\n'.join(lines) 
				raise DPPDStatusUpdateFailed
	#	----------------------------------------------------------------------
	def deleteGame(self, gameName, gamePass, judgeId = None):
		absent = None
		if self.dppd is not None:
			absent = self.dppd.deleteGame(gameName, gamePass, judgeId) or False
		if self.urls:
			dict = urllib.urlencode({
				'judge': (judgeId or host.dpjudgeID).encode('latin-1'),
				'name': gameName.encode('latin-1'),
				'password': gamePass.encode('latin-1')})
			for dppdURL in self.urls:
				query = '?&'['?' in dppdURL]
				page = urllib.urlopen(dppdURL + query + 'page=delete&' + dict)
				#   --------------------------------------------------------------------
				#   Check for an error report and raise an exception if that's the case.
				#   --------------------------------------------------------------------
				lines = page.readlines()
				page.close()
				if [1 for x in lines if 'DPjudge Error' in x]:
					if not [1 for x in lines if 'NoGameToDelete' in x]:
						raise DPPDFailedToDeleteGame
					elif absent is None: absent = True
				else: absent = False
		return absent
	#	----------------------------------------------------------------------
	def whois(self, email):
		if self.localMain: return self.dppd.whois(email)
		#	--------------------------------------------------------------
		#	Need to use query string rather than POST it.  Don't know why.
		#	--------------------------------------------------------------
		if not self.urls: return
		dppdURL = self.urls[0]
		query = '?&'['?' in dppdURL]
		page = urllib.urlopen(dppdURL + query +
			'page=whois&email=' + urllib.quote(email, '@'))
		lines = page.readlines()
		page.close()
		if not lines or lines[0][:1] != '#': return
		return unicode(lines[0], 'latin-1')
	#	----------------------------------------------------------------------

import os

import host

class DPPD(dict):
	#	----------------------------------------------------------------------
	class DB:
		#	-----------------------------------------------------------------
		#	MySQL connection parameters. Note the absence of the passwd
		#	For security reasons this should be stored in host.py.
		#	All other parameters may be changed in there as well (see below).
		#	-----------------------------------------------------------------
		mysql	=	{
						'db':	'dpjudge',	'host':		'localhost',
						'user': 'dpjudge',	'passwd':	'',
						'port': 3306
					}
		#	------------------------------------------------------------------
		def __init__(self):
			import MySQLdb, host
			#	----------------------------------------------------
			#	At the very minimum provide a dbPassword in host.py.
			#	----------------------------------------------------
			for (sqlVar, hostVar) in [
				('db', 'dbName'), ('host', 'dbHost'), ('user', 'dbUser'),
				('passwd', 'dbPassword'), ('port', 'dbPort')]:
				if hostVar in vars(host):
					self.mysql[sqlVar] = vars(host)[hostVar]
			db = MySQLdb.connect(**self.mysql)
			self.cursor = db.cursor(MySQLdb.cursors.DictCursor)
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
	def lookup(self, email = '', name = '', id = None):
		if name: name = ' '.join(name.upper().split())
		results = []
		if email:
			if email.count('@') == 1: user, domain = email.lower().split('@')
			else: user, domain = email, ''
		if id is not None: self.db.execute(
			"""
			select * from User where id = %s
			""", id)
		elif name: self.db.execute(
			"""
			select * from User
			where name like %s or name like %s
			""", map(lambda x: x % name.encode('latin-1'), ('%s%%', '%% %s')))
		else:
			howmany = email.count('@')
			at = '@' * ('@' in email)
			try: user, domain = email.split('@')
			except: user, domain = email, ''
			where = 2 + (domain[-6:-2] == '.co.') # .co.uk, .co.nz, etc.
			domain = '.'.join(domain.split('.')[-where:])
			self.db.execute(
			"""
			select * from User, Email
			where address like %s
			and id = userID
			""", '%s%s%%%s' % (user, at, domain))
		for x in self.keys(): del self[x]
		for data in self.db.fetchall(): self[data['id']] = data
		results = self.keys()
		if len(results) == 1: return self[data['id']]
		return results or None
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
					value[0])
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
		self.db.execute("select name from Rule where gameId = %s", game['id'])
		oldrules = set([x['name'] for x in self.db.fetchall()])
		if gameType: newrules.add(gameType)
		[self.db.execute("delete from Rule where gameId = %s and name = %s",
			(game['id'], x)) for x in oldrules - newrules]
		[self.db.execute("insert into Rule (gameId, name) values (%s, %s)",
			(game['id'], x)) for x in newrules - oldrules]
		#	-------------------
		#	Update Role records
		#	-------------------
		self.db.execute("select * from Role where gameId = %s", game['id'])
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
	def deleteGame(self, gameName, judgeId = None):
		#	------------------------------------------------------------
		#	Deletes a game from the database.
		#	Note that a call to Game.updateState() can restore the game,
		#	as long as the game folder is still on the server.
		#	------------------------------------------------------------
		if not self.db.execute(
			"select id from Game where judgeId = %s and name = %s",
			(judgeId or host.dpjudgeID, gameName)): raise NoGameToDelete
		gameId = self.db.fetchone()['id']
		self.db.execute("delete from Role where gameId = %s", gameId)
		self.db.execute("delete from Rule where gameId = %s", gameId)
		self.db.execute("delete from Game where id = %s", gameId)
	#	----------------------------------------------------------------------


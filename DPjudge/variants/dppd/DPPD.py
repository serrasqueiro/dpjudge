import os

class DPPD(dict):
	#	----------------------------------------------------------------------
	class DB:
		#	------------------------------------------------------------------
		#	Came from host.py but this should be in a config file, probably...
		mysql	=	{
						'host':		'sh-mysql3.dca1.superb.net',
						'user':		'shb3_158_1',
						'passwd':	'IamK000l',
						'db':		'shb3_158_1'
					}
		mysql	=	{
						'db':	'dpjudge',	'host':		'localhost',
						'user': 'dpjudge',	'passwd':	'Fa2phiep'
					}
		#	------------------------------------------------------------------
		def __init__(self):
			import MySQLdb
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
						values (%d, "%s", "%s", "%s")
			""" % (next_id, name.encode('latin-1'), password.encode('latin-1'), status))
		user, domain = email.split('@')
		domain = domain.split('.')
		# IGNORE machinename.domain.com, but KEEP domain.com.au
		domain = '.'.join(domain[-2 - (len(domain[-1]) == 2):])
		self.db.execute(
			"""
			insert into Email (userId, address, status)
						values (%d, "%s@%s", "PRIMARY")
			""" % (next_id, user, domain))
		self.db.execute(
			"""
			insert into IP (userId, address)
						values (%d, "%s")
			""" % (next_id, os.environ['REMOTE_ADDR']))
	#	----------------------------------------------------------------------
	def update(self, id):
		self.db.execute(
			"""
			update User set password = "%(password)s", status = "%(status)s"
			where id = %(id)d
			""" % self[id])
	#	----------------------------------------------------------------------
	def lookup(self, email = '', name = '', id = None):
		if name: name = ' '.join(name.upper().split())
		results = []
		if email:
			if email.count('@') == 1: user, domain = email.lower().split('@')
			else: user, domain = email, ''
		if id is not None: self.db.execute(
			"""
			select * from User where id = %d
			""" % id)
		elif name: self.db.execute(
			"""
			select * from User
			where name like "%s%%" or name like "%% %s"
			""" % (name.encode('latin-1'), name.encode('latin-1')))
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
			where address like '%s%s%%%s'
			and id = userID
			""" % (user, at, domain))
		for x in self.keys(): del self[x]
		for data in self.db.fetchall(): self[data['id']] = data
		results = self.keys()
		if len(results) == 1: return self[data['id']]
		return results or None
	#	----------------------------------------------------------------------
	def updateGame(self, data):
		print 'UPDATING', data
		game = oldgame = gameType = result = 0
		newrules, newroles = set(), []
		for info in [x.split(':') for x in data.split('|')]:
			key, value = info[0], info[1:]
			if key == 'JUDGE':
				self.db.execute("select id from Judge where id = '%s'" %
					value[0])
				try: judgeId = self.db.fetchone()['id']
				except: raise UnknownJudge
			elif key == 'GAME':
				while not game:
					self.db.execute("select * from Game where judgeId = '%s' "
									"and name = '%s'" % (judgeId, value[0]))
					game = self.db.fetchone()
					if game: break
					self.db.execute("insert into Game (judgeId, name) "
						"values ('%s', '%s')" % (judgeId, value[0]))
				oldgame = dict(game)
			elif key == 'RESULT': game['endPhase'], result = value[0], value[1:]
			elif key == 'STATUS': gameType, game['status'] = value[:2]
			elif key == 'MAP': game['map'] = value[0]
			elif key == 'ZONE': game['zone'] = value[0]
			elif key == 'PHASE': game['phase'] = value[0]
			elif key == 'DEADLINE': game['deadline'] = value[0]
			elif key == 'PRIVATE': game['private'] = value[0]
			elif key == 'RULES': newrules = set(filter(None, value))
			else: newroles += [{'gameId': game['id'],
								'userId': int(value[-1][1:]),
								'type': (value[0], 'MASTER')[key == 'MASTER'],
								'name': key, 'password': value[-2]}]
		#	-------------------
		#	Update Rule records
		#	-------------------
		self.db.execute("select name from Rule where gameId = %d" % game['id'])
		oldrules = set([x['name'] for x in self.db.fetchall()])
		if gameType: newrules.add(gameType)
		[self.db.execute("delete from Rule where gameId = %d and name = '%s'" %
			(game['id'], x)) for x in oldrules - newrules]
		[self.db.execute("insert into Rule (gameId, name) values (%d, '%s')" %
			(game['id'], x)) for x in newrules - oldrules]
		#	-------------------
		#	Update Role records
		#	-------------------
		self.db.execute("select * from Role where gameId = %d" % game['id'])
		oldroles = self.db.fetchall()
		[self.db.execute(
			"delete from Role "
			"where gameId = %(gameId)d and userId = %(userId)d" % x)
			for x in oldroles if x not in newroles]
		[self.db.execute(
			"insert into Role (gameId, userId, type, name, password) "
			"values (%(gameId)d, %(userId)s, '%(type)s', "
					"'%(name)s', '%(password)s')" % x)
			for x in newroles if x not in oldroles]
		#	------------------
		#	Update Game record
		#	------------------
		clause = ["%s = '%s'" % (x,y) for (x,y) in game.items()
			if y != oldgame.get(x)]
		if clause: self.db.execute("update Game set %s where id = %d" %
			(', '.join(clause), game['id']))
	#	----------------------------------------------------------------------


import os, time, random, socket

from Game import host, Status, Power, Game, Mail
from Map import Map

class Page:
	#	----------------------------------------------------------------------
	def __init__(self, form = {}):
		#	---------------------------------------------------------------
		#	The pwdFlag is 0 or None if bad password, 1 if good (incl. GM),
		#	and 2 if good enough to provide read-only access (omniscient).
		#	---------------------------------------------------------------
		self.pwdFlag = None
		#	---------------------------------------------------
		#	Parameters that may appear in the url (as GET).
		#	If they also appear in the form (as POST),
		#	they end up as a list of 2 nearly identical values,
		#	which is undesirable.
		#	---------------------------------------------------
		self.variant = self.game = self.power = self.password = self.page = ''
		for key in form.keys():
			if type(form) is dict or type(form[key]) != list:
				vars(self)[key] = unicode(form.get(key), 'latin-1')
			elif key in vars(self) and type(vars(self)[key]) == str:
				vars(self)[key] = unicode(form[key][0].value, 'latin-1')
			else: vars(self)[key] = [unicode(x.value, 'latin-1')
				for x in form[key]]
		self.wireless = 'UPG1' in os.environ.get('HTTP_USER_AGENT', '')
		#   -----------------------------------------------------------------
		#	Add banner message if one is provided.
		#	NOTE: if testing a new DPPD, though, you don't want this text to
		#	show, at least for the "page=whois" poor-man's Web Service
		#	invocations because this header will be included in that response,
		#	and bin/mail.py will be confused about a JOIN (etc.)'ing player's
		#	DPPD status.
		#   -----------------------------------------------------------------
		if not self.page or self.page[0].lower() != self.page[0]:
			print host.bannerHtml or ''
		if self.game:
			game = self.game.lower().replace('%23', '#')
			self.game = Status().load(game)
			if self.game and not self.game.name: self.game = None
			if self.game: self.variant = self.game.status[0]
			else:
				self.write('<script>'
					'alert("No such game (%s) can be found on this DPjudge.");'
					"window.location.replace('%s%s');</script>" % (game,
					host.dpjudgeURL, '/index.cgi' * host.needIndexWWW))
				raise SystemExit
		elif not self.variant:
			dir = os.path.dirname(os.environ.get('SCRIPT_NAME',''))
			dir = dir.split('/')[-1]
			if dir and os.path.isdir(host.packageDir + '/' + dir):
				self.variant = dir
		if self.variant and not self.game:
			module = __import__('DPjudge.variants.' + self.variant,
								globals(), locals(), `self.variant`)
			globals().update(vars(module))
		if not self.page:
			if not self.game: self.page = 'Index'
			elif self.power and self.password: self.page = 'Status'
			else: self.page = 'Login'
		if self.power: self.power = self.power.upper().replace('%23', '#')
		if self.include(): raise SystemExit
		self.write("<script>window.location.replace('%s');</script>" %
			host.dpjudgeURL)
	#	----------------------------------------------------------------------
	def write(self, text = ''):
		try: print text.encode('latin-1')
		except UnicodeDecodeError: print text
	#	----------------------------------------------------------------------
	def silent(self):
		self.write = lambda x,y=0: 0
	#	----------------------------------------------------------------------
	def include(self, fileName = None, lims = ('<:', ':>'), data = None):
		global page
		if not (fileName or data): fileName = self.page
		if self.variant: variant = '/variants/' + self.variant
		else: variant = ''
		if fileName:
			# this next line causes problems for the DPPD urllib playerchecker
			# print '<!-- including', fileName, '-->'
			for subdir in	(host.hostDir,
							host.packageDir + variant, host.packageDir):
				try: file = open(subdir + '/pages/' + fileName)
				except: continue
				data = file.read()
				file.close()
				break
			else: return
		page, inCode = self, 0
		while data:
			where = data.find(lims[inCode])
			if where < 0: stuff, data = data, ''
			else: stuff, data = data[:where], data[where + len(lims[inCode]):]
			stuff = (stuff.replace('<URL>',		host.dpjudgeURL)
						  .replace('<MAP>',		host.gameMapURL)
						  .replace('<PAGE>',	host.dpjudgeURL + '?page=')
						  .replace('<WEB>',		host.dpjudgeDir)
						  .replace('<ID>',		host.dpjudgeID)
						  .replace('<MAIL>',	host.dpjudge)
						  .replace('<KEEPER>',	host.judgekeeper)
						  .replace('<PKG>',		host.packageDir)
						  .replace('<DPPD>',	host.dppdURL or '')
						  .replace('<POUCH>',	'http://www.diplom.org'))
			inCode = not inCode
			if inCode: self.write(stuff)
			elif stuff[:1] != '=':
				try:
					exec stuff in globals()
				except:
					print('<!-- Exception while executing:\n' + stuff.replace('<','&lt;') + '-->')
					raise
			else: self.write(eval(stuff[1:]))
		#	--------------
		#	Template shown
		#	--------------
		return 1
	#	----------------------------------------------------------------------

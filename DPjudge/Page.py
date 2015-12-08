import os, random, socket, urllib

from Game import host, Status, Power, Game, Mail, View, Time, TimeZone
from Map import Map

class Page:
	#	----------------------------------------------------------------------
	def __init__(self, form = {}):
		self.pwdFlag = None
		#	---------------------------------------------------
		#	Parameters that may appear in the url (as GET).
		#	If they also appear in the form (as POST),
		#	they end up as a list of 2 nearly identical values,
		#	which is undesirable.
		#	---------------------------------------------------
		self.variant = self.game = self.power = self.password = self.user = self.page = ''
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
		if host.bannerHtml and (
			not self.page or self.page[0].lower() != self.page[0]):
			self.write(self.adaptToHTML(host.bannerHtml))
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
		if self.power:
			self.power = self.power.upper().replace('%23', '#')
			if self.game:
				try: self.power = [x for x in self.game.powers if x.name in
					(self.power, '_' + self.power)][0]
				except: 
					if self.power in ('MASTER', 'JUDGEKEEPER'):
						self.power = Power(self.game, self.power)
		if self.user:
			try: self.user = int(self.user)
			except: self.user = -1
		#	---------------------------------------------------------------
		#	Values for pwdFlag:
		#	 0: Bad or no password
		#	 1: Valid DPPD user, but no power specified or not in control
		#	 2: Good enough to provide read-only access (omniscient)
		#	 3: Valid password for power (player is or controls power)
		#	 4: Game password (Master)
		#	 5: Host password (Judgekeeper)
		#	---------------------------------------------------------------
		if not self.password: self.pwdFlag = 0
		elif self.password == host.judgePassword: self.pwdFlag = 5
		elif self.game:
			if self.password == self.game.password: self.pwdFlag = 4
			elif self.power:
				if self.password == self.power.password: self.pwdFlag = 3
		if self.include(): raise SystemExit
		self.write("<script>window.location.replace('%s');</script>" %
			host.dpjudgeURL)
	#	----------------------------------------------------------------------
	def setdefault(self, var, val = ''):
		return vars(self).setdefault(var, val)
	#	----------------------------------------------------------------------
	def get(self, var, val = ''):
		return urllib.unquote(vars(self).get(var, val))
	#	----------------------------------------------------------------------
	def getint(self, var, val = None):
		if not var in vars(self): return None
		try: return vars(self).get(var)
		except: return val
	#	----------------------------------------------------------------------
	def has(self, var):
		return var in vars(self)
	#	----------------------------------------------------------------------
	def write(self, text = ''):
		if not text:
			print
			return
		#	------------------------------------------------------------
		#	Strip spaces in front for texts surrounded by triple quotes.
		#	------------------------------------------------------------
		lines = text.split('\n')
		if not lines[-1].strip() and not lines[0].strip():
			text = '\n'.join([x.strip() for x in lines[1:-1]])
		try: print text.encode('latin-1')
		except UnicodeDecodeError: print text
	#	----------------------------------------------------------------------
	def silent(self):
		self.write = lambda x,y=0: 0
	#	----------------------------------------------------------------------
	def apprise(self, option, value):
		try: value = value.name
		except: pass
		self.write('<input type=hidden name="%s" value="%s">' % (option, value))
	#	----------------------------------------------------------------------
	def comprise(self, options):
		for option in options:
			self.write('<input type=hidden name="%s">' % option)
	#	----------------------------------------------------------------------
	def surprise(self, option, fallBack):
		try: self.apprise(option, vars(self)[option])
		except: self.apprise(option, fallBack)
	#	----------------------------------------------------------------------
	def reprise(self, options):
		for option in options:
			try: self.apprise(option, vars(self)[option])
			except: pass
	#	----------------------------------------------------------------------
	def convertPlainTextToHTML(self, text):
		return text.replace('-', '&#8722;').replace(
			'<', '&#60;').replace('>', '&#62;')
	#	----------------------------------------------------------------------
	def isolateHTMLTag(self, text):
		tag = ''
		while 1:
			slashes = text.split('>', 1)
			if len(slashes) == 1: return [tag + text]
			cuts = text.split('<', 1)
			if len(cuts) == 1 or len(cuts[0]) > len(slashes[0]):
				return [tag + slashes[0], slashes[1]]
			slashes = self.isolateHTMLTag(cuts[1])
			if len(slashes) == 1: return [tag + text]
			tag += cuts[0] + '<' + slashes[0] + '>'
			text = slashes[1]
	#	----------------------------------------------------------------------
	def adaptToHTML(self, text):
		html = ''
		while 1:
			cuts = text.split('<', 1)
			if len(cuts) == 1: break
			slashes = self.isolateHTMLTag(cuts[1])
			html += self.convertPlainTextToHTML(cuts[0])
			if len(slashes) == 1:
				html += '&#60;'
				text = cuts[1]
			else:
				html += '<' + slashes[0] + '>'
				text = slashes[1]
		return html + self.convertPlainTextToHTML(text)
	#	----------------------------------------------------------------------
	def addURLParam(self, url, param):
		if not url: return ''
		return url + ('?' in url and '&' or '?') + param
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
		pageURL = self.addURLParam(host.dpjudgeURL, 'page=')
		if not host.dppdURL: dppdURL = ''
		else:
			dppdURL = host.dppdURL.split(',')[0]
			if dppdURL not in (host.dpjudgeURL + host.dppdSubURL,
				os.path.join(host.dpjudgeURL, host.dppdSubURL)):
				dppdURL = self.addURLParam(dppdURL, 'dpjudge=' + host.dpjudgeID)
		page, inCode = self, 0
		while data:
			where = data.find(lims[inCode])
			if where < 0: stuff, data = data, ''
			else: stuff, data = data[:where], data[where + len(lims[inCode]):]
			stuff = (stuff
				.replace('<URL>',	host.dpjudgeURL)
				.replace('<MAP>',	host.gameMapURL)
				.replace('<PAGE>',	pageURL)
				.replace('<WEB>',	host.dpjudgeDir)
				.replace('<ID>',	host.dpjudgeID)
				.replace('<MAIL>',	host.dpjudge)
				.replace('<KEEPER>',	host.judgekeeper)
				.replace('<PKG>',	host.packageDir)
				.replace('<DPPD>',	dppdURL)
				.replace('<POUCH>',	'http://www.diplom.org'))
			inCode = not inCode
			if inCode:
				stuff = stuff.strip()
				if stuff: self.write(stuff)
			elif stuff[:1] != '=':
				try:
					exec stuff in globals()
				except:
					print('<!-- Exception while executing:\n' +
						stuff.replace('<','&lt;') + '-->')
					raise
			else: self.write(eval(stuff[1:]))
		#	--------------
		#	Template shown
		#	--------------
		return 1
	#	----------------------------------------------------------------------

from DPPD import DPPD

class Mail:
	#	----------------------------------------------------------------------
	def __init__(self):
		mime = self.email = self.boundary = self.ip = None
		self.response, self.dppd, lineNo = [], [], 0
		self.message = [unicode(x, 'latin-1') for x in sys.stdin.readlines()]
		msg, inBody = [], 0
		self.message = [x for x in self.message if x.strip()[:2] != '//']
		#	----------------------------------------
		#	Alternate line ending character (mostly
		#	for pager/cell-phone e-mailers who don't
		#	know how to send newline characters)
		#	----------------------------------------
		for line in self.message:
			if line.strip()[:2] != '\\\\': msg += [line]
			else:
				eol = line[2:].strip()[:1] or '\n'
				if eol.isalnum(): eol = '\n'
				msg.extend([x + '\n' for x in line.split(eol)[1:]])
		self.message = msg[:]
		for line in msg:
			word = line.split()
			lineNo += 1
			#	-----------------------
			#	Check for an empty line
			#	-----------------------
			if not word:
				#	--------------------------------------------------
				#	Truncate everything up to and including this line,
				#	and ensure that we are now in the message body.
				#	--------------------------------------------------
				del self.message[:lineNo]
				lineNo = 0
				inBody = not self.boundary or mime in ('text/plain', 'text')
				continue
			if (self.boundary
			and line[(line[:2] == '--') * 2:].startswith(self.boundary)):
				inBody = 0
			upword = word[0].upper()
			#	---------------------
			#	Detect message origin
			#	---------------------
			if not inBody:
				if upword == 'CONTENT-TYPE:':
					mime = word[1].split(';')[0].lower()
					arg = line.upper().find('BOUNDARY="')
					if arg > -1: self.boundary = line[arg:].split('"')[1]
				elif upword[:10] == 'BOUNDARY="':
					self.boundary = line.split('"')[1]
				elif upword in ('FROM:', 'REPLY-TO:'):
					for self.email in [x for x in word[1:] if '@' in x]:
						#	---------------------------------
						#	The form could be '<abc@xyz.com>'
						#	or even '<abc@xyz.com>,' (comma)
						#	---------------------------------
						if self.email[0] == '<':
							self.email = self.email[1:].split('>')[0]
						self.email = self.email.lower()
						if self.email[0] == self.email[-1] == '"':
							self.email = self.email[1:-1]
						break
					else: self.email = None
				elif (upword == 'RECEIVED:' and len(word) > 2
				and word[1] == 'from' and '@' not in word[2]):
					ip = word[2].replace('[', '').replace(']', '')
					if '.' not in ip and len(word) > 3:
						ip = (word[3].replace('[', '').replace(']', '')
									 .replace('(', '').replace(')', ''))
					if '.' not in ip: ip = 'localhost'
					if max(map(ip.find, (
						'localhost', '127.0.0.1',
						'.proxy.aol.com', '.mx.aol.com',
						'fastmail.fm'))) == -1: self.ip = ip
					else: self.ip = self.email
				elif upword in ('X-ORIGINATING-IP:',
								'X-ORIGINATING-SERVER:'): self.ip = word[1]
				elif upword == 'DPPD:': self.dppd = word[1:]
			#	----------------------
			#	See if we are the DPPD
			#	----------------------
			elif len(self.dppd) == 1: self.dppdCheck()
		#	----------------------------------
		#	If the message was just LIST, etc.
		#	commands, we've processed it all.
		#	----------------------------------
		if not self.message: return
	#	----------------------------------------------------------------------
	def dppdCheck(self):
		#	-------------------------------------------------
		#	We have received a DPPD: header line in this mail
		#	-------------------------------------------------
		if len(self.dppd) != 1: raise BadDPPDheader
		#	----------------
		#	We are the DPPD.
		#	----------------
		dppd, data = DPPD(), self.dppd[0]
		if data.startswith('JUDGE:'):
			#	The idea here is that we've received a game status
			#	which is a dppdString value for a game.  We (as the
			#	DPPD) will then update the DPPD database with the
			#	data that was sent (and, I guess, just not respond
			#	to the mail).
			dppd.updateGame(data)
			os._exit(os.EX_OK)
		#	-------------------------------------------------------
		#	self.dppd[0] is an e-mail address that a DPjudge wants
		#	us to check (and the message body is the message sent
		#	to that judge by that e-mail address.  Check membership
		#	status of self.dppd[0] and pack into a
		#			DPPD: #idNum email1,email2 First_Last
		#	header that we return to the requesting judge with that
		#	same message body (it will then fulfill the request).
		#	-------------------------------------------------------
		id, name = dppd.lookup(data), ''
		if id is None: id = 'NO-ID'
		else:
			status = dppd[id].get('status', 'ACTIVE')
			#	check for sponsor request
			if status[0].isdigit() or status == 'ACTIVE': status = ''
			name = dppd[id].get('name', name).replace(' ', '_')
			id = status or '#%d' % id
		response = ' '.join((id, data, name))
		msg = Mail(self.email, 'reply ' + response, mailAs = host.dppd,
			header = 'DPPD: ' + response)
		msg.write(''.join(self.message))
		msg.close()
		os._exit(os.EX_OK)
	#	----------------------------------------------------------------------

#	=========================================================================
#	If this is the main module when called, update DPPD data from stdin email
#	-------------------------------------------------------------------------
if __name__ == '__main__':
	Mail()


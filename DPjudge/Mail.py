from codecs import open

import host

class Mail:
	#	----------------------------------------------------------------------
	def __init__(self, sendTo, subject, copy = '', mailAs = '', header = ''):
		import smtplib, socket, os
		self.copy = self.copyFile = copy
		if copy:
			try: self.copy = open(copy, 'a')
			except:
				self.copy, notice = None, Mail(host.judgekeeper,
					'DPjudge Mail.copy failure!')
				notice.write('Failed to open file %s\n' % copy)
				notice.close()
		if self.copy:
			try: os.chmod(copy, 0666)
			except: pass
		mailAs = mailAs or host.dpjudge
		if host.smtpService is not None:
			try: self.mail = smtplib.SMTP()
			except:
				socket.gethostname = lambda: 'localhost'
				self.mail = smtplib.SMTP()
			self.msg, self.mailAs, self.mailTo = '', mailAs, sendTo.split(',')
			self.mail.connect(host.smtpService)
		else: self.mail = os.popen(host.packageDir + '/tools/sendmail -t', 'w')
		self.write('To: %s\nFrom: %s\nReply-To: %s\nDate: %s\n'
			'Subject: %s\n%s\n\n' % (sendTo, mailAs, mailAs,
			self.logTimeFormat(), subject, header), 0)
	#	----------------------------------------------------------------------
	def write(self, text, addToCopy = 1):
		if host.smtpService is not None: self.msg += text
		elif host.sendmailDir: self.mail.write(text.encode('latin-1'))
		if addToCopy and self.copy: self.copy.write(text.encode('latin-1'))
	#	----------------------------------------------------------------------
	def close(self):
		if host.smtpService is not None:
			logtext = 0
			try: self.mail.sendmail(self.mailAs, self.mailTo,
				self.msg.encode('latin-1'))
			except SMTPServerDisconnected:
				logtext  = '{ERROR: Server Disconnected|\n'
			except SMTPResponseException: 
				logtext  = '{ERROR: Response Error|\n'
				logtext += SMTPResponseException.smtp_error
			except SMTPSenderRefused: 
				logtext  = '{ERROR: Sender Address Refused|\n'
				logtext += SMTPSenderRefused.sender
			except SMTPRecipientsRefused: 
				logtext  = '{ERROR: All Recipients Refused|\n'
				for key, recip in SMTPRecipientsRefused.recipients.items():
					logtext += `recip` + ';'
			except SMTPDataError: 
				logtext  = '{ERROR: Data Error|\n'
			except SMTPConnectError: 
				logtext  = '{ERROR: Connection Error|\n'
			except SMTPHeloError: 
				logtext  = '{ERROR: Helo Refused|\n'
			except:
				logtext  = '{ERROR: Unknown|\n'
			if logtext:
				try:
					logfile = open(host.hostDir + '/log/smtperror.log', 'a')
					logtext += '|\n' + self.msg + '|\n'
					logtext += self.logTimeFormat() + '}'
					logfile.write(logtext.encode('latin-1'))
					logfile.close()
				except: pass
			self.mail.quit()
		elif host.sendmailDir: self.mail.close()
		if self.copy:
			self.copy.close()
			try: os.chmod(self.copyFile, 0666)
			except: pass
	#	----------------------------------------------------------------------
	def logTimeFormat(self):
		import time
		if hasattr(host, 'timeZone') and host.timeZone:
			return time.strftime('%a, %d %b %Y %H:%M:%S ') + host.timeZone
		else:
			return time.strftime('%a, %d %b %Y %H:%M:%S %Z')
	#	----------------------------------------------------------------------

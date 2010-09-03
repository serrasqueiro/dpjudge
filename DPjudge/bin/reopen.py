from DPjudge import Status, host

class Reopen(Status):
	#	----------------------------------------------------------------------
	"""
	This class is invoked by the Judgekeeper to inform The Diplomatic Pouch
	openings list that this DPjudge is up and available.  The bin/reopen
	tool is run manually when the judge is back in service at some point
	after the openings list informed the judgekeeper that it had recorded
	the judge as being down.
	"""
	#	----------------------------------------------------------------------
	def __init__(self):
		Status.__init__(self)
		self.list('openings@diplom.org')
		print '-' * 52
		print 'The Diplomatic Pouch Openings List has been e-mailed'
		print 'announcing the availability of the %s DPjudge.' % host.dpjudgeID
		print '-' * 52
	#	----------------------------------------------------------------------

#	----------------------------------
#	Announce Re-Opening of the DPjudge
#	----------------------------------
Reopen()

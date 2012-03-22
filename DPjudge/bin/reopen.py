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
		if host.openingsList:
			Status.__init__(self)
			self.list(host.openingsList)
		print '-' * 56
		print(('The Diplomatic Pouch Openings List has been e-mailed\n'
			'announcing the availability of the %s DPjudge.',
			'No openings list address given. Make sure the %s judge\n'
			'is registered with the Diplomatic Pouch Openings List.')
			[not host.openingsList] % host.dpjudgeID)
		print '-' * 56
	#	----------------------------------------------------------------------

#	----------------------------------
#	Announce Re-Opening of the DPjudge
#	----------------------------------
Reopen()

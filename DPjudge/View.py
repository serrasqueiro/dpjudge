import os

import host

class View:
	#	----------------------------------------------------------------------
	def __init__(self, game):
		self.game = game
	#	----------------------------------------------------------------------
	def makeMaps(self):
		#	--------------------------------------------------------
		#	If the map is marked as text only, make no graphical map
		#	--------------------------------------------------------
		if self.game.map.textOnly: return
		#	----------------------------------------------------------
		#	Get a list of all the different powers for whom we need to
		#	make maps.  In a BLIND game, the powers see separate maps.
		#	----------------------------------------------------------
		if 'BLIND' in self.game.rules and self.game.phase != 'COMPLETED':
			maps = [(x, '.' + y + `hash(z)`)
				for x, y, z in [('MASTER', 'M', self.game.password)] +
					[(x.name, x.abbrev or 'O', (x.password or self.game.password) + x.name)
					for x in self.game.powers if (not x.type or x.omniscient)]]
		else: maps = [(None, '')]
		for viewer, pwd in maps:
			#	-------------------------------------------------
			#	Make a complete "season-by-season" PostScript map
			#	(putting the file into the maps subdirectory)
			#	-------------------------------------------------
			self.makePostScriptMap(viewer, pwd)
			#	--------------------------------------
			#	Make .gif files from the last pages of
			#	the PostScript map that was just made.
			#	--------------------------------------
			self.makeGifMaps(pwd)
			#	-------------
			#	Make .pdf map
			#	-------------
			self.makePdfMaps(pwd)
	#	----------------------------------------------------------------------
	def makePostScriptMap(self, viewer = 0, password = ''):
		import DPmap
		fileName = host.gameMapDir + '/' + self.game.name + password
		for ext in ['.ps', '.pdf', '.gif', '_.gif', '_.pdf']:
			try: os.unlink(fileName + ext)
			except: pass
		map = DPmap.PostScriptMap(host.packageDir + '/' +
								  self.game.map.rootMapDir + '/' + self.game.map.rootMap, self.game.file('results'),
								  host.gameMapDir + '/' + self.game.name + password + '.ps', viewer)
		os.chmod(fileName + '.ps', 0666)
		self.game.error += map.error
	#	----------------------------------------------------------------------
	def makeGifMaps(self, password = '', pages = None):
		import DPimage
		#	------------------------------------------------------------------
		#	Make .gif files from the last page(s) of the .ps map for the game.
		#	------------------------------------------------------------------
		DPimage.ImageView(self.game.map, None, host.toolsDir, host.gameMapDir, host.imageResolution).extract(
			self.game.name + password, pages or [-1, 0])
	#	----------------------------------------------------------------------
	def makePdfMaps(self, password = ''):
		import DPghost
		#	---------------------------------------------------------
		#	Make a .pdf file with the final page(s) from the .ps file
		#	---------------------------------------------------------
		psFileName, params = host.gameMapDir + '/' + self.game.name + password + '.ps', []
		if self.game.map.papersize: params += [('sPAPERSIZE', self.game.map.papersize)]
		if host.usePDFMark:
			#	----------------------------------------------------------
			#	All maps already have their bbox altered to fit on a page.
			#	----------------------------------------------------------
			params += ['dDPghostPageSizeBBox', 'dDPghostUndoBBox']
		#	----------------------------------------
		#	Add more parameters before this comment.
		#	----------------------------------------
		#	-----------------------------------------------------------------
		#	(We could run psselect -_2-_1 xx.ps 2>/dev/null > tmp.ps and then
		#	run the ps2pdf on the tmp.ps file, but we now pdf the full game.)
		#	-----------------------------------------------------------------
		ghost = DPghost.GhostScript(pdfFileMode = 0666, ps2pdfDir = host.toolsDir)
		if host.usePDFMark:
			ghost.markForms(psFileName, pdfParams=params)
		else:
			ghost.ps2pdf(psFileName, pdfParams=params)

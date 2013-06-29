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
		if 'BLIND' in self.game.rules:
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
		#	--------------------------------------------
		#	Make .gif files from the last page(s) of the
		#	.ps map for the game.  To do so, extract the
		#	target page using the psselect utility (from
		#	Andrew Duggan's "psutils" package), and mess
		#	with it until it is all converted to a .gif.
		#	--------------------------------------------
		root = host.gameMapDir + '/' + self.game.name + password
		file = root + '.'
		upscale = host.imageResolution / 72.
		origin = size = None
		if self.game.map.bbox:
			origin = [self.game.map.bbox[0] * upscale, self.game.map.bbox[1] * upscale]
			size = [(self.game.map.bbox[2] - self.game.map.bbox[0]) * upscale,
					(self.game.map.bbox[3] - self.game.map.bbox[1]) * upscale]
		psf, ppmf, tmpf1, tmpf2 = file + 'ps', file + 'ppm', file + 'dat', file + 'dta'
		if os.name == 'nt':
			err  = '2>nul'
			inp  = (psf, tmpf1,
					ppmf, '< %s' % tmpf1, '< %s' % tmpf2, '< %s' % tmpf1)
			outp = ('> %s;' % tmpf1, ppmf,
					'> %s;' % tmpf1, '> %s;' % tmpf2, '> %s;' % tmpf1)
		else:
			err  = '2>/dev/null'
			inp  = (psf, '-', ppmf, '', '', '')
			outp = ('|', ppmf, '|', '|', '|')
		if err: inp = tuple(['%s %s' % (x, err) for x in inp])
		toolsDir = host.toolsDir
		chop = ('%s/psselect -p%%s %s %s'
				'%s/gs -q -r%d -dSAFER -sDEVICE=ppmraw -o %s %s;' %
				(toolsDir, inp[0], outp[0],
				 toolsDir, host.imageResolution, outp[1], inp[1]))
		#	----------------------------------------------------------
		#	All landscape maps must be rotated 270 degrees by pnmflip.
		#	----------------------------------------------------------
		make, idx = '', 2
		if self.game.map.rotation:
			make += '%s/pnmflip -r%d %s %s' % (toolsDir,
											   self.game.map.rotation * 90, inp[idx], outp[idx])
			idx += 1
		if origin:
			make += '%s/pnmcut %d %d %d %d %s %s' % (toolsDir,
													 origin[0], origin[1], size[0], size[1], inp[idx], outp[idx])
			idx += 1
		make += '%s/pnmcrop -white %s %s' % (toolsDir, inp[idx], outp[idx])
		idx += 1
		make +=	'%s/ppmtogif -interlace %s > %%s' % (toolsDir, inp[idx])
		if not pages: pages = [0] + [-1] * (self.game.phase != self.game.map.phase)
		for page in pages:
			gif = root + '_' * (page < 0) + ('%d' % abs(page)) * (
			not 1 > page > -2) + '.gif'
			try: os.unlink(gif)
			except: pass
			map(os.system, (chop % ('_' * (page < 1) + '%d' % (
			page > 0 and page or 1 - page)) + make % gif).split(';'))
			#	------------------------------------------------------------
			#	If the gif make fails, the file will be 0 bytes.  Remove it.
			#	------------------------------------------------------------
			if os.path.getsize(gif): os.chmod(gif, 0666)
			else:
				try: os.unlink(gif)
				except: pass
		try: map(os.unlink, (ppmf, tmpf1, tmpf2))
		except: pass
	#	----------------------------------------------------------------------
	def makePdfMaps(self, password = ''):
		import DPghost
		#	---------------------------------------------------------
		#	Make a .pdf file with the final page(s) from the .ps file
		#	---------------------------------------------------------
		psFileName, params = host.gameMapDir + '/' + self.game.name + password + '.ps', []
		if self.game.map.papersize: params += [('sPAPERSIZE', self.game.map.papersize)]
		#	----------------------------------------
		#	Add more parameters before this comment.
		#	----------------------------------------
		#	-----------------------------------------------------------------
		#	(We could run psselect -_2-_1 xx.ps 2>/dev/null > tmp.ps and then
		#	run the ps2pdf on the tmp.ps file, but we now pdf the full game.)
		#	-----------------------------------------------------------------
		DPghost.GhostScript(pdfFileMode = 0666, ps2pdfDir = host.toolsDir).ps2pdf(psFileName, pdfParams=params)


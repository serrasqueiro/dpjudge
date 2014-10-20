#!/usr/bin/env python -SO

import sys
import os
from codecs import open

class ImageView:
	def __init__(self, mapName, mapDirs, toolsDir, gameDir, imageResolution):
		self.mapDirs = mapDirs
		self.toolsDir = toolsDir
		self.gameDir = gameDir
		self.imageResolution = imageResolution
		#	----------------------------------------------
		#   In Python 3.x replace 'basestring' with 'str'.
		#	----------------------------------------------
		if isinstance(mapName, basestring):
			self.mapName = mapName
			self.loadInfo()
		else:
			self.mapName = mapName.name
			self.bbox = mapName.bbox
			self.papersize = mapName.papersize
			self.rotation = mapName.rotation
	#	----------------------------------------------------------------------
	def loadInfo(self):
		self.error = []
		self.bbox, self.papersize, self.rotation = None, '', 3
		for mapDir in self.mapDirs:
			#	-----------------
			#	Open ps info file
			#	-----------------
			try: file = open(os.path.join(mapDir, 'psinfo'), encoding = 'latin-1')
			except:
				self.error.append('PSINFO FILE NOT FOUND IN ' + mapDir)
				continue
			#	------------------------------------
			#	Assign default values
			#	Order: bbox papersize rotation blind
			#	------------------------------------
			defVals = [''] * 3
			curVals = defVals[:]
			#	-----------------------------------------------------------
			#	Parse the file, searching for the map name
			#	and determining its parameter values
			#	Missing values are replaced with the default values.
			#   Special values:
			#		'_': replace with the default value
			#		'-': copy the corresponding value for the preceding map
			#		'=': copy all remaining values from the preceding map
			#	-----------------------------------------------------------
			for line in file:
				word = line.split()
				if not word or word[0][0] == '#': continue
				curName = word.pop(0)
				for idx in range(len(defVals)):
					if len(word) <= idx or word[idx] == '_':
						curVals[idx] = defVals[idx]
					elif word[idx] == '-': pass
					elif word[idx] == '=': break
					else: curVals[idx] = word[idx]
				if curName == self.mapName: break
			else:
				continue
			break
		else:
			return self.error.append('MAP NOT DEFINED IN PSINFO FILE: ' + self.mapName)
		#	------------------------------------------------------
		#	Determine bbox and pixel size of graphic map at 72 dpi
		#	after rotation (for .gif file creation and display)
		#	------------------------------------------------------
		if curVals[0] != '':
			try:
				bbox = [eval(x) for x in curVals[0].split(',')]
				if len(bbox) == 4:
					self.bbox = bbox
					self.size = [bbox[2] - bbox[0], bbox[3] - bbox[1]]
				else: raise
			except: self.error.append('BBOX NOT CORRECT IN PSINFO FOR MAP: ' +
				self.mapName)
		#	-------------------
		#	Determine papersize
		#	-------------------
		if curVals[1] != '': self.papersize = curVals[1]
		#	-----------------------------------------
		#	Determine rotation from page orientation:
		#		Portrait:	0 (No rotation)
		#		Landscape:	3 (270 degrees rotation)
		#		(Seascape:	1 (90 degrees rotation))
		#	-----------------------------------------
		if curVals[2] != '':
			try:
				rotation = eval(curVals[2])
				if rotation in range(4): self.rotation = rotation
				else: raise
			except: self.error.append('ROTATION NOT 0 TO 3 IN PSINFO FOR MAP: ' +
				self.mapName)
	#	----------------------------------------------------------------------
	def extract(self, gameName, pages):
		#	--------------------------------------------
		#	Make .gif files from selected page(s) of the
		#	.ps map for which the root is given.  
		#   To do so, extract the target page using the 
		#   psselect utility (from Andrew Duggan's 
		#   "psutils" package), and mess with it until 
		#   it is all converted to a .gif.
		#	--------------------------------------------
		root = os.path.join(self.gameDir, gameName)
		file = root + '.'
		upscale = self.imageResolution / 72.
		origin = size = None
		if self.bbox:
			origin = [self.bbox[0] * upscale, self.bbox[1] * upscale]
			size = [(self.bbox[2] - self.bbox[0]) * upscale,
					(self.bbox[3] - self.bbox[1]) * upscale]
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
		chop = ('%s/psselect -p%%s %s %s'
				'%s/gs -q -r%d -dSAFER -sDEVICE=ppmraw -o %s %s;' %
				(self.toolsDir, inp[0], outp[0],
				 self.toolsDir, self.imageResolution, outp[1], inp[1]))
		#	----------------------------------------------------------
		#	All landscape maps must be rotated 270 degrees by pnmflip.
		#	----------------------------------------------------------
		make, idx = '', 2
		if self.rotation:
			make += '%s/pnmflip -r%d %s %s' % (self.toolsDir,
				self.rotation * 90, inp[idx], outp[idx])
			idx += 1
		if origin:
			make += '%s/pnmcut %d %d %d %d %s %s' % (self.toolsDir,
				origin[0], origin[1], size[0], size[1], inp[idx], outp[idx])
			idx += 1
		make += '%s/pnmcrop -white %s %s' % (self.toolsDir, inp[idx], outp[idx])
		idx += 1
		make +=	'%s/ppmtogif -interlace %s > %%s' % (self.toolsDir, inp[idx])
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

if __name__ == '__main__':
	rootPath, error, pages = os.path.dirname(sys.argv[0]), 0, [0]
	mapName, mapDirs = 'standard', [os.path.join(rootPath, 'trials'), os.path.join(rootPath, 'maps')]
	toolsDir, imageResolution = os.path.join(rootPath, 'tools'), 72.
	if len(sys.argv) == 1 or sys.argv[1] == '-?':
		error += 1
	else:
		gameDir, gameName = os.path.split(sys.argv[1])
		if not gameDir: gameDir = '.'
		if not gameName: error += 1
		if len(sys.argv) > 2:
			pages = []
			for r in sys.argv[2].split(','):
				try:
					h = r[1:].find('-') + 1
					if not h: n = m = int(r)
					elif r[0] == '-': n, m = int(r[h:]), int(r[:h])
					else: n, m = int(r[:h]), -int(r[h:])
					if m < n: error += 1
					elif not n: pages += range(-m, 1)
					else: pages += range(n, m + 1)
				except: error += 1
		if len(sys.argv) > 3:
			mapDir, mapName = os.path.split(sys.argv[3])
			if mapDir: mapDirs = [mapDir] + mapDirs
			if not mapName: error += 1
		if len(sys.argv) > 4:
			try: imageResolution = float(sys.argv[4])
			except: error += 1
			if imageResolution <= 0: error += 1
		if len(sys.argv) > 5: error += 1
	if error:
		temp = ('Usage: %s gameName [pages=0] [mapName=standard] [imageResolution=72.]'
				'\n\twhereby pages = n,-n,n-m,-n-m with 0 <= n <= m'
		        '\n\tand 1, 2, ... = first page, second page, ..., while 0, -1, ... = last page, second to last page, ...' %
			os.path.basename(sys.argv[0]))
		sys.stderr.write(temp.encode('latin-1'))
	else:
		iv = ImageView(mapName, mapDirs, toolsDir, gameDir, imageResolution)
		if iv.error:
			sys.stderr.write('\n'.join(iv.error).encode('latin-1'))
		else:
			iv.extract(gameName, pages)

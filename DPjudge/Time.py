class Time(str):
	#	------------------------------------------------------------------
	def __new__(self, when = None, npar = 5):
		try:
			if (unicode(when, 'latin-1').isnumeric() and
				len(when) in range(8, 16, 2)): return str.__new__(self, when)
			else: raise AssertionError
		except:
			try: return str.__new__(self, '%02d' * npar % when)
			except:
				try: return str.__new__(self, '%02d' * npar %
					time.localtime(when)[:npar])
				except: return str.__new__(self)
	#	------------------------------------------------------------------
	def tuple(self):
		return tuple(map(int, [self[:4]] + [self[x:x+2] or '0'
			for x in range(4, 14, 2)] + [0, 0, -1]))
	#	------------------------------------------------------------------
	def seconds(self):
		return time.mktime(self.tuple())
	#	------------------------------------------------------------------
	def struct(self):
		return time.localtime(self.seconds())
	#	------------------------------------------------------------------


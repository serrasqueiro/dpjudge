import os, time
from datetime import datetime, timedelta, tzinfo
import host

class TimeZone(tzinfo):
	zones = zoneGroups = adding = None
	#	----------------------------------------------------------------------
	def __new__(self, zone = None):
		if self.adding: return tzinfo.__new__(self)
		try:
			if 'zone' in vars(zone): return zone
		except: pass
		if not self.zones:
			self.adding = 1
			self.zones = {'GMT': TimeZone('GMT')}
			zoneFile = open(host.zoneFile)
			for line in zoneFile:
				word = line.strip().split()
				if word and word[0][0] != '#':
					self.zones[word[2].upper()] = TimeZone(word[2])
			zoneFile.close()
			self.adding = None
		if not zone: zone = host.timeZone or 'GMT'
		zone = zone.upper()
		if zone in self.zones: return self.zones[zone]
		for zoneInfo in self.zones.values():
			if zoneInfo.tzname().upper() == zone: return zoneInfo
		return None
	#	----------------------------------------------------------------------
	def groupZones(self):
		if not TimeZone.zoneGroups:
			TimeZone('GMT')
			TimeZone.zoneGroups = {'': ['GMT']}
			for zoneInfo in TimeZone.zones.values():
				zone = zoneInfo.__repr__()
				if zone == 'GMT': continue
				try: label = zoneInfo.gmtlabel()
				except: label = ''
				TimeZone.zoneGroups.setdefault(label, []).append(zone)
		return TimeZone.zoneGroups
	#	----------------------------------------------------------------------
	def __init__(self, zone = None):
		if 'zone' in vars(self): return
		if not zone: zone = host.timeZone or 'GMT'
		self.zone = zone
		self.putZone()
		now = time.time()
		self.offset = datetime.fromtimestamp(now) - datetime.utcfromtimestamp(now)
		self.saving = time.localtime(now).tm_isdst > 0
		self.label = not host.showGMT and time.strftime('%Z', time.localtime(now))
	#	----------------------------------------------------------------------
	def __repr__(self):
		return self.zone
	#	----------------------------------------------------------------------
	def utcoffset(self, dt = None):
		if not dt: return self.offset
		self.putZone()
		now = time.mktime(dt.timetuple())
		offset = datetime.fromtimestamp(now) - datetime.utcfromtimestamp(now)
		return offset
	#	----------------------------------------------------------------------
	def dst(self, dt = None):
		self.putZone()
		if not time.daylight: return timedelta(0)
		if not self.saving: return timedelta(0)
		return timedelta(0, time.timezone - time.altzone)
	#	----------------------------------------------------------------------
	def tzname(self, dt = None):
		return self.label or self.gmtlabel(dt)
	#	----------------------------------------------------------------------
	def gmtlabel(self, dt = None):
		label = 'GMT'
		offset = self.utcoffset(dt)
		minutes = offset.seconds / 60
		if minutes:
			hours = minutes / 60
			minutes %= 60
			if offset.days < 0:
				hours -= 24
				if minutes: minutes = 60 - minutes
			label += '%+03d' % hours
			if minutes: label += '%02d' % minutes
		return label
	#	----------------------------------------------------------------------
	def putZone(self):
		os.putenv('TZ', self.zone)
#	------------------------------------------------------------------
class Time(str):
	#	----------------------------------------------------------------------
	def __new__(self, zone = None, when = None, npar = 5):
		zone = TimeZone(zone)
		zone.putZone()
		while 1:
			try:
				if (when.isnumeric() and len(when) in range(8, 16, 2)):
					this = str.__new__(self, when.ljust(14, '0')[:npar * 2 + 2])
					break
			except: pass
			try:
				if (unicode(when, 'latin-1').isnumeric()
				and len(when) in range(8, 16, 2)):
					this = str.__new__(self,
						when.ljust(14, '0')[:npar * 2 + 2])
					break
			except: pass
			try:
				this = str.__new__(self, '%02d' * npar % when[:npar])
				break
			except: pass
			try:
				this = str.__new__(self, '%02d' * npar %
					time.localtime(when)[:npar])
				break
			except: pass
			try:
				this = str.__new__(self, '%02d' * npar %
					time.strptime(when)[:npar])
				break
			except: pass
			for fmt in ['%A %d %B %Y %H:%M', '%a %d %b %Y %H:%M',
				'%a, %d %b %Y %H:%M:%S', '%d %B %Y', '%A %d %B %Y']:
				try:
					this = str.__new__(self, '%02d' * npar %
						time.strptime(when, fmt)[:npar])
					break
				except: pass
			else: this = str.__new__(self)
			break
		this.zone = zone
		this.tail = [0, 0, -1]
		if this:
			this.tail = list(time.localtime(this.seconds())[6:])
		return this
	#	----------------------------------------------------------------------
	def npar(self):
		return len(self) / 2 - 1
	#	----------------------------------------------------------------------
	def mod(self, off = 0, mod = 1200):
		dict = { 'M': 60, 'H': 3600, 'D': 86400, 'W': 604800 }
		try: off / 1
		except: off = int(off[:-1]) * dict.get(off[-1], 1)
		try: return off / mod
		except: return off / int(mod[:-1]) * dict.get(mod[-1], 1)
	#	----------------------------------------------------------------------
	def offset(self, off = 0):
		return Time(self.zone, self.seconds() + self.mod(off, 1), self.npar())
	#	----------------------------------------------------------------------
	def trunc(self, mod = 1200, up = 0):
		if mod == 1: return self.offset()
		#	----------------------------------------
		#	Truncating to a day requires some magic.
		#	----------------------------------------
		zone, self.zone = self.zone, TimeZone('GMT')
		secs = self.seconds()
		zone, self.zone = self.zone, zone
		#	-------------------
		#	Convert to seconds.
		#	-------------------
		mod = self.mod(mod, 1)
		return self.offset(((secs - up) / mod  + up) * mod - secs)
	#	----------------------------------------------------------------------
	def diff(self, other = None, mod = 1200):
		secs = self.seconds()
		try: osecs = other.seconds()
		except: osecs = Time(self.zone, other, self.npar()).seconds()
		return self.mod(osecs - secs, mod)
	#	----------------------------------------------------------------------
	def adjust(self, npar):
		if npar == self.npar(): return self
		return Time(self.zone, self.tuple(), npar)
	#	----------------------------------------------------------------------
	def next(self, at, mod = 1200, frm = 3):
		try:
			at, npar = at.tuple(), at.npar()
			week = (None, at[6])[frm == 6]
			if week: npar = 3
		except:
			date, fmt, tim, week, npar = at.split(), [], [], [], 3
			if ':' in date[-1]:
				npar += len(date[-1].split(':'))
				if npar > 6: raise MalformedTime
				tim = ['%H:%M' + ':%S' * (npar > 5)]
				del date[-1]
				if date and date[-1].upper() == 'AT':
					tim = date[-1:] + tim
					del date[-1]
			if date and date[0][0].isalpha():
				week = [('%A', '%a')[len(date[0]) == 3]]
				del date[0]
			if date:
				fmt = ['%d']
				if len(date) > 1:
					fmt += [('%B', '%b')[len(date[1]) == 3]]
					if len(date) > 2:
						fmt += [('%Y', '%y')[len(date[2]) < 3]]
						if len(date) > 3: raise MalformedDate
			frm = 3 - len(date)
			at = time.strptime(at, ' '.join(week + fmt + tim))
			if week: week = at[6]
			else: week = None
		at = ('%02d' * (6 - frm)) % at[frm:6]
		if not frm:
			when = Time(self.zone, at, npar)
		else:
			day = self.adjust(frm)
			when = Time(self.zone, day + at, npar)
			if when < self.adjust(npar):
				date = day.tuple()
				days = (frm == 1 and (datetime(date[0] + 1, 1, 1) -
					datetime(date[0], 1, 1)).days or frm == 2 and
					(datetime(date[0] + date[1] / 12, date[1] % 12 + 1, 1) -
					datetime(date[0], date[1], 1)).days or 1)
				when = Time(self.zone, day.offset('%dD' % days) + at, npar)
		if week is not None and week != when.tuple()[6]:
			if frm < 3: raise MalformedDate
			when = when.offset('%dD' % ((week - when.tuple()[6]) % 7))
		return when.trunc(mod, 1)
	#	----------------------------------------------------------------------
	def tuple(self):
		return tuple(map(int, [self[:4] or '1901'] + [self[x:x+2] or '1'
			for x in range(4, 8, 2)] + [self[x:x+2] or '0'
			for x in range(8, 14, 2)]) + self.tail)
	#	----------------------------------------------------------------------
	def seconds(self):
		self.zone.putZone()
		return int(time.mktime(self.tuple()))
	#	----------------------------------------------------------------------
	def struct(self):
		when = time.localtime(self.seconds())
		return when
	#	----------------------------------------------------------------------
	def cformat(self):
		when = time.ctime(self.seconds())
		return when
	#	----------------------------------------------------------------------
	def format(self, form = 0):
		#	---------------------------------------------------------------
		#	If "form" is 0, the return format is:
		#		20150901080059 --> Tuesday 1 September 2015 08:00 JST
		#		20150901 --> Tuesday 1 September 2015
		#	If "form" is 1, the return format is:
		#		20150901080059 --> Tue 1 Sep 2015 08:00 JST
		#		20150901 --> Tue 1 Sep 2015
		#	If "form" is 2, the return format is:
		#		20150901080059 --> Tue, 01 Sep 2015 08:00:59 JST
		#		20150901 --> Tue, 01 Sep 2015
		#	If "form" is 3, the return format is:
		#		20150901080059 --> 1 September 2015 08:00 JST
		#		20150901 --> 1 September 2015
		#	If "form" is 4, the return format is:
		#		20150901080059 --> 1 Sep 2015 08:00
		#		20150901 --> 1 Sep 2015
		#	If "form" is 5, the return format is:
		#		20150901080059 --> 1 Sep 08:00
		#		20150901 --> 1 Sep
		#	if the year is current, otherwise:
		#		20150901080059 --> 1 Sep 2015 08:00
		#		20150901 --> 1 Sep 2015
		#	If "form" is 6, the return format is:
		#		20150901080059 --> 2015/09/01 08:00
		#		20150901 --> 2015/09/01
		#	If "form" is 7, the return format is:
		#		20150901080059 --> 09/01 08:00
		#		20150901 --> 09/01
		#	if the year is current, otherwise:
		#		20150901080059 --> 2015/09/01 08:00
		#		20150901 --> 2015/09/01
		#	---------------------------------------------------------------
		when = [self.formatDate(form)]
		if self.npar() > 3:
			when += [self.formatTime(form > 3 and 1 or form == 2 and 2 or 0)]
		return ' '.join(when)
	#	----------------------------------------------------------------------
	def formatDate(self, form = 0):
		#	---------------------------------------------------------------
		#	If "form" is 0, the return format is:
		#		20150901 --> Tuesday 1 September 2015
		#	If "form" is 1, the return format is:
		#		20150901 --> Tue 1 Sep 2015
		#	If "form" is 2, the return format is:
		#		20150901 --> Tue, 01 Sep 2015
		#	If "form" is 3, the return format is:
		#		20150901 --> 1 September 2015
		#	If "form" is 4, the return format is:
		#		20150901 --> 1 Sep 2015
		#	If "form" is 5, the return format is:
		#		20150901 --> 1 Sep
		#	if the year is current, otherwise:
		#		20150901 --> 1 Sep 2015
		#	If "form" is 6, the return format is:
		#		20150901 --> 2015/09/01
		#	If "form" is 7, the return format is:
		#		20150901 --> 09/01
		#	if the year is current, otherwise:
		#		20150901 --> 2015/09/01
		#	---------------------------------------------------------------
		when, stc = [], self.struct()
		if form < 3: when += [time.strftime(form == 2 and '%a,' or
			form == 1 and '%a' or '%A', stc)]
		when += [time.strftime(form in (0, 3) and '%d %B %Y' or
			form > 5 and '%Y/%m/%d' or '%d %b %Y', stc)]
		if form != 2 and form < 6: when[-1] = when[-1].lstrip('0')
		if form in (5, 7):
			now = Time(self.zone)
			if now[:4] == self[:4]:
				when[-1] = form > 5 and when[-1][5:] or when[-1][:-5]
		return ' '.join(when)
	#	----------------------------------------------------------------------
	def formatTime(self, form = 0):
		#	---------------------------------------------------------------
		#	If "form" is 0, the return format is:
		#		20150901080059 --> 08:00 JST
		#	If "form" is 1, the return format is:
		#		20150901080059 --> 08:00
		#	If "form" is 2, the return format is:
		#		20150901080059 --> 08:00:59 JST
		#	---------------------------------------------------------------
		when = [time.strftime(form == 2 and '%H:%M:%S' or '%H:%M', self.tuple())]
		if form != 1: when += [self.zone.tzname()]
		return ' '.join(when)
	#	----------------------------------------------------------------------
	def changeZone(self, zone = None):
		zone = TimeZone(zone)
		if not zone: return None
		if zone == self.zone: return self
		dt = datetime.fromtimestamp(self.seconds(), self.zone)
		return Time(zone, dt.astimezone(zone).timetuple(), self.npar())
	#	----------------------------------------------------------------------
	def __eq__(self, other):
		try: return self.seconds() == other.seconds()
		except: return str.__eq__(self, other)
	#	----------------------------------------------------------------------
	def __lt__(self, other):
		try: return self.seconds() < other.seconds()
		except: return str.__lt__(self, other)
	#	----------------------------------------------------------------------
	def __gt__(self, other):
		try: return self.seconds() > other.seconds()
		except: return str.__gt__(self, other)
	#	----------------------------------------------------------------------
	def __ne__(self, other):
		return not self.__eq__(other)
	#	----------------------------------------------------------------------
	def __ge__(self, other):
		return not self.__lt__(other)
	#	----------------------------------------------------------------------
	def __le__(self, other):
		return not self.__gt__(other)
	#	------------------------------------------------------------------


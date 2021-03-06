#   ===============
#   DPjudge package
#   ===============
import os
os.sys.path[:0] = [os.path.dirname(os.path.abspath(os.sys.argv[0])) + '/..']

import host
from Game import Game, Power, Mail, Status

host.packageDir = __path__[0]
host.hostDir = os.path.dirname(os.path.abspath(host.__file__))

for (var, value) in [
	('toolsSubDir', 'tools'),
	('gameSubDir', 'games'),
	('logSubDir', 'log'),
	('dpjudgeSubDir', 'web'),
	('gameMapSubDir', 'maps'),
	('dpjudgeURL', 'http://localhost'),
	('zoneFileName', 'zone.tab'), ('timeZone', ''), ('showGMT', 0),
	('headerHtml', ''), ('bannerHtml', ''), ('bannerExpireDate', ''),
	('tester', ''),
	('openingsList', ''), ('openingsAddress', ''),
	('dppd', ''), ('dppdSubURL', '?variant=dppd'),
	('dpjudgeNick', 'DPjudge'),
	('judgePassword', ''),
	('judgekeeper', vars(host).get('judgekeepers', [''])[0]),
	('judgekeepers', [vars(host).get('judgekeeper', '')]),
	('publicDomains', []),
	('createLimit', 20),
	('imageResolution', 72), ('usePDFMark', True),
	('copy', 0), ('notify', 0)]:
	vars(host).setdefault(var, value)

for (var, base, path) in [
	('toolsDir', 'packageDir', 'toolsSubDir'),
	('gameDir', 'hostDir', 'gameSubDir'),
	('logDir', 'hostDir', 'logSubDir'),
	('dpjudgeDir', 'hostDir', 'dpjudgeSubDir'),
	('gameMapDir', 'dpjudgeDir', 'gameMapSubDir'),
	('gameMapURL', 'dpjudgeURL', 'gameMapSubDir'),
	('dppdURL', 'dpjudgeURL', 'dppdSubURL'),
	('resultsID', 'dpjudgeID', ''),
	('resultsFrom', 'dpjudge', ''),
	('resultsURL', 'dpjudgeURL', ''),
	('zoneFile', 'toolsDir', 'zoneFileName')]:
	if var not in vars(host):
		vars(host)[var] = path and os.path.join(vars(host)[base],
			vars(host)[path]) or vars(host)[base]
	elif vars(host)[var] and os.path.isabs(
		vars(host)[base]) and not os.path.isabs(vars(host)[var]):
		vars(host)[var] = os.path.join(vars(host)[base], vars(host)[var])

#   =========================================================================
#   Synchronize the timestamps we will get from time.time() with NTP service.
#   -------------------------------------------------------------------------
if vars(host).get('ntpService'):
    import telnetlib, time
    try:
        systime, synch, time.time = time.time, 0.0, lambda: systime() + synch
        sysNow, ntp = systime(), telnetlib.Telnet(*host.ntpService)
        for byte in ntp.read_all(): synch = synch * 256 + ord(byte)
        synch -= 70*365*24*60*60 + 17*24*60*60 + sysNow
        ntp.close()
    except: pass
   
if __name__ != '__main__': from Page import Page



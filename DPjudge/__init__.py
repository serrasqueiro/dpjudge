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
	('toolsDir', host.packageDir + '/tools'),
	('dpjudgeDir', host.hostDir + '/web'), ('gameDir', host.hostDir + '/games'),
	('bannerHtml', '')]: vars(host).setdefault(var, value)

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



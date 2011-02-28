#   ===============
#   DPjudge package
#   ===============
import os
os.sys.path[:0] = [os.path.dirname(os.path.abspath(os.sys.argv[0])) + '/..']

import host
from Game import Game, Power, Mail, Status

try: host.packageDir
except: host.packageDir = __path__[0]
try: host.dpjudgeDir
except: host.dpjudgeDir = host.hostDir + '/web'
try: host.gameDir
except: host.gameDir = host.hostDir + '/games'
try: host.toolsDir
except: host.toolsDir = host.packageDir + '/tools'

try: host.bannerHtml
except: host.bannerHtml = ''

if __name__ != '__main__': from Page import Page

#   =========================================================================
#   Synchronize the timestamps we will get from time.time() with NTP service.
#   -------------------------------------------------------------------------
if 'ntpService' in dir(host) and host.ntpService:
    import telnetlib, time
    try:
        systime, synch, time.time = time.time, 0.0, lambda: systime() + synch
        sysNow, ntp = systime(), telnetlib.Telnet(*host.ntpService)
        for byte in ntp.read_all(): synch = synch * 256 + ord(byte)
        synch -= 70*365*24*60*60 + 17*24*60*60 + sysNow
        ntp.close()
    except: pass

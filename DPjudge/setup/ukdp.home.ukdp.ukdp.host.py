import os

#	-------------------------------------------------------
#	Set "testing" to None to use the production package.
#	Otherwise, set it to the directory holding the package.
#	Also set up a banner message to display on every page.
#	-------------------------------------------------------
os.sys.path.insert(0, '/home/ukdp/site-packages')
testing			=	 None
if testing:
	bannerHtml = """
		<p align=center><font color=red><b>
		
		WARNING: THIS DPJUDGE SITE IS PRE-RELEASE!
		<br>
		<a href=http://www.floc.net/dpjudge><u>-- CLICK HERE FOR THE PRODUCTION DPJUDGE --
		</u></a></b></font></p>
		"""

#	--------------------------------------------------------
#	Give "tester" an e-mail address to redirect all (?) mail
#	traffic to that person, or to an invalid address to
#	generate no mail at all.
#	-------------------------------------------------------
tester = None # '@'

#	-----------------------------------------------------------------
#	Set the host directory.  That is where this particular host.py is
#	-----------------------------------------------------------------
#hostDir      	=	'/home/ukdp/ukdp' #os.path.dirname(__file__)

#	--------------------------------------------------------------
#	E-mail address, PBEM judge identifier, and URL of this DPjudge
#	--------------------------------------------------------------
dpjudgeID		=	'UKDP'
dpjudge			=	'ukdp@uk.diplom.org'
judgekeeper     =	'woelpad@gmail.com' # 'peter@spikings.com'
#	--------------------------------------------------------------
dpjudgeURL      =	'http://uk.diplom.org'

#dpjudgeSubDir	=	'web'	# Location: hostDir
#gameMapSubDir	=	'maps'	# Location: dpjudgeDir
#toolsSubDir	=	'tools'	# Location: packageDir
needIndexWWW	=	False
#	--------------------------------------------------------------

#	-----------------------
#	DPPD used by this judge
#	-----------------------
dppd			=	'dppd@diplom.org'
dppdURL			=	'http://www.floc.net/dpjudge?variant=dppd'

#	------------------------------
#	Database connection parameters
#	------------------------------
#dbName			=	'ukdp'
#dbHost			=	'localhost'
#dbUser			=	'ukdp'
#dbPassword		=	'********'
#dbPort			=	3306

#	--------------------------------------------------------
#	Location of game directories (and main game status file)
#	This should be a directory that is NOT Web-accessible!!!
#	--------------------------------------------------------
#gameSubDir	  	=	'games'	# Location: hostDir

#	---------------------------------------------------------
#	Notify the judgekeeper of any game created on a trial map
#	0: no notice [default]; 1: trial maps only; 2: all maps
#	---------------------------------------------------------
notify = 1

#   --------------------------------------------------------------
#	Set timeZone only as a last resort, i.e. if you're on Windows
#	on a non-English/non-Latin computer where the local timezone
#	comes out as a unicode string that results in a 
#	UnicodeDecodeError for the ascii codec.
#	This will probably also ignore any timezone directive in the
#	game settings.
#   --------------------------------------------------------------
timeZone		=	None
zoneFile    	=	'/usr/share/zoneinfo/zone.tab'

#	--------------------------------------------------------------
#	Image resolution. Determines the resolution used for the
#	bitmaps (gifs) of the game maps. Choose wisely. Too small
#	creates blocky images, too big increases render time and
#	file size and consequently download time. Unit is dpi (dots
#	per inch). The industry standard, used in the old days, is 72.
#	--------------------------------------------------------------
imageResolution =	108

#   --------------------------------------------------------------
#   Time synchronizaion.  Set ntpService to None if you do not 
#   want to automatically synchronize all reported times with an 
#   NTP Service. Otherwise, set to a (host, port) tuple (NTP is
#   usually on port 37)
#   --------------------------------------------------------------
ntpService    =	('time.nist.gov', 37)
ntpService      =	None

#	----------------------------------------------------------
#	E-mail will be sent either directly via an SMTP service, or
#	through a pipe to a UNIX "sendmail" utility program.  If
#	"smtpService" is set to a string having the format 
#	'host:port' or 'host' or '' (defaults are
#	'localhost:25'), SMTP is used.  If "smtpService" is None,
#	the sendmail pipe is used and sendmailDir is the location
#	of the sendmail program.  You would use the sendmail pipe
#	rather than SMTP if, for example, your SMTP service is not
#	configured to allow mail relaying to out-of-domain
#	addresses.
#	----------------------------------------------------------
smtpService     =	'localhost:25'
sendmailDir     =	'/usr/sbin'

#	-------------
#	Notifications
#	-------------
detectives      =	[]
hall_keeper     =	'hall_keeper@ugcs.caltech.edu'
observers   	=	None # 'observer@floc.net'

#	==========================================================
#					UNIX MINIMUM PERMISSIONS
#	dpjudgeDir  must be 755
#	packageDir	must be 755
#	gameDir	    must be 777
#	    ***as must each game directory within it***
#	==========================================================


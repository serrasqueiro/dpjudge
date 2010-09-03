raise NotImplementedException

#   ============================ WHAT THIS WILL BE ============================
"""
This is the setup script to install a single instance of a DPjudge, given that
the DPjudge Python package has previously been installed.  This script would be
run, for example, as:
    $ python -i DPjudge.setup
This script will accomplish the following:
    1. Determine the host directory for the new DPjudge installation.
       This is a user-provided directory name.
    2. Write a "host.py" file into that directory, based on answers to
       questions ("What is the judgekeeper email address", etc.).
       A template host.py file is given below. 
    3. Create the following subdirectories beneath the host directory and
       populate them as described:
       ==> a bin/ directory, containing:
           judgekeeper utilities "check", "inspect", "mail", and "reopen"
           Each of these is a one-line Python executable script.  E.g.:
           import DPjudge.bin.check
       ==> a games/ directory, initially containing an empty file named
           "status".  This directory, and all files and directories beneath
           it must be writeable by the user under which the web server runs.
       ==> a pages/ directory, intially empty.  This directory can contain
           any webpage templates specific to this particular DPjudge, as
           created by the judgekeeper (overriding those in the package).
       ==> a web/ directory.  This directory must be made (or must be a
           softlink to) the root directory of the Website served (by apache,
           etc.) to the Internet for this DPjudge.  This directory will
           be populated with:
           --> an executable file named index.cgi, which should be made the
               default page served by webserver (apache, etc.).  This file
               is a one-line Python executable script: import DPjudge.web
           --> an images/ directory, which should be a SOFTLINK to the
               /web/images directory within the installed package.
           --> a maps/ directory, initially empty.  This directory must be
               writeable by the user under which the Webserver runs.
           --> IF THE web/ DIRECTORY IS A SOFTLINK TO ELSEWHERE ON THE DISK
               (that is, if it is a softlink to apache servable directory),
               then the web/ directory MUST also be given a copy of (or,
               preferably, a softlink to) the host.py file that was created
               in its parent (the host) directory.  This must be done since
               the mechanism used to import the host file depends on "host.py"
               being either in "." or ".." relative to each executable that
               runs (i.e., in "bin/" or "web/"), and if the webserver believes
               in a different directory structure when running, ".." will not
               identify the host directory.
       ==> a log/ directory.  This directory is initially empty and will
           contain various output from cron and procmail jobs.
    4. Install a crontab to cause game processing every 20 minutes.  This
       crontab entry should have the following format:
           HOST=/path/to/dpjudge/hostdir
           */20 * * * * $HOST/bin/check > $HOST/log/check.log 2>&1
    5. Install a .procmailrc in the $HOME directory of the user receiving
       email for this DPjudge.  This .procmailrc should have the following
       format:
           HOST=/path/to/dpjudge/hostdir

           :0
           |($HOST/bin/mail > $HOST/log/email.log 2>&1)
       The script should also ask the Judgekeeper if procmail logging should
       be done (or alternately redirected to /dev/null) and if bounce-handling
       should be put into the .procmailrc (causing mails detected as bounces
       to be deleted silently or perhaps tossed into an (ever-growing) mailbox
       file in $HOST/log with entries like:
           LOGFILE=$HOST/log/procmail.log # or /dev/null
            
           :0
           * ^From MAILER-DAEMON
           $HOST/log/bounces
       above the main entry directing mail at the ../bin/mail program.
"""

#   ============================ SAMPLE host.py FILE ============================
"""
#   --------------------------------------------------------------
#   E-mail address, PBEM judge identifier, and URL of this DPjudge
#   --------------------------------------------------------------
hostDir         =   '/home/dpjudge/usdp'
dpjudgeID       =   'USDP'
dpjudge         =   'dpjudge@diplom.org'
judgekeeper     =   'manus@diplom.org'
dpjudgeURL      =   'http://www.diplom.org/dpjudge'
needIndexWWW    =   False

#   -----------------------
#   DPPD used by this judge
#   -----------------------
dppd            =   'dppd@diplom.org'
dppdURL         =   'http://www.diplom.org/dpjudge?variant=dppd'

#   -----------------------------------------------------------
#   Image resolution. Determines the resolution used for the
#   bitmaps (gifs) of the game maps. Choose wisely. Too small
#   creates blocky images, too big increases render time and
#   file size and consequently download time. Unit is dpi (dots
#   per inch). The industry standard, from the old days, is 72.
#   -----------------------------------------------------------
imageResolution =   108

#   ------------------------------------------------------------
#   Time synchronizaion.  Set ntpService to None if you do not
#   want to automatically synchronize all reported times with an
#   NTP Service. Otherwise, set to a (host, port) tuple (NTP is
#   usually on port 37).
#   ------------------------------------------------------------
ntpService      =   None # ('time.nist.gov', 37)
zoneFile        =   '/usr/share/zoneinfo/zone.tab'

#   ---------------------------------------------------------
#   E-mail will be sent EITHER directly via an SMTP service,
#   or through a pipe to a UNIX "sendmail" utility program.
#   If "smtpService" is set to a string having the format
#   'host:port' or 'host' or '' (default to 'localhost:25'),
#   SMTP is used.  If "smtpService" is None, the sendmail
#   pipe is used.  You would use the sendmail pipe rather
#   than SMTP if, for example, your SMTP service is not
#   configured to allow relaying to out-of-domain addresses.
#   ---------------------------------------------------------
smtpService     =   'localhost:25'

#   -------------
#   Notifications
#   -------------
detectives      =   []                          # suspicious activity
hall_keeper     =   'hall_keeper@diplom.org'    # endgame summaries
observers       =   'observer@floc.net'         # new games

"""
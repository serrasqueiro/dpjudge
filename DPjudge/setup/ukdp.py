"""
While I'm installing UKDP, I will use this mail to keep track of my actions. 
UKDP is located on spikings.com, a Ubuntu server.

First I needed to install mercurial:
> sudo apt-get install mercurial
Then I went to download the dpjudge package. Following the instructions on the 
googlecode download page:
> cd ~/site-packages
> hg clone https://woelpad@code.google.com/p/dpjudge/
This however creates a dpjudge folder inside site-packages, which in turn 
contains the DPjudge root folder. That's one level to deep, so we erase the 
clone, go back to the home directory and tell clone to rename dpjudge to 
site-packages:
> cd ~
> hg clone https://woelpad@code.google.com/p/dpjudge/ site-packages

After following my own instructions in the first mail, I copied the inspect 
script in $JDG/bin to check, mail and reopen (I wonder why usdp renamed the 
latter to "reOpen") and altered the last word in each ("inspect") to the 
respective script names. I changed the path name in $JDG/web/index.cgi and 
then edited $JDG/host.py, replacing path names, urls and mail addresses as I 
saw fit. A .vimrc that ensures that tab stops are 4 spaces was added.

Script files in $JDG/bin need to be executable, hence "chmod a+x *". inspect 
turned out to have dos line endings, messing up with the python shebang. Load 
in vi, type ":set ff=unix", then save and quit and repeat that for each script 
file. I ran inspect, and created the test game with the Status.createGame() 
call. So far, so good.

I added "umask 002" and PKG and JDG environment variables to .bashrc. I should 
have done that earlier, as now I had to go back and do a "chmod g+w" on all 
files and folders in $JDG (except $JDG/bin, I guess). This is so that apache, 
logging in in the same group as ukdp, will be able to run DPjudge code and 
modify games.

I like to run multiple terminals in screen, so that I can look in source code, 
inspect games and visit game folders at the same time, simply by switching 
screens. For that I have made the following alias, and put it in .bash_profile:
~ alias attach='screen -D -RR $(screen -ls | grep \(..tached\) | awk "NR == 1 {print \$1}")'
Every time I log in, I just have to enter "attach" and it will reattach to my 
screen session.

Now, to install apache, do the same as for mercurial:
> sudo apt-get install apache2
We'll also need mod-python, otherwise apache2 doesn't know how to execute 
python scripts:
> sudo apt-get install libapache2-mod-python
Next, we add apache_configuration.conf. I don't know how Alain made sure that 
this file got loaded. I simply wrote in httpd.conf to load the file.
> sudo vi /etc/apache2/httpd.conf
~ Include /home/ukdp/apache_configuration.conf
The "sudo apachectl graceful" given in the comments there must have applied to 
an older apache installation. Nowadays you restart apache2 as follows:
> sudo /etc/init.d/apache2 restart

To check that ukdp is now running on apache, we start python:
> python
>>> import urllib
>>> response = urllib.urlopen('http://localhost/ukdp')
>>> response.read()
'<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">\n<html><head>\n<title>500 Internal Server Error</title>\n</head><body>\n<h1>Internal Server Error</h1>\n<p>The server encountered an internal error or\nmisconfiguration and was unable to complete\nyour request.</p>\n<p>Please contact the server administrator,\n webmaster@localhost and inform them of the time the error occurred,\nand anything you might have done that may have\ncaused the error.</p>\n<p>More information about this error may be available\nin the server error log.</p>\n<hr>\n<address>Apache/2.2.14 (Ubuntu) Server at localhost Port 80</address>\n</body></html>\n'
>>> 

Something wrong? Let's check the error log, set in apache's main configuration 
file by the ErrorLog parameter:
> grep ErrorLog /etc/apache2/apache2.conf
... # ErrorLog: The location of the error log file.
... # If you do not specify an ErrorLog directive within a <VirtualHost>
... ErrorLog /var/log/apache2/error.log
> tail /var/log/apache2/error.log
[<timestamp>] [error] (13)Permission denied: exec of '/home/ukdp/ukdp/web/index.cgi' failed
[<timestamp>] [error] [client ::1] Premature end of script headers: index.cgi
I see, index.cgi needs to be executable:
> chmod a+x $JDG/web/index.cgi

Second try:
>>> response = urllib.urlopen('http://localhost/ukdp')
>>> response.read()
'\n\n\t\t\t<H3>DPjudge Error</H3><p class=bodycopy>\n\t\t\tPlease <a href=mailto:woelpad@gmail.com>e-mail the judgekeeper</a>\n\t\t\tand report how you got this error.  Thank you.\n\t\t\t<!--\n\t\t\t\n  File "/home/ukdp/site-packages/DPjudge/web/index.py", line 5, in handle\n    try: DPjudge.Page(form)\n  File "/home/ukdp/site-packages/DPjudge/Page.py", line 51, in __init__\n    if self.include(): raise SystemExit\n  File "/home/ukdp/site-packages/DPjudge/Page.py", line 90, in include\n    .replace(\'<DPPD>\',\thost.dppdURL)\nTraceback (most recent call last):\n  File "/home/ukdp/site-packages/DPjudge/web/index.py", line 5, in handle\n    try: DPjudge.Page(form)\n  File "/home/ukdp/site-packages/DPjudge/Page.py", line 51, in __init__\n    if self.include(): raise SystemExit\n  File "/home/ukdp/site-packages/DPjudge/Page.py", line 90, in include\n    .replace(\'<DPPD>\',\thost.dppdURL)\nTypeError: expected a character buffer object\n-->\n'
>>>
Right, it doesn't like it that we didn't assign a dppd in host.py. Let's 
change that:
> vi $JDG/host.py
~ dppd            =   'dppd@diplom.org'
~ dppdURL         =   'http://www.floc.net/dpjudge?variant=dppd'
(Note: The host.py that I sent had dpforge in the url, not dpjudge. Check that 
it's the latter.)

After this little upheaval, we repeat the urllib sequence and, behold, we get 
the DPjudge home page in the response! Let's see if the outside world can 
already see something. We enter the site's address in a browser 
(http://mediacentre.spikings.com/ukdp), but alas we get a "Page not found" 
error. Time to contact the site owner.

[Continued]

The site owner, Peter Spikings, wants the ukdp/web folder as the DocumentRoot, 
so that you simply have to enter the host address to get the DPjudge home page, 
e.g. "http://ukdp.spikings.com/" or "http://uk.diplom.org" which was the host 
name 10 years ago. To accomplish that, we need to add a new site to apache, 
and can as well disable the default one, which is staring at /var/www.

We start by copying default to ukdp:
> sudo cp /etc/apache2/sites-available/default /etc/apache2/sites-available/ukdp
Then we open that file in vi and start messing around, integrating all what 
was in apache_configuration.conf, so that we can throw the latter out 
afterwards. Incidentally we let ErrorLog and CustomLog point to 
$JDG/log/apache2 and create that folder. We then disable default and enable 
ukdp:
> sudo a2dissite default & a2ensite ukdp
> sudo /etc/init.d/apache2 reload
> sudo /etc/init.d/apache2 restart
Checking with python whether we can read localhost:
>>> response = urllib.urlopen('http://localhost/')
>>> response.read()
'\n<html>\n<head>\n<title>UKDP: The DPjudge</title>\n\n<style type="text/css">...'
That works. Now we can go and delete apache_configuration.conf and make 
/etc/apache2/httpd.conf empty again.

While we're waiting for Peter and Millis (site owner of diplom.org) to create 
the new host name, let's check and see if we can set up and run a test game 
proper. So far we only created the game testing (see previous mail), but it's 
still in its forming state, with no players signed up yet. We don't need 
players though, we can use dummies. The fastest way is to simply edit the 
status file:
> vi $JDG/games/testing/status
---
MORPH DUMMY AUSTRIA ENGLAND FRANCE GERMANY ITALY RUSSIA TURKEY
RULE HIDE_DUMMIES
---
The rule added will ensure that we can log in to any dummy's game page. Note: 
If you want to start with less players (at least 2), simply omit the rest on 
the DUMMY line. Now let's start the game:
> cd $JDG/bin
> inspect testing
>>> self.begin()
sh: /home/ukdp/site-packages/DPjudge/tools/ps2pdf: not found
>>> self.phase
u'SPRING 1901 MOVEMENT'

It's complaining that ps2pdf is not installed, but it did move to S1901M. 
Indeed, we did not put any links in $PKG/tools for all the external resources 
needed to run the judge. Now, there's a __init__.py file there that is just a 
Readme file telling you what should be installed here. Since it didn't list 
the actual packages, I'm listing them here and adding that to the __init__ 
file. These are:
... gs -> /usr/bin/gs
... ps2pdf -> /usr/bin/ps2pdf
to convert from ps to pdf (package: ghostscript).
... psselect -> /usr/bin/psselect
to extract a page from a ps file (package: psutils).
... pnmcrop -> /usr/bin/pnmcrop
... pnmcut -> /usr/bin/pnmcut
... pnmflip -> /usr/bin/pnmflip
... ppmtogif -> /usr/bin/ppmtogif
to convert from ps to gif (package: netpbm).
... sendmail -> /usr/sbin/sendmail
to send mail, obviously (package: sendmail). Only used if you want to use the 
smtp service. Note that Ubuntu users are quite vocal in saying you are better 
off installing the more secure Postfix frontend.
... zone.tab -> /usr/share/zoneinfo/zone.tab
to convert time zones (on system installation). You can also specify this file 
directly into your host.py file, making this link superfluous.

Afer installing all 4 packages ("sudo apt-get install <package>"), try to 
remake the maps:
> inspect testing 'self.makeMaps()'
No error gets reported and checking $JDG/web/maps, we see a ps, pdf and gif 
file. All well then. Note that by providing a second parameter, embraced in 
quotes to not mess with the shell substitutions, inspect executes that command 
and exits. The self here points to the Game instance. More info in 
$PKG/bin/inspect.py.

Let us now set up the smtp service. 
> sudo sendmailconfig
Perhaps not really a necessity, since I'm just accepting the defaults. Anyway, 
let's test sendmail by sending a simple test mail to myself.
> echo "sendmail test" | sendmail woelpad@gmail.com
Success, I'm getting mail. The only problem is, it's coming from 
ukdp@ukdp.diplom.org, not the intended ukdp@uk.diplom.org. By repeating the 
same command as above, but adding the -v option (verbose), I come to know that 
the EHLO is ukdp.diplom.org. I ask Peter to change that, but even then the 
from-address is still the same. Turns out it's written like that in the 
/etc/hosts file.
> cat /etc/hosts
---
127.0.0.1       localhost
192.168.10.2    ukdp.diplom.org   ukdp
---
A quick edit to change the first ukdp to uk, a new test mail, and yes, we're 
ok now.

Big news from Millis: The site is up. I can access the site, but any mail I 
send gets swallowed whole. Oh right, forgot to install procmail. A 
"dpkg -s procmail" tells me procmail is already installed (comes with sendmail, 
I guess). Just need to add .procmailrc, and replace all instances of dpjudge 
and usdp with ukdp, as unlike dpjudge/dpforge ukdp is both the user name and 
the judge name.

Well, that doesn't do anything yet. Let's try to dry run procmail. First I 
create a message with the following contents:
---
From: me@spikings.com
To: ukdp@uk.diplom.org (self test)

signon mtesting test
broadcast
Broadcasting...
endpress
signoff
---

Then I run that through .procmailrc
> procmail VERBOSE=on DEFAULT=/dev/null .procmailrc < test.msg
procmail: [19776] Sun Feb 19 21:18:38 2012
procmail: Assigning "DEFAULT=/dev/null"
procmail: Rcfile: "/home/ukdp/.procmailrc"
procmail: Assigning "MAILDIR=/home/ukdp"
procmail: Assigning "SHELL=/bin/sh"
procmail: Assigning "PATH=.:/home/ukdp/bin:/bin:/usr/bin:/usr/local/bin:/usr/sbin:/usr/lib"
procmail: Assigning "LOGFILE=/home/ukdp/ukdp/log/procmail.log"
procmail: Opening "/home/ukdp/ukdp/log/procmail.log"

And then nothing. After waiting for a while I interrupt the process and 
inspect the log-file given above.
> tail /home/ukdp/ukdp/log/procmail.log
procmail: Locking "ukdp"
procmail: [19776] Sun Feb 19 21:19:26 2012
procmail: Locking "ukdp"
procmail: [19776] Sun Feb 19 21:19:34 2012
procmail: Locking "ukdp"
procmail: Terminating prematurely whilst waiting for lockfile ""
  Folder: **Bounced**                                                         0
procmail: Unlocking "/home/ukdp/ukdp/log/.procmail.lock"

After 8 seconds it seems to respawn the process, but gets stuck because the 
previous lock was not released yet. What's the command it's executing like? 
Looking in .procmailrc, I see:
---
:0 H: ukdp
* ^To:.*ukdp@.*
|(cd /home/ukdp/ukdp; /user/usr/bin/timelimit -t 300 bin/mail > output.email 2>&1)
----
The first line indicates that this is the ukdp lock, the second line the 
matching condition (any message destined for user ukdp), the third line what 
to execute. Wait, ukdp, is that not the name of the lock file? That gets 
written where? In the home dir? But there's already a dir with that name! (In 
all fairness, Peter tipped me off on this one.) Let's add ".lock" to the lock 
file name and dump it in the /tmp folder for good measure: 
":0 H: /tmp/ukdp.lock". 

One more surprise, "timelimit"?! Pretty evocative, but is it installed and 
what kind of a path is that: /user/usr/bin? Must be some floc peculiarity. A 
new apt-get to install timelimit and check that it's in /usr/bin, a small edit 
on .procmailrc, a new dry run, and bingo. Next I send a similar message from 
my gmail account, and check that I get a reply. Looks like procmail is working.

Now, the dpforge .procmailrc file also had a dppd lock for any mails sent to 
dppd@..., with exactly the same timelimit command and it's body. Being 
efficient, I combine that into one regexp: "* ^To:.*(ukdp|dppd)@", because I 
don't see the need for a second lock file. And as Peter proposes to add a 
judge alias as well, I expand that to "* ^To:.*(ukdp|judge|dppd)@", and add 
these aliases to /etc/aliases:
> sudo vi /etc/aliases
---
# Other aliases
judge: ukdp
dppd: ukdp
---
> sudo newaliases
A test message to judge@uk.diplom.org and dppd@diplom.org confirms that this 
works. DPPD? Now that you mention it, we're still using the USDP DPPD. Setting 
up our own database will be for some other time. Note: the .procmailrc in 
attachment is the modified one for ukdp.

One more thing to do now: Start the cron job.
> crontab -e
---
UKDP=/home/ukdp/ukdp

*/20 * * * * $UKDP/bin/check > $UKDP/log/check.log 2> $UKDP/log/check.err
---
Does it work? Sure it does, because a few minutes later (note that it runs 
every 20 minutes) we receive a late notice for game testing!

That's enough for now. Let's go out and announce the resurrection of UKDP to 
the rest of the world.
"""

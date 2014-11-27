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
This would also be a good time to identify ourselves to Mercurial. Next time
we commit something it will know who the author is. To do this, I added the
following to site-packages/.hg/hgrc:
---
[ui]
username = ukdp <ukdp@uk.diplom.org>
---
There, source downloaded and ready to edit. Now let's set up the judge proper.

Let's start with the structure of the judge folder (that what is not part
of the project). BTW, to distinguish the source and the judge, we use two
environment variables: PKG pointing to the DPjudge source folder (e.g.
~/site-packages/DPjudge, meaning you unpacked the project in a folder
called site-packages), and JDG pointing to the judge root folder (e.g.
~/usdp).

After creating the judge root folder ($JDG), you put in there the following
subfolders:
  bin games log web
and the host.py file, an example of which I'm attaching here. Note that
both dppd and smtpmail are set to None, and that tester is set to '@' to
generate no mail. You will probably want to change that to None and set
smtpmail correctly.

In bin you can put a few simple scripts that call the python files in
$PKG/bin. I'm attaching the most useful one, inspect, for reference. The
rest all follow the same pattern. You will need to make these files
executable.

The games folder simply can start empty. It will be populated by game
folders and a status file when you create games. That status file, which
should be distinguished from the status file inside a particular game
folder, lists every available game, its variant, its status (forming,
active, completed, etc.) and optionally whether it's a private game. A few
lines in the status file for DPFG (our test judge on floc.net):
  pawn standard active
  ae090802 payola completed private
This status file is managed by Status.py.

A typical game folder contains the following files:
  access press results status
and a list of saved status files, one per processed phase that have the
phase attached at the end (e.g. status.S1901M). These are used to rollback
the game, should the necessity arise. Very useful for testing, as you can
now rollback and roll forward any game, diffing the results to see if any
code changes resulted in unexpected differences in the results file. I
think the other file names are pretty self-explanatory: access stores all
logins to the game page, press keeps a copy of all press between the
players, results contains the judge results, and status has the current
game status. It's the status file that you will be most concerned about.

The log folder also starts out empty and will contain various error logs,
which may be of some help, though I mostly ignore them. A useful one is
smtperror.log in case you use smtpmail and are having mail problems.

The web folder contains the following folders:
  images maps
and the file index.cgi, attached here. You will need to replace the path
given in there with the parent folder of $PKG. Note that images can simply
be a soft link to $PKG/web/images. The maps folder will contain all your
game maps (gif, ps, pdf).

If all went well, you should now be able to run inspect. Run
  cd $JDG/bin
  inspect

Now you are in a Python shell with the DPjudge preloaded.
>>>> self = Status().createGame('john@doe.edu', 'testgame', 'test')
should create a game called testgame with the given email address as master
and test as password.

[Continued]

After following my own instructions spelled out above, I copied the inspect 
script in $JDG/bin to check, mail and reopen and altered the last word in
each ("inspect") to the respective script names. I changed the path name in
$JDG/web/index.cgi and then edited $JDG/host.py, replacing path names, urls
and mail addresses as I saw fit. A .vimrc that ensures that tab stops are 4
spaces was added.

Script files in $JDG/bin need to be executable, hence "chmod a+x *". inspect 
turned out to have dos line endings, messing up with the python shebang. Load 
in vi, type ":set ff=unix", then save and quit and repeat that for each script 
file. I ran inspect, and created the test game with the Status.createGame() 
call. So far, so good. Let's not forget to make $JDG/web/index.cgi executable,
otherwise we may run into deep troubles.

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
We now add the apache user to group ukdp:
> sudo usermod -a -G ukdp www-data
The "sudo apachectl graceful" given in the comments there must have applied to 
an older apache installation. Nowadays you restart apache2 as follows:
> sudo /etc/init.d/apache2 restart

To check that ukdp is now running on apache, we start python:
> python
>>> import urllib
>>> response = urllib.urlopen('http://localhost/ukdp')
>>> response.read()
'\n\n\t\t\t<H3>DPjudge Error</H3><p class=bodycopy>\n\t\t\tPlease <a href=mailto:woelpad@gmail.com>e-mail the judgekeeper</a>\n\t\t\tand report how you got this error.  Thank you.\n\t\t\t<!--\n\t\t\t\n  File "/home/ukdp/site-packages/DPjudge/web/index.py", line 5, in handle\n    try: DPjudge.Page(form)\n  File "/home/ukdp/site-packages/DPjudge/Page.py", line 51, in __init__\n    if self.include(): raise SystemExit\n  File "/home/ukdp/site-packages/DPjudge/Page.py", line 90, in include\n    .replace(\'<DPPD>\',\thost.dppdURL)\nTraceback (most recent call last):\n  File "/home/ukdp/site-packages/DPjudge/web/index.py", line 5, in handle\n    try: DPjudge.Page(form)\n  File "/home/ukdp/site-packages/DPjudge/Page.py", line 51, in __init__\n    if self.include(): raise SystemExit\n  File "/home/ukdp/site-packages/DPjudge/Page.py", line 90, in include\n    .replace(\'<DPPD>\',\thost.dppdURL)\nTypeError: expected a character buffer object\n-->\n'
>>>
Right, it doesn't like it that we didn't assign a dppd in host.py. Let's 
change that:
> vi $JDG/host.py
~ dppd            =   'dppd@diplom.org'
~ dppdURL         =   'http://www.floc.net/dpjudge?variant=dppd'

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
> inspect testing 'self.view.makeMaps()'
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
I guess). Just need to copy .procmailrc to the home directory, and replace all
instances of dpjudge and usdp with ukdp, as unlike dpjudge/dpforge ukdp is both
the user name and the judge name.

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
dppd@..., with exactly the same timelimit command and its body. Being 
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

[Continued]

Problems that came up later.

Some mail programs insist on being able to do reverse DNS lookup. To accomplish that, you need to add PTR records. Check the net on how to do that. Basically you have to request your IP-provider to set it up for you. Also, IPv4 and IPv6 use different IP addresses (obviously), so if your site has both, you need Reverse DNS for both. If not, you might end up with "DNS: Service unavailable (dns=5.0.0) in your /var/log/mail.log file. In such cases your mail gets bounced, which gets logged in the daemon.log file we configured previously (that's $JDG/log/daemon.log if you configured it as written here). Check that too for better diagnostics.

After a few players joined the first games, I started receiving "Suspicious activity" emails. This was not because they were on the same network, but because they, and even I, the master, were routed through home.spikings.com when accessing the web page at uk.diplom.org. I decided to create a publicDomains host parameter, move the problematic .aol.com domain names in there, and add .spikings.com to that list. Not entirely satisfactory, so let's look for a real solution.

Game.logAccess() gets its host url from an environment variable called REMOTE_ADDR that Apache fills in. But with a reverse proxy the host gets in the way. To resolve that we need to install a package called mod_rpaf.
> sudo apt-get install libapache2-mod-rpaf
> sudo /etc/init.d/apache2 restart
Log in to a game as GM and check the access file (link at the bottom of the page, above the Submit button).
Still home.spikings.com. Hmm. Right, we need to add the host ip to rpaf's config parameters. To find the ip, we comment out the socket.gethostbyaddr() lines in Game.logAccess() and log in to the web page again. The top of the access log (or bottom of the access file) now shows:
---
Wed Jun 20 01:09:14 2012 2a01:348:1f1:10::1 MASTER     !-MASTER-!
---
Let's add that ip address (never mind that it's in IPv6 format) to the proxy list of rpaf:
> sudo vi /etc/apache2/mods-enabled/rpaf.conf
---
<IfModule mod_rpaf.c>
RPAFenable On
RPAFsethostname On
RPAFproxy_ips 127.0.0.1 2a01:348:1f1:10::1
</IfModule>
---
Restart apache, log in to a game page, check the access log, and presto: The correct host name appears.

New feature: A judgekeeper password to rule all the others. In host.py we now have the option to fill in judgePassword, so that we don't have to look up the Master password to log in to a game on the web or by email, or even to log in to the DPPD to change someone's email address.

To limit the damage if ever this password gets leaked, we can use a little script called scramble to periodically overwrite this password in the host file. Just add this to your crontab:
---
0 0 1 * * $UKDP/bin/scramble -o > $UKDP/log/scramble.log
---
The log file will contain a copy of the password. You can check the date to confirm that the script is running correctly. It should run on midnight on the first day of the month, but you can adapt the parameters to update the password more or less often.

Note that you don't have to assign a judgekeeper password. Omitting the judgePassword line or leaving the value blank in the host file will disable this feature. Just make sure that the scramble script is removed from crontab as well.

Speaking of crontab, here's another improvement I doctored out. The check script checks deadlines every 20 minutes, but once in a while, every day at midnight actually, sends reminders to the GMs of any waiting and forming games. I split up this functionality, so that I can more easily decide how often to send out these reminders.

Let's say I want them to be sent out once a week, on Sunday night. I direct crontab to run 2 check jobs, one for the active games (indicated by -a), and one for reminders (-r).
> crontab -e
---
UKDP=/home/ukdp/ukdp

0 0 * * 0 $UKDP/bin/check -t -r > $UKDP/log/remind.log 2> $UKDP/log/remind.err
*/20 * * * * $UKDP/bin/check -t -a > $UKDP/log/check.log 2> $UKDP/log/check.err
---
Notice that I also chose different log files. If no parameters are fed to the check script, it would operate as before.

The observant reader may have noticed a second flag added to these commands, -t. This flag guards against processing games immediately after a server outage when the server comes back online. This is to prevent that games that went past their deadline during the outage would process before players got the chance to enter orders. It is the judgekeeper's task to extend deadlines first, and then run the check script once without the -t flag to restart the cron jobs.

Remote backup.

After floc.net, the server hosting USDP and DPFG, crashed and stayed down for a couple of days, I decided to back up the game data and even the program data on this server. And vice versa to back up UKDP on floc.net. I chose rsync as the backup application and wrote a script, rbackup, to perform the task. 

Inside rbackup, which is stored in ~/bin, you need to set USR to the current user (ukdp), JDG to the name of the judge (ukdp), choose the target directory in TRG (start with a local directory first), select whether to do a dry-run with DRY (recommended for the first few runs) and enter the correct port number in the -p option inside the --rsh option in the actual rsync command.

Two other files are important, both in the same bin directory. The first is rbackup.files, which lists the directories to include, relative to the user home dir, and rbackup.exclude, which lists the file patterns to exclude. I chose to exclude vim swap files (of course) and game maps, because of their size and because they're relatively easy to regenerate by invoking inspect:
> inspect "<game>.makeMaps()"
If during dry-run you spot other files that are too big and don't need to be backed up, like tar files and older log files, consider to exclude them as well, especially if your remote server file space is limited. This is the case for the ukdp server, and for that reason I have opted to back up only running games from USDP, not completed or terminated games, using a replicate script that I won't explain here. 

To connect to a remote server, rsync, or actually ssh, will ask for a password. To avoid that we need to make a public-private key pair and send the public key to the remote server. The following commands will do the trick:
> ssh-keygen
Generates the key pair. Press Enter on every question.
> ssh-copy-id -i ~/.ssh/id_rsa.pub "mario@floc.net -p 4"
Copies the public key to my home dir on floc.net through port 4. It will ask for your password one last time, after that you won't need to enter it anymore.

Now you're set. Do a couple of dry-runs, which will mimic the operation but not actually copy any file or directory, and when satisfied execute the first backup. Are we finished now? No. The last step is to add it to crontab. To reduce the risk of losing a processed turn, the best timing is to back up right after the check script finishes. This can be done by appending the rbackup call to the check entry, separated by a semicolon.
> crontab -e
---
...
BIN=/home/ukdp/bin
...
*/20 * * * * $UKDP/bin/check -t -a > $UKDP/log/check.log 2> $UKDP/log/check.err; $BIN/rbackup >> $UKDP/log/rbackup.log 2>> $UKDP/log/rbackup.err
...
---

Displaying an icon in the browser tab title.

Ever noticed that USDP has a little image of a cannon displayed in front of the browser tab title? It's called a favicon.

There are two ways of adding it to your web pages, either by adding a link to the header of every web page (flexible, but too cumbersome), or by putting an image file called favicon.ioo in the document root folder of your web site.

For reference the link in the header would look like this:
<link rel="shortcut icon" href="http://uk.diplom.org/favicon.ico">
Add something like "?v=2" if ever you made a change to it and want to force your browser to reload it.

We go with the second method. Where's our document root? That's determined by how you configured Apache. The default Apache root folder is /var/www, which is the one used on USDP. But you need to be root to put a file there. (On UKDP we become root by entering "sudo -s" with the same password as for the ukdp user.)

On UKDP however we set it up better. If we browse to /etc/apache2/sites-available, there's a ukdp configuration file there that sets DocumentRoot to /home/ukdp/ukdp/web. So we just need to copy favicon.ico, conveniently located in $PKG/web, to that location.

Does this immediately reflect in our browser? Unfortunately no, and clearing the browser's cache also doesn't seem to work. What we need to do is to visit the icon itself and do a refresh. In your browser enter "http://uk.diplom.org/favicon.ico", load the image and then press Ctrl+F5. It immediately changes the icons in the title bar for all your UKDP tabs.

---

After upgrading to Python 2.7 I could no longer run hg. An error message appeared telling that mercurial was not in the install path or PYTHONPATH. I did a find to confirm that mercurial was only located under python2.6.

To fix this I purged and reinstalled mercurial.
> sudo apt-get purge --remove mercurial
> sudo apt-get autoremove
> sudo apt-get install mercurial
This did not place a mercurial folder or link in python2.7, but somehow the problem was solved.
> find / -name mercurial -print
...
/usr/lib/pyshared/python2.6/mercurial
/usr/lib/pymodules/python2.6/mercurial
...

---

Again a chilling surprise today. On visiting http://uk.diplom.org/maps I could see a directory list of all game maps. Imagine playing a blind game and knowing that you can simply download the maps for every player, including the master. That's simply not acceptable!

After searching on the Internet and comparing with USDP, I browsed through this setup file and noticed the extra configuration files I had created, in particular /etc/apache2/sites-available/ukdp. I knew that Options Indexes was the likely culprit, and finally I found a file that had it set. I put a "-" in front of Indexes and restarted the apache2 service. Now this server too displays a "No permission" error page.
"""

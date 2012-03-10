"""
The tools/ directory does NOT contain any Python subpackage code.

Rather, this directory will be populated by the package installer.
It will be populated with copies of (or, preferably, softlinks to)
the following files:
From package ghostscript (in /usr/bin):
	gs
	ps2pdf
From package psutils (in /usr/bin):
	psselect
From package netpbm (in /usr/bin):
	pnmcrop
	pnmcut
	pnmflip
	ppmtogif
From package sendmail (in /usr/sbin):
	sendmail
On system installation (in /usr/share/zoneinfo):
	zone.tab

The first seven of these are public-domain executable imaging tools
used in map-making.

The sendmail will only be used by any DPjudge instances that are
configured to NOT use an SMTP server to send email.

The zone.tab file must be in place, even if it built by the package
installer (for example, to contain only specific timezones).  It must
be in the standard format for such files, as it is parsed and its
data displayed to the user and passed to os.putenv('TZ').
"""

This /tools directory will be populated by the package installer.
It must be populated with copies of (or, preferably, softlinks to)
the following files:
	gs
	pnmcrop
	pnmcut
	pnmflip
	ppmtogif
	ps2pdf
	psselect
	sendmail
	zone.tab

The first seven files listed above are public domain imaging utility
executables that are used by map-making.

The sendmail executable is not used except by DPjudge instances that
choose NOT to send email via an SMTP server.

The zone.tab file must be present to provide a list of at least one
timezone,  according to the usual format of that file -- even if the
file is built during package install, rather than softlinked-to.
The file must be in standard zone.tab format, as its data will be
parsed and passed to os.putenv('TZ').
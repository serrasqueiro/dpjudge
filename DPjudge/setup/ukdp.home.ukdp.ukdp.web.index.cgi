#!/usr/bin/python -O
# -*- coding: latin-1 -*-

import traceback, os
os.sys.path.insert(0, '/home/ukdp/site-packages')

try: import DPjudge.web
except:
	print 'Content-type: text/html\n\n'
#	print """
#            <H3>DPjudge Error</H3><p class=bodycopy>
#            Please <a href=mailto:%s>e-mail the judgekeeper</a>
#            and report how you got this error.  Thank you.
#            """ % DPjudge.host.judgekeeper
	traceback.print_tb(os.sys.exc_traceback, None, os.sys.stdout)
	traceback.print_exc(None, os.sys.stdout)


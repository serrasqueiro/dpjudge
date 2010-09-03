import os

def handle(form):
	import DPjudge
	try: DPjudge.Page(form)
	except SystemExit: pass
	except:
		import traceback
		print """
			<H3>DPjudge Error</H3><p class=bodycopy>
			Please <a href=mailto:%s>e-mail the judgekeeper</a>
			and report how you got this error.  Thank you.
			<!--
			""" % DPjudge.host.judgekeeper
		traceback.print_tb(os.sys.exc_traceback, None, os.sys.stdout)
		traceback.print_exc(None, os.sys.stdout)
		print '-->'

#	------------------------------------------------------------------
#	Entry function for installations using Apache's mod_python package
#	------------------------------------------------------------------
def handler(req):
	from mod_python import apache, util
	import urllib
	os.chdir(os.path.dirname(req.filename))
	os.sys.stdout, req.content_type = req, 'text/html'
	req.send_http_header()
	os.environ, form, mod = req.subprocess_env, {}, util.FieldStorage(req)
	for key in mod.keys(): form[key] = mod[key]
	os.environ['REMOTE_ADDR'] = req.connection.remote_ip
	handle(form)
	return apache.OK

try:
	if not os.environ['GATEWAY_INTERFACE']: raise
	import cgi
	form = cgi.FieldStorage()
	form.get = form.getvalue
	print 'Content-type: text/html\n'
	handle(form)
except: pass

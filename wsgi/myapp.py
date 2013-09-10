# -*- coding: utf-8 -*-
from cgi import parse_qs, escape

# this is to ensure we are able to import packages and the like
import os
import sys
current_dir = os.path.dirname(__file__)
sys.path.append(current_dir)
sys.path.append(os.path.join(current_dir, "src"))

from router import *
from logger import Logger

def application(environ, startResponse):
	# we need the ability to do some logging, I think
	Logger.init(environ["wsgi.errors"], S.LOG_LEVEL)
		
	router = Router(environ)
	try:
		resp = router.route()
	except Exception, e:
		import traceback
		exc_type, exc_value, exc_traceback = sys.exc_info()
		output = "Exception raised: %s" % e
		output = output + repr(traceback.format_tb(exc_traceback))
		print >> environ['wsgi.errors'], output
		resp = ErrorRouteResponse(output) 
	
	startResponse(resp.getStatus(), resp.getHeaders())

	return [resp.getContent()]

if __name__ == "__main__":
	from wsgiref.simple_server import make_server
	srv = make_server('localhost', 8080, application)
	srv.serve_forever()

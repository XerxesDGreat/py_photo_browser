import re
import os
import controller

from cgi import parse_qs, escape
from logger import Logger
from settings import Settings as S
from template import Template
from util import underscore_to_camel_case
from jinja2 import Environment, FileSystemLoader

class Router:
	def __init__(self, environ):
		self._environ = environ

	def route (self):
		path = self._environ.get('PATH_INFO', '').lstrip('/')
		_, ext = os.path.splitext(path)
		response = None
		Logger.debug(path)
		for regex, callback in S.ROUTES:
			Logger.debug(regex)
			match = re.search(regex, path)
			if match is not None:
				Logger.debug("matched %s" % regex)
				self._environ['myapp.url_args'] = match.groups()
				response = self._success(callback)#, ext.lstrip("."))
				break

		if response == None:
			response = self._notfound()

		return response;

	
	def _success (self, callback):#, filetype):
		parts = callback.split('.', 2)
	
		if len(parts) == 2:
			controller_str = parts[0]
			action_str = parts[1]
		elif len(parts) == 1:
			controller_str = parts[0]
			action_str = "default"
		else:
			raise RuntimeError('invalid route set up: ' + callback)

		controller_name = underscore_to_camel_case(controller_str) + "Controller"

		controller_obj = getattr(controller, controller_name)(self._environ, RouteResponse)
		resp = getattr(controller_obj, action_str)()

		addl_headers = []

		headers = [("Content-type", resp["file_type"])] + addl_headers
		return RouteResponse.ok(resp["content"], headers)

	def _notfound (self):
		return RouteResponse.missing(Template.render("404.html"))

class RouteResponse:
	STATUS_OK = "200 OK"
	STATUS_404 = "404 NOT FOUND"

	HTML_CONTENT_TYPE = "text/html; charset=utf8"
	CSS_CONTENT_TYPE = "text/css; charset=utf8"
	JPEG_CONTENT_TYPE = "image/jpg;"
	JSON_CONTENT_TYPE = "application/json;"
	
	UTF_CONTENT_TYPES = [HTML_CONTENT_TYPE, CSS_CONTENT_TYPE]

	def __init__ (self, status, content, headers):
		self._status = status
		self._headers = headers
		self._content = content
		
		lenHeader = ("Content-Length", str(len(self._content)))
		self._headers.append(lenHeader)
		Logger.debug("added another header")
	
	@staticmethod
	def ok(content, headers):
		return RouteResponse(RouteResponse.STATUS_OK, content, headers)

	@staticmethod
	def missing(content):
		headers = [("Content-Length", RouteResponse.HTML_CONTENT_TYPE)]
		return RouteResponse(RouteResponse.STATUS_404, content, headers)

	def getStatus (self):
		return self._status
	
	def getHeaders (self):
		return self._headers
	
	def getContent (self):
		for h in self._headers:
			Logger.debug("Header in getContent: %s" % str(h))
			if h[0] == "Content-type" and h[1] in RouteResponse.UTF_CONTENT_TYPES:
				Logger.debug("getContent hello")
				return self._content.encode("utf-8")
		return self._content

class ErrorRouteResponse(RouteResponse):
	def __init__ (self, errorText):
		content = "There was an error encountered: " + errorText
		status = RouteResponse.STATUS_OK
		headers = [("Content-Length", RouteResponse.HTML_CONTENT_TYPE)]
		RouteResponse.__init__(self, status, content, headers)

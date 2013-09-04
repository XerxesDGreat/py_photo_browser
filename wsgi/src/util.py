from cgi import parse_qs, escape
from logger import Logger
from settings import Settings as S

import math
import os
import hashlib

def underscore_to_camel_case (str):
	return str.title().replace('_', '')

def make_file_hash(path):
	h = hashlib.sha1()
	f = open(path)
	h.update(f.read())
	f.close()
	return h.hexdigest()

def get_thumb_name(path):
	dirname, filename = os.path.split(path)
	filebase, ext = os.path.splitext(filename)
	return "%s.%s.%s" % (filebase, make_file_hash(path), ext.lstrip(".").lower())

def is_image_file(file_name):
	"""
	Determines whether the given file_name seems to be one of the
	supported image file types.
	"""
	_, ext = os.path.splitext(file_name)
	return ext.lstrip(".").lower() in S.SUPPORTED_IMG_EXTENSIONS

class Paginator:
	"""
	Creates pages from a given list
	"""
	def __init__(self, env, list):
		self.env = env
		args = parse_qs(env.get("QUERY_STRING", ""))
		self.list = list
		self.cur_page = 0
		if "page" in args:
			self.cur_page = int(escape(args["page"][0]))

		self.limit = S.DEFAULT_PER_PAGE
		if "limit" in args:
			self.limit = int(escape(args["limit"][0]))
	
	@property
	def page_contents(self):
		"""
		Fetches contents of the current page
		"""
		start = self.cur_page * self.limit
		end = start + self.limit


		if start < 0 or start > len(self.list) or end < 0:
			raise IndexError("start and end must be valid indeces of list; start=%d end=%d list_len=%d" % (start, end, len(self.list)))

		if start > end:
			raise ValueError("start must be less than end; start=%d end=%d" % (start, end))

		if end >= len(self.list):
			end = len(self.list)

		a = self.next_page if self.next_page != None else -1
		b = self.prev_page if self.prev_page != None else -1
		c = self.num_pages if self.num_pages != None else -1
		Logger.debug("num_pages: %s, next_page: %s, next_page_url: %s, prev_page: %s, prev_page_url: %s" % (c, a, self.next_page_url, b, self.prev_page_url))
		
		Logger.debug("start: %d, end: %d" % (start, end))

		return self.list[start:end]
	
	@property
	def num_pages(self):
		"""
		Fetches the number of pages the list will contain
		"""
		return math.ceil(len(self.list) / float(self.limit))

	@property
	def next_page(self):
		"""
		Fetches the next page number
		"""
		if ((self.cur_page + 1) * self.limit) > len(self.list):
			return None
		return self.cur_page + 1
	
	@property
	def next_page_url(self):
		"""
		Fetches a url for the next page
		"""
		return self._build_page_url(self.next_page) 
	
	@property
	def prev_page(self):
		"""
		Fetches the previous page number
		"""
		if self.cur_page == 0:
			return None
		return self.cur_page - 1
	
	@property
	def prev_page_url(self):
		"""
		Fetches a url for the previous page
		"""
		return self._build_page_url(self.prev_page) 
	
	def _build_page_url(self, page):
		"""
		Builds a page url
		"""
		Logger.debug(self.env.get("PATH_INFO", "").lstrip("/"))
		if page == None:
			return None
		return "%s/%s?page=%d" % (S.BASE_URL, self.env.get("PATH_INFO", "").lstrip("/"), page)

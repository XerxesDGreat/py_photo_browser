from logger import Logger
from template import Template
from settings import Settings as S
from model import Photo
from cgi import parse_qs

import glob
import json
import urllib
import os
import re
import math
import Image
import base64
import util

class BaseController:
	_env = None

	def __init__ (self, env):
		self._env = env
	
	def default (self):
		raise NotImplementedError('Child classes must define a default action')
	
class IndexController(BaseController):
	"""
	Controller for the main, top-level app pages
	"""
	def default(self):
		"""
		Renders the main page
		"""
		return Template.render("index.html")

class StatsController(BaseController):
	def default(self):
		stats = []

		# get all the thumbnails
		stats.extend(self._thumb_info(Photo.SMALL_THUMB_SIZE))
		stats.extend(self._thumb_info(Photo.MEDIUM_THUMB_SIZE))

		with open(S.MARK_FILE) as f:
			for i, l in enumerate(f):
				pass
		stats.append(("Number of marked files", (i + 1), "raw"))

		num_images = 0
		for root, dirs, files in os.walk(S.BASE_FS_PATH):
			for f in files:
				if util.is_image_file(f):
					num_images += 1
		stats.append(("Number of source images", num_images, "raw"))

		return Template.render("stats.html", {"stats": stats})
	
	def _thumb_info(self, size):
		ret = []
		size_string = "%sx%s" % size
		globbed_thumbs = glob.glob(os.path.join(S.THUMBNAIL_DIR, size_string, "*"))
		ret.append(("Thumbnail count (%s)" % size_string, len(globbed_thumbs), "raw"))

		total_size = 0
		for f in globbed_thumbs:
			Logger.debug("file: %s; size: %s" % (f, str(os.path.getsize(f))))
			total_size += os.path.getsize(f)
		ret.append(("Thumbnail disk usage (%s)" % size_string, total_size, "bytes"))
		return ret
		

class PhotoController(BaseController):
	def default(self):
		"""
		Performs default controller action. Basically, makes a list of files/folders.
		"""
		path = self._env.get('PATH_INFO', '').lstrip('/')
		file_path = os.path.join(S.BASE_FS_PATH, os.path.relpath(path, "photos"))
		if not os.path.exists(file_path):
			return "404"
		dir_info = []
		all_file_info = []
		p = None
		for current_dir, dirs, files in os.walk(file_path):
			for d in dirs:
				dir_info.append({
					"path": os.path.join(current_dir, d),
					"friendly_name": d,
					"url": "%s/%s" % (S.BASE_URL, os.path.join(path, d))
				})
			files.sort()
			# optimization: alter the paginator to only construct objects for the
			# items which end up on the indicated page, possibly by passing in
			# a pointer to the constructor of Photo
			for f in files:
				if not util.is_image_file(f):
					continue
				all_file_info.append(Photo(os.path.join(current_dir, f)))
			p = util.Paginator(self._env, all_file_info)
			break
		tokens = {
			"dirs": dir_info,
			"paginator": p,
			"current_path": path.rstrip("/"),
			"path_links": self.__get_path_links(path),
			"med_thumb_size": Photo.MEDIUM_THUMB_SIZE
		}
		Logger.debug(str(tokens["path_links"]))
		return Template.render("photos.html", tokens)
	
	def get_marked_photos(self):
		"""
		Renders a list of marked files
		"""
		f = open(S.MARK_FILE)
		photos = []
		for line in f:
			photos.append(Photo(line.rstrip()))
		f.close()
		return Template.render("mark.html", {"photos": photos})
	
	def get_one(self):
		path = self._env.get('PATH_INFO', '').lstrip('/')
		photo_id = os.path.relpath(path, "photos/get_single")
		# testing
		photo_id = 1
		a = Photo.get_by_id(photo_id)
		return str(a)
		
		
	def update_mark(self):
		"""
		Handles the AJAX calls from the app mark actions
		"""
		input = parse_qs(self._env["wsgi.input"].read())
		required = ["marked", "file"]
		valid = True
		for r in required:
			if r not in input or len(input[r]) != 1:
				valid = False
		if not valid:
			return json.dumps({"success": False, "error": "Not enough args", "details": input})

		fname = urllib.unquote(input["file"][0])
		mark = True if input["marked"][0] == "true" else False
		if mark:
			f = open(S.MARK_FILE, "a+")
			f.write("%s\n" % fname)
			f.close()
		else:
			rex = re.compile(r"^%s$" % fname)
			f = open(S.MARK_FILE)
			keep = []
			Logger.debug("fname: %s" % fname)
			i = 0
			for line in f:
				i += 1
				Logger.debug("line: %s" % line)
				if not rex.match(line):
					Logger.debug("no match")
					keep.append(line)
			f.close()
			Logger.debug("total lines: %d, lines to keep: %d" % (i, len(keep)))
			f = open(S.MARK_FILE, "w+")
			f.writelines(keep)
			f.close()
		return json.dumps({
				"success": True,
				"details": {
					"marked": mark,
					"file": fname
				}
			})
	
	def get_large_image(self):
		path = os.path.relpath(self._env.get('PATH_INFO', '').lstrip('/'), "photos/big/")
		Logger.debug(path)
		file_path = os.path.join(S.BASE_FS_PATH, path)
		Logger.debug(file_path)
		if not os.path.exists(file_path):
			return "404"

		p = Photo(file_path)
		rel_thumb_path = p.get_or_create_thumb(Photo.MEDIUM_THUMB_SIZE)
		f = open(os.path.join(S.THUMBNAIL_DIR, rel_thumb_path))
		raw_image = f.read()
		f.close()
		return raw_image

	
	def __get_path_links(self, path):
		"""
		Fetches a list of path links for the provided path.

		This is currently hardcoded, which is not ideal.
		"""
		link_set = []
		cur_link = os.path.join("/")
		#rel_path = os.path.relpath(path, "photos")
		path_parts = path.split("/")
		for p in path_parts:
			if p in ("", "."):
				continue
			cur_link = os.path.join(cur_link, p)
			link_set.append((urllib.quote(cur_link), p))
		return link_set
	
class CssController(BaseController):
	def default(self):
		path = os.path.join("css",os.path.relpath(self._env.get("PATH_INFO"), "css"))
		return Template.render(path)

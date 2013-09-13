from logger import Logger
from template import Template
from settings import Settings as S
from model import Photo
from cgi import parse_qs, escape

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
	def __init__ (self, env, route_types):
		self._env = env
		self._route_types = route_types
	
	def default (self):
		raise NotImplementedError('Child classes must define a default action')

	def construct_response(self, response_str, file_type=None):
		return {
			"content": response_str,
			"file_type": self._route_types.HTML_CONTENT_TYPE if file_type == None else file_type
		}

	
class IndexController(BaseController):
	"""
	Controller for the main, top-level app pages
	"""
	def default(self):
		"""
		Renders the main page
		"""
		return self.construct_response(Template.render("index.html"))

class StatsController(BaseController):
	def default(self):
		stats = {}

		# get all the thumbnails
		stats["Database stats"] = [
			("Number of marked files", Photo.get_num_marked_photos(), "raw"),
			("Number of DB files", Photo.get_count_by_date(), "raw")
		]

		stats["File System stats"] = []
		for s in [Photo.SMALL_THUMB_SIZE, Photo.MEDIUM_THUMB_SIZE]:
			stats["File System stats"].extend(self._thumb_info(s))
			
		num_images = 0
		total_size = 0
		for root, dirs, files in os.walk(S.BASE_FS_PATH):
			for f in files:
				if util.is_image_file(f):
					num_images += 1
					total_size += os.path.getsize(os.path.join(root, f))
		stats["File System stats"].extend([
			("Number of source images", num_images, "raw"),
			("Disk space", total_size, "bytes")
		])

		Logger.debug(str(stats.keys()))
		return self.construct_response(Template.render("stats.html", {"stats": stats}))
	
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
	def get_dirs_from_date(self):
		"""
		Renders a list of all the year "folders" in the system.

		As we're not rendering any photos, we can assume this to be a separate
		function from the photo fetching and rendering; this is just reporting
		certain dates.
		"""
		path = self._env.get('PATH_INFO', '').lstrip('/')
		path = os.path.relpath(path, "photos")
		Logger.debug(path)
		path_parts = path.split(os.sep)
		Logger.debug(path_parts)
		if len(path_parts) == 1 and path_parts[0] == ".":
			path_parts = []
		Logger.debug(path_parts)

		year = None if len(path_parts) < 1 else path_parts[0]
		month = None if len(path_parts) < 2 else path_parts[1]
		list = Photo.get_all_dates(year=year, month=month)

		list = [("0%d" % f if f < 10 else str(f)) for f in list]
		list.sort()
		tokens = {
			"dirs": list,
			"year": year,
			"month": month
		}
		Logger.debug(list)
		return self.construct_response(Template.render("photos/dirs.html", tokens))
	
	def get_photos_from_date(self):
		"""
		Fetches a list of photos which apply to the given filter

		This function should be able to handle listing directories (for instance,
		month directories in the year or days in each month) as well as actually
		rendering photos.
		"""
		year, month, day = self._get_id_from_path("").split(os.sep)

		offset = self._get_from_query("page", 1) - 1
		limit = self._get_from_query("limit", S.DEFAULT_PER_PAGE)

		num_photos = Photo.get_count_by_date(year=year, month=month, day=day)
		start_index = (offset * limit) + 1
		end_index = min(((offset + 1) * limit), num_photos)
		Logger.debug("num_photos: %d, start_index: %d, end_index: %d" % (num_photos, start_index, end_index))

		photos = Photo.get_by_date(year=year, month=month, day=day, limit=limit,
			offset=(offset * limit))
		Logger.debug("first: %d, last: %d" % (photos[0].id, photos[-1].id))
		Logger.debug("num_photos_fetched: %d" % len(photos))
		tokens = {
			"photos": photos,
			"offset": offset,
			"limit": limit,
			"start_index": start_index,
			"end_index": end_index,
			"num_photos": num_photos
		}
		return self.construct_response(Template.render("photos/list.html", tokens))
	
	def get_large_image(self):
		"""
		Fetches the large image for lightboxing for the given photo id. Returns
		the image raw data.
		"""
		id = self._get_id_from_path("big")
		p = Photo.get_by_id(id)
		if p == None:
			return "404"
		rel_thumb_path = p.get_or_create_thumb(Photo.MEDIUM_THUMB_SIZE)
		f = open(os.path.join(S.THUMBNAIL_DIR, rel_thumb_path))
		Logger.debug(rel_thumb_path)
		raw_image = f.read()
		f.close()
		return self.construct_response(raw_image, self._route_types.JPEG_CONTENT_TYPE)
	
	def get_one(self):
		"""
		Fetches and returns raw data for a single photo
		"""
		self._get_id_from_path("single")
		a = Photo.get_by_id(id)
		return self.construct_response()
		
	def get_marked_photos(self):
		"""
		Renders a list of marked files
		"""
		offset = self._get_from_query("page", 1) - 1
		limit = self._get_from_query("limit", S.DEFAULT_PER_PAGE)
		photos = Photo.get_marked()
		num_photos = len(photos) 
		start_index = (offset * limit) + 1
		end_index = num_photos
		tokens = {
			"photos": photos,
			"offset": offset,
			"limit": limit,
			"start_index": start_index,
			"end_index": end_index,
			"num_photos": num_photos
		}
		return self.construct_response(Template.render("photos/mark.html", tokens))

	def mark_photo(self):
		"""
		Wrapper for mark updating function
		"""
		return self._update_mark(True)

	def unmark_photo(self):
		"""
		Wrapper for mark updating function
		"""
		return self._update_mark(False)
	
	def _update_mark(self, marked):
		"""
		Handles the AJAX calls from the app mark actions
		"""
		post_args = parse_qs(self._env["wsgi.input"].read())
		if "id" not in post_args:
			Logger.debug("not in post args: %s" % str(post_args))
			return self.construct_response(json.dumps({
				"success": False,
				"error": "missing args",
				"id": None
			}), self._route_types.JSON_CONTENT_TYPE)

		post_ids = post_args["id"]
		_, id = post_ids[0].split("_")
		p = Photo.get_by_id(id)
		if p == None:
			Logger.debug("no photo retrieved")
			return self.construct_response(json.dumps({
				"success": False,
				"error": "invalid_id",
				"id": id
			}), self._route_types.JSON_CONTENT_TYPE)

		p.marked = marked
		p.store()
		a = self.construct_response(json.dumps({
				"success": True,
				"details": {
					"marked": p.marked,
					"id": id
				}
			}), self._route_types.JSON_CONTENT_TYPE)
		Logger.debug(a)
		return a
	
	def _get_id_from_path(self, command):
		"""
		Fetches the identifying info from the given path 
		"""
		path = self._env.get('PATH_INFO', '').lstrip('/')
		return os.path.relpath(path, "photos/%s" % command)

	def _get_from_query(self, key, default=None):
		"""
		Fetches key from the query values, GET overriding POST
		"""
		get = parse_qs(self._env.get("QUERY_STRING", ""))
		if key in get:
			return get[key]
		post = parse_qs(self._env["wsgi.input"].read())
		if key in post:
			return post[key]
		return default
	
	def _get_path_links(self, path):
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
	
	def _get_photos_from_dir(self, path):
		dir_info = []
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
		return (dir_info, p)
	
class CssController(BaseController):
	def default(self):
		path = os.path.join("css",os.path.relpath(self._env.get("PATH_INFO"), "css"))
		return self.construct_response(Template.render(path), self._route_types.CSS_CONTENT_TYPE)

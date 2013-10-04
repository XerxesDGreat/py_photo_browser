from logger import Logger
from template import Template
from settings import Settings as S
from model import Photo
from cgi import parse_qs, escape
from operator import itemgetter

import glob
import json
import urllib
import os
import re
import math
import Image
import base64
import util
import time
import hashlib
import jsonpickle

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
	"""
	Controller for creating a report of usage and count statistics
	"""
	def default(self):
		"""
		Default action fetches all the stats and renders a template using them
		"""
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

		return self.construct_response(Template.render("stats.html", {"stats": stats}))
	
	def _thumb_info(self, size):
		"""
		Fetches information about a particular size of thumbnails
		"""
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
	"""
	Controller for fetching, assembling, and causing to be rendered requests
	which have to do with displaying and updating photos
	"""
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
		if len(path_parts) == 1 and path_parts[0] == ".":
			path_parts = []

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

		photos = Photo.get_by_date(year=year, month=month, day=day, limit=limit,
			offset=(offset * limit))
		tokens = {
			"photos": photos,
			"offset": offset,
			"limit": limit,
			"start_index": start_index,
			"end_index": end_index,
			"num_photos": num_photos
		}
		return self.construct_response(Template.render("photos/list.html", tokens))
	
	def get_small_image(self):
		return self._get_image(Photo.SMALL_THUMB_SIZE, "small")
	
	def get_large_image(self):
		return self._get_image(Photo.MEDIUM_THUMB_SIZE, "big")
	
	def _get_image(self, size, action):
		"""
		Fetches the large image for lightboxing for the given photo id. Returns
		the image raw data.
		"""
		id = self._get_id_from_path(action)
		try:
			id = int(id)
			p = Photo.get_by_id(id)
		except Exception as e:
			p = None

		if p == None:
			fc = util.FileContainer(os.path.join(S.IMPORT_DIR, id), S.IMPORT_DIR)
			fc.time = util.get_time(fc)["time"]
			p = Photo.from_file_container(fc)

		if p == None:
			Logger.warning("could not find photo for %s" % id)
			image_path = S.BROKEN_IMG_PATH
		else:
			rel_thumb_path = p.get_or_create_thumb(size)
			image_path = os.path.join(S.THUMBNAIL_DIR, rel_thumb_path)

		f = open(image_path)
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
			Logger.warning("not in post args: %s" % str(post_args))
			return self.construct_response(json.dumps({
				"success": False,
				"error": "missing args",
				"id": None
			}), self._route_types.JSON_CONTENT_TYPE)

		post_ids = post_args["id"]
		_, id = post_ids[0].split("_")
		p = Photo.get_by_id(id)
		if p == None:
			Logger.warning("no photo retrieved")
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

class ImportController(BaseController):
	"""
	Controller for handling import commands and logic
	"""
	def default(self):
		"""
		Fetches a list of directories, files, or some combination thereof which
		need to be imported. The specific path is assumed from the PATH_INFO
		provided by self._env
		"""
		rel_import_dir = os.path.relpath(self._env.get("PATH_INFO", "").lstrip("/"), "import")
		dir_to_show = os.path.join(S.IMPORT_DIR, rel_import_dir)
		file_listing = []
		dir_listing = []
		get_details = True
		total_files = 0
		for base_dir, dirs, files in os.walk(dir_to_show):
			if get_details:
				for d in dirs:
					dir_listing.append({
						"rel_path": os.path.relpath(os.path.join(base_dir, d), S.IMPORT_DIR),
						"friendly_name": d
					})
				dir_listing = sorted(dir_listing, key=itemgetter("friendly_name"))
			for f in files:
				if not util.is_image_file(f):
					continue
				total_files += 1
				if not get_details:
					continue
				fc = util.FileContainer(os.path.join(base_dir, f), base_dir)
				time_resp = util.get_time(fc, allow_date_from_path=False)
				if time_resp["time"] != None:
					fc.time = time.strftime(util.EXIF_DATE_FORMAT, time_resp["time"])
				file_listing.append(fc)
			get_details = False

		file_listing = sorted(file_listing, key=itemgetter('name'))

		return self.construct_response(
			Template.render("import/listing.html", {
				"dirs": dir_listing,
				"files": file_listing,
				"total_files": total_files,
				"current_dir": rel_import_dir
			})
			, self._route_types.HTML_CONTENT_TYPE
		)
	
	def preview(self):
		"""
		Presents a preview of the files to be imported, giving the user an
		opportunity to view and change dates for images, highlighting images
		which may already be in the system, and the like.
		"""
		rel_import_dir = os.path.relpath(self._env.get("PATH_INFO", "").lstrip("/"), "import/preview")
		import_dir = os.path.realpath(os.path.join(S.IMPORT_DIR, rel_import_dir))
		file_listing = []
		import_identifier = hashlib.sha1()
		hashes = []
		session_file_struct = {}
		for base_dir, _, files in os.walk(import_dir):
			for f in files:
				if not util.is_image_file(f):
					continue
				fc = util.FileContainer(os.path.join(import_dir, f), S.IMPORT_DIR)
				ts = util.get_time(fc, allow_date_from_path=False)
				if ts["time"] != None:
					fc.time = time.strftime("%Y-%m-%d %H:%M:%S", ts["time"])
				hashes.append(fc.hash)
				import_identifier.update(fc.hash)
				file_listing.append(fc)
				session_file_struct[fc.hash] = {
					"file_data": fc.__dict__(),
					"conflicts": None
				}
			break
		file_listing = sorted(file_listing, key=itemgetter('name'))
		conflicts = Photo.get_by_hash(hashes)

		for conflict_hash in conflicts.keys():
			conflicts_for_json = [c.id for c in conflicts[conflict_hash]]
			session_file_struct[conflict_hash]["conflicts"] = conflicts_for_json
			session_file_struct[conflict_hash]["file_data"]["marked"] = True
			Logger.debug(session_file_struct)

		session_id = import_identifier.hexdigest()
		session_data = {
			"file_listing": session_file_struct,
			"rel_dir": rel_import_dir,
			"session_id": session_id
		}
		with open(os.path.join("/tmp", "%s.txt" % session_id), "w+") as f:
			f.write(json.dumps(session_data))

		return self.construct_response(
			Template.render(
				"import/preview.html",
				{
					"files": file_listing,
					"import_id": session_id,
					"import_dir": rel_import_dir,
					"conflicts": conflicts
				}
			),
			self._route_types.HTML_CONTENT_TYPE
		)

	def update_and_confirm(self):
		post_args = parse_qs(self._env["wsgi.input"].read())
		if "import_id" not in post_args.keys():
			raise Exception("need valid import_id")

		session_data = None
		session_id = post_args["import_id"][0]
		session_file_path = os.path.join("/tmp", "%s.txt" % session_id)
		with open(session_file_path, "r") as handle:
			session_data = json.loads(handle.read())

		delete_hashes = post_args["delete"] if "delete" in post_args.keys() else []
		file_listing = []
		conflicts = {}
		for file_hash in session_data["file_listing"].keys():
			file_data = session_data["file_listing"][file_hash]
			fc = util.FileContainer.from_dict(file_data["file_data"])
			if file_hash in delete_hashes: 
				fc.marked = True
			if "time_%s" % file_hash in post_args.keys():
				time_val = post_args["time_%s" % file_hash][0]
				fc.time = None if time_val == "None" else time_val
			session_data["file_listing"][file_hash]["file_data"] = fc.__dict__()
			file_listing.append(fc)
			if file_data["conflicts"] != None:
				conflicts[file_hash] = file_data["conflicts"]

		file_listing = sorted(file_listing, key=itemgetter('name'))
		
		with open(session_file_path, "w+") as handle:
			handle.write(json.dumps(session_data))

		return self.construct_response(
			Template.render(
				"import/confirm.html",
				{
					"files": file_listing,
					"import_id": session_id,
					"import_dir": session_data["rel_dir"],
					"conflicts": conflicts
				}
			),
			self._route_types.HTML_CONTENT_TYPE
		)

	def execute_import(self):
		"""
		Performs the actual import, taking information from the session file and
		applying the settings/whatever to the various images in the import dir
		"""
		post_args = parse_qs(self._env["wsgi.input"].read())
		if "import_id" not in post_args.keys():
			raise Exception("need valid import_id")

		session_data = None
		session_id = post_args["import_id"][0]
		session_file_path = os.path.join("/tmp", "%s.txt" % session_id)
		with open(session_file_path, "r") as handle:
			session_data = json.loads(handle.read())
		import_dir = os.path.join(S.IMPORT_DIR, session_data["rel_dir"])
		success_results = []
		deleted_results = []
		failed_results = []
		for file_hash in session_data["file_listing"].keys():
			file_data = session_data["file_listing"][file_hash]
			fc = util.FileContainer.from_dict(file_data["file_data"])
			result = {
				"filename": fc.name,
				"from": fc.rel_path
			}
			try:
				if fc.marked:
					to_remove = fc.file_path
					fc.destroy()
					Logger.info("not importing %s because it is marked" % to_remove)
					os.remove(to_remove)
					result["to"] = "deleted"
					result["id"] = None
					deleted_results.append(result)
				else:
					p = Photo.from_file_container(fc)
					p.move_file(src_dir=p.path, copy=False)
					p.get_or_create_thumb(Photo.SMALL_THUMB_SIZE)
					p.get_or_create_thumb(Photo.MEDIUM_THUMB_SIZE)
					p.store()
					result["id"] = p.id
					result["to"] = p.rel_path
					success_results.append(result)
			except Exception, e:
				result["error"] = str(e)
				Logger.error("was not able to do something: %s" % str(e))
				failed_results.append(result)

		success_results = sorted(success_results, key=itemgetter('filename'))
		failed_results = sorted(failed_results, key=itemgetter("filename"))
		deleted_results = sorted(deleted_results, key=itemgetter("filename"))
		
		# when all is done, clean up
		Logger.debug("removing %s" % session_file_path)
		os.remove(session_file_path)
		if len(os.listdir(import_dir)) == 0:
			os.rmdir(import_dir)

		return self.construct_response(
			Template.render(
				"import/execute.html",
				{
					"success_results": success_results,
					"failed_results": failed_results,
					"deleted_results": deleted_results,
					"import_id": session_id
				}
			),
			self._route_types.HTML_CONTENT_TYPE
		)
	
	def get_progress(self):
		pass
	
class CssController(BaseController):
	"""
	Controller for rendering css templates since I want to be able to use tokens
	in the css documents
	"""
	def default(self):
		"""
		Performs all rendering actions
		"""
		path = os.path.join("css",os.path.relpath(self._env.get("PATH_INFO"), "css"))
		return self.construct_response(Template.render(path), self._route_types.CSS_CONTENT_TYPE)

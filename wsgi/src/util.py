from cgi import parse_qs, escape
from logger import Logger
from settings import Settings as S

import math
import os
import hashlib
import exifread
import Image
import time

IMAGE_ORIENTATION_TAGNAME = "Image Orientation"
STOP_TAG_NAME = "Orientation"
ORIENTATION_KEY = 0x0112;
BK_DATE_FIELD = "Image DateTime"
DATE_FIELD = "EXIF DateTimeOriginal"
EXIF_DATE_FORMAT = "%Y:%m:%d %H:%M:%S"
EMPTY_DATE = "0000:00:00 00:00:00"

ROTATION_VALUES = {
	exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][3]: 180,
	exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][4]: 180,
	exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][5]: 270,
	exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][6]: 270,
	exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][7]: 90,
	exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][8]: 90
}

class FileContainer(object):
	"""
	Handy wrapper for all sorts of interesting information about a photo. Meant
	to be a stand-in for a full-blown Photo object
	"""
	def __init__(self, file_path, rel_path_base):
		"""
		initializes information about this photo from the file path
		"""
		self.file_path = file_path
		self.rel_path_base = rel_path_base # this is the source of the file_path
		self.file_handle = open(file_path)
		self.tags = exifread.process_file(self.file_handle, details=False)
		self.file_handle.seek(0)
		self.hash = make_file_hash(self.file_path)
		self.time = None
		self.marked = False
	
	def destroy(self):
		"""
		Ensures that handles are cleaned up and nothing is left hanging
		"""
		self.file_handle.close()
		self.tags = None
		self.file_path = None
	
	@property
	def rel_path(self):
		return os.path.relpath(self.file_path, self.rel_path_base)
	
	@property
	def name(self):
		return os.path.split(self.file_path)[1]
	
	@staticmethod
	def from_dict(data_dict):
		Logger.debug(str(data_dict.keys()))
		fc = FileContainer(data_dict["file_path"], data_dict["rel_path_base"])
		fc.time = data_dict["time"]
		fc.marked = data_dict["marked"]
		return fc
	
	def __dict__(self):
		return {
			"file_path": self.file_path,
			"rel_path_base": self.rel_path_base,
			"time": self.time,
			"marked": self.marked
		}
	
	def __getitem__(self, key):
		return getattr(self, key)
	

def underscore_to_camel_case (str):
	return str.title().replace('_', '')

def make_file_hash(path):
	h = hashlib.sha1()
	f = open(path)
	h.update(f.read())
	f.close()
	return h.hexdigest()

def get_thumb_name(filename, hash):
	filebase, ext = os.path.splitext(filename)
	return ".".join([filebase, hash, ext.lstrip(".").lower()])

def create_thumb(src_file, tags, target_path, size):
	src_file.seek(0)
	im = Image.open(src_file)
	if IMAGE_ORIENTATION_TAGNAME in tags.keys():
		img_orientation = tags[IMAGE_ORIENTATION_TAGNAME]
		if str(img_orientation) in ROTATION_VALUES:
			im = im.rotate(ROTATION_VALUES[str(img_orientation)])
	im.thumbnail(size, Image.ANTIALIAS)
	Logger.debug("target path: %s" % target_path)
	im.save(target_path)


def is_image_file(file_name):
	"""
	Determines whether the given file_name seems to be one of the
	supported image file types.
	"""
	_, ext = os.path.splitext(file_name)
	return ext.lstrip(".").lower() in S.SUPPORTED_IMG_EXTENSIONS

def get_time(fc, force_date_from_path = False, allow_date_from_path = True):
	"""
	Returns an object with the time the date was taken and a message about the
	status of the operation
	"""
	retval = {
		"time": None,
		"msg": "no_date"
	}
	file_name = fc.file_path
	Logger.debug("file name: %s" % file_name)
	dir_name, file_name = os.path.split(file_name)
	relpath = fc.rel_path
	parts = relpath.split(os.sep)
	try:
		year = int(parts[0]) if len(parts) > 0 else None
		month = int(parts[1]) if len(parts) > 1 else None
		day = int(parts[2]) if len(parts) > 2 else None
	except Exception:
		year = month = day = None

	# force date supercedes all
	if force_date_from_path:
		if year == None or month == None or day == None:
			return retval
		retval["time"] = time.strptime("%s-%s-%s" % (year, month, day), "%Y-%m-%d")
		retval["msg"] = "force_from_path"
		return retval
	
	exif_time = None
	try:
		exif_time = time.strptime(str(fc.tags[DATE_FIELD]), EXIF_DATE_FORMAT)
	except Exception:
		pass
	
	if exif_time == None:
		try:
			exif_time = time.strptime(str(fc.tags[BK_DATE_FIELD]), EXIF_DATE_FORMAT)
		except Exception:
			pass
	
	get_date_from_path = False
	if (exif_time == None):
		retval["msg"] = "no_exif_date"
		get_date_from_path = True
	
	elif (allow_date_from_path and (exif_time.tm_year != year
		or exif_time.tm_mon != month or exif_time.tm_mday != day)):
		retval["msg"] = "no_date_match[%s-%s-%s]" % (
			exif_time.tm_year,
			exif_time.tm_mon,
			exif_time.tm_mday
		)
		get_date_from_path = True and allow_date_from_path
	
	else:
		retval["msg"] = "date_from_exif"
		retval["time"] = exif_time
	
	if get_date_from_path:
		if (year != None and month != None and day != None):
			retval["time"] = time.strptime("%s-%s-%s" % (year, month, day), "%Y-%m-%d")

	return retval

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

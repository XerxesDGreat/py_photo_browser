from logger import Logger
from settings import Settings as S
from database import Database as DB
from database import FetchFieldArg

import os
import Image
import util
import exifread
import datetime
import time

class Photo():
	SMALL_THUMB_SIZE = (200, 200)
	MEDIUM_THUMB_SIZE = (600, 600)

	ORIENTATION_KEY = 0x0112;
	STOP_TAG_NAME = "Orientation"
	IMAGE_ORIENTATION_TAGNAME = "Image Orientation"

	DB_TABLE_NAME = "photos"

	ROTATION_VALUES = {
		exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][3]: 180,
		exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][4]: 180,
		exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][5]: 270,
		exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][6]: 270,
		exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][7]: 90,
		exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][8]: 90
	}

	GUARD = {}

	############################################################################
	# FETCHING METHODS
	############################################################################
	@staticmethod
	def get_by_id(id):
		id_field = FetchFieldArg("id", FetchFieldArg.CMP_EQ, id)
		row = DB.fetch_by_properties(Photo.DB_TABLE_NAME, [id_field])
		p = Photo(Photo.GUARD, row[0])
		return p
	
	@staticmethod
	def get_by_date(timestamp=None, year=None, month=None, day=None, field="image_date", limit=None, offset=None):
		"""
		Fetches a list of photos based on the given date.

		timestamp (int) will supercede the year, month, day values.
		Valid combinations are:
		- timestamp
		- year
		- year & month
		- year & month & day
		If just a day or just a month or just a month & day is given, will return
		an empty list
		"""
		query_args = []
		if timestamp != None:
			dt = datetime.date.fromtimestamp(timestamp)
			query_args.append(FetchFieldArg(field, FetchFieldArg.CMP_EQ, dt.year, FetchFieldArg.DB_OP_YEAR))
			query_args.append(FetchFieldArg(field, FetchFieldArg.CMP_EQ, dt.month, FetchFieldArg.DB_OP_MONTH))
			query_args.append(FetchFieldArg(field, FetchFieldArg.CMP_EQ, dt.day, FetchFieldArg.DB_OP_DAY))
		else:
			if year == None:
				pass
			elif year != None and day != None and month == None:
				pass
			else:
				query_args.append(FetchFieldArg(field, FetchFieldArg.CMP_EQ, year, FetchFieldArg.DB_OP_YEAR))
				if month != None:
					query_args.append(FetchFieldArg(field, FetchFieldArg.CMP_EQ, month, FetchFieldArg.DB_OP_MONTH))
				if day != None:
					query_args.append(FetchFieldArg(field, FetchFieldArg.CMP_EQ, day, FetchFieldArg.DB_OP_DAY))
		rows = DB.fetch_by_properties(Photo.DB_TABLE_NAME, query_args)
		Logger.debug("all the rows: %s" % str(rows))
		resp = []
		for i in range(0, len(rows)):
			Logger.debug("%s" % str(rows[i]))
			resp.append(Photo(Photo.GUARD, rows[i]))
		return resp

	@staticmethod
	def get_all_years():
		year_field = FetchFieldArg("image_date", None, None, FetchFieldArg.DB_OP_YEAR)
		results = DB.fetch_unique_field_values(Photo.DB_TABLE_NAME, year_field)
		return [f[0] for f in results]
	
	@staticmethod
	def get_all_months_by_year(year):
		year_field = FetchFieldArg("image_date", FetchFieldArg.CMP_EQ, year, FetchFieldArg.DB_OP_YEAR)
		criteria = [year_field]
		month_field = FetchFieldArg("image_date", None, None, FetchFieldArg.DB_OP_MONTH)
		results = DB.fetch_unique_field_values(Photo.DB_TABLE_NAME, month_field, criteria)
		return [f[0] for f in results]

	@staticmethod
	def get_all_days_by_ym(year, month):
		year_field = FetchFieldArg("image_date", FetchFieldArg.CMP_EQ, year, FetchFieldArg.DB_OP_YEAR)
		month_field = FetchFieldArg("image_date", FetchFieldArg.CMP_EQ, month, FetchFieldArg.DB_OP_MONTH)
		criteria = [year_field, month_field]
		day_field = FetchFieldArg("image_date", None, None, FetchFieldArg.DB_OP_DAY)
		results = DB.fetch_unique_field_values(Photo.DB_TABLE_NAME, day_field, criteria)
		return [f[0] for f in results]	
		
	@staticmethod
	def get_by_path(path):
		"""
		Fetches a list of photos from the given path, paginated as indicated
		"""
		full_path = os.path.join(S.BASE_FS_PATH, path)
	
	############################################################################
	# CREATION METHODS
	############################################################################
	@staticmethod
	def create(file_basename, path, hash, created_struct):
		image_date = time.strftime(DB.DB_DATE_FORMAT, created_struct)
		value_list = [
			("filename", file_basename, "%s"),
			("path", path, "%s"),
			("hash", hash, "%s"),
			("image_date", image_date, "%s")
		]
		inserted_id = DB.create(Photo.DB_TABLE_NAME, value_list)
		Logger.debug("insert results: %s" % str(inserted_id))
		return Photo.get_by_id(inserted_id)
		

	def __init__(self, guard, db_row): 
		if guard != Photo.GUARD:
			raise Exception("Must only call __init__ from the accessor methods in Photo")
		self.id = db_row[0]
		self.filename = db_row[1]
		self.path = db_row[2]
		self.marked = db_row[3]
		self.added = db_row[4]
		self.modified = db_row[5]
		self.hash = db_row[6]
		self.image_date = db_row[7]
		self.dirty = False

	def get_or_create_thumb(self, size = SMALL_THUMB_SIZE, path_only = False):
		"""
		Fetches the path to a thumbnail if it exists, else creates the thumb
		and returns the path
		"""
		if not os.path.exists(self.path):
			return None

		thumbname = util.get_thumb_name(self.path)
		Logger.debug("thumb name: %s" % thumbname)
		thumb_subdir = "%dx%d" % size
		thumb_path = os.path.join(S.THUMBNAIL_DIR, thumb_subdir, thumbname)
		return_thumb_path = os.path.join(thumb_subdir, thumbname)
		if os.path.exists(thumb_path):
			return return_thumb_path

		# sometimes we may only want to get the thumb url
		if path_only:
			return return_thumb_path 

		# do something about orientation
		Logger.debug("creating!!")
		Logger.debug("opening %s" % self.path)
		f = open(self.path)
		tags = exifread.process_file(f, stop_tag=Photo.STOP_TAG_NAME)
		f.close()
		f = open(self.path)
		Logger.debug(str(tags.keys()))
		im = Image.open(f)
		if Photo.IMAGE_ORIENTATION_TAGNAME in tags.keys():
			img_orientation = tags[Photo.IMAGE_ORIENTATION_TAGNAME]
			Logger.debug("%s %s %s" % (str(img_orientation), type(img_orientation), str(exifread.tags.EXIF_TAGS[Photo.ORIENTATION_KEY][1][6])))
			if str(img_orientation) in Photo.ROTATION_VALUES:
				Logger.debug("rotation: %d" % Photo.ROTATION_VALUES[str(img_orientation)])
				im = im.rotate(Photo.ROTATION_VALUES[str(img_orientation)])
		im.thumbnail(size, Image.ANTIALIAS)
		im.save(thumb_path)
		return return_thumb_path 
	
	@property
	def is_checked(self):
		"""
		Determines whether the image has been marked for review
		"""
		f = open(S.MARK_FILE)
		contains = False
		if self.path in f.read():
			contains = True
		f.close()
		return contains
	
	@property
	def name(self):
		return os.path.basename(self.path)
	
	@property
	def thumb_url(self):
		return "adsf.jpg"
	
	@property
	def rel_path(self, base_path = S.BASE_FS_PATH):
		return os.path.relpath(self.path, S.BASE_FS_PATH)

	@property
	def path(self):
		return self.path
	
	def __str__(self):
		return "%s %s %s %s %s" % (self.path, self.filename, self.added, self.modified, self.image_date)

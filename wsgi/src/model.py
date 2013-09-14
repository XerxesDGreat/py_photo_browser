from logger import Logger
from settings import Settings as S
from database import Database as DB
from database import FieldArg

import os
import util
import exifread
import datetime
import time

class Photo(object):
	SMALL_THUMB_SIZE = (200, 200)
	MEDIUM_THUMB_SIZE = (600, 600)

	DB_TABLE_NAME = "photos"


	GUARD = {}

	############################################################################
	# PROPERTY METHODS
	############################################################################
	@property
	def marked(self):
		"""
		Determines whether the image has been marked for review
		"""
		return self._marked
	
	@marked.setter
	def marked(self, marked):
		"""
		Updates the checked/marked state
		"""
		self._marked = int(marked)
		self.dirty.append("marked")
	
	@property
	def thumb_url(self):
		return self.get_or_create_thumb()
	
	@property
	def rel_path(self, base_path = S.BASE_FS_PATH):
		return os.path.relpath(self.filepath, S.BASE_FS_PATH)

	@property
	def filepath(self):
		return os.path.join(self.path, self.filename)

	############################################################################
	# FETCHING METHODS
	############################################################################
	@staticmethod
	def get_count_by_date(year=None, month=None, day=None, field="image_date"):
		"""
		Fetches the number of photos on a particular date. Allows Year,
		Year + Month, Year + Month + Day
		"""
		count_field = FieldArg("*", None, None, FieldArg.DB_OP_COUNT)
		query_args = []
		if year != None:
			query_args.append(FieldArg(field, FieldArg.CMP_EQ, year, FieldArg.DB_OP_YEAR))
			if month != None:
				query_args.append(FieldArg(field, FieldArg.CMP_EQ, month, FieldArg.DB_OP_MONTH))
				if day != None:
					query_args.append(FieldArg(field, FieldArg.CMP_EQ, day, FieldArg.DB_OP_DAY))
				
		row = DB.fetch(Photo.DB_TABLE_NAME, [count_field], query_args)
		return int(row[0][0])
	
	@staticmethod
	def get_num_marked_photos():
		"""
		Fetches the number of photos which are marked
		"""
		count_field = FieldArg("*", None, None, FieldArg.DB_OP_COUNT)
		query_args = FieldArg("marked", FieldArg.CMP_EQ, 1)
		row = DB.fetch(Photo.DB_TABLE_NAME, [count_field], [query_args])
		return int(row[0][0])

	@staticmethod
	def get_by_id(id):
		"""
		Fetches a single photo by id
		"""
		row = DB.fetch_one_by_id(Photo.DB_TABLE_NAME, id)
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
			query_args.append(FieldArg(field, FieldArg.CMP_EQ, dt.year, FieldArg.DB_OP_YEAR))
			query_args.append(FieldArg(field, FieldArg.CMP_EQ, dt.month, FieldArg.DB_OP_MONTH))
			query_args.append(FieldArg(field, FieldArg.CMP_EQ, dt.day, FieldArg.DB_OP_DAY))
		else:
			if year == None:
				pass
			elif year != None and day != None and month == None:
				pass
			else:
				query_args.append(FieldArg(field, FieldArg.CMP_EQ, year, FieldArg.DB_OP_YEAR))
				if month != None:
					query_args.append(FieldArg(field, FieldArg.CMP_EQ, month, FieldArg.DB_OP_MONTH))
				if day != None:
					query_args.append(FieldArg(field, FieldArg.CMP_EQ, day, FieldArg.DB_OP_DAY))
		fetch_field = FieldArg("*")
		rows = DB.fetch(Photo.DB_TABLE_NAME,fields=[fetch_field], args=query_args, limit=limit, offset=offset)
		resp = []
		for i in range(0, len(rows)):
			resp.append(Photo(Photo.GUARD, rows[i]))
		return resp
	
	@staticmethod
	def get_marked(offset=None, limit=None):
		field = FieldArg("*")
		criteria = [FieldArg("marked", FieldArg.CMP_EQ, 1)]
		rows = DB.fetch(Photo.DB_TABLE_NAME, fields=[field], args=criteria,
			limit=limit, offset=offset)
		return [Photo(Photo.GUARD, r) for r in rows]

	@staticmethod
	def get_all_dates(year=None, month=None):
		"""
		Fetches all the available date gradation values for the identifiers
		provided. If year is None, fetches all years with photos. If year is not
		None and month is None, fetches months in the given year. If both year
		and month are not None, fetches days in that year and month
		"""
		criteria = []
		results_op = FieldArg.DB_OP_YEAR
		if year != None:
			criteria.append(FieldArg("image_date", FieldArg.CMP_EQ,
				year, FieldArg.DB_OP_YEAR))
			results_op = FieldArg.DB_OP_MONTH
			# we only want to add month if we have a year
			if month != None:
				criteria.append(FieldArg("image_date", FieldArg.CMP_EQ,
					month, FieldArg.DB_OP_MONTH))
				results_op = FieldArg.DB_OP_DAY
		field = FieldArg("image_date", None, None, results_op)
		results = DB.fetch_unique_field_values(Photo.DB_TABLE_NAME, field, criteria)
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
		"""
		Creates a new photo record in the database, constructs and returns a
		Photo object
		"""
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
	
	############################################################################
	# INSTANCE METHODS
	############################################################################
	def __init__(self, guard, db_row):
		"""
		Constructor; uses a guard to ensure noone else uses it
		"""
		if guard != Photo.GUARD:
			raise Exception("Must only call __init__ from the accessor methods in Photo")
		self.id, self.filename, self.path, self.added, self.modified, self.image_date, self.hash, self._marked = db_row
		self.dirty = []
	
	def get_thumb_image_name(self):
		"""
		Gets the file name for a thumbnail (<basename>.<hash>.<ext>)
		"""
		return util.get_thumb_name(self.filename, self.hash)

	def get_or_create_thumb(self, size = SMALL_THUMB_SIZE, path_only = False):
		"""
		Fetches the path to a thumbnail if it exists, else creates the thumb
		and returns the path
		"""
		thumbname = self.get_thumb_image_name()
		thumb_subdir = "%dx%d" % size
		thumb_path = os.path.join(S.THUMBNAIL_DIR, thumb_subdir, thumbname)
		return_thumb_path = os.path.join(thumb_subdir, thumbname)
		if os.path.exists(thumb_path):
			return return_thumb_path

		# sometimes we may only want to get the thumb url
		if path_only:
			return return_thumb_path 

		util.create_thumb(self.filepath, thumb_path, size)
		return return_thumb_path 

	def store(self):
		if len(self.dirty) < 1:
			return
		
		DB.update_by_id(Photo.DB_TABLE_NAME, self.id, self._get_db_tuples())
		self.dirty[:] = []
	
	def _get_db_tuples(self):
		"""
		Gets a list of tuples for each of the fields to be updated
		"""
		field_tuples = []
		for field in self.dirty:
			field_tuples.append(FieldArg(field, FieldArg.CMP_EQ, getattr(self, field)))
		return field_tuples
		
	def __str__(self):
		return "%s %s %s %s %s" % (self.path, self.filename, self.added, self.modified, self.image_date)

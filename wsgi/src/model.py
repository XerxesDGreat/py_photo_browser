from logger import Logger
from settings import Settings as S
from database import Database as DB
from database import FieldArg
from registry import ObjectRegistry

import os
import util
import exifread
import datetime
import time
import shutil
import threading

class Photo(object):
	SMALL_THUMB_SIZE = (200, 200)
	MEDIUM_THUMB_SIZE = (600, 600)

	DB_TABLE_NAME = "photos"

	# constants for indexes
	ID_IDX = 0
	FILENAME_IDX = 1
	PATH_IDX = 2
	ADDED_IDX = 3
	MODIFIED_IDX = 4
	IMAGE_DATE_IDX = 5
	HASH_IDX = 6
	MARKED_IDX = 7

	# blacklist for fields which cannot be externally updated
	UPDATE_BLACKLIST = ["id", "added", "modified", "hash"]

	# next id to use
	NEXT_AVAILABLE_ID = -1

	# default dir for photos without a date
	NO_DATE_DIR = "no_date"

	dirty_list = {}

	GUARD = {}

	############################################################################
	# PROPERTY METHODS
	############################################################################
	def __getattr__(self, name):
		try:
			property_name = "_%s" % name
			return getattr(self, property_name)
		except:
			return None
	
	def __setattr__(self, name, value):
		self._set_internal(name, value)
	
	def _set_internal(self, name, value, bypass_checks=False, set_dirty=True):
		if bypass_checks and name in Photo.UPDATE_BLACKLIST:
			raise Exception("cannot update field %s externally" % name)
		property_name = "_%s" % name
		object.__setattr__(self, property_name, value)

		self.set_dirty()

	@property
	def thumb_url(self):
		return self.get_or_create_thumb()
	
	@property
	def rel_path(self):
		return os.path.relpath(self.filepath, S.BASE_FS_PATH)

	@property
	def filepath(self):
		return os.path.join(self.path, self.filename)

	@property
	def tags(self):
		if self._tags == None:
			if self.file_container != None:
				self._tags = self.file_container.tags
			else:
				self._tags = exifread.process_file(self.handle, details=False)
		return self._tags
	
	@tags.setter
	def tags(self, value):
		self._tags = value

	@property
	def handle(self):
		if self._handle == None:
			if self.file_container != None:
				self._handle = self.file_container.file_handle
			else:
				self._handle = open(os.path.join(self.path, self.filename))
		return self._handle
	
	@handle.setter
	def handle(self, value):
		self._handle = value

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
		if len(row) < 1:
			return None
		p = Photo(Photo.GUARD, row[0])
		return p
	
	@staticmethod
	def get_by_hash(hashes):
		"""
		Fetches all photos which match the hash or hashes provided. This SHOULD
		only return one photo per hash, but it's possible that it will return
		more than one; support this. Also, hashes can be either a single hash or
		a list of hashes; support both
		"""
		field = FieldArg("*")
		if isinstance(hashes, basestring):
			hashes = [hashes]
		condition = FieldArg("hash", FieldArg.CMP_IN, hashes)
		rows = DB.fetch(Photo.DB_TABLE_NAME, [field], [condition])
		photos = {}
		for row in rows:
			p = Photo(Photo.GUARD, row)
			if p.hash not in photos.keys():
				photos[p.hash] = []
			photos[p.hash].append(p)

		return photos
	
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
		"""
		Fetch Photo object for all records in the database which are marked
		"""
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
	def get_from_data(**kwargs):
		"""
		Creates a Photo object, specifying values for the various properties
		rather than assigning them from a database query
		"""
		next_id = Photo.get_next_id()
		now = DB.fetch_current_timestamp()
		data_tuple = (
			next_id,
			kwargs["filename"] if "filename" in kwargs.keys() else "",
			kwargs["path"] if "path" in kwargs.keys() else "",
			now,
			now,
			kwargs["image_date"] if "image_date" in kwargs.keys() else None,
			kwargs["hash"] if "hash" in kwargs.keys() else None,
			kwargs["marked"] if "marked" in kwargs.keys() else False
		)
		return Photo(Photo.GUARD, data_tuple, True)
	
	@staticmethod
	def from_file_container(fc):
		"""
		Creates a photo object from the provided FileContainer object
		"""
		fpath, fname = os.path.split(fc.file_path)
		next_id = Photo.get_next_id()
		now = DB.fetch_current_timestamp()
		data_tuple = (
			next_id,
			fname,
			fpath,
			now,
			now,
			fc.time,	
			fc.hash,
			False
		)
		p = Photo(Photo.GUARD, data_tuple, True)
		p.file_container = fc
		return p

	@staticmethod
	def get_next_id():
		"""
		Fetches the next available id for new Photo objects
		"""
		if Photo.NEXT_AVAILABLE_ID < 0:
			Photo.NEXT_AVAILABLE_ID = DB.fetch_max_id(Photo.DB_TABLE_NAME)
		Photo.NEXT_AVAILABLE_ID += 1
		retval = Photo.NEXT_AVAILABLE_ID
		return Photo.NEXT_AVAILABLE_ID

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
		inserted_id = Photo._create_work(file_basename, path, hash, created_struct)
		Logger.info("insert results: %s" % str(inserted_id))
		return Photo.get_by_id(inserted_id)
	
	@staticmethod
	def _create_work(file_basename, path, hash, created_struct):
		"""
		Creates a new photo record in the database and returns the new id
		"""
		image_date = time.strftime(DB.DB_DATE_FORMAT, created_struct)
		value_list = [
			("filename", file_basename, "%s"),
			("path", path, "%s"),
			("hash", hash, "%s"),
			("image_date", image_date, "%s")
		]
		inserted_id = DB.create(Photo.DB_TABLE_NAME, value_list)
		return inserted_id
	
	############################################################################
	# INSTANCE METHODS
	############################################################################
	def __init__(self, guard, db_row, new = False):
		"""
		Constructor; uses a guard to ensure noone else uses it
		"""
		if guard != Photo.GUARD:
			raise Exception("Must only call __init__ from the accessor methods in Photo")
		self._id, self._filename, self._path, self._added, self._modified, self._image_date, self._hash, self._marked = db_row
		self.new = new
		self._tags = None
		self._handle = None
		self.file_container = None
		ObjectRegistry.register(self)
	
	def get_thumb_image_name(self):
		"""
		Gets the file name for a thumbnail (<basename>.<hash>.<ext>)
		"""
		return util.get_thumb_name(self.filename, self.hash)
	
	def get_dir_from_date(self):
		if self.image_date == None:
			return os.path.join(S.BASE_FS_PATH, Photo.NO_DATE_DIR)
		struct = time.strptime(self.image_date, DB.DB_DATE_FORMAT)
		year = str(struct[0])
		month = "0%d" % struct[1] if struct[1] < 10 else str(struct[1])
		day = "0%d" % struct[2] if struct[2] < 10 else str(struct[2])

		return os.path.join(S.BASE_FS_PATH, year, month, day) 

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

		util.create_thumb(self.handle, self.tags, thumb_path, size)
		return return_thumb_path 

	def move_file(self, src_dir=None, target_dir=None, copy=True, resolve=True):
		"""
		Moves the photo file, optionally performing a copy rather than a move.
		
		If src_dir is specified, moves the file from src_dir to the directory
		specified by self.image_date (BASE_FS_DIR/YYYY/MM/DD).
		If target_dir is specified, moves, the file from self.path to target_dir.
		Only the directory should be passed in either case; self.filename will be
		used. If a file by self.filename exists in the target directory, will
		raise an exception unless resolve is set, in which case will add a
		segment of self.hash to the file name for uniqueness. If this still
		fails, will raise an exception.
		"""
		if ((src_dir == None and target_dir == None)
			or (src_dir != None and target_dir != None)):
			raise Exception("Must define either src_dir or target_dir")

		src_dir = self.get_dir_from_date() if src_dir == None else src_dir
		src_path = os.path.join(src_dir, self.filename)
		target_dir = self.get_dir_from_date() if target_dir == None else target_dir
		if not os.path.exists(target_dir):
			Logger.info("making dir: %s" % target_dir)
			os.makedirs(target_dir)
		new_filename = self.filename

		if not os.path.exists(src_path):
			raise Exception("File %s does not exist" % src_path)

		if os.path.exists(os.path.join(target_dir, new_filename)):
			if not resolve:
				raise Exception("File %s exists at target %s" % (new_filename, target_dir))
			base, ext = os.path.splitext(new_filename)
			new_filename = "%s-%s%s" % (base, self.hash[-7:], ext)
			if os.path.exists(os.path.join(target_dir, new_filename)):
				raise Exception("File %s exists at target %s after resolution"
					% (new_filename, target_dir))
		target_path = os.path.join(target_dir, new_filename)

		# can't do crap with an open file reference
		if self.file_container != None and self.file_container.file_handle != None:
			self.file_container.file_handle.close()
			self.file_container.file_handle = None

		if copy:
			Logger.info("copying from %s to %s" % (src_path, target_path))
			shutil.copy2(src_path, target_path)
		else:
			Logger.info("moving from %s to %s" % (src_path, target_path))
			shutil.move(src_path, target_path)

		self.path = target_dir
		self.filename = new_filename
		if self.file_container != None:
			self.file_container.file_path = os.path.join(target_dir, new_filename)
			self.file_container.handle = open(self.file_container.file_path)
	
	def set_dirty(self):
		"""
		Sets this object as dirty
		"""
		if self.hash not in Photo.dirty_list.keys():
			Photo.dirty_list[self.hash] = self

	def store(self):
		"""
		Stores any changes to this object to the database. Also creates the
		db record if necessary
		"""
		if self.new:
			time_struct = time.strptime(self.image_date, DB.DB_DATE_FORMAT)
			photo = Photo.create(self.filename, self.path, self.hash, time_struct)
			self._values_from_photo_object(photo, False)
			del(photo)

		else:
			if self.hash not in Photo.dirty_list:
				return
		
			DB.update_by_id(Photo.DB_TABLE_NAME, self.id, self._get_db_tuples())
			del(Photo.dirty_list[self.hash])
	
	def _values_from_photo_object(self, photo, set_dirty=True):
		"""
		Updates this photo object with values from the provided photo object
		"""
		Logger.debug("updating information")
		self._id = photo.id
		self._added = photo.added
		self._modified = photo.modified
		self.set_dirty()
	
	def destroy(self):
		"""
		Cleans up and destroys this object
		"""
		self.tags = None
		if self.handle != None:
			self.handle.close()
		self.handle = None
		if self.file_container != None:
			self.file_container.destroy()
	
	def _get_db_tuples(self):
		"""
		Gets a list of tuples for each of the fields to be updated
		"""
		field_tuples = []
		for field in ["id", "filename", "path", "hash", "image_date", "marked"]:
			field_tuples.append(FieldArg(field, FieldArg.CMP_EQ, getattr(self, field)))
		field_tuples.append(FieldArg("modified", FieldArg.CMP_EQ, DB.fetch_current_timestamp()))
		return field_tuples
		
	def __str__(self):
		return "photo obj[id=%s] [name=%s] [img_date=%s]" % (self.id, self.filename, self.image_date)
	
	def __del__(self):
		self.destroy()

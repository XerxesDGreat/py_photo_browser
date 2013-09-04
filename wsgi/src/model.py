from logger import Logger
from settings import Settings as S

import os
import Image
import util
import exifread

class Node:
	def __init__(self, path):
		self._path = path

class Photo(Node):
	SMALL_THUMB_SIZE = (200, 200)
	MEDIUM_THUMB_SIZE = (600, 600)

	ORIENTATION_KEY = 0x0112;
	STOP_TAG_NAME = "Orientation"
	IMAGE_ORIENTATION_TAGNAME = "Image Orientation"

	ROTATION_VALUES = {
		exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][3]: 180,
		exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][4]: 180,
		exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][5]: 270,
		exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][6]: 270,
		exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][7]: 90,
		exifread.tags.EXIF_TAGS[ORIENTATION_KEY][1][8]: 90
	}

	def get_hash(self):
		pass

	def get_or_create_thumb(self, size = SMALL_THUMB_SIZE, path_only = False):
		"""
		Fetches the path to a thumbnail if it exists, else creates the thumb
		and returns the path
		"""
		if not os.path.exists(self._path):
			return None

		thumbname = util.get_thumb_name(self._path)
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
		Logger.debug("opening %s" % self._path)
		f = open(self._path)
		tags = exifread.process_file(f, stop_tag=Photo.STOP_TAG_NAME)
		f.close()
		f = open(self._path)
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
		if self._path in f.read():
			contains = True
		f.close()
		return contains
	
	@property
	def name(self):
		return os.path.basename(self._path)
	
	@property
	def rel_path(self, base_path = S.BASE_FS_PATH):
		return os.path.relpath(self.path, S.BASE_FS_PATH)

	@property
	def path(self):
		return self._path
	
class Directory(Node):
	def get_friendly_name(self):
		pass

	def get_url(self):
		pass


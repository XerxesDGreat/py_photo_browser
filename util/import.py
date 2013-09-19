#!/usr/bin/python
import os
import sys
import time
import re
import shutil
import hashlib
import argparse
import exifread
import Image

# some fun to get to the src dir
this_file = os.path.realpath(__file__)
this_dir = os.path.dirname(this_file)
sys.path.append(os.path.realpath(os.path.join(this_dir, "..", "wsgi")))
from src.database import *
from src.model import Photo
from src.logger import Logger as L
import src.util
from src.settings import Settings as S
L.init(sys.stderr, L.WARNING)

WORKING_BASE_DIR = "."
DEST_BASE_DIR = "/home/josh/Dropbox/Photos"
WRITE = True
DATE_FIELD = "Image DateTime"
BK_DATE_FIELD = "EXIF DateTimeOriginal"
EMPTY_DATE = "0000:00:00 00:00:00"
EXIF_DATE_FORMAT = "%Y:%m:%d %H:%M:%S"
SUPPORTED_IMG_EXTENSIONS = [
	"jpeg",
	"jpg",
	#"mov",
	#"avi",
	"bmp",
	"png",
	"gif",
	"tiff",
	#"mp4",
	#"nef"
]
DESCRIPTION = """Transfers images from one directory to another, putting each
image in a subdirectory corresponding to its creation date. If the image already exists in the destination, will compare the files using SHA1 and, if they have different contents, will copy using a new name based on the hash. Outputs one line for each file encountered in the format "<source_file_path> <dest_file_path> <action_taken> where resolution is in ("exists_same", "exists_different_copied", "new", "not_img"). Most common image extensions will be copied: (%s)""" % (
	", ".join(SUPPORTED_IMG_EXTENSIONS)
)

class FileContainer(object):
	def __init__(self, file_path):
		self.file_path = file_path
		self.file_handle = open(file_path)
		self.tags = exifread.process_file(self.file_handle, details=False)
		self.file_handle.seek(0)
		self.hash = src.util.make_file_hash(self.file_path)
	
	def destroy(self):
		self.file_handle.close()
		self.tags = None
		self.file_path = None
	

def is_img_file(file_name, options):
	_, ext = os.path.splitext(file_name)
	ext = re.sub(r"\.", "", ext.lower(), 1)
	return ext in SUPPORTED_IMG_EXTENSIONS and ext not in options.exclude_types

def is_in_database(file_basename, hash, created_date):
	db_args = []
	db_args.append(FieldArg("filename", FieldArg.CMP_EQ, file_basename))
	c = time.strftime(Database.DB_DATE_FORMAT, created_date)
	db_args.append(FieldArg("image_date", FieldArg.CMP_EQ, c))
	db_args.append(FieldArg("hash", FieldArg.CMP_EQ, hash))
	fetch_field = FieldArg("*")
	rows = Database.fetch(Photo.DB_TABLE_NAME, [fetch_field], db_args)
	return len(rows) > 0

def get_hash(file_name):
	h = hashlib.sha1()
	f = open(file_name)
	h.update(f.read())
	f.close()
	return h.hexdigest()

def create_dir(created_date):
	options = get_options()
	pic_dir = os.path.realpath(options.dest)
	i = 0
	while i <= 2:
		p = "0%s" % str(created_date[i]) if created_date[i] < 10 else str(created_date[i])
		pic_dir = os.path.join(pic_dir, p)
		if not os.path.exists(pic_dir) and options.write:
			os.mkdir(pic_dir)
		i += 1
	return pic_dir

def create_thumbs(fc):
	path, filename = os.path.split(fc.file_path)
	thumb_name = src.util.get_thumb_name(filename, fc.hash)
	for s in [Photo.SMALL_THUMB_SIZE, Photo.MEDIUM_THUMB_SIZE]:
		create_single_thumb(s, fc, thumb_name)

def create_single_thumb(size, fc, thumb_name):
	thumbnail_dir = S.THUMBNAIL_DIR
	target = os.path.join(thumbnail_dir, "%sx%s" % size, thumb_name)
	if os.path.exists(target):
		return
	src.util.create_thumb(fc.file_handle, fc.tags, target, size)

def get_time(fc):
	retval = {
		"time": None,
		"msg": "no_date"
	}
	file_name = fc.file_path
	dir_name, file_name = os.path.split(file_name)
	relpath = os.path.relpath(dir_name, os.path.realpath(DEST_BASE_DIR))
	parts = relpath.split(os.sep)
	try:
		year = int(parts[0]) if len(parts) > 0 else None
		month = int(parts[1]) if len(parts) > 1 else None
		day = int(parts[2]) if len(parts) > 2 else None
	except Exception:
		year = month = day = None

	# force date supercedes all
	if get_options().force_date_from_path:
		if year == None or month == None or day == None:
			return retval
		return time.strptime("%s-%s-%s" % (year, month, day), "%Y-%m-%d")
	
	exif_time = None
	try:
		exif_time = time.strptime(str(fc.tags[DATE_FIELD]), EXIF_DATE_FORMAT)
	except Exception:
		pass
	
	try:
		exif_time = time.strptime(str(fc.tags[BK_DATE_FIELD]), EXIF_DATE_FORMAT)
	except Exception:
		pass
	
	get_date_from_path = False
	if (exif_time == None):
		retval["msg"] = "no_exif_date"
		get_date_from_path = True
	
	elif (exif_time.tm_year != year or exif_time.tm_mon != month
		or exif_time.tm_mday != day):
		retval["msg"] = "no_date_match[%s-%s-%s]" % (
			exif_time.tm_year,
			exif_time.tm_mon,
			exif_time.tm_mday
		)
		get_date_from_path = True
	
	else:
		retval["msg"] = "date_from_exif"
		retval["time"] = exif_time
	
	if get_date_from_path:
		if (year != None and month != None and day != None):
			retval["time"] = time.strptime("%s-%s-%s" % (year, month, day), "%Y-%m-%d")

	return retval

def write(pieces):
	global logfile
	print " ".join(pieces)
	if logfile != None:
		logfile.write(" ".join(pieces) + "\n")

logfile = None
def set_up_logfile():
	global logfile
	if options.logfile == None:
		return
	if not os.path.exists(os.path.dirname(options.logfile)):
		return
	try:
		logfile=open(options.logfile, "w+")
	except:
		pass

def tear_down_logfile():
	global logfile
	if logfile == None:
		return
	logfile.close()
	logfile = None

def handle_conflict(src_path, src_hash, dest_path):
	dest_hash = get_hash(dest_path)
	if src_hash == dest_hash:
		resolution = "exists_same"
	elif not options.no_copy_conflict:
		resolution = "exists_different_copying"
		pic_dir, f = os.path.split(dest_path)
		old, ext = os.path.splitext(f)
		new_f = "".join([old, "_conflict", ext])
		dest_path = os.path.join(pic_dir, new_f)
	else:
		resolution = "exists_no_copy"
	return (resolution, src_path, dest_path)

options = None
def get_options():
	global options
	if options is not None:
		return options
	parser = argparse.ArgumentParser(description=DESCRIPTION)
	path_group = parser.add_argument_group("Path options")
	path_group.add_argument(
		"-s", "--src",
		dest="src",
		default=WORKING_BASE_DIR,
		help="Source directory containing images to copy; will walk over all subdirectories. [default: %s]" % WORKING_BASE_DIR
	)
	path_group.add_argument(
		"-d", "--dest",
		dest="dest",
		default=DEST_BASE_DIR,
		help="Base destination directory in which the subdirectories will be created (if necessary) and to which the images will be copied. [default: %s]" % DEST_BASE_DIR
	)
	path_group.add_argument(
		"-l", "--logfile",
		dest="logfile",
		default=None,
		help="File to which to write the operation output. [default: None]"
	)
	op_group = parser.add_argument_group("Execution options", "Options to change how the script processes files")
	op_group.add_argument(
		"--db-only",
		dest="db_only",
		default=False,
		action="store_true",
		help="Only perform the database import; make no changes to the file system"
	)
	op_group.add_argument(
		"--dry-run",
		dest="write",
		default=True,
		action="store_false",
		help="Simulate the operation without actually copying files"
	)
	op_group.add_argument(
		"--exclude-types",
		dest="exclude_types",
		default="",
		action="store",
		help="Comma-separated, case insensitive, list of file types which should be excluded from copying"
	)
	op_group.add_argument(
		"--force-date-from-path",
		dest="force_date_from_path",
		default=False,
		action="store_true",
		help="Force using the directory structure for the date, even if there is EXIF data"
	)
	op_group.add_argument(
		"--no-copy-conflict",
		dest="no_copy_conflict",
		default=False,
		action="store_true",
		help="Add this to report file conflicts instead of copy using a different filename."
	)
	op_group.add_argument(
		"--no-db",
		dest="write_to_db",
		default=True,
		action="store_false",
		help="Do no database processing; overrides --db-only"
	)
	op_group.add_argument(
		"--no-recurse",
		dest="recurse",
		default=True,
		action="store_false",
		help="Disallow directory recursion when looking for images"
	)
	op_group.add_argument(
		"--no-thumbs",
		dest="thumbs",
		default=True,
		action="store_false",
		help="Prevent script from creating thumbnails"
	)
	options = parser.parse_args()
	return options

def main():
	options = get_options()
	options.exclude_types = options.exclude_types.lower().split(",")
	set_up_logfile()
	src = os.path.realpath(options.src)
	for src_dir, dirs, files in os.walk(src):
		for f in files:
			src_fpath = os.path.join(src_dir, f)
			out = [src_fpath]
			f_container = FileContainer(src_fpath)
			# check to see if this is an image file
			if not is_img_file(src_fpath, options):
				out.append("not_img")
				write(out)
				f_container.destroy()
				del f_container
				continue
		
			# get the date
			date_info = get_time(f_container)
			out.append(date_info["msg"])
			created = date_info["time"]
			if created == None:
				write(out)
				f_container.destroy()
				del f_container
				continue

			# check the db to see if it already exists
			src_hash = f_container.hash
			if options.write_to_db and is_in_database(f, src_hash, created):
				out.append("in_db")
				write(out)
				f_container.destroy()
				del f_container
				continue

			# ensure the path exists and check to see if the file is there
			dest_dir = create_dir(created)
			dest_fpath = os.path.join(dest_dir, f)
			out.append(dest_fpath)
			if os.path.exists(dest_fpath):
				res = handle_conflict(src_fpath, src_hash, dest_fpath)
				resolution, src_fpath, dest_fpath = res 
				if resolution in ("exists_same", "exists_no_copy") and not options.db_only:
					out.append(resolution)
					write(out)
					f_container.destroy()
					del f_container
					continue
				if resolution == "exists_different_copying":
					_, new_f = os.path.split(dest_fpath)
					out.append("%s[%s]" % (resolution, new_f))
			else:
				out.append("new")

			if options.write:
				if not options.db_only:
					shutil.copy2(src_fpath, dest_fpath)
					out.append("copied")
				else:
					out.append("not_copied_db_only")
				if options.write_to_db:
					p = Photo.create(
						f,
						dest_dir,
						src_hash,
						created
					)
					out.append("created_id[%d]" % p.id)
				else:
					out.append("not_created_no_db")
				if options.thumbs:
					out.append("creating_thumb")
					create_thumbs(f_container)
			write(out)
			f_container.destroy()
			del f_container
					
		if options.recurse == False:
			break
	tear_down_logfile()

if __name__ == "__main__":
	main()

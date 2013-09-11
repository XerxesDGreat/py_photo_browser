#!/usr/bin/python
import os
import sys
import time
import re
import shutil
import hashlib
import argparse
import exifread

# some fun to get to the src dir
this_file = os.path.realpath(__file__)
this_dir = os.path.dirname(this_file)
sys.path.append(os.path.realpath(os.path.join(this_dir, "..", "wsgi")))
from src.database import *
from src.model import Photo
from src.logger import Logger as L
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


def is_img_file(file_name, options):
	_, ext = os.path.splitext(file_name)
	ext = re.sub(r"\.", "", ext.lower(), 1)
	return ext in SUPPORTED_IMG_EXTENSIONS and ext not in options.exclude_types

def is_in_database(file_basename, hash, created_date):
	db_args = []
	db_args.append(FetchFieldArg("filename", FetchFieldArg.CMP_EQ, file_basename))
	c = time.strftime(Database.DB_DATE_FORMAT, created_date)
	db_args.append(FetchFieldArg("image_date", FetchFieldArg.CMP_EQ, c))
	db_args.append(FetchFieldArg("hash", FetchFieldArg.CMP_EQ, hash))
	rows = Database.fetch_by_properties(Photo.DB_TABLE_NAME, db_args)
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

def get_time(file_name):
	f = open(file_name)
	tags = exifread.process_file(f, details=False)
	f.close()
	file_time = None
	if not get_options().force_date_from_path:
		try:
			file_time = time.strptime(str(tags[DATE_FIELD]), EXIF_DATE_FORMAT)
		except Exception:
			pass
		
		try:
			file_time = time.strptime(str(tags[BK_DATE_FIELD]), EXIF_DATE_FORMAT)
		except Exception:
			pass

	if file_time == None:
		if get_options().date_from_path or get_options().force_date_from_path:
			dir_name, file_name = os.path.split(file_name)
			relpath = os.path.relpath(dir_name, os.path.realpath(DEST_BASE_DIR))
			parts = relpath.split(os.sep)
			if len(parts) == 3:
				file_time = time.strptime("%s-%s-%s" % (parts[0], parts[1], parts[2]), "%Y-%m-%d")
		elif not get_options().no_copy_nodate:
			mtime = os.path.getmtime(file_name)
			ctime = os.path.getctime(file_name)
			ts = mtime if mtime < ctime else ctime
			file_time = time.localtime(ts)
	return file_time

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
		"--date-from-path",
		dest="date_from_path",
		default=False,
		action="store_true",
		help="Parse the date from the directory structure (Y/m/d/filename) if no EXIF data exists. Overrides --no-copy-nodate"
	)
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
		"--no-copy-nodate",
		dest="no_copy_nodate",
		default=False,
		action="store_true",
		help="Add this to report when a file doesn't have a date in the EXIF data instead of copying. Useless if --date-from-path is set"
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
			# check to see if this is an image file
			if not is_img_file(src_fpath, options):
				out.append("not_img")
				write(out)
				continue
		
			# get the date
			created = get_time(src_fpath)
			if created == None:
				out.append("no_date")
				write(out)
				continue

			# check the db to see if it already exists
			src_hash = get_hash(src_fpath)
			if options.write_to_db and is_in_database(f, src_hash, created):
				out.append("in_db")
				write(out)
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
			write(out)
					
		if options.recurse == False:
			break
	tear_down_logfile()

if __name__ == "__main__":
	main()

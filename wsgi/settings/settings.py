import os
from jinja2 import Environment, FileSystemLoader

# root directory for the app
ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "../../"))
WSGI_DIR = os.path.join(ROOT_DIR, "wsgi")

# connection information for the database
DATABASE = {
	'name': 'test_pics',
	'host': 'localhost',
	'port': 3306,
	'user': 'root',
	'password': 'Irtpws2b'
}

# where templates are located; requires trailing backslash
TEMPLATE_DIRS = [
	os.path.join(WSGI_DIR, "templates")
]

# identify various routes with callbacks which can be taken
ROUTES = [
	(r"^css/?[_a-z]+\.css$", "css"),
	(r"photos/big/.*$", "photo.get_large_image"),
	(r"photos/?.*$", "photo"),
	(r"^mark/?$", "photo.get_marked_photos"),
	(r"^mark/update/?$", "photo.update_mark"),
	(r"^stats/?$", "stats"),
	(r"^/?$", "index")
	#(r'photos/?$', 'photo'),
	#(r'admin/?$', 'admin'),
	#(r'admin/photos/?$', 'admin.photos'),
	#(r'admin/photos/edit/(.+)?/?$', 'admin.edit_photo'),
	#(r'admin/photos/new/?$', 'admin.new_photo'),
	#(r'admin/photos/create/?$', 'admin.create_photo')
	#(r'hello/(.+)$', hello)
]

TEMPLATE_ENV = Environment(loader=FileSystemLoader(TEMPLATE_DIRS))

# important urls
BASE_URL = 'http://browser.hobby-site.com'
IMG_URL = "%s/img" % BASE_URL # find the canonical way to do this
THUMBNAIL_URL = "%s/thumbs" % IMG_URL 

# important directory paths
HTDOCS_DIR = os.path.join(ROOT_DIR, "htdocs")
HTDOCS_IMAGE_DIR = os.path.join(HTDOCS_DIR, "img")
THUMBNAIL_DIR = os.path.join(HTDOCS_IMAGE_DIR, "thumbs")
BASE_FS_PATH = "/media/sf_storage/Dropbox/Photos"

# important files
MARK_FILE = os.path.join(HTDOCS_DIR, "user_input", "marked_photos.txt")

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

DEFAULT_PER_PAGE = 20

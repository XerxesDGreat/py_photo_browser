import os
import json
from jinja2 import Environment, FileSystemLoader
from logger import Logger


class _Settings:
	######################
	# init functionality
	######################
	def __init__(self):
		self._config = {}
		self._init_config()

		# get the local settings to override the defaults here
		from config import local_config
		self._config.update(local_config.config)

		# perform post-local assignments
		self._post_local_assignments()
	
	def _init_config(self):
		# root directory for the app
		self._config["ROOT_DIR"] = os.path.realpath(os.path.join(os.path.dirname(__file__), "../../"))
	
		# important directory paths
		self._config["HTDOCS_DIR"] = os.path.join(self.ROOT_DIR, "htdocs")
		self._config["HTDOCS_IMAGE_DIR"] = os.path.join(self.HTDOCS_DIR, "img")
		self._config["THUMBNAIL_DIR"] = os.path.join(self.HTDOCS_IMAGE_DIR, "thumbs")
		self._config["WSGI_DIR"] = os.path.join(self.ROOT_DIR, "wsgi")
		self._config["CONFIG_DIR"] = os.path.join(self.WSGI_DIR, "config")

		# Root path to where your files are stored. You will need to define this
		self._config["BASE_FS_PATH"] = None
		
		# connection information for the database
		self._config["DATABASE"] = {}
	
		# set up the template parameters
		self._config["TEMPLATE_DIRS"] = [
			os.path.join(self.WSGI_DIR, "templates")
		]
		self._config["TEMPLATE_ENV"] = Environment(loader=FileSystemLoader(self.TEMPLATE_DIRS))

		# main app url. You will need to define this
		self._config["BASE_URL"] = None
		
		# identify various routes with callbacks which can be taken
		self._config["ROUTES"] = [
			# css documents
			(r"^css/?[_a-z]+\.css$", "css"),

			# photo opereations
			(r"^photos/single/.*$", "photo.get_one"),
			(r"^photos/big/.*$", "photo.get_large_image"),
			(r"^photos/small/.*$", "photo.get_small_image"),
			(r"^photos/[0-9]{4}/(0[0-9]|1[0-2])/([0-2][0-9]|3[0-1])/?$", "photo.get_photos_from_date"),
			(r"^photos/?([0-9]{4}/?((0[0-9]|1[0-2])/?)?)?$", "photo.get_dirs_from_date"),

			# marked photo operations
			(r"^marked/?$", "photo.get_marked_photos"),
			(r"^photos/mark/?$", "photo.mark_photo"),
			(r"^photos/unmark/?$", "photo.unmark_photo"),

			# importing
			(r"^import/preview/.*$", "import.preview"),
			(r"^import/confirm/?$", "import.update_and_confirm"),
			(r"^import/execute/?$", "import.execute_import"),
			(r"^import/progress/[a-z0-9]{32}", "import.get_progress"),
			(r"^import(/?|/.*)$", "import"),

			# stats
			(r"^stats/?$", "stats"),

			# main index page
			(r"^/?$", "index")
		]
		
		# important files
		self._config["MARK_FILE"] = os.path.join(self.HTDOCS_DIR, "user_input", "marked_photos.txt")
		
		self._config["SUPPORTED_IMG_EXTENSIONS"] = [
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

		self._config["DEFAULT_PER_PAGE"] = 20

		self._config["SITE_NAME"] = "Photo Browser"
	
	def _post_local_assignments(self):
		"""
		Assignments which depend on something in the local config to be assigned
		"""
		pass
	
	def __getattr__(self, name):
		if name not in self._config.keys():
			return None
		return self._config[name]

Settings = _Settings()

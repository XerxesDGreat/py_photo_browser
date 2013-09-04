import os
import json
from jinja2 import Environment, FileSystemLoader
from logger import Logger


class _Settings:
	APP_ROOT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "../../"))

	######################
	# init functionality
	######################
	def __init__(self):
		self._init = False
		self._config = {}
		# root directory for the app
		self._config["ROOT_DIR"] = _Settings.APP_ROOT_DIR
		
		# connection information for the database
		self._config["DATABASE"] = {}
	
		# where templates are located; requires trailing backslash
		self._config["TEMPLATE_DIRS"] = [
			os.path.join(self.ROOT_DIR, "wsgi", "templates")
		]
		
		# identify various routes with callbacks which can be taken
		self._config["ROUTES"] = [
			(r"^css/?[_a-z]+\.css$", "css"),
			(r"photos/big/.*$", "photo.get_large_image"),
			(r"photos/?.*$", "photo"),
			(r"^mark/?$", "photo.get_marked_photos"),
			(r"^mark/update/?$", "photo.update_mark"),
			(r"^stats/?$", "stats"),
			(r"^/?$", "index")
		]
		
		self._config["TEMPLATE_ENV"] = Environment(loader=FileSystemLoader(self.TEMPLATE_DIRS))
		
		# important urls
		self._config["BASE_URL"] = 'http://browser.hobby-site.com'
		
		# important directory paths
		self._config["HTDOCS_DIR"] = os.path.join(self.ROOT_DIR, "htdocs")
		self._config["HTDOCS_IMAGE_DIR"] = os.path.join(self.ROOT_DIR, "htdocs", "img")
		self._config["THUMBNAIL_DIR"] = os.path.join(self.ROOT_DIR, "htdocs", "img", "thumbs")
		self._config["BASE_FS_PATH"] = "/media/sf_storage/Dropbox/Photos"
		self._config["CONFIG_DIR"] = os.path.join(self.ROOT_DIR, "wsgi", "config")
		
		# important files
		self._config["MARK_FILE"] = os.path.join(self.ROOT_DIR, "htdocs", "user_input", "marked_photos.txt"),
		
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
		

	def init(self, environment):
		if self._init == True:
			return

		# get the environment stuff
		config_file = os.path.join(self.CONFIG_DIR, "%s.json" % environment["HTTP_HOST"])
		if not os.path.exists(config_file):
			raise Exception("a settings file for this environment [%s] has not been created (expecting %s)" % (environment["HTTP_HOST"], environment["HTTP_HOST"] + ".json"))
		f = open(config_file)
		env_config = json.loads(f.read())
		f.close()
		self._config.update(env_config)

		self._init = True
	
	def __getattr__(self, name):
		if name not in self._config.keys():
			return None
		return self._config[name]

Settings = _Settings()

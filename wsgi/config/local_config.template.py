import os

config = {}

# configuration for your mysql database
config["DATABASE"] = {
	"name": "mydb",
	"host": "myhost",
	"port": "myport",
	"user": "myuser",
	"password": "mypass"
}

# base url for the website
config["BASE_URL"] = "http://mysite.com"

# LOG_LEVEL
# Bitmask for which types of logs should be surfaced
# 1=fatal, 2=warning, 4=error, 8=info, 16=debug
# ex: 1|2 means show only fatals + warnings; 1|8 means show only fatals + info
config["LOG_LEVEL"] = 1|2|4|8|16

# Name of the application to be displayed in HTML
config["SITE_NAME"] = "Photo Browser"

# base directory which stores the image files
config["BASE_FS_PATH"] = "/media/sf_storage/Dropbox/Photos"

# base directory for the files to be imported
config["IMPORT_DIR"] = os.path.join(config["BASE_FS_PATH"], "import")

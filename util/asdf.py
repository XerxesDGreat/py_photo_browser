import MySQLdb
import os
import re
db = MySQLdb.connect(
	host="localhost",
	user="browser-dev-user",
	passwd="browser-dev-password",
	db="dev-photo-browser"
)
c = db.cursor()

def filename_in_db(c):
	query = "select count(*) from photos where filename='%s' and path='%s';"
	a = re.compile(r".*2010/08.*")
	b = re.compile(r".*not_img$")
	with open("/home/josh/tmp/2010_photo_db_import.txt") as f:
		for line in f.readlines():
			line = line.rstrip()
			if b.match(line) or not a.match(line):
				print "no_match"
				continue
			parts = line.split(" ")
			path, filename = os.path.split(parts[0])
			q = query % (filename, path)
			c.execute(q)
			rows = c.fetchall()
			print "%s/%s in db %d time" % (path, filename, rows[0][0])
			if rows[0][0] != 1:
				print "not in db: %s/%s" % (path, filename)

def db_has_file(c):
	query = "select * from photos where year(image_date) = 2010"
	c.execute(query)
	rows = c.fetchall()

	for r in rows:
		fpath = os.path.join(r[2], r[1])
		if not os.path.exists(fpath):
			print fpath

db_has_file(c)

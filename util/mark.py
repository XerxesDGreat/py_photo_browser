#!/usr/bin/python
import os
import MySQLdb
db = MySQLdb.connect(
	host="localhost",
	user="browser-dev-user",
	passwd="browser-dev-password",
	db="dev-photo-browser"
)
c = db.cursor()
f_query = "select * from photos where path='%s' and filename='%s';"
u_query = "update photos set marked = 1 where path='%s' and filename='%s';"

with open("/home/josh/www/photoBrowser/htdocs/user_input/marked_photos.txt") as f:
	for line in f.readlines():
		path, filename = os.path.split(line.rstrip())
		c.execute(f_query % (path, filename))
		rows = c.fetchall()
		if len(rows) < 1:
			print "%s/%s was not found!" % (path, filename)
		elif len(rows) > 1:
			print "multiples found for %s/%s" % (path, filename)
		else:
			print "executing for %s/%s" % (path, filename)
			c.execute(u_query % (path, filename))
			db.commit()


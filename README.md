Python Photo Browser
====================

A web application for browsing and marking photos for review. Inspired by having
a large photo collection to sort through to weed out unwanted photos, and the
desire to not be tied to one computer to do so, I decided to make an app which
allows me to go through all the photos in my collection and mark them for later
review. This later review step is not fully thought out yet, but at least I
have a list of photos to review

Features
--------

* Import script for pulling photos into the database, along with creation of
small and medium thumbnails
* Dynamic thumbail creation for directory browsing
* Dynamic larger thumbnail creation for Lightbox browsing
* Allows marking files for deletion as a flag in the database
* Stats page which reports on how many thumbs have been created, how much disk
space has been consumed by thumbnails, etc.

Requirements
------------

* Python Image Library (PIL) [link](http://www.pythonware.com/products/pil/)
* ExifRead [link](https://pypi.python.org/pypi/ExifRead)
* Apache with mod\_wsgi
* MySQLdb
* tested/developed in Python 2.7.3 on Ubuntu Linux

Changeset
---------

* v0.0.0 Initial commit; functional web app
* v0.0.1 Add in Lightbox and dynamic creation of large thumbnails
* v0.1.0 Use database backend rather than file system backend

Roadmap
-------

* Album creation
* Import script which will allow moving items from an import directory into
directories based on the date (YYYY/MM/DD/&lt;filename&gt;)
* Support for newly imported files to be surfaced until first seen

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

* Dynamic thumbnail creation for page views; if you don't access a directory,
a thumbnail won't be created for it
* Dynamic larger thumbnail creation for Lightbox browsing
* Reads files from an arbitrary directory structure and writes thumbnails to
the htdocs/img/thumbs/<size>/ directory
* Writes file paths of marked files to a plaintext file
* Stats page which reports on how many thumbs have been created, how much disk
space has been consumed by thumbnails, etc.

Requirements
------------

* Python Image Library (PIL) [link](http://www.pythonware.com/products/pil/)
* ExifRead [link](https://pypi.python.org/pypi/ExifRead)
* Apache with mod\_wsgi
* tested/developed in Python 2.7.3 on Ubuntu Linux

class Logger:
	_environ = None
	_logLevel = None 

	ERROR = 1
	WARNING = 2
	NOTICE = 4
	DEBUG = 8

	@staticmethod
	def init(environ, logLevel = ERROR):
		Logger._environ = environ
		Logger._logLevel = logLevel

	@staticmethod
	def isInit ():
		 return Logger._environ != None
	
	@staticmethod
	def error(msg):
		if Logger._logLevel & Logger.ERROR:
			Logger._log("ERROR: " + msg)

	@staticmethod
	def warning(msg):
		if Logger._logLevel & Logger.WARNING:
			Logger._log("WARNING: " + msg)
	
	@staticmethod
	def notice(msg):
		if Logger._logLevel & Logger.NOTICE:
			Logger._log("NOTICE: " + msg)
	
	@staticmethod
	def debug(msg):
		if Logger._logLevel & Logger.DEBUG:
			Logger._log("DEBUG: " + msg)

	@staticmethod
	def _log(msg):
		assert Logger.isInit(), "must initialize Logger before use"
		print >> Logger._environ['wsgi.errors'], msg
	
	@staticmethod
	def setLogLevel(level):
		Logger._logLevel = level

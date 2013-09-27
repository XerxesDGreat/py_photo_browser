import inspect
import os

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
			Logger._log("ERROR", msg)

	@staticmethod
	def warning(msg):
		if Logger._logLevel & Logger.WARNING:
			Logger._log("WARNING", msg)
	
	@staticmethod
	def notice(msg):
		if Logger._logLevel & Logger.NOTICE:
			Logger._log("NOTICE", msg)
	
	@staticmethod
	def debug(msg):
		if Logger._logLevel & Logger.DEBUG:
			Logger._log("DEBUG,", msg)

	@staticmethod
	def _log(log_type, msg):
		assert Logger.isInit(), "must initialize Logger before use"
		'''
		frames = inspect.stack()
		if len(frames) < 3:
			frame_str = ""
		else:
			caller_frame = frames[2]
			_, file_name = os.path.split(caller_frame[1])
			frame_str = "::".join([file_name, str(caller_frame[2]), caller_frame[3]])
		'''
		frame_str = ""
		print >> Logger._environ, "[%s] %s: %s" % (frame_str, log_type, str(msg))
	
	@staticmethod
	def setLogLevel(level):
		Logger._logLevel = level

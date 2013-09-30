import inspect
import os

class Logger:
	_environ = None
	_log_level = None 

	FATAL = 1
	ERROR = 2
	WARNING = 4
	INFO = 8
	DEBUG = 16

	@staticmethod
	def init(environ, log_level = None):
		"""
		Initializes the logger

		@param environ anything which can be written to (string io, file handle, etc)
		@param log_level bitmask for which log levels to report
		"""
		Logger._environ = environ
		if log_level == None:
			log_level = Logger.FATAL|Logger.ERROR|Logger.WARNING|Logger.INFO
		Logger._log_level = log_level

	@staticmethod
	def set_log_level(level):
		"""
		setter for the log level, allowing it to be changed during runtime
		"""
		Logger._log_level = level


	@staticmethod
	def fatal(msg):
		"""
		Logs a fatal error
		"""
		if Logger._log_level & Logger.FATAL:
			Logger._log("FATAL", msg)
	
	@staticmethod
	def error(msg):
		"""
		Logs an error
		"""
		if Logger._log_level & Logger.ERROR:
			Logger._log("ERROR", msg)

	@staticmethod
	def warning(msg):
		"""
		Logs a warning
		"""
		if Logger._log_level & Logger.WARNING:
			Logger._log("WARNING", msg)
	
	@staticmethod
	def info(msg):
		"""
		Logs some info
		"""
		if Logger._log_level & Logger.INFO:
			Logger._log("INFO", msg)
	
	@staticmethod
	def debug(msg):
		"""
		Logs a debug message
		"""
		if Logger._log_level & Logger.DEBUG:
			Logger._log("DEBUG", msg)
	
	@staticmethod
	def _is_init ():
		"""
		Checks to see if Logger has been initialized
		"""
		return Logger._environ != None

	@staticmethod
	def _log(log_type, msg):
		"""
		Writes the provided msg to the environment
		"""
		assert Logger._is_init(), "must initialize Logger before use"
		frame_str = Logger._get_stack_info()
		print >> Logger._environ, "[%s] %s: %s" % (frame_str, log_type, str(msg))
	
	@staticmethod
	def _get_stack_info():
		"""
		Fetches stack info about where this log was called
		"""
		frames = inspect.stack()
		if len(frames) < 3:
			frame_str = ""
		else:
			caller_frame = frames[3]
			_, file_name = os.path.split(caller_frame[1])
			frame_str = "::".join([file_name, str(caller_frame[2]), caller_frame[3]])
		return frame_str
	

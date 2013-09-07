from settings import Settings as S
import MySQLdb
from logger import Logger

class Database:
	_db = None
	_cursor = None

	@staticmethod
	def _init():
		if (Database._cursor != None and Database._db != None):
			return

		cfg = S.DATABASE
		Database._db = MySQLdb.connect(
			host=cfg['host'],
			user=cfg['user'],
			passwd=cfg['password'],
			db=cfg['name']
		)
		Database._cursor = Database._db.cursor()

	@staticmethod	
	def fetch_all_from_table(table_name):
		Database._init()
		query = "SELECT * FROM `%s`" % table_name
		return Database._do_query(query)
	
	@staticmethod
	def fetch_one_by_id (table_name, id):
		Database._init()
		query = "SELECT * FROM `%s` WHERE `id` = %d" % (table_name, id)
		return Database._do_query(query)

	@staticmethod
	def fetch_by_properties(table_name, property_dict, limit=None, offset=None):
		Database._init()
		field_value_list = []
		for field_name, value in property_dict.iteritems():
			field_value_list.append("`%s` = \"%s\"" % (field_name, value))
		limit_stmt = "" if limit == None else "LIMIT=%d" % limit
		offset_stmt = "" if offset == None else "OFFSET=%d" % offset
		query = "SELECT * FROM `%s` WHERE %s %s %s;" % (
			table_name,
			" AND ".join(field_value_list),
			limit_stmt,
			offset_stmt
		)
		return Database._do_query(query)

	@staticmethod
	def update (table_name, id, data_list):
		Database._init()
		query = "UPDATE `%s` SET" % (table_name)
		value_list = []
		query_parts = []
		for field, value, repl_type in data_list:
			query_parts.append("`%s` = %s" % (field, repl_type))
			value_list.append(value)
		query = "%s %s" % (query, " AND ".join(query_parts))
		value_tuple = tuple(value_list)
		Logger.debug(query)
		return 'blah'

	@staticmethod
	def create (table_name, data_list):
		Database._init()
		#query = 'INSERT INTO `' + table_name + '` SET '
		value_list = []
		field_list = []
		repl_type_list = []
		for field, value, repl_type in data_list:
			value_list.append(value)
			field_list.append(field)
			repl_type_list.append(repl_type)
		query = "INSERT INTO `%s` (`%s`) VALUES (%s)" % (
			table_name,
			"`, `".join(field_list),
			", ".join(repl_type_list)
		)
		value_tuple = tuple(value_list)
		Logger.debug(query)
		return Database._do_query(query, [value_tuple])

	@staticmethod
	def _do_query(query, values = [], commit = True):
		Logger.debug(query)
		results = []
		try:
			Database._cursor.execute(query, values)
			if commit:
				Database._db.commit()
			results = Database._cursor.fetchall()
			Logger.debug(results)

		except Exception, e:
			Logger.debug("database exception caught: %s" % str(e))
			Logger.error('some exception caught')
			Database._db.rollback()

		Logger.debug(repr(results))
		return results

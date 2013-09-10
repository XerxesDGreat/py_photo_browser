from settings import Settings as S
import MySQLdb
from logger import Logger

class Database:
	DB_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
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
	def fetch_by_properties(table_name, fields, limit=None, offset=None):
		Database._init()
		limit_stmt = "" if limit == None else "LIMIT=%d" % limit
		offset_stmt = "" if offset == None else "OFFSET=%d" % offset
		query = "SELECT * FROM `%s` WHERE %s %s %s;" % (
			table_name,
			" AND ".join([f.get_query_string() for f in fields]),
			limit_stmt,
			offset_stmt
		)
		return Database._do_query(query)
	
	@staticmethod
	def fetch_unique_field_values(table_name, unique_field, criteria_fields = []):
		Database._init()
		where_stmt = ""
		if len(criteria_fields) > 0:
			where_stmt = "WHERE %s" % " AND ".join([f.get_query_string() for f in criteria_fields])
		query = "SELECT DISTINCT %s from `%s` %s;" % (
			unique_field.get_query_string(),
			table_name,
			where_stmt
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
		resp = Database._do_query(query, value_tuple)
		return Database._cursor.lastrowid

	@staticmethod
	def _do_query(query, values = None, commit = True):
		Logger.debug("Executing query: %s" % query)
		results = []
		try:
			Database._cursor.execute(query, values)
			if commit:
				Database._db.commit()
			results = Database._cursor.fetchall()

		except Exception, e:
			Logger.debug("database exception caught: %s" % str(e))
			Logger.debug("query: %s, values: %s, commit: %s" % (
				str(query),str(values), str(commit)))
			Logger.error('some exception caught')
			Database._db.rollback()

		return results

class FetchFieldArg():
	CMP_LT = "<"
	CMP_GT = ">"
	CMP_LTE = "<="
	CMP_GTE = ">="
	CMP_EQ = "="
	CMP_NE = "<>"
	CMP_BETWEEN = "BETWEEN"
	CMP_IN = "IN"

	DB_OP_YEAR = "YEAR"
	DB_OP_MONTH = "MONTH"
	DB_OP_DAY = "DAY"

	def __init__(self, field, compare_operation = None, compare_value = None, db_op = None):
		self._field = field
		self._compare_operation = compare_operation
		self._compare_value = compare_value
		self._db_op = db_op

	def get_query_string(self):
		if self._db_op == None:
			field_str = "`%s`" % self._field
		else:
			field_str = "%s(`%s`)" % (self._db_op, self._field)
		if self._compare_operation == FetchFieldArg.CMP_BETWEEN:
			str = "%s BETWEEN '%s' AND '%s'" % (
				field_str,
				self._compare_value[0],
				self._compare_value[1]
			)
		elif self._compare_operation != None:
			str = "%s %s '%s'" % (
				field_str,
				self._compare_operation,
				self._compare_value
			)
		else:
			str = field_str
		return str

from settings import Settings as S
from logger import Logger

import MySQLdb
import time

class Database:
	DB_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
	_db = None
	_cursor = None

	@staticmethod
	def _init(force=False):
		if Database._cursor != None and Database._db != None and not force:
			return

		cfg = S.DATABASE
		Database._db = MySQLdb.connect(
			host=cfg['host'],
			user=cfg['user'],
			passwd=cfg['password'],
			db=cfg['name']
		)
		Database._cursor = Database._db.cursor()

	#TODO: we can certainly consolidate a bunch of the query creating functions

	@staticmethod	
	def fetch(table_name, fields=[], args=[], limit=None, offset=None):
		"""
		Builds a select query given the parameters. This is the most low-level
		fetching method.
		"""
		Database._init()
		Database._assert_valid_args(args)
		Database._assert_valid_fields(fields)

		limit_stmt = "" if limit == None else "LIMIT %d" % limit
		offset_stmt = "" if offset == None else "OFFSET %d" % offset
		where_stmt = ""
		if len(args) > 0:
			where_stmt = "WHERE %s" % " AND ".join([a.get_query_string() for a in args])
		query = "SELECT %s FROM `%s` %s %s %s;" % (
			", ".join([f.get_query_string() for f in fields]),
			table_name,
			where_stmt,
			limit_stmt,
			offset_stmt
		)
		return Database._do_query_wrapper(query)
	
	@staticmethod
	def _assert_valid_args(args):
		pass
	
	@staticmethod
	def _assert_valid_fields(args):
		pass
		
	@staticmethod
	def fetch_all_from_table(table_name):
		"""
		Shortcut to get all fields from the requested table
		"""
		field = FieldArg("*")
		return Database.fetch(table_name, fields=[field])
	
	@staticmethod
	def fetch_one_by_id (table_name, id):
		"""
		Shortcut to get the record for id from the requested table
		"""
		field = FieldArg("*")
		arg = FieldArg("id", FieldArg.CMP_EQ, id)
		return Database.fetch(table_name, [field], [arg])

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
		return Database._do_query_wrapper(query)
	
	@staticmethod
	def fetch_max_id(table_name):
		field = FieldArg("id", None, None, FieldArg.DB_OP_MAX)
		result_set = Database.fetch(table_name, [field])
		return result_set[0][0]

	@staticmethod
	def update (table_name, values_to_update, id_values):
		Database._init()
		query = "UPDATE `%s` SET %s WHERE %s" % (
			table_name,
			", ".join([v.get_query_string() for v in values_to_update]),
			" AND ".join([a.get_query_string() for a in id_values])
		)
		return Database._do_query_wrapper(query)
	
	@staticmethod
	def update_by_id(table_name, id, values_to_update):
		id_arg = FieldArg("id", FieldArg.CMP_EQ, id)
		Database.update(table_name, values_to_update, [id_arg])

	@staticmethod
	def create (table_name, data_list):
		Database._init()
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
		resp = Database._do_query_wrapper(query, value_tuple)
		return Database._cursor.lastrowid
	
	@staticmethod
	def fetch_current_timestamp():
		return time.strftime(Database.DB_DATE_FORMAT)

	@staticmethod
	def _do_query_wrapper(query, values = None, commit = True):
		Logger.info("Executing query: %s" % query)
		results = []
		try:
			results = Database._do_query(query, values, commit)

		except MySQLdb.OperationalException as e:
			if e.errno == 2006:
				self._init(True)
				Database._do_query(query, values, commit)

		except Exception as e:
			Logger.error("database exception caught: %s" % str(e))
			Logger.info("query: %s, values: %s, commit: %s" % (
				str(query),str(values), str(commit)))
			Database._db.rollback()

		return results

	@staticmethod
	def _do_query(query, values = None, commit = True):
		Database._cursor.execute(query, values)
		if commit:
			Database._db.commit()
		results = Database._cursor.fetchall()
		return results

class FieldArg(object):
	CMP_LT = "<"
	CMP_GT = ">"
	CMP_LTE = "<="
	CMP_GTE = ">="
	CMP_EQ = "="
	CMP_NE = "<>"
	CMP_BETWEEN = "BETWEEN"
	CMP_IN = "IN"
	CMP_NOT_IN = "NOT IN"

	DB_OP_YEAR = "YEAR"
	DB_OP_MONTH = "MONTH"
	DB_OP_DAY = "DAY"
	DB_OP_COUNT = "COUNT"
	DB_OP_MIN = "MIN"
	DB_OP_MAX = "MAX"

	def __init__(self, field, compare_operation = None, compare_value = None, db_op = None):
		self._field = field
		self._compare_operation = compare_operation
		self._compare_value = compare_value
		self._db_op = db_op

	def get_query_string(self):
		field_str = "`%s`" % self._field if self._field != "*" else self._field
		if self._db_op != None:
			field_str = "%s(%s)" % (self._db_op, field_str)
		if self._compare_operation == FieldArg.CMP_BETWEEN:
			str = "%s BETWEEN '%s' AND '%s'" % (
				field_str,
				self._compare_value[0],
				self._compare_value[1]
			)
		elif self._compare_operation in [FieldArg.CMP_IN, FieldArg.CMP_NOT_IN]:
			str = "%s %s ('%s')" % (
				field_str,
				self._compare_operation,
				"', '".join(self._compare_value)
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

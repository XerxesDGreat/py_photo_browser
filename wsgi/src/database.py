from settings import settings
import MySQLdb
from logger import Logger

class Database:
	_db = None
	_cursor = None

	@staticmethod
	def _init():
		if (Database._cursor != None and Database._db != None):
			return

		cfg = settings.DATABASE
		Database._db = MySQLdb.connect(
			host=cfg['host'],
			user=cfg['user'],
			passwd=cfg['password'],
			db=cfg['name']
		)
		Database._cursor = Database._db.cursor()

	@staticmethod	
	def fetchAllFromTable(tableName):
		Database._init()
		query = "SELECT * FROM " + tableName
		return Database._doQuery(query)
	
	@staticmethod
	def fetchOneById (tableName, id):
		Database._init()
		query = "SELECT * FROM " + tableName + " WHERE `id` = %s"
		valueList = [id]
		return Database._doQuery(query, valueList)

	@staticmethod
	def update (tableName, id, dataList):
		Database._init()
		query = 'UPDATE `' + tableName + '` SET '
		l = len(dataList)
		i = 0
		valueList = []
		for field, value, replType in dataList:
			query = query + '`' + field + '` = ' + replType
			if i <= (l - 1):
				query = query + ' AND '
			i += 1
			valueList.append(value)
		valueTuple = tuple(valueList)
		Logger.debug(query)
		Logger.debug(repr(valueTuple))
		return 'blah'

	@staticmethod
	def create (tableName, dataList):
		Database._init()
		query = 'INSERT INTO `' + tableName + '` SET '
		valueList = []
		fieldList = []
		replTypeList = []
		for field, value, replType in dataList:
			valueList.append(value)
			fieldList.append(field)
			replTypeList.append(replType)
		query = 'INSERT INTO `' + tableName + '` (`' + '`, `'.join(fieldList) + '`)'
		query = query + ' VALUES (' + ', '.join(replTypeList) + ')'
		valueTuple = tuple(valueList)
		Logger.debug(query)
		Logger.debug(repr(valueTuple))
		return Database._doQuery(query, [valueTuple])

	@staticmethod
	def _doQuery(query, values = [], commit = True):
		Logger.debug(query)
		results = []
		try:
			Database._cursor.execute(query, values)
			if commit:
				Database._db.commit()
			results = Database._cursor.fetchall()
			Logger.debug(results)

		except Exception, e:
			Logger.debug("database exception caught: " + str(e))
			Logger.error('some exception caught')
			Database._db.rollback()

		Logger.debug(repr(results))
		return results

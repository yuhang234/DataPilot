"""MySQL handler:SqlConnector + mysql 方言。"""

from datapilot.handlers.mysql_handler.connection_args import connection_args, connection_args_example
from datapilot.handlers.sql_base import SqlConnector


class MySQLHandler(SqlConnector):
    name = 'mysql'
    title = 'MySQL'
    driver = 'mysql+pymysql'
    default_port = 3306
    connection_args = connection_args
    connection_args_example = connection_args_example

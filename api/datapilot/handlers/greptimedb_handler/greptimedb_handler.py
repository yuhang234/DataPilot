"""GreptimeDB handler:MySQL 协议,复用 SqlConnector + mysql+pymysql。"""

from datapilot.handlers.greptimedb_handler.connection_args import connection_args, connection_args_example
from datapilot.handlers.sql_base import SqlConnector


class GreptimeDBHandler(SqlConnector):
    name = 'greptimedb'
    title = 'GreptimeDB'
    driver = 'mysql+pymysql'
    default_port = 4002
    connection_args = connection_args
    connection_args_example = connection_args_example

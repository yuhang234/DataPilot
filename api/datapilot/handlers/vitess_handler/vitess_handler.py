"""Vitess handler:MySQL 协议,复用 SqlConnector + mysql+pymysql。"""

from datapilot.handlers.sql_base import SqlConnector
from datapilot.handlers.vitess_handler.connection_args import connection_args, connection_args_example


class VitessHandler(SqlConnector):
    name = 'vitess'
    title = 'Vitess'
    driver = 'mysql+pymysql'
    default_port = 15306
    connection_args = connection_args
    connection_args_example = connection_args_example

"""Teradata handler:复用 SqlConnector + teradatasql 方言。"""

from datapilot.handlers.sql_base import SqlConnector
from datapilot.handlers.teradata_handler.connection_args import connection_args, connection_args_example


class TeradataHandler(SqlConnector):
    name = 'teradata'
    title = 'Teradata'
    driver = 'teradatasql'
    default_port = 1025
    connection_args = connection_args
    connection_args_example = connection_args_example

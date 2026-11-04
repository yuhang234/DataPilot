"""IBM Informix handler:复用 SqlConnector + informix。"""

from urllib.parse import quote_plus  # noqa: F401

from datapilot.handlers.informix_handler.connection_args import connection_args, connection_args_example
from datapilot.handlers.sql_base import SqlConnector


class InformixHandler(SqlConnector):
    name = 'informix'
    title = 'IBM Informix'
    driver = 'informix'
    default_port = 9088
    connection_args = connection_args
    connection_args_example = connection_args_example

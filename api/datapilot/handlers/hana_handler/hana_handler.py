"""SAP HANA handler:复用 SqlConnector + hana 方言。"""

from datapilot.handlers.hana_handler.connection_args import connection_args, connection_args_example
from datapilot.handlers.sql_base import SqlConnector


class HanaHandler(SqlConnector):
    name = 'hana'
    title = 'SAP HANA'
    driver = 'hana'
    default_port = 30015
    connection_args = connection_args
    connection_args_example = connection_args_example

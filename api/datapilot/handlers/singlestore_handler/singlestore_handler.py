"""SingleStore handler:MySQL 协议,复用 SqlConnector + mysql+pymysql。"""

from datapilot.handlers.singlestore_handler.connection_args import connection_args, connection_args_example
from datapilot.handlers.sql_base import SqlConnector


class SingleStoreHandler(SqlConnector):
    name = 'singlestore'
    title = 'SingleStore'
    driver = 'mysql+pymysql'
    default_port = 3306
    connection_args = connection_args
    connection_args_example = connection_args_example

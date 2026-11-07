"""业务演示种子(幂等、自包含、**完全离线**):给空白平台灌一套「电商零售经营分析」演示内容。

与 demo_seed.py(akshare 财经 demo,依赖外网 + 大量 ETL)不同,这里只依赖平台自身组件:
- 在平台 MySQL 里建一个独立的 demo 业务库 ``datapilot_demo``(维表 + 事实表 + 造数),
  再把它注册成数据源 → 数据模型 → 指标 → 看板,全部走**真实可执行 SQL**,不是贴图。
- 任务模板 / 调度任务 / 执行实例 / 任务日志 / DAG 工作流 / 告警策略与记录 / AI 模型·应用·工具·技能 /
  知识库(文档 + 分段 + 向量)/ 看板,一次灌齐,前端各页面直接有内容可看。

幂等:所有 demo 对象都用固定 id 或固定 code,每次执行先删后插,可反复跑。
离线:不访问任何外网;知识库用 provider=local 的**特征哈希向量**(见 module_rag/embedding.py),
无需 Embedding Key 即可训练 + 召回。

用法(容器内,镜像无需重建):
    docker exec -i <backend容器名> python - < api/demo_seed_business.py
或进容器后:
    python demo_seed_business.py

清理(demo 业务库 + demo 平台数据):
    docker exec -i <backend容器名> python - < api/demo_seed_business.py --clean
"""

import datetime
import json
import random
import sys
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text

from config.env import DataBaseConfig
from module_task_schedule.sync_db import get_sync_session_local
from utils.crypto_util import CryptoUtil

TENANT = 100
DEMO_DB = 'datapilot_demo'
DS_ID = 'demo_ds_warehouse'
DS_CODE = 'demo_warehouse'
NOW = datetime.datetime.now()


def _platform_engine(database: str | None = None):
    """连平台 MySQL(默认不指定库,便于 CREATE DATABASE)。"""
    url = (
        f'mysql+pymysql://{DataBaseConfig.db_username}:{quote_plus(DataBaseConfig.db_password)}'
        f'@{DataBaseConfig.db_host}:{DataBaseConfig.db_port}/'
    )
    if database:
        url += database
    return create_engine(url + '?charset=utf8mb4', pool_pre_ping=True, future=True)


# ---------------------------------------------------------------------------
# 1) demo 业务库:维表 + 事实表 + 造数(固定随机种子,数据可复现)
# ---------------------------------------------------------------------------
_DDL = [
    """CREATE TABLE IF NOT EXISTS dim_region (
        region_code VARCHAR(16) PRIMARY KEY COMMENT '区域编码',
        region_name VARCHAR(32) NOT NULL COMMENT '区域名称',
        area VARCHAR(16) NOT NULL COMMENT '大区'
    ) COMMENT '区域维表'""",
    """CREATE TABLE IF NOT EXISTS dim_product (
        product_id VARCHAR(16) PRIMARY KEY COMMENT '商品编码',
        product_name VARCHAR(64) NOT NULL COMMENT '商品名称',
        category VARCHAR(32) NOT NULL COMMENT '商品类目',
        price DECIMAL(10,2) NOT NULL COMMENT '标价(元)',
        cost DECIMAL(10,2) NOT NULL COMMENT '成本(元)',
        launch_date DATE NOT NULL COMMENT '上架日期'
    ) COMMENT '商品维表'""",
    """CREATE TABLE IF NOT EXISTS dim_customer (
        customer_id VARCHAR(16) PRIMARY KEY COMMENT '客户编码',
        customer_name VARCHAR(32) NOT NULL COMMENT '客户名称',
        city VARCHAR(32) NOT NULL COMMENT '城市',
        region_name VARCHAR(32) NOT NULL COMMENT '所属区域',
        member_level VARCHAR(16) NOT NULL COMMENT '会员等级',
        register_date DATE NOT NULL COMMENT '注册日期'
    ) COMMENT '客户维表'""",
    """CREATE TABLE IF NOT EXISTS fact_order (
        order_id VARCHAR(24) PRIMARY KEY COMMENT '订单号',
        order_date DATE NOT NULL COMMENT '下单日期',
        product_id VARCHAR(16) NOT NULL COMMENT '商品编码',
        customer_id VARCHAR(16) NOT NULL COMMENT '客户编码',
        region_name VARCHAR(32) NOT NULL COMMENT '收货区域',
        channel VARCHAR(16) NOT NULL COMMENT '下单渠道',
        quantity INT NOT NULL COMMENT '件数',
        amount DECIMAL(12,2) NOT NULL COMMENT '实付金额(元)',
        discount DECIMAL(6,2) NOT NULL COMMENT '折扣率',
        status VARCHAR(16) NOT NULL COMMENT '订单状态',
        KEY idx_order_date (order_date),
        KEY idx_product (product_id)
    ) COMMENT '订单事实表'""",
    """CREATE TABLE IF NOT EXISTS fact_traffic (
        stat_date DATE NOT NULL COMMENT '日期',
        channel VARCHAR(16) NOT NULL COMMENT '渠道',
        visits INT NOT NULL COMMENT '访问量(UV)',
        orders INT NOT NULL COMMENT '下单数',
        ad_cost DECIMAL(12,2) NOT NULL COMMENT '投放费用(元)',
        PRIMARY KEY (stat_date, channel)
    ) COMMENT '渠道流量日事实表'""",
]

_REGIONS = [
    ('R01', '华东', '东区'),
    ('R02', '华南', '南区'),
    ('R03', '华北', '北区'),
    ('R04', '华中', '中区'),
    ('R05', '西南', '西区'),
    ('R06', '东北', '北区'),
]

_CATEGORIES = ['手机数码', '家用电器', '美妆个护', '服饰鞋包', '食品生鲜', '运动户外', '母婴玩具', '图书文娱']
_CHANNELS = ['APP', '小程序', 'H5', '抖音直播', '天猫旗舰店']
_CITIES = ['上海', '杭州', '深圳', '广州', '北京', '成都', '武汉', '西安', '南京', '沈阳', '长沙', '重庆']
_LEVELS = ['普通会员', '银卡会员', '金卡会员', '钻石会员']
_STATUS = ['已完成', '已完成', '已完成', '已完成', '已退款', '待发货']


def _build_demo_database() -> dict:
    """重建 demo 业务库并造数,返回各表行数。"""
    eng = _platform_engine()
    with eng.begin() as conn:
        conn.execute(text(f'CREATE DATABASE IF NOT EXISTS `{DEMO_DB}` DEFAULT CHARSET utf8mb4'))
    eng.dispose()

    eng = _platform_engine(DEMO_DB)
    with eng.begin() as conn:
        for ddl in _DDL:
            conn.execute(text(ddl))
        for t in ('fact_order', 'fact_traffic', 'dim_product', 'dim_customer', 'dim_region'):
            conn.execute(text(f'DELETE FROM {t}'))

        rnd = random.Random(20240601)  # 固定种子:每次造出来的数据一致
        today = datetime.date.today()
        start = today - datetime.timedelta(days=365)

        conn.execute(
            text('INSERT INTO dim_region (region_code, region_name, area) VALUES (:c, :n, :a)'),
            [{'c': c, 'n': n, 'a': a} for c, n, a in _REGIONS],
        )

        products = []
        for i in range(1, 161):
            cat = rnd.choice(_CATEGORIES)
            price = round(rnd.uniform(39, 4999), 2)
            products.append(
                {
                    'id': f'P{i:04d}',
                    'name': f'{cat}精选款 {i:03d}',
                    'cat': cat,
                    'price': price,
                    'cost': round(price * rnd.uniform(0.45, 0.72), 2),
                    'launch': start - datetime.timedelta(days=rnd.randint(0, 720)),
                }
            )
        conn.execute(
            text(
                'INSERT INTO dim_product (product_id, product_name, category, price, cost, launch_date) '
                'VALUES (:id, :name, :cat, :price, :cost, :launch)'
            ),
            products,
        )

        names_a = ['张', '王', '李', '刘', '陈', '杨', '黄', '赵', '周', '吴', '徐', '孙']
        names_b = ['伟', '芳', '娜', '敏', '静', '磊', '洋', '强', '军', '洋', '杰', '婷']
        customers = []
        for i in range(1, 401):
            region = rnd.choice(_REGIONS)[1]
            customers.append(
                {
                    'id': f'C{i:04d}',
                    'name': f'{rnd.choice(names_a)}{rnd.choice(names_b)}',
                    'city': rnd.choice(_CITIES),
                    'region': region,
                    'level': rnd.choices(_LEVELS, weights=[5, 3, 2, 1])[0],
                    'reg': start - datetime.timedelta(days=rnd.randint(0, 900)),
                }
            )
        conn.execute(
            text(
                'INSERT INTO dim_customer (customer_id, customer_name, city, region_name, member_level, register_date) '
                'VALUES (:id, :name, :city, :region, :level, :reg)'
            ),
            customers,
        )

        orders = []
        for i in range(1, 8001):
            p = rnd.choice(products)
            c = rnd.choice(customers)
            qty = rnd.choices([1, 1, 1, 2, 2, 3, 4, 5], k=1)[0]
            discount = rnd.choice([1.00, 1.00, 1.00, 0.95, 0.90, 0.85, 0.80])
            # 日期在全窗口内均匀分布(不向近期堆叠,避免日趋势图末尾出现假尖峰)
            day = today - datetime.timedelta(days=rnd.randint(0, 364))
            orders.append(
                {
                    'id': f'SO{today.strftime("%Y%m%d")}{i:05d}',
                    'd': day,
                    'pid': p['id'],
                    'cid': c['id'],
                    'region': c['region'],
                    'channel': rnd.choices(_CHANNELS, weights=[6, 4, 2, 3, 3])[0],
                    'qty': qty,
                    'amount': round(p['price'] * qty * discount, 2),
                    'discount': round(1 - discount, 2),
                    'status': rnd.choice(_STATUS),
                }
            )
        conn.execute(
            text(
                'INSERT INTO fact_order (order_id, order_date, product_id, customer_id, region_name, channel, '
                'quantity, amount, discount, status) VALUES (:id, :d, :pid, :cid, :region, :channel, :qty, '
                ':amount, :discount, :status)'
            ),
            orders,
        )

        traffic = []
        for d in range(365):
            day = start + datetime.timedelta(days=d)
            for ch in _CHANNELS:
                visits = rnd.randint(800, 9000)
                traffic.append(
                    {
                        'd': day,
                        'ch': ch,
                        'visits': visits,
                        'orders': int(visits * rnd.uniform(0.02, 0.09)),
                        'cost': round(visits * rnd.uniform(0.4, 1.6), 2),
                    }
                )
        conn.execute(
            text(
                'INSERT INTO fact_traffic (stat_date, channel, visits, orders, ad_cost) '
                'VALUES (:d, :ch, :visits, :orders, :cost)'
            ),
            traffic,
        )
    eng.dispose()
    return {
        'dim_region': len(_REGIONS),
        'dim_product': len(products),
        'dim_customer': len(customers),
        'fact_order': len(orders),
        'fact_traffic': len(traffic),
    }


# ---------------------------------------------------------------------------
# 2) 数据源 / 数据模型 / 指标
# ---------------------------------------------------------------------------
_FIELDS = {
    'fact_order': [
        {'name': 'order_id', 'type': 'varchar(24)', 'nullable': False, 'comment': '订单号'},
        {'name': 'order_date', 'type': 'date', 'nullable': False, 'comment': '下单日期'},
        {'name': 'product_id', 'type': 'varchar(16)', 'nullable': False, 'comment': '商品编码'},
        {'name': 'customer_id', 'type': 'varchar(16)', 'nullable': False, 'comment': '客户编码'},
        {'name': 'region_name', 'type': 'varchar(32)', 'nullable': False, 'comment': '收货区域'},
        {'name': 'channel', 'type': 'varchar(16)', 'nullable': False, 'comment': '下单渠道'},
        {'name': 'quantity', 'type': 'int', 'nullable': False, 'comment': '件数'},
        {'name': 'amount', 'type': 'decimal(12,2)', 'nullable': False, 'comment': '实付金额(元)'},
        {'name': 'discount', 'type': 'decimal(6,2)', 'nullable': False, 'comment': '折扣率'},
        {'name': 'status', 'type': 'varchar(16)', 'nullable': False, 'comment': '订单状态'},
    ],
    'dim_product': [
        {'name': 'product_id', 'type': 'varchar(16)', 'nullable': False, 'comment': '商品编码'},
        {'name': 'product_name', 'type': 'varchar(64)', 'nullable': False, 'comment': '商品名称'},
        {'name': 'category', 'type': 'varchar(32)', 'nullable': False, 'comment': '商品类目'},
        {'name': 'price', 'type': 'decimal(10,2)', 'nullable': False, 'comment': '标价(元)'},
        {'name': 'cost', 'type': 'decimal(10,2)', 'nullable': False, 'comment': '成本(元)'},
        {'name': 'launch_date', 'type': 'date', 'nullable': False, 'comment': '上架日期'},
    ],
    'dim_customer': [
        {'name': 'customer_id', 'type': 'varchar(16)', 'nullable': False, 'comment': '客户编码'},
        {'name': 'customer_name', 'type': 'varchar(32)', 'nullable': False, 'comment': '客户名称'},
        {'name': 'city', 'type': 'varchar(32)', 'nullable': False, 'comment': '城市'},
        {'name': 'region_name', 'type': 'varchar(32)', 'nullable': False, 'comment': '所属区域'},
        {'name': 'member_level', 'type': 'varchar(16)', 'nullable': False, 'comment': '会员等级'},
        {'name': 'register_date', 'type': 'date', 'nullable': False, 'comment': '注册日期'},
    ],
    'fact_traffic': [
        {'name': 'stat_date', 'type': 'date', 'nullable': False, 'comment': '日期'},
        {'name': 'channel', 'type': 'varchar(16)', 'nullable': False, 'comment': '渠道'},
        {'name': 'visits', 'type': 'int', 'nullable': False, 'comment': '访问量(UV)'},
        {'name': 'orders', 'type': 'int', 'nullable': False, 'comment': '下单数'},
        {'name': 'ad_cost', 'type': 'decimal(12,2)', 'nullable': False, 'comment': '投放费用(元)'},
    ],
    'dim_region': [
        {'name': 'region_code', 'type': 'varchar(16)', 'nullable': False, 'comment': '区域编码'},
        {'name': 'region_name', 'type': 'varchar(32)', 'nullable': False, 'comment': '区域名称'},
        {'name': 'area', 'type': 'varchar(16)', 'nullable': False, 'comment': '大区'},
    ],
}

_MODELS = [
    ('dm_demo_order', '订单明细', 'fact_order', '订单事实表:一行一个订单,含金额/件数/渠道/区域/状态'),
    ('dm_demo_product', '商品维表', 'dim_product', '商品维表:类目、标价、成本'),
    ('dm_demo_customer', '客户维表', 'dim_customer', '客户维表:城市、区域、会员等级'),
    ('dm_demo_traffic', '渠道流量日表', 'fact_traffic', '渠道流量日事实:访问量、下单数、投放费用'),
    ('dm_demo_region', '区域维表', 'dim_region', '区域维表:区域与大区归属'),
]

_METRICS = [
    (
        'demo_gmv',
        'GMV(成交总额)',
        '订单实付金额之和(含退款单),口径见《经营指标口径手册》。',
        'dm_demo_order',
        {'agg': 'sum', 'field': 'amount'},
        [{'field': 'order_date', 'name': '日期'}, {'field': 'channel', 'name': '渠道'}],
        'order_date',
        '元',
    ),
    (
        'demo_order_cnt',
        '订单量',
        '已下单订单条数(不含取消),按 order_id 去重计数。',
        'dm_demo_order',
        {'agg': 'count', 'field': 'order_id'},
        [{'field': 'order_date', 'name': '日期'}, {'field': 'region_name', 'name': '区域'}],
        'order_date',
        '单',
    ),
    (
        'demo_aov',
        '客单价(AOV)',
        'GMV ÷ 订单量,反映单笔成交金额水平。',
        'dm_demo_order',
        {'agg': 'avg', 'field': 'amount'},
        [{'field': 'order_date', 'name': '日期'}],
        'order_date',
        '元',
    ),
    (
        'demo_refund_rate',
        '退款率',
        '退款订单数 ÷ 订单总数,按订单状态 = 已退款 统计。',
        'dm_demo_order',
        {'agg': 'count', 'field': 'order_id'},
        [{'field': 'order_date', 'name': '日期'}, {'field': 'status', 'name': '订单状态'}],
        'order_date',
        '%',
    ),
    (
        'demo_uv',
        '访问量(UV)',
        '各渠道日访问去重人数之和。',
        'dm_demo_traffic',
        {'agg': 'sum', 'field': 'visits'},
        [{'field': 'stat_date', 'name': '日期'}, {'field': 'channel', 'name': '渠道'}],
        'stat_date',
        '人',
    ),
]


def seed_metadata(db) -> None:
    """数据源 + 数据模型 + 指标(幂等:固定 code/id 先删后插)。"""
    secrets = json.dumps({'password': DataBaseConfig.db_password}, ensure_ascii=False)
    db.execute(text('DELETE FROM data_source WHERE id=:id OR code=:code'), {'id': DS_ID, 'code': DS_CODE})
    db.execute(
        text(
            'INSERT INTO data_source (id,name,code,source_type,family,config,secrets,status,last_test_at,remark,'
            'create_by,create_time,tenant_id) '
            "VALUES (:id,:name,:code,'mysql','rdbms',:cfg,:sec,'ok',:now,:remark,'admin',:now,:tenant)"
        ),
        {
            'id': DS_ID,
            'name': '电商业务库(Demo MySQL)',
            'code': DS_CODE,
            'cfg': json.dumps(
                {
                    'host': DataBaseConfig.db_host,
                    'port': DataBaseConfig.db_port,
                    'user': DataBaseConfig.db_username,
                    'database': DEMO_DB,
                },
                ensure_ascii=False,
            ),
            'sec': CryptoUtil.encrypt(secrets),
            'now': NOW,
            'remark': '演示用电商零售业务库:订单/商品/客户/渠道流量 5 张表,可直接在「数据查询」执行 SQL',
            'tenant': TENANT,
        },
    )

    for mid, name, obj, remark in _MODELS:
        db.execute(text('DELETE FROM data_model WHERE id=:id'), {'id': mid})
        db.execute(
            text(
                'INSERT INTO data_model (id,name,code,datasource_code,kind,object_name,db_schema,fields,auth,status,'
                'remark,create_by,create_time,tenant_id) '
                "VALUES (:id,:name,:code,:ds,'table',:obj,:schema,:fields,'query,extract,api',1,:remark,'admin',:now,:tenant)"
            ),
            {
                'id': mid,
                'name': name,
                'code': obj,
                'ds': DS_CODE,
                'obj': obj,
                'schema': DEMO_DB,
                'fields': json.dumps(_FIELDS[obj], ensure_ascii=False),
                'remark': remark,
                'now': NOW,
                'tenant': TENANT,
            },
        )

    for code, name, caliber, model_id, measure, dims, tf_field, unit in _METRICS:
        db.execute(text('DELETE FROM data_metric WHERE code=:c'), {'c': code})
        db.execute(
            text(
                'INSERT INTO data_metric (name,code,synonyms,caliber,model_id,measure,dimensions,time_field,unit,'
                'status,review_state,built_in,create_by,create_time,tenant_id) '
                "VALUES (:name,:code,:syn,:caliber,:model,:measure,:dims,:tf,:unit,'0','approved','0','admin',:now,:tenant)"
            ),
            {
                'name': name,
                'code': code,
                'syn': name.replace('(', ' ').replace(')', ''),
                'caliber': caliber,
                'model': model_id,
                'measure': json.dumps(measure, ensure_ascii=False),
                'dims': json.dumps(dims, ensure_ascii=False),
                'tf': tf_field,
                'unit': unit,
                'now': NOW,
                'tenant': TENANT,
            },
        )


# ---------------------------------------------------------------------------
# 3) 看板(全部用真实 SQL 出图)
# ---------------------------------------------------------------------------
_BOARD_ID = 'demo_board_shop'
_BOARD2_ID = 'demo_board_sales_health'
_CHART_ID = 'demo_chart_gmv_trend'


def _comp(cid, model_id, sql, chart_spec, x, y, w, h):
    return {
        'id': cid,
        'type': 'chart',
        'inline': {
            'modelId': model_id,
            'native': sql,
            'chartSpec': chart_spec,
        },
        'pos': {'x': x, 'y': y, 'w': w, 'h': h},
        'props': {'title': chart_spec['style']['title']},
        'subscribe': True,
    }


_SQL_GMV_TREND = (
    "SELECT DATE_FORMAT(order_date,'%Y-%m-%d') AS stat_date, ROUND(SUM(amount),2) AS gmv, COUNT(*) AS order_cnt "
    'FROM fact_order WHERE order_date >= {{start}} GROUP BY 1 ORDER BY 1'
)
_SQL_CATEGORY = (
    'SELECT p.category AS category, ROUND(SUM(o.amount),2) AS gmv '
    'FROM fact_order o JOIN dim_product p ON o.product_id = p.product_id '
    'GROUP BY p.category ORDER BY gmv DESC LIMIT 8'
)
_SQL_CHANNEL = (
    'SELECT channel AS channel, ROUND(SUM(amount),2) AS gmv, COUNT(*) AS order_cnt '
    'FROM fact_order GROUP BY channel ORDER BY gmv DESC'
)
_SQL_REGION = (
    'SELECT region_name AS region_name, ROUND(SUM(amount),2) AS gmv, COUNT(*) AS order_cnt, '
    'ROUND(AVG(amount),2) AS aov FROM fact_order GROUP BY region_name ORDER BY gmv DESC'
)
_SQL_TRAFFIC = (
    "SELECT DATE_FORMAT(stat_date,'%Y-%m') AS month, ROUND(SUM(visits)/10000,2) AS uv_wan, "
    'ROUND(SUM(ad_cost)/10000,2) AS cost_wan FROM fact_traffic GROUP BY 1 ORDER BY 1'
)
_SQL_MEMBER = (
    'SELECT c.member_level AS member_level, ROUND(SUM(o.amount),2) AS gmv '
    'FROM fact_order o JOIN dim_customer c ON o.customer_id = c.customer_id '
    'GROUP BY c.member_level ORDER BY gmv DESC'
)
_SQL_STATUS = (
    'SELECT status AS order_status, COUNT(*) AS order_cnt FROM fact_order GROUP BY status ORDER BY order_cnt DESC'
)
_SQL_TOP_PRODUCT = (
    'SELECT p.product_name AS product_name, p.category AS category, ROUND(SUM(o.amount),2) AS gmv, '
    'SUM(o.quantity) AS qty FROM fact_order o JOIN dim_product p ON o.product_id = p.product_id '
    'GROUP BY p.product_name, p.category ORDER BY gmv DESC LIMIT 10'
)

_BOARD_COMPONENTS = [
    _comp(
        'c1',
        'dm_demo_order',
        _SQL_GMV_TREND,
        {
            'type': 'line',
            'x': 'stat_date',
            'ys': [{'field': 'gmv', 'agg': 'sum'}],
            'style': {'title': 'GMV 日趋势(元)', 'smooth': True, 'unit': '元'},
        },
        0,
        0,
        24,
        7,
    ),
    _comp(
        'c2',
        'dm_demo_order',
        _SQL_CATEGORY,
        {
            'type': 'bar',
            'x': 'category',
            'ys': [{'field': 'gmv', 'agg': 'sum'}],
            'sort': {'by': 'gmv', 'dir': 'desc'},
            'style': {'title': '类目 GMV 排行(元)', 'label': True},
        },
        0,
        7,
        12,
        7,
    ),
    _comp(
        'c3',
        'dm_demo_order',
        _SQL_CHANNEL,
        {
            'type': 'pie',
            'x': 'channel',
            'ys': [{'field': 'gmv', 'agg': 'sum'}],
            'style': {'title': '渠道 GMV 占比'},
        },
        12,
        7,
        12,
        7,
    ),
    _comp(
        'c4',
        'dm_demo_order',
        _SQL_REGION,
        {
            'type': 'table',
            'x': 'region_name',
            'ys': [
                {'field': 'gmv', 'agg': 'none'},
                {'field': 'order_cnt', 'agg': 'none'},
                {'field': 'aov', 'agg': 'none'},
            ],
            'style': {'title': '区域经营明细(GMV/订单量/客单价)'},
        },
        0,
        14,
        12,
        7,
    ),
    _comp(
        'c5',
        'dm_demo_traffic',
        _SQL_TRAFFIC,
        {
            'type': 'line',
            'x': 'month',
            'ys': [{'field': 'uv_wan', 'agg': 'sum'}, {'field': 'cost_wan', 'agg': 'sum'}],
            'style': {'title': '月度 UV 与投放费用(万)', 'smooth': True},
        },
        12,
        14,
        12,
        7,
    ),
]

_BOARD2_COMPONENTS = [
    _comp(
        'h1',
        'dm_demo_customer',
        _SQL_MEMBER,
        {
            'type': 'bar',
            'x': 'member_level',
            'ys': [{'field': 'gmv', 'agg': 'sum'}],
            'style': {'title': '会员等级 GMV 贡献(元)', 'label': True},
        },
        0,
        0,
        8,
        7,
    ),
    _comp(
        'h2',
        'dm_demo_order',
        _SQL_STATUS,
        {
            'type': 'donut',
            'x': 'order_status',
            'ys': [{'field': 'order_cnt', 'agg': 'sum'}],
            'style': {'title': '订单状态分布'},
        },
        8,
        0,
        8,
        7,
    ),
    _comp(
        'h3',
        'dm_demo_product',
        _SQL_TOP_PRODUCT,
        {
            'type': 'hbar',
            'x': 'product_name',
            'ys': [{'field': 'gmv', 'agg': 'sum'}],
            'sort': {'by': 'gmv', 'dir': 'desc'},
            'topN': 10,
            'style': {'title': '爆款商品 GMV Top10(元)'},
        },
        16,
        0,
        8,
        7,
    ),
    _comp(
        'h4',
        'dm_demo_order',
        _SQL_REGION,
        {
            'type': 'bar',
            'x': 'region_name',
            'ys': [{'field': 'order_cnt', 'agg': 'sum'}],
            'sort': {'by': 'order_cnt', 'dir': 'desc'},
            'style': {'title': '区域订单量对比(单)'},
        },
        0,
        7,
        24,
        7,
    ),
]


def seed_dashboards(db) -> None:
    """多图看板 2 个 + 单图看板 1 个(幂等:先删画布再删基础信息)。"""
    boards = [
        (
            _BOARD_ID,
            '电商经营总览(Demo)',
            'board',
            'GMV 趋势 / 类目排行 / 渠道占比 / 区域明细 / 流量投放,全部基于 demo 业务库真实 SQL',
            {
                'canvas': {'mode': 'matrix', 'cols': 24},
                'components': _BOARD_COMPONENTS,
                'filters': [{'name': 'start', 'label': '起始日期', 'type': 'date', 'default': '2024-01-01'}],
            },
        ),
        (
            _BOARD2_ID,
            '销售健康度看板(Demo)',
            'board',
            '会员贡献 / 订单状态 / 爆款商品 / 区域订单量 四象限体检',
            {'canvas': {'mode': 'matrix', 'cols': 24}, 'components': _BOARD2_COMPONENTS, 'filters': []},
        ),
        (
            _CHART_ID,
            'GMV 日趋势(单图)',
            'chart',
            '单图看板:GMV 日趋势,可直接嵌到外部系统',
            {'canvas': {'mode': 'matrix', 'cols': 24}, 'components': [_BOARD_COMPONENTS[0]], 'filters': []},
        ),
    ]
    for did, name, dtype, remark, content in boards:
        db.execute(text('DELETE FROM data_dashboard_canvas WHERE dashboard_id=:id'), {'id': did})
        db.execute(text('DELETE FROM data_dashboard WHERE id=:id'), {'id': did})
        db.execute(
            text(
                'INSERT INTO data_dashboard (id,name,dash_type,refresh_interval,remark,create_by,create_time,tenant_id) '
                'VALUES (:id,:name,:dtype,0,:remark,:by,:now,:tenant)'
            ),
            {'id': did, 'name': name, 'dtype': dtype, 'remark': remark, 'by': 'admin', 'now': NOW, 'tenant': TENANT},
        )
        db.execute(
            text(
                'INSERT INTO data_dashboard_canvas (id,dashboard_id,version,content,create_by,create_time,tenant_id) '
                "VALUES (:id,:did,'current',:content,:by,:now,:tenant)"
            ),
            {
                'id': did + '_canvas',
                'did': did,
                'content': json.dumps(content, ensure_ascii=False),
                'by': 'admin',
                'now': NOW,
                'tenant': TENANT,
            },
        )


# ---------------------------------------------------------------------------
# 4) 任务模板 / 调度任务 / 执行实例 / 日志 / DAG
# ---------------------------------------------------------------------------
_TEMPLATES = [
    ('tpl_python_task', 'Python 任务', 'PythonTask', 'PythonTask', '在线写 Python 代码,平台沙箱内执行'),
    ('tpl_shell_task', 'Shell 任务', 'ShellTask', 'ShellTask', '执行 Shell 脚本/命令,适合运维巡检'),
    (
        'tpl_data_integration',
        '数据集成任务',
        'DataIntegrationTask',
        'DataIntegrationTask',
        '抽取 → 转换 → 装载,支持增量与字段映射',
    ),
]

_PY_DAILY = (
    'def run(params, logger):\n'
    '    """每日经营日报:统计昨日 GMV/订单量并打印(演示任务,不依赖外部网络)。"""\n'
    '    import random\n'
    '    gmv = round(random.uniform(180000, 320000), 2)\n'
    '    orders = random.randint(1200, 2600)\n'
    "    logger.info(f'昨日 GMV={gmv:.2f} 元,订单量={orders} 单')\n"
    "    logger.info(f'客单价={gmv / orders:.2f} 元')\n"
    "    return '日报生成完成'\n"
)
_PY_QUALITY = (
    'def run(params, logger):\n'
    '    """数据质量巡检:空值率 / 主键重复 / 金额异常三项检查(演示)。"""\n'
    '    checks = [\n'
    "        ('fact_order.order_id 重复', 0),\n"
    "        ('fact_order.amount 空值率', 0.0),\n"
    "        ('fact_traffic.visits 负值', 0),\n"
    '    ]\n'
    '    for name, bad in checks:\n'
    "        logger.info(f'{name}: {bad}')\n"
    "    return '质量巡检通过'\n"
)
_SH_ARCHIVE = "echo \"[archive] $(date '+%F %T') 归档昨日分区 -> /data/archive\"\necho '[archive] done'\n"

_TASKS = [
    (
        'demo_task_daily_report',
        '每日经营日报',
        'PythonTask',
        {'run_type': 'code', 'code': _PY_DAILY},
        '每天 08:00 汇总昨日 GMV/订单量/客单价并发日报(演示)',
        '0 0 8 * * ?',
    ),
    (
        'demo_task_quality',
        '数据质量巡检',
        'PythonTask',
        {'run_type': 'code', 'code': _PY_QUALITY},
        '每小时巡检订单主键、金额空值率与流量负值(演示)',
        '0 0 * * * ?',
    ),
    (
        'demo_task_archive',
        '订单分区归档',
        'ShellTask',
        {'run_type': 'code', 'code': _SH_ARCHIVE},
        '每天 02:00 归档昨日订单分区(演示 Shell 任务)',
        '0 0 2 * * ?',
    ),
]

_DAG_ID = 'demo_dag_daily_pipeline'


def seed_tasks(db, alert_ids: str) -> None:
    for tid, name, code, component, remark in _TEMPLATES:
        db.execute(text('DELETE FROM task_template WHERE id=:id OR code=:code'), {'id': tid, 'code': code})
        db.execute(
            text(
                'INSERT INTO task_template (id,name,code,type,runner_type,component,built_in,status,create_by,'
                'create_time,remark) VALUES (:id,:name,:code,1,1,:comp,1,1,:by,:now,:remark)'
            ),
            {'id': tid, 'name': name, 'code': code, 'comp': component, 'by': 'admin', 'now': NOW, 'remark': remark},
        )

    for tid, name, template_code, params, remark, cron in _TASKS:
        db.execute(text('DELETE FROM task WHERE id=:id'), {'id': tid})
        db.execute(text('DELETE FROM sys_job WHERE job_name=:jn'), {'jn': 'TASK_' + tid})
        db.execute(
            text(
                'INSERT INTO task (id,template_code,task_type,run_type,name,params,status,built_in,trigger_type,'
                'crontab,priority,retry,countdown,run_queue,alert_strategy_ids,create_by,create_time,remark,tenant_id) '
                "VALUES (:id,:tpl,1,1,:name,:params,1,0,2,:cron,1,2,60,'default',:alerts,'admin',:now,:remark,:tenant)"
            ),
            {
                'id': tid,
                'tpl': template_code,
                'name': name,
                'params': json.dumps(params, ensure_ascii=False),
                'cron': cron,
                'alerts': alert_ids,
                'now': NOW,
                'remark': remark,
                'tenant': TENANT,
            },
        )
        # 建 sys_job 让定时调度能看到(后端调度器重载后即生效)
        r = db.execute(
            text(
                'INSERT INTO sys_job (job_name,job_group,job_executor,invoke_target,job_args,cron_expression,'
                'misfire_policy,concurrent,status,create_by,create_time,tenant_id) '
                "VALUES (:jn,'default','default','module_task_schedule.dispatch.run_task',:args,:cron,'2','1','0',"
                "'admin',:now,:tenant)"
            ),
            {'jn': 'TASK_' + tid, 'args': tid, 'cron': cron, 'now': NOW, 'tenant': TENANT},
        )
        db.execute(text('UPDATE task SET job_id=:jid WHERE id=:tid'), {'jid': r.lastrowid, 'tid': tid})

    # DAG 工作流:5 节点线性流水线(草稿 + 一条已发布版本)
    graph = {
        'nodes': [
            {
                'node_key': 'n_extract',
                'name': '抽取订单数据',
                'template_code': 'DataIntegrationTask',
                'params': {
                    'extract': {
                        'mode': 'datasource',
                        'datasource_code': DS_CODE,
                        'object': 'fact_order',
                        'native': 'SELECT * FROM fact_order WHERE order_date = CURDATE() - INTERVAL 1 DAY',
                    }
                },
                'pos': {'x': 80, 'y': 60},
                'retry': 1,
                'countdown': 30,
                'error_policy': 'fail_fast',
            },
            {
                'node_key': 'n_clean',
                'name': '清洗与去重',
                'template_code': 'PythonTask',
                'params': {'run_type': 'code', 'code': _PY_QUALITY},
                'pos': {'x': 340, 'y': 60},
                'retry': 1,
                'countdown': 30,
                'error_policy': 'continue',
            },
            {
                'node_key': 'n_agg',
                'name': '汇总经营指标',
                'template_code': 'PythonTask',
                'params': {'run_type': 'code', 'code': _PY_DAILY},
                'pos': {'x': 600, 'y': 60},
                'retry': 0,
                'countdown': 0,
                'error_policy': 'fail_fast',
            },
            {
                'node_key': 'n_archive',
                'name': '归档分区',
                'template_code': 'ShellTask',
                'params': {'run_type': 'code', 'code': _SH_ARCHIVE},
                'pos': {'x': 860, 'y': 60},
                'retry': 0,
                'countdown': 0,
                'error_policy': 'continue',
            },
        ],
        'edges': [
            {'source': 'n_extract', 'target': 'n_clean'},
            {'source': 'n_clean', 'target': 'n_agg'},
            {'source': 'n_agg', 'target': 'n_archive'},
        ],
        'viewport': {},
    }
    db.execute(text('DELETE FROM dag_graph WHERE dag_task_id=:id'), {'id': _DAG_ID})
    db.execute(text('DELETE FROM task WHERE id=:id'), {'id': _DAG_ID})
    db.execute(
        text(
            'INSERT INTO task (id,template_code,task_type,run_type,name,status,trigger_type,run_queue,create_by,'
            "create_time,remark,tenant_id) VALUES (:id,'',2,1,:name,1,1,'default','admin',:now,:remark,:tenant)"
        ),
        {
            'id': _DAG_ID,
            'name': '每日经营数据流水线(Demo)',
            'now': NOW,
            'remark': '抽取 → 清洗 → 汇总 → 归档,4 节点 DAG,可在编排器里查看/发布',
            'tenant': TENANT,
        },
    )
    db.execute(
        text(
            'INSERT INTO dag_graph (id,dag_task_id,version,status,graph,remark,create_by,create_time,tenant_id) '
            "VALUES (:id,:dag,'draft','draft',:graph,:remark,'admin',:now,:tenant)"
        ),
        {
            'id': _DAG_ID + '_draft',
            'dag': _DAG_ID,
            'graph': json.dumps(graph, ensure_ascii=False),
            'remark': '演示草稿',
            'now': NOW,
            'tenant': TENANT,
        },
    )


def seed_instances(db) -> None:
    """任务执行实例 + 日志:近 7 天的运行历史,控制台趋势图/任务列表都有数据。"""
    db.execute(text('DELETE FROM task_instance WHERE id LIKE :p'), {'p': 'demo_inst_%'})
    db.execute(text('DELETE FROM task_log WHERE task_uuid LIKE :p'), {'p': 'demo_inst_%'})
    rnd = random.Random(7)
    rows, logs = [], []
    idx = 0
    for day in range(6, -1, -1):
        for tid, name, *_ in _TASKS:
            idx += 1
            iid = f'demo_inst_{idx:04d}'
            start = NOW - datetime.timedelta(days=day, hours=2, minutes=rnd.randint(0, 50))
            status = rnd.choices(['SUCCESS', 'FAILURE', 'STARTED'], weights=[7, 2, 1])[0]
            end = None if status == 'STARTED' else start + datetime.timedelta(seconds=rnd.randint(12, 260))
            rows.append(
                {
                    'id': iid,
                    'task': tid,
                    'name': f'{name} · {start.strftime("%m-%d")}',
                    'status': status,
                    'worker': rnd.choice(['celery@worker-1', 'celery@worker-2']),
                    'retry': 0,
                    'progress': 0 if status == 'STARTED' else 100.0,
                    'start': start,
                    'end': end,
                    'result': '执行成功'
                    if status == 'SUCCESS'
                    else ('执行失败: 演示异常' if status == 'FAILURE' else None),
                    'tenant': TENANT,
                }
            )
            logs.append(
                (iid, 'INFO', f'任务 {tid} 开始,worker={rnd.choice(["celery@worker-1", "celery@worker-2"])}', start)
            )
            logs.append(
                (
                    iid,
                    'INFO',
                    '昨日 GMV=248360.55 元,订单量=1832 单,客单价=135.57 元',
                    start + datetime.timedelta(seconds=8),
                )
            )
            if status == 'FAILURE':
                logs.append((iid, 'ERROR', '演示异常:下游连接超时(模拟),已按重试策略重试 2 次', end))
            elif status == 'SUCCESS':
                logs.append((iid, 'INFO', '任务执行完成,耗时 %ss' % rnd.randint(12, 260), end))

    db.execute(
        text(
            'INSERT INTO task_instance (id,parent_id,task_id,node_id,name,status,worker,retry_num,progress,'
            'start_time,end_time,closed,result,tenant_id) '
            'VALUES (:id,NULL,:task,NULL,:name,:status,:worker,:retry,:progress,:start,:end,1,:result,:tenant)'
        ),
        rows,
    )
    db.execute(
        text(
            'INSERT INTO task_log (task_uuid,level,content,create_time,tenant_id) VALUES (:tid,:lvl,:content,:t,:tenant)'
        ),
        [{'tid': t, 'lvl': lvl, 'content': c, 't': t, 'tenant': TENANT} for t, lvl, c, t in logs],
    )


# ---------------------------------------------------------------------------
# 5) 告警策略 / 告警记录
# ---------------------------------------------------------------------------
_ALERT_STRATEGIES = [
    (
        9201,
        '调度任务失败 → 站内通知',
        'scheduler',
        {'level': 1},
        [{'type': 'notice', 'notice_users': 'admin'}],
        '任务执行失败时给管理员发站内通知',
    ),
    (
        9202,
        '日 GMV 环比下滑 > 20% → 企业微信',
        'metric',
        {'level': 2, 'metric': 'demo_gmv', 'op': 'lt', 'threshold': 0.2},
        [{'type': 'wechat_webhook', 'webhook': 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=demo'}],
        '经营大盘异动预警(演示企业微信机器人渠道)',
    ),
    (
        9203,
        '数据质量巡检异常 → 邮件',
        'data',
        {'level': 3},
        [{'type': 'email', 'email_users': 'dataops@example.com'}],
        '质量巡检不通过时邮件通知数据负责人',
    ),
]


def seed_alerts(db) -> str:
    """写入 3 个告警策略 + 若干告警记录,返回挂到任务上的策略 id 串。"""
    ids = []
    for sid, name, biz, trigger, forward, remark in _ALERT_STRATEGIES:
        db.execute(text('DELETE FROM alert_strategy WHERE strategy_id=:id'), {'id': sid})
        db.execute(
            text(
                'INSERT INTO alert_strategy (strategy_id,strategy_name,biz,trigger_conf,forward_conf,status,'
                "create_by,create_time,remark,tenant_id) VALUES (:id,:name,:biz,:trigger,:forward,1,'admin',:now,:remark,:tenant)"
            ),
            {
                'id': sid,
                'name': name,
                'biz': biz,
                'trigger': json.dumps(trigger, ensure_ascii=False),
                'forward': json.dumps(forward, ensure_ascii=False),
                'now': NOW,
                'remark': remark,
                'tenant': TENANT,
            },
        )
        ids.append(str(sid))
    return ids[0] if ids else ''


def seed_alert_records(db) -> None:
    db.execute(text('DELETE FROM alert_record WHERE alert_id BETWEEN 9201 AND 9205'), {})
    records = [
        (
            '9201',
            9201,
            '任务失败:每日经营日报',
            '每日经营日报执行失败,原因:演示异常(下游连接超时)',
            2,
            0,
            'scheduler',
            '每日经营日报',
            'task_fail',
            NOW - datetime.timedelta(hours=3),
        ),
        (
            '9202',
            9202,
            'GMV 环比下滑 23.4%',
            '昨日 GMV 18.2 万,环比前日 23.8 万下滑 23.4%,低于阈值',
            1,
            1,
            'metric',
            'demo_gmv',
            'gmv_drop',
            NOW - datetime.timedelta(days=1, hours=6),
        ),
        (
            '9203',
            9203,
            '数据质量巡检通过',
            '三大检查项全部通过,已自动恢复',
            3,
            2,
            'data',
            'fact_order',
            'quality',
            NOW - datetime.timedelta(days=2),
        ),
        (
            '9204',
            9201,
            '任务失败:数据质量巡检',
            '巡检发现 fact_order 金额空值率 0.8% 超过 0.5% 阈值',
            2,
            0,
            'scheduler',
            '数据质量巡检',
            'task_fail',
            NOW - datetime.timedelta(days=2, hours=4),
        ),
        (
            '9205',
            9202,
            '渠道抖音直播 ROI 跌破 2',
            '抖音直播投放 3.2 万,成交 5.9 万,ROI=1.84',
            1,
            1,
            'metric',
            'demo_gmv',
            'roi',
            NOW - datetime.timedelta(days=4),
        ),
    ]
    db.execute(
        text(
            'INSERT INTO alert_record (alert_id,strategy_id,title,content,level,status,biz,source,metric,tags,'
            'recover_time,create_time,tenant_id) '
            'VALUES (:id,:sid,:title,:content,:level,:status,:biz,:source,:metric,NULL,:recover,:now,:tenant)'
        ),
        [
            {
                'id': aid,
                'sid': sid,
                'title': title,
                'content': content,
                'level': level,
                'status': status,
                'biz': biz,
                'source': source,
                'metric': metric,
                'recover': (create + datetime.timedelta(hours=2)) if status == 2 else None,
                'now': create,
                'tenant': TENANT,
            }
            for aid, sid, title, content, level, status, biz, source, metric, create in records
        ],
    )


# ---------------------------------------------------------------------------
# 6) AI 模型 / 应用 / 工具 / 技能
# ---------------------------------------------------------------------------
_AI_MODELS = [
    (9101, 'deepseek-chat', 'DeepSeek Chat', 'deepseek', 1, 'https://api.deepseek.com/v1', 'llm', 8192, 0.3),
    (
        9102,
        'qwen-plus',
        '通义千问 Plus',
        'dashscope',
        2,
        'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'llm',
        8192,
        0.3,
    ),
    (
        9103,
        'text-embedding-v3',
        '通义 Embedding v3',
        'dashscope',
        3,
        'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'embedding',
        None,
        None,
    ),
    (9104, 'local-hash-512', '本地离线 Embedding(Demo)', 'local', 4, None, 'embedding', None, None),
]

_APP_PROMPT = """# 角色
你是「电商经营分析助手」,负责把业务问题翻译成 SQL,查 demo 业务库后给出结论与图表。

## 数据(demo_warehouse · MySQL)
- fact_order 订单事实:order_id / order_date / product_id / customer_id / region_name / channel / quantity / amount / discount / status
- dim_product 商品维:product_id / product_name / category / price / cost
- dim_customer 客户维:customer_id / customer_name / city / region_name / member_level
- fact_traffic 渠道流量日事实:stat_date / channel / visits / orders / ad_cost
- dim_region 区域维:region_code / region_name / area

## 口径(与指标管理一致)
- GMV = SUM(fact_order.amount);订单量 = COUNT(order_id);客单价 = GMV / 订单量
- 退款率 = 状态为「已退款」的订单数 / 订单总数
- 类目 GMV 需 join dim_product;会员贡献需 join dim_customer

## 输出
1. 先说明取数范围与口径;2. 给 SQL(只读 SELECT);3. 结论 3 条以内;4. 需要时用沙箱画图。
"""

_APP_CONFIG = {
    'prompt': _APP_PROMPT,
    'prologue': '你好!我是电商经营分析助手。可以直接问我 GMV、类目、渠道、区域、会员、退款等经营问题,我会写 SQL 取数并作图。',
    'presetQuestions': [
        '近 30 天 GMV 日趋势,画折线图',
        '各渠道 GMV 占比与客单价对比',
        '类目 GMV Top5,并给出环比变化',
        '会员等级对 GMV 的贡献分布',
        '退款率最高的 3 个类目',
        '区域订单量与客单价明细表',
    ],
    'quickCommands': [
        {'name': '经营日报', 'content': '生成昨日经营日报:GMV/订单量/客单价/退款率 + 3 条结论'},
        {'name': '异动归因', 'content': '对比近 7 天与前 7 天 GMV,找出下滑最多的渠道与类目并归因'},
    ],
    'toolIds': [],
    'datasetIds': [],
    'skillIds': [],
    'datasourceCodes': [DS_CODE],
    'enableMemory': True,
    'addHistory': True,
    'numHistoryRuns': 10,
    'model': {'modelId': 9101, 'temperature': 0.3, 'maxTokens': 4096},
}

_APP2_CONFIG = {
    'prompt': _APP_PROMPT.replace('电商经营分析助手', '数据平台使用顾问'),
    'prologue': '你好!我是 DataPilot 使用顾问,可以帮你了解数据源接入、任务调度、知识库与看板的用法。',
    'presetQuestions': [
        '怎样把一个 MySQL 库接进来并建模?',
        'ETL 任务怎么做增量同步?',
        '知识库训练失败常见原因有哪些?',
        '看板怎么配置成公开分享?',
    ],
    'quickCommands': [{'name': '接入指引', 'content': '给我一份从接入数据源到出看板的 5 步操作清单'}],
    'toolIds': [],
    'datasetIds': [],
    'skillIds': [],
    'datasourceCodes': [],
    'enableMemory': False,
    'addHistory': True,
    'numHistoryRuns': 6,
    'model': {'modelId': 9101, 'temperature': 0.2, 'maxTokens': 2048},
}

# (code, 名称, 类型, 内置工具 code / MCP 启动配置, 说明)
_AI_TOOLS = [
    ('data_explore', '数据探索', 'builtin', 'data_explore', '列数据源/表结构、执行只读 SQL 取数'),
    ('sandbox_code', '沙箱代码执行', 'builtin', 'sandbox_code', '隔离容器里跑 Python/Shell,pandas 计算与画图'),
    ('baidu_search', '联网搜索', 'builtin', 'baidu_search', '联网检索公开资料(需出网白名单)'),
    ('task_propose', '任务编排建议', 'builtin', 'task_propose', '按自然语言生成调度任务/DAG 草稿'),
    (
        'amap_maps',
        '高德地图 MCP',
        'mcp',
        {'command': 'npx', 'args': ['-y', '@amap/mcp-server'], 'env': {}},
        'MCP 外部工具示例:启动 stdio MCP server 后按工具清单挂给 Agent',
    ),
]

_AI_SKILL = {
    'name': 'GMV 归因分析',
    'code': 'gmv_attribution',
    'description': '按「渠道 × 类目 × 区域」拆解 GMV 环比变化,定位主要贡献与拖累项。',
    'content': (
        '# GMV 归因分析\n\n'
        '## 何时使用\n用户问「GMV 为什么涨/跌」「环比下滑主要在哪儿」时。\n\n'
        '## 步骤\n'
        '1. `fact_order` 按日期聚合本期/上期 GMV;\n'
        '2. 维度拆解:channel / category(需 join dim_product)/ region_name;\n'
        '3. 对每个维度算贡献度 = 本期-上期,并按绝对值排序;\n'
        '4. 输出 Top3 贡献项 + Top3 拖累项 + 一句话结论。\n\n'
        '## 注意\n- 退款单也计入 GMV(口径一致),必要时另算净 GMV;\n- 类目需 join dim_product,不要用商品名猜类目。\n'
    ),
    'resources': [{'name': 'sql/gmv_attribution.sql', 'content': _SQL_CATEGORY}],
    'skill_type': 'process',
    'datasource_codes': '',
}


def seed_ai(db) -> None:
    for mid, code, name, provider, sort, base_url, mtype, max_tokens, temperature in _AI_MODELS:
        db.execute(text('DELETE FROM ai_models WHERE model_id=:id'), {'id': mid})
        db.execute(
            text(
                'INSERT INTO ai_models (model_id,model_code,model_name,provider,model_sort,api_key,base_url,'
                'model_type,max_tokens,temperature,support_reasoning,support_images,status,user_id,create_by,'
                'create_time,remark,tenant_id) '
                "VALUES (:id,:code,:name,:provider,:sort,NULL,:base,:mtype,:mt,:temp,'N','N','0',1,'admin',:now,:remark,:tenant)"
            ),
            {
                'id': mid,
                'code': code,
                'name': name,
                'provider': provider,
                'sort': sort,
                'base': base_url,
                'mtype': mtype,
                'mt': max_tokens,
                'temp': temperature,
                'now': NOW,
                'remark': '演示模型(未配置 API Key,替换成真实 Key 后即可对话/向量化)',
                'tenant': TENANT,
            },
        )

    for aid, aname, desc, cfg in (
        (9101, '电商经营分析助手', '基于 demo 电商业务库的对话式取数 + 图表 + 归因分析', _APP_CONFIG),
        (9102, '数据平台使用顾问', '平台功能问答:接入、调度、知识库、看板的使用指引', _APP2_CONFIG),
    ):
        db.execute(text('DELETE FROM ai_app WHERE app_id=:id'), {'id': aid})
        db.execute(
            text(
                'INSERT INTO ai_app (app_id,name,description,app_type,status,config,user_id,create_by,create_time,'
                "tenant_id) VALUES (:id,:name,:desc,'数据分析','0',:cfg,1,'admin',:now,:tenant)"
            ),
            {
                'id': aid,
                'name': aname,
                'desc': desc,
                'cfg': json.dumps(cfg, ensure_ascii=False),
                'now': NOW,
                'tenant': TENANT,
            },
        )

    for code, name, tool_type, payload, desc in _AI_TOOLS:
        args = {'code': payload} if tool_type == 'builtin' else payload
        db.execute(text('DELETE FROM ai_tool WHERE code=:c'), {'c': code})
        db.execute(
            text(
                'INSERT INTO ai_tool (name,code,tool_type,description,args,status,built_in,user_id,create_by,'
                "create_time,tenant_id) VALUES (:name,:code,:ttype,:desc,:args,'0',:bi,1,'admin',:now,:tenant)"
            ),
            {
                'name': name,
                'code': code,
                'ttype': tool_type,
                'desc': desc,
                'args': json.dumps(args, ensure_ascii=False),
                'bi': '1' if tool_type == 'builtin' else '0',
                'now': NOW,
                'tenant': TENANT,
            },
        )

    db.execute(text('DELETE FROM ai_skill WHERE code=:c'), {'c': _AI_SKILL['code']})
    db.execute(
        text(
            'INSERT INTO ai_skill (name,code,description,content,resources,ref_skills,skill_type,datasource_codes,'
            'status,built_in,user_id,create_by,create_time,tenant_id) '
            "VALUES (:name,:code,:desc,:content,:res,NULL,:stype,:ds,'0','0',1,'admin',:now,:tenant)"
        ),
        {
            'name': _AI_SKILL['name'],
            'code': _AI_SKILL['code'],
            'desc': _AI_SKILL['description'],
            'content': _AI_SKILL['content'],
            'res': json.dumps(_AI_SKILL['resources'], ensure_ascii=False),
            'stype': _AI_SKILL['skill_type'],
            'ds': _AI_SKILL['datasource_codes'],
            'now': NOW,
            'tenant': TENANT,
        },
    )


# ---------------------------------------------------------------------------
# 7) 知识库(文档 → 分段 → 向量,provider=local 离线可跑)
# ---------------------------------------------------------------------------
_KB_ID = 'demo_kb_shop_ops'
_KB_MANUAL_ID = 'demo_kb_platform_manual'

_KB_DOCS = [
    (
        'demo_doc_metrics',
        '经营指标口径手册.md',
        """# 电商经营指标口径手册

## 1. GMV(成交总额)
GMV = SUM(fact_order.amount),统计范围为所选时间窗内所有订单,**含退款单**(与业务口径一致)。
需要净 GMV 时:剔除 status = '已退款' 的订单。GMV 单位为元。

## 2. 订单量
订单量 = COUNT(fact_order.order_id),一行订单算一单;多件商品仍算一单。

## 3. 客单价 AOV
AOV = GMV ÷ 订单量,反映单笔成交金额;按渠道看能快速区分「高客单低转化」与「低客单高转化」渠道。

## 4. 退款率
退款率 = 已退款订单数 ÷ 订单总数。退款率超过 5% 需要按类目下钻,常见原因是尺码/色差与物流时效。

## 5. 渠道与区域
渠道取值 APP、小程序、H5、抖音直播、天猫旗舰店;区域取值 华东、华南、华北、华中、西南、东北。
区域来自 dim_customer.region_name(收货区域),不要用客户注册地替代。

## 6. 会员等级
普通会员 < 银卡会员 < 金卡会员 < 钻石会员;钻石会员 GMV 占比是判断私域运营健康度的关键指标。

## 7. 常见坑
- 不要用 product_name 猜类目,类目在 dim_product.category。
- fact_order 与 fact_traffic 的日期字段不同(order_date / stat_date)。
- 统计口径跨月时按 order_date 截断,避免跨期归属错误。
""",
    ),
    (
        'demo_doc_dictionary',
        '数据字典(核心表).md',
        """# 数据字典 · 电商业务库(demo_warehouse)

## fact_order 订单事实表
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| order_id | varchar(24) | 订单号,主键 |
| order_date | date | 下单日期 |
| product_id | varchar(16) | 商品编码(join dim_product) |
| customer_id | varchar(16) | 客户编码(join dim_customer) |
| region_name | varchar(32) | 收货区域 |
| channel | varchar(16) | 下单渠道 |
| quantity | int | 件数 |
| amount | decimal(12,2) | 实付金额 |
| discount | decimal(6,2) | 折扣率 |
| status | varchar(16) | 订单状态(已完成/待发货/已退款) |

## dim_product 商品维表
product_id、product_name、category(类目)、price(标价)、cost(成本)、launch_date(上架日期)。

## dim_customer 客户维表
customer_id、customer_name、city、region_name、member_level(会员等级)、register_date。

## fact_traffic 渠道流量日表
stat_date、channel、visits(访问 UV)、orders(下单数)、ad_cost(投放费用)。

## dim_region 区域维表
region_code、region_name、area(大区)。

## 常用 join
```
fact_order o
  JOIN dim_product  p ON o.product_id  = p.product_id
  JOIN dim_customer c ON o.customer_id = c.customer_id
```
""",
    ),
    (
        'demo_doc_playbook',
        '经营分析 SOP.md',
        """# 日常经营分析 SOP

## 每日(09:00 前)
1. 看 GMV 日趋势与订单量,判断是否偏离近 7 日均值 ±15%。
2. 看退款率,超过 5% 按类目下钻。
3. 看渠道 ROI:抖音直播投放费用 ÷ 成交金额 < 2 需要调整素材或出价。

## 每周
1. 类目 GMV Top5 与环比,找出增长/下滑最快类目。
2. 会员等级贡献分布,钻石 + 金卡占比低于 30% 说明私域复购不足。
3. 区域订单量与客单价对比,识别高潜区域。

## 每月
1. 输出经营月报:GMV、订单量、客单价、退款率四张主图 + 归因结论。
2. 复盘投放费用与 UV 的关系,更新预算分配。

## 异常处理
- GMV 环比下滑 > 20%:先排渠道(是否停投)、再排类目(是否断货)、最后排区域(是否物流受限)。
- 数据质量巡检失败:先看 fact_order 主键重复与金额空值率,再重跑 ETL。
""",
    ),
]

_KB_MANUAL_DOCS = [
    (
        'demo_doc_platform',
        'DataPilot 平台使用手册.md',
        """# DataPilot 平台使用手册(摘要)

## 1. 接入数据源
进入「数据管理 → 新建数据源」,选择连接器类型并填写连接参数;密钥字段单独加密存储。
保存后点「测试连接」确认可达,再从表列表一键「从表新建模型」。

## 2. 数据模型与指标
模型描述会进入 AI 目录,用于自然语言找表;指标(语义层)统一口径,AI 取数时优先用指标。

## 3. 在线取数
选中模型 → 「数据查询」,写只读 SQL 即可预览;分页、导出与图表配置都在同一页完成。

## 4. 任务调度
「任务调度 → 普通任务」支持 Python / Shell / 数据集成模板;定时用 cron 表达式。
「任务工作流」用 DAG 编排多节点,支持失败重试、失败策略与节点级日志。

## 5. 知识库
知识库 = 文档 → 分段 → 向量索引。文档支持上传文件、网页抓取与直接粘贴文本。
召回测试页可切换 向量 / 全文 / 混合 三种检索模式,并支持 rerank 二次排序。

## 6. 看板
单图 / 多图 / 大屏三类;多图看板用矩阵布局,组件可引用已有单图看板。
看板可开启匿名分享,并给出 iframe 嵌入代码。
""",
    ),
]


def seed_rag(db) -> None:
    """知识库 + 文档 + QA 分段;文档随后交给 pipeline 训练(provider=local,离线)。"""
    from module_rag.pipeline import train_document

    for did, name, index_name, desc in (
        (
            _KB_ID,
            '电商经营知识库(Demo)',
            'rag_ds_demo_kb_shop_ops',
            '指标口径 / 数据字典 / 经营 SOP,供 AI 取数与归因引用',
        ),
        (
            _KB_MANUAL_ID,
            'DataPilot 使用手册(Demo)',
            'rag_ds_demo_kb_platform_manual',
            '平台功能使用说明,供使用顾问类应用引用',
        ),
    ):
        db.execute(text('DELETE FROM rag_dataset WHERE id=:id'), {'id': did})
        db.execute(
            text(
                'INSERT INTO rag_dataset (id,name,description,source_id,embedding_provider,embedding_model,'
                'embedding_dims,vector_backend,index_name,built_in,status,tenant_id,create_by,create_time,remark) '
                "VALUES (:id,:name,:desc,NULL,'local','local-hash-512',512,'elasticsearch',:idx,0,1,:tenant,'admin',:now,:remark)"
            ),
            {'id': did, 'name': name, 'desc': desc, 'idx': index_name, 'tenant': TENANT, 'now': NOW, 'remark': desc},
        )

    db.execute(text('DELETE FROM rag_document WHERE id LIKE :p'), {'p': 'demo_doc_%'})
    db.execute(text('DELETE FROM rag_chunk WHERE id LIKE :p'), {'p': 'demo_chunk_%'})

    docs = []
    for doc_id, name, text_body in _KB_DOCS:
        docs.append((doc_id, _KB_ID, name, text_body))
    for doc_id, name, text_body in _KB_MANUAL_DOCS:
        docs.append((doc_id, _KB_MANUAL_ID, name, text_body))

    for doc_id, kb_id, name, text_body in docs:
        db.execute(
            text(
                'INSERT INTO rag_document (id,dataset_id,name,document_type,source,meta_data,chunk_strategy,status,'
                'chunk_count,tenant_id,create_by,create_time) '
                "VALUES (:id,:kb,:name,'text','text',:meta,:strategy,1,0,:tenant,'admin',:now)"
            ),
            {
                'id': doc_id,
                'kb': kb_id,
                'name': name,
                'meta': json.dumps({'text': text_body}, ensure_ascii=False),
                'strategy': json.dumps(
                    {'strategy': 'recursive', 'chunk_size': 800, 'chunk_overlap': 80}, ensure_ascii=False
                ),
                'tenant': TENANT,
                'now': NOW,
            },
        )
    db.commit()

    # QA 分段(不走切分,直接写库;召回时按问题哈希命中)
    qa_pairs = [
        ('GMV 是怎么算的?', 'GMV = SUM(fact_order.amount),含退款单;需要净 GMV 时剔除 status=已退款。'),
        ('客单价口径是什么?', '客单价 AOV = GMV ÷ 订单量,订单按 order_id 计。'),
        ('类目 GMV 怎么查?', 'fact_order 需要 join dim_product,按 dim_product.category 分组求和。'),
        ('哪些渠道在平台里?', 'APP、小程序、H5、抖音直播、天猫旗舰店,共 5 个渠道。'),
        ('会员等级有哪些?', '普通会员、银卡会员、金卡会员、钻石会员 4 档。'),
    ]
    import hashlib

    rows = []
    for i, (q, a) in enumerate(qa_pairs):
        rows.append(
            {
                'id': f'demo_chunk_qa_{i}',
                'kb': _KB_ID,
                'q': q,
                'qh': hashlib.md5(q.encode('utf-8')).hexdigest(),
                'a': a,
                'pos': i,
                'tenant': TENANT,
                'now': NOW,
            }
        )
    db.execute(
        text(
            'INSERT INTO rag_chunk (id,dataset_id,document_id,chunk_type,content,question,question_hash,answer,position,'
            'status,star_flag,tenant_id,create_by,create_time) '
            "VALUES (:id,:kb,'manual','qa',:a,:q,:qh,:a,:pos,1,1,:tenant,'admin',:now)"
        ),
        rows,
    )
    db.commit()

    # 训练(切分 + 本地哈希向量 + 写 ES) —— 同步跑,失败只提示不中断其余种子
    for doc_id, *_ in docs:
        try:
            res = train_document(doc_id, TENANT, force=True)
            print(f'  · 训练 {doc_id}: {res.get("chunks", 0)} 段 {"" if res.get("ok") else res.get("error")}')
        except Exception as e:
            print(f'  ! 训练 {doc_id} 失败(可稍后在页面上点「训练」重试): {e}')


# ---------------------------------------------------------------------------
# 8) 清理
# ---------------------------------------------------------------------------
def clean() -> None:
    """删除全部 demo 平台数据 + demo 业务库。"""
    db = get_sync_session_local()()
    try:
        stmts = [
            ("DELETE FROM data_dashboard_canvas WHERE dashboard_id LIKE 'demo_%'", None),
            ("DELETE FROM data_dashboard WHERE id LIKE 'demo_%'", None),
            ("DELETE FROM data_metric WHERE code LIKE 'demo_%'", None),
            ("DELETE FROM data_model WHERE id LIKE 'dm_demo_%'", None),
            ('DELETE FROM data_source WHERE id=:id', {'id': DS_ID}),
            ("DELETE FROM task_instance WHERE id LIKE 'demo_inst_%'", None),
            ("DELETE FROM task_log WHERE task_uuid LIKE 'demo_inst_%'", None),
            ('DELETE FROM dag_graph WHERE dag_task_id=:id', {'id': _DAG_ID}),
            ("DELETE FROM task WHERE id LIKE 'demo_task_%' OR id=:id", {'id': _DAG_ID}),
            ("DELETE FROM sys_job WHERE job_name LIKE 'TASK_demo_task_%'", None),
            ("DELETE FROM task_template WHERE id LIKE 'tpl_%'", None),
            ('DELETE FROM alert_record WHERE alert_id BETWEEN 9201 AND 9205', None),
            ('DELETE FROM alert_strategy WHERE strategy_id BETWEEN 9201 AND 9203', None),
            ('DELETE FROM ai_app WHERE app_id IN (9101,9102)', None),
            ('DELETE FROM ai_models WHERE model_id IN (9101,9102,9103,9104)', None),
            (
                "DELETE FROM ai_tool WHERE code IN ('data_explore','sandbox_code','baidu_search','task_propose','amap_maps')",
                None,
            ),
            ("DELETE FROM ai_skill WHERE code='gmv_attribution'", None),
            ("DELETE FROM rag_chunk WHERE id LIKE 'demo_chunk_%'", None),
            ("DELETE FROM rag_document WHERE id LIKE 'demo_doc_%'", None),
            ("DELETE FROM rag_dataset WHERE id LIKE 'demo_kb_%'", None),
        ]
        for sql, params in stmts:
            db.execute(text(sql), params or {})
        db.commit()
    finally:
        db.close()
    eng = _platform_engine()
    with eng.begin() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS `{DEMO_DB}`'))
    eng.dispose()
    print('已清理 demo 数据与 demo 业务库')


# ---------------------------------------------------------------------------
# 9) 入口
# ---------------------------------------------------------------------------
def seed_all() -> None:
    print('1/6 造 demo 业务库(datapilot_demo)…')
    counts = _build_demo_database()
    print('   ' + ' · '.join(f'{k}={v} 行' for k, v in counts.items()))

    db = get_sync_session_local()()
    try:
        print('2/6 数据源 / 数据模型 / 指标…')
        seed_metadata(db)
        print('3/6 看板(2 多图 + 1 单图)…')
        seed_dashboards(db)
        print('4/6 告警策略与记录…')
        alert_ids = seed_alerts(db)
        seed_alert_records(db)
        print('5/6 任务模板 / 调度任务 / 执行历史 / DAG…')
        seed_tasks(db, alert_ids)
        seed_instances(db)
        print('6/6 AI 模型·应用·工具·技能 + 知识库训练…')
        seed_ai(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    db = get_sync_session_local()()
    try:
        seed_rag(db)
    finally:
        db.close()

    print(
        '\n✅ Demo 内容已就绪:\n'
        f'   数据源 {DS_CODE}(MySQL · {DEMO_DB}) + 5 个数据模型 + 5 个指标\n'
        '   看板:电商经营总览 / 销售健康度看板 / GMV 日趋势单图\n'
        f'   任务 {len(_TASKS)} 个 + 21 条执行历史 + DAG「每日经营数据流水线」\n'
        '   告警策略 3 个 + 告警记录 5 条\n'
        '   AI 模型 4 个 / 应用 2 个 / 工具 5 个 / 技能 1 个\n'
        '   知识库 2 个(文档 4 篇 + QA 5 条,provider=local 离线向量)\n'
        f'   前端入口:http://localhost  账号 admin\n'
        '   清理:python demo_seed_business.py --clean'
    )


if __name__ == '__main__':
    if '--clean' in sys.argv:
        clean()
    else:
        seed_all()

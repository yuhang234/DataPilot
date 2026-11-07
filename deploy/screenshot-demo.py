"""演示界面截图(Playwright):登录后逐个截取主要功能页,产出 README 用的截图。

前置:
1. dev/prod 栈已启动(默认 http://localhost);
2. 已灌演示数据:``docker exec -i <backend容器> python - < api/demo_seed_business.py``;
3. 登录验证码已关闭(种子/演示环境):``sys_config.sys.account.captchaEnabled=false``
   —— 否则需在此脚本里人工过验证码。

用法:
    python deploy/screenshot-demo.py                     # 默认 http://localhost admin/admin123
    python deploy/screenshot-demo.py --base http://127.0.0.1:8080 --user admin --password xxx
    python deploy/screenshot-demo.py --out docs/screenshots --only dashboard,board

依赖:``pip install playwright && playwright install chromium``
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

# (文件名, 路由, 页面就绪等待选择器, 额外等待毫秒)
PAGES = {
    'dashboard': ('01_dashboard', '/index', '.el-card', 3500),
    'data-manage': ('02_data_manage', '/data/manage', '.src-tree', 3000),
    'board': ('03_dashboard_board', '/data/dashboard-list', '.el-table__row', 2500),
    'rag-dataset': ('04_knowledge_base', '/rag/dataset', '.el-table__row', 2500),
    'rag-retrieval': ('05_rag_retrieval', '/rag/retrieval', '.el-select', 2500),
    'task': ('06_task_schedule', '/task/info', '.el-table__row', 2500),
    'alert': ('07_alert_center', '/alert/record', '.el-table__row', 2500),
}


def login(pg: Page, base: str, user: str, password: str) -> None:
    pg.goto(f'{base}/login', wait_until='networkidle')
    pg.wait_for_timeout(1200)
    pg.fill('input[placeholder="账号"]', user)
    pg.fill('input[placeholder="密码"]', password)
    pg.click('button:has-text("登 录")')
    pg.wait_for_url('**/index', timeout=20000)
    pg.wait_for_timeout(2500)


def capture(pg: Page, base: str, out: Path, only: set[str] | None) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for key, (filename, path, ready, extra) in PAGES.items():
        if only and key not in only:
            continue
        pg.goto(base + path, wait_until='domcontentloaded')
        try:
            pg.wait_for_selector(ready, timeout=20000)
        except Exception:
            print(f'  ! {key}: 未等到 {ready},仍按当前状态截图')
        pg.wait_for_timeout(extra)
        target = out / f'{filename}.png'
        pg.screenshot(path=str(target))
        print(f'  · {target}')


def capture_extra(pg: Page, base: str, out: Path) -> None:
    """需要交互才有内容的页面:数据查询结果、看板预览、知识库分段、召回结果。"""
    # 数据管理:选中 demo 数据源 → 订单模型 → 数据查询跑示例 SQL
    pg.goto(base + '/data/manage', wait_until='domcontentloaded')
    pg.wait_for_timeout(3000)
    if pg.locator('text=电商业务库(Demo MySQL)').count():
        pg.click('text=电商业务库(Demo MySQL)')
        pg.wait_for_timeout(1000)
        pg.click('text=订单明细')
        pg.wait_for_timeout(1500)
        pg.locator('.el-tabs__item:has-text("数据查询")').click()
        pg.wait_for_timeout(2000)
        pg.locator('.el-tab-pane:visible button:has-text("查询")').last.click()
        pg.wait_for_timeout(4500)  # 等结果 + 提示条自动消失
        pg.mouse.move(840, 190)
        pg.wait_for_timeout(500)
        pg.screenshot(path=str(out / '02_data_manage.png'))
        print(f'  · {out / "02_data_manage.png"}')

    # 看板:打开「电商经营总览」预览
    pg.goto(base + '/data/dashboard-list', wait_until='domcontentloaded')
    pg.wait_for_timeout(2500)
    row = pg.locator('tr:has-text("电商经营总览(Demo)")')
    if row.count():
        row.locator('button:has-text("预览")').click()
        pg.wait_for_timeout(7000)  # 5 张图逐张取数
        pg.screenshot(path=str(out / '03_dashboard_board.png'))
        print(f'  · {out / "03_dashboard_board.png"}')
        pg.keyboard.press('Escape')
        pg.wait_for_timeout(1000)

    # 知识库:文档管理 → 分段抽屉
    pg.goto(base + '/rag/dataset', wait_until='domcontentloaded')
    pg.wait_for_timeout(2500)
    kb = pg.locator('tr:has-text("电商经营知识库(Demo)")')
    if kb.count():
        kb.locator('button:has-text("文档管理")').click()
        pg.wait_for_timeout(2000)
        pg.locator('tr:has-text("数据字典(核心表)")').locator('button:has-text("分段")').click()
        pg.wait_for_timeout(2500)
        pg.mouse.move(10, 10)
        pg.screenshot(path=str(out / '04_knowledge_base.png'))
        print(f'  · {out / "04_knowledge_base.png"}')
        pg.keyboard.press('Escape')
        pg.wait_for_timeout(700)
        pg.keyboard.press('Escape')
        pg.wait_for_timeout(700)

    # 召回测试:选知识库 → 输入问题 → 召回
    pg.goto(base + '/rag/retrieval', wait_until='domcontentloaded')
    pg.wait_for_timeout(2500)
    pg.locator('.el-select').first.click()
    pg.wait_for_timeout(800)
    item = pg.locator('.el-select-dropdown__item:has-text("电商经营知识库(Demo)")')
    if item.count():
        item.first.click()
        pg.keyboard.press('Escape')
        pg.fill('textarea', 'GMV 口径怎么算?')
        pg.locator('button:has-text("召回测试")').click()
        pg.wait_for_timeout(2500)
        pg.screenshot(path=str(out / '05_rag_retrieval.png'))
        print(f'  · {out / "05_rag_retrieval.png"}')


def main() -> int:
    parser = argparse.ArgumentParser(description='DataPilot 演示界面截图')
    parser.add_argument('--base', default='http://localhost', help='前端地址')
    parser.add_argument('--user', default='admin')
    parser.add_argument('--password', default='admin123')
    parser.add_argument('--out', default='docs/screenshots', help='截图输出目录')
    parser.add_argument('--only', default='', help='只截指定页面(逗号分隔: dashboard,data-manage,board,...)')
    parser.add_argument('--no-extra', action='store_true', help='跳过需要交互的页面(查询结果/看板预览/分段/召回)')
    args = parser.parse_args()

    out = Path(args.out)
    only = {s.strip() for s in args.only.split(',') if s.strip()} or None
    base = args.base.rstrip('/')

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={'width': 1680, 'height': 1000}, device_scale_factor=2, locale='zh-CN')
        page = ctx.new_page()
        login(page, base, args.user, args.password)
        capture(page, base, out, only)
        if not args.no_extra and not only:
            capture_extra(page, base, out)
        browser.close()
    print(f'\n完成:截图已输出到 {out.resolve()}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

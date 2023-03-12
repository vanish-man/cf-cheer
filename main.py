import asyncio
from os import getenv

import requests
from cf_clearance import async_cf_retry, async_stealth
from playwright.async_api import async_playwright
from pyvirtualdisplay import Display

session = requests.Session()


async def main():
    try:
        ret = await pw_challenge(getenv('CF_DEST_URL'))
        if not ret['success']:
            await error('get cf_clearance failed.')

        user_agent = ret.get('user_agent')
        if not user_agent:
            await error('get user_agent failed.')

        cookies = ret.get('cookies')
        if not cookies:
            cookies = {}

        cf_clearance = cookies.get('cf_clearance')
        if not cf_clearance:
            await error('miss cf_clearance in cookies.')

        await upload(cf_clearance, user_agent)
    except Exception as e:
        await error(str(e))


async def upload(cf_clearance, user_agent):
    data = {
        'cf_clearance': cf_clearance,
        'user_agent': user_agent,
    }
    resp = session.post(url=getenv('CF_UPSTREAM_UPLOAD_URL'), data=data, timeout=100)

    if 200 == resp.status_code and 'ok' == resp.text:
        await notify('update cf_clearance success: \n  {}\n  {}'.format(cf_clearance, user_agent))
        return

    await notify('update cf_clearance failed: {} - {}'.format(resp.status_code, resp.text))


async def notify(msg):
    data = {
        "msg_type": "text",
        "content": {
            "text": '[cf-cheer]: {}'.format(msg)
        }
    }

    session.post(url=getenv('CF_NOTIFY_URL'), json=data, timeout=100)


async def error(msg):
    await notify(msg)
    raise Exception(msg)


async def pw_challenge(url):
    launch_data = {
        "headless": False,
        "proxy": {
            "server": getenv('CF_PROXY_SERVER'),
            "username": getenv('CF_PROXY_USERNAME'),
            "password": getenv('CF_PROXY_PASSWORD'),
        },
        "args": [
            '--safe-mode',
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--no-first-run",
            "--no-service-autorun",
            "--no-default-browser-check",
            "--password-store=basic",
        ],
    }
    with Display():
        async with async_playwright() as p:
            browser = await p.firefox.launch(**launch_data)
            page = await browser.new_page()
            await async_stealth(page, pure=False)
            await page.goto(url)
            success = await async_cf_retry(page)
            if not success:
                await browser.close()
                return {"success": success, "msg": "cf challenge fail"}
            user_agent = await page.evaluate("() => navigator.userAgent")
            cookies = {
                cookie["name"]: cookie["value"]
                for cookie in await page.context.cookies()
            }
            content = await page.content()
            await browser.close()
    return {
        "success": success,
        "user_agent": user_agent,
        "cookies": cookies,
        "msg": "cf challenge success",
        "content": content,
    }


if __name__ == '__main__':
    asyncio.run(main())

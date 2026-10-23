import asyncio, json, sys, http.server, threading, socketserver, os
from playwright.async_api import async_playwright
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','web'))
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=socketserver.TCPServer(('127.0.0.1',8765),Q); threading.Thread(target=srv.serve_forever,daemon=True).start()
ERR=[]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(args=['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--autoplay-policy=no-user-gesture-required'])
        ctx=await b.new_context(viewport={'width':412,'height':900},locale='ar-EG',permissions=['microphone','camera'])
        pg=await ctx.new_page()
        pg.on('pageerror',lambda e:ERR.append('PAGEERROR: '+str(e)))
        pg.on('console',lambda m:ERR.append('CONSOLE.'+m.type+': '+m.text) if m.type in('error',) else None)
        pg.on('dialog',lambda d:asyncio.ensure_future(d.accept()))
        await pg.goto('http://127.0.0.1:8765/index.html'); await pg.wait_for_timeout(800)
        async def txt(): return (await pg.inner_text('#view')).replace('\n',' ')[:140]
        async def step(name,fn):
            try: await fn(); await pg.wait_for_timeout(350); print(f'✓ {name}: {await txt()}')
            except Exception as e: print(f'✗ {name}: {e}'); ERR.append(f'STEP {name}: {e}')
        # home
        print('home:',await txt())
        # Dalal: pretest skip then real pretest
        await step('open dalal',lambda:pg.click('[data-k="dalal"]'))
        await step('pretest start',lambda:pg.click('#pre'))
        for i in range(10):
            await step(f'pretest q{i+1}',lambda:pg.click('#tq .opt >> nth=0'))
            await step('next',lambda:pg.click('#nx'))
        await step('home after pretest',lambda:pg.click('#h'))
        # scene 1 flow for Dalal (lane C)
        await step('start scene',lambda:pg.click('button[data-s]:not([disabled]) >> nth=0'))
        await step('listen next',lambda:pg.click('#next'))
        await step('guess',lambda:pg.click('#guess'))
        # q1: click wrong first, then right
        async def q1():
            opts=await pg.query_selector_all('#q1 .opt')
            for o in opts:
                if 'كثيرة الأوراق' not in (await o.inner_text()): await o.click(); break
            await pg.wait_for_timeout(100)
            for o in await pg.query_selector_all('#q1 .opt'):
                if 'كثيرة الأوراق' in (await o.inner_text()): await o.click(); break
        await step('q1 wrong→right',q1)
        async def q2():
            for o in await pg.query_selector_all('#q2 .opt'):
                if 'مُورِقَةً' in (await o.inner_text()): await o.click(); break
        await step('q2 right',q2)
        await step('understand next',lambda:pg.click('#next:not([disabled])'))
        # record step: record narr + line
        async def rec_all():
            for rb in await pg.query_selector_all('[data-rec]'):
                await rb.click(); await pg.wait_for_timeout(1500)
                key=await rb.get_attribute('data-rec')
                await pg.click(f'[data-stop="{key}"]'); await pg.wait_for_timeout(900)
        await step('record all',rec_all)
        await step('record next',lambda:pg.click('#next:not([disabled])'))
        async def family():
            for c in await pg.query_selector_all('[data-w]'):
                if (await c.get_attribute('data-w')) in ('وَرَقَة','أَوْرَاق','وَرَّاق'): await c.click(); await pg.wait_for_timeout(80)
        await step('family',family)
        await step('family next',lambda:pg.click('#next:not([disabled])'))
        async def conj():
            for o in await pg.query_selector_all('#q3 .opt'):
                if 'أَوْرَقَتِ' in (await o.inner_text()): await o.click(); break
        await step('conj',conj)
        await step('conj next',lambda:pg.click('#next:not([disabled])'))
        await step('produce record',rec_all)
        await step('produce next',lambda:pg.click('#next:not([disabled])'))
        await step('create finish',lambda:pg.click('#next'))
        await step('finish home',lambda:pg.click('#h'))
        # games hub
        await step('games',lambda:pg.click('#gmBtn'))
        await step('hide game',lambda:pg.click('[data-g="hide"]'))
        async def hide():
            for sp in await pg.query_selector_all('#wt span'):
                if 'حَدِيدِيَّةٌ' in (await sp.inner_text()): await sp.click(); break
        await step('hide click',hide); await pg.wait_for_timeout(2000)
        await step('back games',lambda:pg.click('#bk'))
        await step('ant',lambda:pg.click('[data-g="ant"]'))
        await step('ant answer',lambda:pg.click('#qx .opt >> nth=0'))
        await step('back',lambda:pg.click('#homeBtn'))
        # Kareem simplified home + picture
        await step('open kareem',lambda:pg.click('[data-k="kareem"]'))
        await step('skip pretest',lambda:pg.click('#preSkip'))
        print('kareem home:',await txt())
        await step('kareem start',lambda:pg.click('button[data-s] >> nth=0'))
        await step('listen next',lambda:pg.click('#next'))
        await step('picture tap',lambda:pg.click('#kg button >> nth=0'))
        await step('more',lambda:pg.click('#homeBtn'))
        # Parent
        await step('parent',lambda:pg.click('#pBtn'))
        await step('parent scene1',lambda:pg.click('[data-ps="0"]'))
        await step('parent record word',lambda:pg.click('[data-rec="model:s0:word"]')); await pg.wait_for_timeout(1200)
        await step('parent stop',lambda:pg.click('[data-stop="model:s0:word"]')); await pg.wait_for_timeout(800)
        await step('parent back',lambda:pg.click('#bk'))
        await step('parent review dalal',lambda:pg.click('[data-pr="dalal"]'))
        async def tapword():
            sp=await pg.query_selector('.wtap span'); 
            if sp: await sp.click()
        await step('fluency tap',tapword)
        await step('parent back2',lambda:pg.click('#bk'))
        await step('inbox',lambda:pg.click('#inbox'))
        await step('back',lambda:pg.click('#bk'))
        # theater
        await step('home',lambda:pg.click('#homeBtn'))
        await step('theater',lambda:pg.click('#thBtn'))
        await step('rehearse',lambda:pg.click('#rehearse'))
        await step('play',lambda:pg.click('#play')); await pg.wait_for_timeout(2500); print('  theater now:',await txt())
        await step('home',lambda:pg.click('#homeBtn'))
        # dedication + book export
        await step('dalal',lambda:pg.click('[data-k="dalal"]'))
        await step('ded',lambda:pg.click('#dedBtn'))
        await step('ded save',lambda:pg.click('#save'))
        await step('home',lambda:pg.click('#homeBtn'))
        await step('parent',lambda:pg.click('#pBtn'))
        async with pg.expect_download(timeout=15000) as dl:
            await pg.click('[data-book="dalal"]')
        d=await dl.value; path=await d.path(); print('book size KB',os.path.getsize(path)//1024)
        async with pg.expect_download(timeout=15000) as dl2:
            await pg.click('[data-bk="dalal"]')
        d2=await dl2.value; print('backup size KB',os.path.getsize(await d2.path())//1024)
        await pg.screenshot(path='/tmp/hadeeqa-shot.png',full_page=False)
        await b.close()
asyncio.run(main())
print('\n=== ERRORS ===');print('\n'.join(ERR) if ERR else 'none')

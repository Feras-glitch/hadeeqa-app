import asyncio, os, http.server, threading, socketserver, json
from playwright.async_api import async_playwright
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','web'))
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=socketserver.TCPServer(('127.0.0.1',8766),Q); threading.Thread(target=srv.serve_forever,daemon=True).start()
ERR=[]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(args=['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--autoplay-policy=no-user-gesture-required'])
        ctx=await b.new_context(viewport={'width':412,'height':900},permissions=['microphone','camera'],accept_downloads=True)
        pg=await ctx.new_page()
        pg.on('pageerror',lambda e:ERR.append('PAGEERROR: '+str(e)))
        pg.on('console',lambda m:ERR.append('CONSOLE: '+m.text) if m.type=='error' and 'sw.js' not in m.text else None)
        pg.on('dialog',lambda d:asyncio.ensure_future(d.accept()))
        await pg.goto('http://127.0.0.1:8766/index.html'); await pg.wait_for_timeout(800)
        async def txt(): return (await pg.inner_text('#view')).replace('\n',' ')[:150]
        async def step(name,fn,wait=350):
            try: await fn(); await pg.wait_for_timeout(wait); print(f'✓ {name}: {await txt()}')
            except Exception as e: print(f'✗ {name}: {e}'); ERR.append(f'STEP {name}: {e}')
        async def rec_all():
            for rb in await pg.query_selector_all('[data-rec]'):
                await rb.click(); await pg.wait_for_timeout(1200); key=await rb.get_attribute('data-rec')
                await pg.click(f'[data-stop="{key}"]'); await pg.wait_for_timeout(800)
        # --- fast-forward helper: complete all 10 scenes for a kid via JS (simulating done) ---
        async def mark_all_done(kid):
            await pg.evaluate("""async(kid)=>{const p=await loadProg(kid);for(let i=0;i<10;i++){p.done[i]=true;p.doneT=p.doneT||{};p.doneT[i]=Date.now()-15*864e5;const w=SCENES[i].word;p.leitner[w]={box:1,due:today()-1};p.results[w]={q1:{first:true,attempts:1,t:Date.now()}}}p.tests={pre:{score:4,t:Date.now(),detail:{}}};await saveProg(kid,p)}""",kid)
        # ===== Farah (lane B) scene 1 =====
        await step('farah',lambda:pg.click('[data-k="farah"]'))
        await step('skip pretest',lambda:pg.click('#preSkip'))
        await step('start',lambda:pg.click('button[data-s] >> nth=0'))
        await step('next',lambda:pg.click('#next'))
        await step('guess',lambda:pg.click('#guess'))
        async def q1():
            for o in await pg.query_selector_all('#q1 .opt'):
                if 'كثيرة الأوراق' in (await o.inner_text()): await o.click(); break
        await step('q1',q1)
        await step('next',lambda:pg.click('#next:not([disabled])'))
        await step('record (farah+kareem lines)',rec_all)
        n=await pg.evaluate("document.querySelectorAll('[data-rb]').length"); print('   rec blocks for farah:',n)
        await step('next',lambda:pg.click('#next:not([disabled])'))
        async def root():
            for c in await pg.query_selector_all('[data-r]'):
                if (await c.get_attribute('data-r'))=='و ر ق': await c.click(); break
        await step('root',root)
        await step('next',lambda:pg.click('#next:not([disabled])'))
        await step('produce',rec_all)
        await step('next',lambda:pg.click('#next:not([disabled])'))
        await step('finish',lambda:pg.click('#next'))
        await step('home',lambda:pg.click('#h'))
        # ===== Leitner review due today: force due and run review =====
        await pg.evaluate("""async()=>{const p=await loadProg('farah');for(const w in p.leitner){p.leitner[w].due=today()}await saveProg('farah',p)}""")
        await step('reload kid',lambda:pg.click('#homeBtn'))
        await step('farah again',lambda:pg.click('[data-k="farah"]'))
        await step('review',lambda:pg.click('#revBtn'))
        async def anyright():
            for o in await pg.query_selector_all('#q1 .opt'):
                if await pg.is_enabled('#nx'): break
                if await o.is_enabled(): await o.click(); await pg.wait_for_timeout(150)
        await step('review answer',anyright)
        await step('review next',lambda:pg.click('#nx:not([disabled])'))
        box=await pg.evaluate("async()=>{const p=await loadProg('farah');return p.leitner['مُورِقَة']}"); print('   leitner after review:',box)
        # ===== Mark all done for dalal, test order game + post test gating + hidden word for all scenes =====
        await mark_all_done('dalal')
        await step('home',lambda:pg.click('#homeBtn'))
        await step('dalal',lambda:pg.click('[data-k="dalal"]'))
        print('   post test visible:', 'اختبار الكلمات العشر' in await txt())
        await step('order 1-5',lambda:pg.click('[data-og="0,4"]'))
        async def order():
            for i in range(5):
                await pg.click(f'[data-o="{i}"]'); await pg.wait_for_timeout(250)
        await step('order taps',order)
        await step('order rec',rec_all)
        await step('order done',lambda:pg.click('#h'))
        await step('games',lambda:pg.click('#gmBtn'))
        # hidden word for all 10
        await step('hide',lambda:pg.click('[data-g="hide"]'))
        for i in range(10):
            subs=await pg.evaluate("EXTRA.map(e=>e.hide)")
            async def h():
                found=False
                for sp in await pg.query_selector_all('#wt span'):
                    t=await sp.inner_text()
                    if t in subs: await sp.click(); found=True; break
                if not found: raise Exception('substitute not found in scene '+str(i))
            await step(f'hide scene {i+1}',h,2000)
        # post test
        await step('home',lambda:pg.click('#homeBtn'))
        await step('dalal',lambda:pg.click('[data-k="dalal"]'))
        await step('post test',lambda:pg.click('#postBtn'))
        for i in range(10):
            await pg.click('#tq .opt >> nth=0'); await pg.click('#nx')
        print('   post done:',await txt())
        await step('home',lambda:pg.click('#h'))
        # ===== Theater: advance through 3 lines (fake audio ends quickly) =====
        await step('home',lambda:pg.click('#homeBtn'))
        await step('theater',lambda:pg.click('#thBtn'))
        await step('play',lambda:pg.click('#play'),4000)
        await step('next line',lambda:pg.click('#nx'),800)
        await step('next line',lambda:pg.click('#nx'),800)
        # ===== Backup round trip with identity lock =====
        await step('home',lambda:pg.click('#homeBtn'))
        await step('farah',lambda:pg.click('[data-k="farah"]'))
        async with pg.expect_download() as dl:
            await pg.click('#myBk')
        path=await (await dl.value).path(); data=json.load(open(path)); print('   backup kid:',data['kid'],'audio keys:',len(data['audio']))
        await step('home',lambda:pg.click('#homeBtn'))
        await step('kareem',lambda:pg.click('[data-k="kareem"]'))
        await pg.set_input_files('#preRs',path); await pg.wait_for_timeout(800); print('   wrong-kid restore toast shown?', 'ليس ملفك' in (await pg.inner_text('#toast')))
        await step('home',lambda:pg.click('#homeBtn'))
        await step('farah',lambda:pg.click('[data-k="farah"]'))
        await pg.set_input_files('#myRs',path); await pg.wait_for_timeout(1500); print('   restore ok:',await txt())
        await pg.screenshot(path='/tmp/hadeeqa-shot.png'); await b.close()
asyncio.run(main())
print('\n=== ERRORS ===');print('\n'.join(ERR) if ERR else 'none')

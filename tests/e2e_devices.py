"""اختبار الانتقال بين الأجهزة وألعاب المراجعة والمسرح سطرًا بسطر.
جهاز ١ وجهاز ٢ = سياقان منفصلان في المتصفح (قاعدتا بيانات مستقلتان)، كتابلت فرح وتابلت كريم."""
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from helpers import serve, new_page, view, solve_quiz, record_all, run_scene

URL = serve(8794)
ERR, FAIL = [], []


def ok(name, cond, detail=''):
    print(('✓ ' if cond else '✗ ') + name + (' — ' + detail if detail else ''))
    if not cond:
        FAIL.append(name)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', '--autoplay-policy=no-user-gesture-required'])

        # ================= جهاز ١: تابلت فرح =================
        pg = await new_page(b, ERR); ev = pg.evaluate
        await pg.goto(URL); await pg.wait_for_timeout(900)
        await pg.click('[data-k="farah"]'); await pg.click('#preSkip'); await pg.wait_for_timeout(400)
        await pg.click('button[data-s] >> nth=0'); await pg.wait_for_timeout(400)
        ok('farah: scene 1 to celebration', await run_scene(pg, log=lambda s: None))
        recs = await ev("(async()=>{const ks=await skeys('audio');return ks.filter(k=>k.startsWith('rec:farah:s0:'))})()")
        exp = await ev("['rec:farah:s0:narr',...SCENES[0].lines.map((l,j)=>l.w==='farah'?'rec:farah:s0:l'+j:null).filter(Boolean)]")
        ok('farah reads narrator + exactly her own lines', sorted(recs) == sorted(exp), ', '.join(recs))
        await pg.click('#mg'); await pg.wait_for_timeout(300); await record_all(pg)
        await pg.click('#bk'); await pg.click('#homeBtn'); await pg.click('[data-k="farah"]'); await pg.wait_for_timeout(400)
        await pg.click('#bag summary'); await pg.wait_for_timeout(200)
        async with pg.expect_download() as d:
            await pg.click('#myBk')
        path = await (await d.value).path()
        bk = json.load(open(path))
        ok('backup: identity + progress + voices', bk['kid'] == 'farah' and bk['prog']['done'].get('0') and 'magic:farah:0' in bk['audio'] and len(bk['audio']) >= 3, f"{len(bk['audio'])} voices")

        # ================= جهاز ٢: تابلت جديد فارغ =================
        pg2 = await new_page(b, ERR); ev2 = pg2.evaluate
        await pg2.goto(URL); await pg2.wait_for_timeout(900)
        await pg2.click('[data-k="kareem"]'); await pg2.set_input_files('#preRs', path); await pg2.wait_for_timeout(700)
        ok('wrong child refused (kareem cannot load farah file)', 'ليس ملفك' in await pg2.inner_text('#toast') and not (await ev2("loadProg('kareem')")).get('done', {}).get('0'))
        await pg2.click('#homeBtn'); await pg2.click('[data-k="farah"]'); await pg2.set_input_files('#preRs', path); await pg2.wait_for_timeout(1500)
        ok('farah restored on new device: home with garden', bool(await pg2.query_selector('svg.garden')) and 'المشهد ٢' in await view(pg2))
        ok('restored garden shows her first word', bool(await pg2.query_selector('.gw[data-gw="0"]')))
        ok('restored voices playable', bool(await ev2("sget('audio','magic:farah:0')")) and bool(await ev2("sget('audio','rec:farah:s0:narr')")))
        # استعادة ثانية من داخل الحقيبة (فوق بيانات موجودة) — تطلب تأكيدًا ثم تنجح
        await pg2.click('#bag summary'); await pg2.set_input_files('#myRs', path); await pg2.wait_for_timeout(1500)
        ok('second restore from bag keeps one copy', (await ev2("loadProg('farah')"))['done'].get('0') is True and 'المشهد ٢' in await view(pg2))

        # ================= ألعاب المراجعة على جهاز ١ =================
        await ev("""(async()=>{const p=await loadProg('dalal');for(let i=0;i<10;i++){p.done[i]=true;(p.doneT=p.doneT||{})[i]=Date.now()-15*864e5;p.leitner[SCENES[i].word]={box:1,due:today()+1}}p.tests={pre:{score:5,t:Date.now()}};await saveProg('dalal',p)})()""")
        await pg.click('#homeBtn'); await pg.click('[data-k="dalal"]'); await pg.wait_for_timeout(400)
        await pg.click('#gmBtn'); await pg.wait_for_timeout(300)
        await pg.click('[data-g="hide"]'); await pg.wait_for_timeout(300)
        subs = await ev("EXTRA.map(e=>e.hide)")
        found = 0
        for i in range(10):
            for sp in await pg.query_selector_all('#wt span'):
                if (await sp.inner_text()) in subs:
                    await sp.click(); found += 1; break
            await pg.wait_for_timeout(2000)
        ok('hidden-word game: intruder found in all 10 scenes', found == 10, f'{found}/10')
        await pg.click('#homeBtn'); await pg.click('[data-k="dalal"]'); await pg.click('#gmBtn'); await pg.click('[data-g="ant"]'); await pg.wait_for_timeout(300)
        ok('antonym game opens a question', bool(await pg.query_selector('#qx .opt')))
        await solve_quiz(pg, 'qx')
        ok('antonym game advances', not await pg.is_disabled('#nx'))

        # ================= المسرح سطرًا بسطر =================
        await pg.click('#homeBtn'); await pg.click('#thBtn'); await pg.click('#play'); await pg.wait_for_timeout(2500)
        t1 = await view(pg)
        await pg.click('#nx'); await pg.wait_for_timeout(900)
        t2 = await view(pg)
        ok('theater next line moves forward', t1 != t2)
        await pg.click('#homeBtn'); await b.close()

asyncio.run(main())
print('\n=== FAILED ===', FAIL or 'none')
print('=== ERRORS ===', ERR or 'none')
sys.exit(1 if FAIL or ERR else 0)

"""اختبار الانتقال بين الأجهزة وألعاب المراجعة والمسرح سطرًا بسطر.
جهاز ١ وجهاز ٢ = سياقان منفصلان في المتصفح (قاعدتا بيانات مستقلتان)، كتابلت فرح وتابلت كريم."""
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from helpers import answer_gate, serve, new_page, view, solve_quiz, record_all, run_scene, skip_pre, take_test

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
        await pg.click('[data-k="farah"]'); await skip_pre(pg)
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
                if (await sp.inner_text()).rstrip('.,،؛:!؟') in subs:
                    await sp.click(); found += 1; break
            await pg.wait_for_timeout(2000)
        ok('hidden-word game: intruder found in all 10 scenes', found == 10, f'{found}/10')
        await pg.click('#homeBtn'); await pg.click('[data-k="dalal"]'); await pg.click('#gmBtn'); await pg.click('[data-g="ant"]'); await pg.wait_for_timeout(300)
        ok('antonym game opens a question', bool(await pg.query_selector('#qx .opt')))
        await solve_quiz(pg, 'qx')
        ok('antonym game advances', not await pg.is_disabled('#nx'))

        # ================= تحدّي الإخوة وأسئلة بابا وماما بين تابلتين =================
        async def rec(page, key):
            await page.click(f'[data-rec="{key}"]'); await page.wait_for_timeout(1100)
            await page.click(f'[data-stop="{key}"]'); await page.wait_for_timeout(800)
        async def bag(page, kid):
            await page.click('#homeBtn'); await page.click(f'[data-k="{kid}"]'); await page.wait_for_timeout(400)
            if await page.query_selector('#more'):
                await page.click('#more summary'); await page.wait_for_timeout(150)
            await page.click('#bag summary'); await page.wait_for_timeout(150)
            async with page.expect_download() as d:
                await page.click('#myBk')
            return await (await d.value).path()
        async def parent_import(page, path, choice):
            await page.click('#homeBtn'); await page.click('#pBtn'); await page.wait_for_timeout(200); await answer_gate(page); await page.wait_for_timeout(700)
            await page.set_input_files('#bkin', path); await page.wait_for_timeout(700)
            await page.click(f'.mdl-c button >> text={choice}'); await page.wait_for_timeout(1200)
        # فرح (تابلتها) ترسل تحديًا لكريم وتسأل بابا وماما
        await pg.click('#homeBtn'); await pg.click('[data-k="farah"]'); await pg.click('#gmBtn'); await pg.click('[data-g="chal"]'); await pg.wait_for_timeout(400)
        await pg.select_option('#cto', 'kareem'); await rec(pg, 'chal:new:farah'); await pg.click('#send'); await pg.wait_for_timeout(500)
        await pg.click('#bk'); await pg.click('[data-g="ask"]'); await pg.wait_for_timeout(300); await rec(pg, 'ask:new:farah'); await pg.click('#send'); await pg.wait_for_timeout(500)
        f_bag = await bag(pg, 'farah')
        fb = json.load(open(f_bag))
        ok('farah\'s bag carries her challenge + its question audio + her question', len(fb.get('challenges', [])) == 1 and any(k.startswith('chal:') and k.endswith(':q') for k in fb['audio']) and len(fb['prog'].get('asks', [])) == 1)
        # تابلت كريم: ولي الأمر يضمّ رسائل فرح فقط
        pg3 = await new_page(b, ERR); ev3 = pg3.evaluate
        await pg3.goto(URL); await pg3.wait_for_timeout(900)
        await pg3.click('[data-k="kareem"]'); await pg3.wait_for_timeout(300); await skip_pre(pg3)
        await ev3("(async()=>{const p=await loadProg('kareem');p.done[0]=true;p.leitner[SCENES[0].word]={box:1,due:today()+1};await saveProg('kareem',p)})()")
        await parent_import(pg3, f_bag, 'الرسائل والتحديات فقط')
        ok('messages-only on kareem\'s tablet: challenge arrives, no farah profile created', len(await ev3("allChallenges()")) == 1 and await ev3("sget('kv','prog:farah')") is None)
        await pg3.click('#homeBtn'); await pg3.click('[data-k="kareem"]'); await pg3.click('#gmBtn'); await pg3.wait_for_timeout(300)
        ok('kareem sees a challenge waiting (🔔)', '🔔' in await view(pg3))
        await pg3.click('[data-g="chal"]'); await pg3.wait_for_timeout(400)
        cid = (await ev3("allChallenges()"))[0]['id']
        await rec(pg3, f'chal:{cid}:a'); await pg3.wait_for_timeout(500)
        ok('kareem answered on his tablet', bool((await ev3("allChallenges()"))[0].get('a')))
        k_bag = await bag(pg3, 'kareem')
        # تابلت فرح: ضمّ إجابة كريم، ثم حكم ولي الأمر
        await parent_import(pg, k_bag, 'الرسائل والتحديات فقط')
        ok('kareem\'s answer reaches farah\'s tablet', bool((await ev("allChallenges()"))[0].get('a')) and await ev(f"hasKey('chal:{cid}:a')"))
        await pg.click('#inbox'); await pg.wait_for_timeout(500)
        await pg.click(f'[data-j="{cid}"][data-v="1"]'); await pg.wait_for_timeout(500)
        ok('judging on farah\'s tablet does not create a kareem profile there', await ev("sget('kv','prog:kareem')") is None and (await ev("allChallenges()"))[0].get('star') is True)
        f_bag2 = await bag(pg, 'farah')
        await parent_import(pg3, f_bag2, 'الرسائل والتحديات فقط')
        ok('the star reaches kareem\'s results on his tablet', bool((await ev3("loadProg('kareem')"))['results'].get(await ev3("SCENES[0].word"), {}).get('chal')))
        # الحاسوب (pg2 فيه بيانات فرح): ولي الأمر يجيب سؤالها، ثم يعود الجواب لتابلتها دون أن يمحو تقدّمها الأحدث
        await parent_import(pg2, f_bag, 'استعادة كاملة')
        aid = (await ev2("loadProg('farah')"))['asks'][0]['id']
        await pg2.click('#homeBtn'); await pg2.click('#pBtn'); await pg2.wait_for_timeout(200); await answer_gate(pg2); await pg2.wait_for_timeout(700)
        await pg2.click('#inbox'); await pg2.wait_for_timeout(500); await rec(pg2, f'ans:farah:{aid}')
        await pg2.click('#bk'); await pg2.wait_for_timeout(700)
        async with pg2.expect_download() as d:
            await pg2.click('[data-bk="farah"]')
        pc_bag = await (await d.value).path()
        await ev("(async()=>{const p=await loadProg('farah');p.done[1]=true;p.doneT[1]=Date.now()+5*60e3;await saveProg('farah',p)})()")
        await pg.click('#homeBtn'); await pg.click('[data-k="farah"]'); await pg.wait_for_timeout(400); await pg.click('#bag summary')
        await pg.set_input_files('#myRs', pc_bag); await pg.wait_for_timeout(800)
        ok('older file from the computer: app offers messages-only', bool(await pg.query_selector('.mdl-c')) and 'أقدم' in await pg.inner_text('.mdl-c'))
        await pg.click('.mdl-c button >> text=الرسائل والتحديات فقط'); await pg.wait_for_timeout(1200)
        fp = await ev("loadProg('farah')")
        ok('parent\'s answer arrives; farah\'s newer progress kept', fp['asks'][0].get('answered') == 1 and await ev(f"hasKey('ans:farah:{aid}')") and fp['done'].get('1') is True)

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

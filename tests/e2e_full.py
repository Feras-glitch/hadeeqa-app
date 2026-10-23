"""اختبار شامل في المتصفح: الأطفال الثلاثة، المفاجآت الخمس، الحديقة، اللفافة، السقاية، كلمة اليوم، حكاية النوم،
الأصوات السحرية، المسابقة، ولي الأمر، الكتاب، النسخة الاحتياطية، الاختبار البعدي، المسرح."""
import asyncio, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from helpers import serve, new_page, view, solve_quiz, solve_fun, record_all, run_scene, answer_gate, take_test, skip_pre, start_next_scene

URL = serve(8790)
ERR, FAIL = [], []


HS = []


async def nohs(pg, where):
    """لا تمرير أفقي: الصفحة لا تتجاوز عرض الشاشة."""
    w = await pg.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
    if w[0] > w[1] + 1:
        HS.append(f'{where}: {w[0]}>{w[1]}')


def ok(name, cond, detail=''):
    print(('✓ ' if cond else '✗ ') + name + (' — ' + detail if detail else ''))
    if not cond:
        FAIL.append(name)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', '--autoplay-policy=no-user-gesture-required'])
        pg = await new_page(b, ERR)
        await pg.goto(URL); await pg.wait_for_timeout(900)
        ev = pg.evaluate

        # ---------- دلال (المسار الأكبر) ----------
        await pg.click('[data-k="dalal"]'); await pg.wait_for_timeout(500)
        ok('pre-test gate blocks the story', bool(await pg.query_selector('#pre')) and not await pg.query_selector('svg.garden'))
        await pg.click('#pre'); await pg.wait_for_timeout(300)
        ok('pre-test asks oral first (word shown, no options yet)', bool(await pg.query_selector('#tdk')) and not await pg.query_selector('#tq'))
        # pause half-way and resume
        for _ in range(7):
            if await pg.query_selector('#tdk'): await pg.click('#tdk')
            else: await pg.click('#tq .opt >> nth=0')
            await pg.wait_for_timeout(600)
        await pg.click('#tpause'); await pg.wait_for_timeout(400)
        ok('paused test resumes where it stopped', 'أكمل (٧' in await view(pg))
        await pg.click('#pre'); await pg.wait_for_timeout(300)
        n = await take_test(pg)
        pre = await ev("S.prog.tests.pre")
        conds = await ev("Object.keys(S.prog.tests.pre.resp).map(id=>testItem(id).cond).reduce((a,c)=>(a[c]=(a[c]||0)+1,a),{})")
        ok('dalal pre-test: 10 story + 10 control + 20 bonus words', conds == {'T': 10, 'C': 10, 'B': 20} and pre['done'], str(conds))
        ok('no test word leaks into the family quiz', await ev("(()=>{const st=new Set();for(let r=0;r<400;r++){const q=quizQ(['dalal','farah','feras'][r%3],new Set());if(q&&q.q)st.add(q.q.s)}const T=[...TEST_T,...CONTROL,...TEST_B.flat()].map(x=>x.s);return !T.some(s=>st.has(s))})()"))
        await pg.click('#h'); await pg.wait_for_timeout(500)
        await nohs(pg, 'kid home C'); ok('kid home: garden', bool(await pg.query_selector('svg.garden')))
        ok('kid home: map has 10 stations', await ev("document.querySelectorAll('.mp-n').length") == 10)
        ok('kid home: only current station open', await ev("document.querySelectorAll('.mp-n[data-s]').length") == 1)
        ok('kid home: 4 action buttons', await ev("document.querySelectorAll('.acts button').length") == 4)
        await pg.click('button[data-s] >> nth=0'); await pg.wait_for_timeout(400)
        ok('scene 1 (lane C) to celebration incl. bonus words + jigsaw', await run_scene(pg, hs=HS))
        ok('celebration: new garden object pops', bool(await pg.query_selector('.gw.pop')))
        b1 = await ev("S.prog.bonus"); ok('bonus words recorded', b1 and len(b1) == 2, str(list((b1 or {}).keys())))
        # magic from celebration
        await pg.click('#mg'); await pg.wait_for_timeout(400)
        await nohs(pg, 'magic'); ok('magic game opens on this word', 'مُورِقَة' in await view(pg))
        await record_all(pg); await pg.wait_for_timeout(300)
        for fx in range(10):
            await ev(f"(async()=>{{const r=await sget('audio','magic:dalal:0');await magicPlay(r.blob,{fx})}})()")
        await pg.wait_for_timeout(500)
        ok('all 10 magic effects play without error', not [e for e in ERR if 'magic' in e.lower() or 'decode' in e.lower()])
        await pg.click('#bk'); await pg.click('#homeBtn'); await pg.click('[data-k="dalal"]'); await pg.wait_for_timeout(400)
        ok('one new scene a day: scene 2 waits for tomorrow', 'غدًا' in await view(pg))
        await start_next_scene(pg)
        ok('scene 2 to celebration incl. magnifier (parent unlocked)', await run_scene(pg, hs=HS))
        # remaining surprises, jumped to directly
        for sc, name in [(4, 'maze'), (5, 'size order'), (8, 'scratch')]:
            await ev(f"(async()=>{{S.prog.scene={sc};S.prog.step=2;await go('scene')}})()"); await pg.wait_for_timeout(500)
            await nohs(pg, name)
            await solve_fun(pg)
            ok(f'surprise {name} solved', not await pg.is_disabled('#next'))
        await ev("(async()=>{S.prog.scene=1;S.prog.step=0;delete S.prog.done[4];delete S.prog.done[5];delete S.prog.done[8];await saveProg('dalal',S.prog)})()")

        # ---------- السقاية + اللفافة ----------
        await ev("(async()=>{const p=await loadProg('dalal');for(const w in p.leitner)p.leitner[w].due=today();for(const w in p.bleit)p.bleit[w].due=today();await saveProg('dalal',p)})()")
        await pg.click('#homeBtn'); await pg.click('[data-k="dalal"]'); await pg.wait_for_timeout(400)
        ok('water button shows 6 due (2 words + 4 bonus)', '(٦)' in await view(pg))
        # يجيب الاختبار إجابات صحيحة: نرتّب الخيارات مؤقتًا لتكون الصحيحة أولًا (التطبيق لا يكشفها في الصفحة)
        await ev("(()=>{window.__sh=shuffle;shuffle=a=>{const r=a.slice();if(r.length&&r[0]&&typeof r[0]==='object'&&'c' in r[0])r.sort((x,y)=>(y.c?1:0)-(x.c?1:0));return r}})()")
        await pg.click('#revBtn'); await pg.wait_for_timeout(300)
        for _ in range(8):
            if 'حديقتك!' in await view(pg):
                break
            if await pg.query_selector('#kg'):
                await pg.click('#kg button >> nth=0')
            else:
                await solve_quiz(pg, 'q1')
            await pg.wait_for_timeout(200)
            await pg.click('#nx'); await pg.wait_for_timeout(300)
        ok('watering ends with celebration', 'حديقتك!' in await view(pg))
        await ev("(()=>{shuffle=window.__sh})()")
        lit = await ev("litCount(S.prog)"); ok('scroll: both watered words light a letter', lit == 2, f'lit={lit}')
        await ev("(async()=>{const p=S.prog;SCENES.slice(0,5).forEach(s=>p.leitner[s.word]={box:2,due:today()+3});await saveProg('dalal',p);await go('scroll')})()"); await pg.wait_for_timeout(400)
        on, tot = await ev("document.querySelectorAll('.lt.on').length"), await ev("document.querySelectorAll('.lt').length")
        await nohs(pg, 'scroll'); ok('scroll: half the letters at 5/10', on == tot // 2, f'{on}/{tot}')
        await pg.fill('#gs', 'كنز العائله'); await pg.click('#gsb'); await pg.wait_for_timeout(300)
        ok('scroll: early guess accepted (ة/ه tolerant)', bool(await ev("S.prog.scrollGuess")))
        await ev("(async()=>{const p=S.prog;SCENES.forEach(s=>p.leitner[s.word]={box:2,due:today()+3});await saveProg('dalal',p);await go('scroll')})()"); await pg.wait_for_timeout(400)
        ok('scroll: all letters at 10/10 + open button', await ev("document.querySelectorAll('.lt.on').length") == tot and bool(await pg.query_selector('#openMsg')))
        await ev("(async()=>{const p=S.prog;SCENES.forEach((s,i)=>{if(i>1)delete p.leitner[s.word]});await saveProg('dalal',p)})()")

        # ---------- كلمة اليوم ----------
        await pg.click('#homeBtn'); await pg.click('[data-k="dalal"]'); await pg.wait_for_timeout(400)
        ok('word of the day banner', bool(await pg.query_selector('.wotd')))
        await pg.click('#wotdStar'); await pg.wait_for_timeout(200)
        ok('parent gate answered', await answer_gate(pg)); await pg.wait_for_timeout(500)
        ok('star awarded', await ev("S.prog.stars") == 1)

        # ---------- حكاية النوم ----------
        await pg.click('#bedBtn'); await pg.click('[data-v="model"]'); await pg.wait_for_timeout(1500)
        await nohs(pg, 'bedtime'); ok('bedtime overlay plays text', bool(await pg.query_selector('.ovl.bed')) and len((await pg.inner_text('.bed-t')).strip()) > 10)
        await pg.click('.bed-x'); await pg.wait_for_timeout(400)
        ok('bedtime closes cleanly', not await pg.query_selector('.ovl.bed') and await ev("S.view") == 'kid')

        # ---------- فرح (المسار الأوسط) ----------
        await pg.click('#homeBtn'); await pg.click('[data-k="farah"]'); await skip_pre(pg)
        await pg.click('button[data-s] >> nth=0'); await pg.wait_for_timeout(400)
        ok('scene 1 (lane B) to celebration', await run_scene(pg, hs=HS))

        # ---------- كريم (المسار الأصغر) ----------
        await pg.click('#homeBtn'); await pg.click('[data-k="kareem"]'); await skip_pre(pg)
        await nohs(pg, 'kid home A'); ok('kareem: big picture start button', bool(await pg.query_selector('button[data-s] img, button[data-s] .ph')))
        ok('kareem: extras tucked under ⋯', bool(await pg.query_selector('details#more')))
        await pg.click('button[data-s] >> nth=0'); await pg.wait_for_timeout(400)
        ok('scene 1 (lane A) to celebration incl. 2×2 jigsaw', await run_scene(pg, hs=HS))
        await pg.click('#h'); await pg.wait_for_timeout(300)
        await pg.click('.gw[data-gw="0"]'); await pg.wait_for_timeout(300)
        ok('garden object opens word card', bool(await pg.query_selector('.mdl-c')) and 'مُورِقَة' in await pg.inner_text('.mdl-c'))
        await pg.click('.mdl-c button >> text=حسنًا')

        # ---------- مسابقة العائلة ----------
        await pg.click('#homeBtn'); await pg.click('#qzBtn'); await pg.click('[data-r="2"]'); await pg.click('#qgo')
        for _ in range(12):
            if await pg.query_selector('#again'):
                break
            await pg.click('#rdy'); await pg.wait_for_timeout(300)
            if await pg.query_selector('#kg button'):
                await pg.click('#kg button >> nth=0')
            else:
                await pg.click('#qo .opt >> nth=0')
            await pg.wait_for_timeout(150); await pg.click('#qn'); await pg.wait_for_timeout(200)
        await nohs(pg, 'podium'); ok('quiz: 10 turns to podium', bool(await pg.query_selector('.pod')))

        # ---------- ولي الأمر ----------
        await pg.click('#hm'); await pg.click('#pBtn'); await pg.wait_for_timeout(200); await answer_gate(pg); await pg.wait_for_timeout(600)
        await pg.select_option('#wotdSel', 'عَتِيق'); await pg.wait_for_timeout(200)
        await nohs(pg, 'parent'); ok('parent: word of day pinned', (await ev("sget('kv','wotd:o')"))['w'] == 'عَتِيق')
        await pg.click('details.card >> text=📜 اللفافة السرية ورسائلها')
        await pg.fill('[data-php="kareem"]', 'بابا يحبك'); await pg.click('[data-phs="kareem"]'); await pg.wait_for_timeout(300)
        ok('parent: scroll phrase saved', (await ev("loadProg('kareem')"))['scrollPhrase'] == 'بابا يحبك')
        async with pg.expect_download(timeout=30000) as d:
            await pg.click('[data-book="dalal"]')
        bp = await (await d.value).path()
        ok('book export (embedded images)', os.path.getsize(bp) > 1_000_000, f'{os.path.getsize(bp)//1024} KB')
        async with pg.expect_download(timeout=30000) as d:
            await pg.click('[data-bk="dalal"]')
        bk = json.load(open(await (await d.value).path()))
        ok('backup carries magic voice + progress', 'magic:dalal:0' in bk['audio'] and bk['prog']['stars'] == 1)

        # ---------- الاختبار البعدي + الترتيب ----------
        await ev("(async()=>{const p=await loadProg('dalal');for(let i=0;i<10;i++){p.done[i]=true;(p.doneT=p.doneT||{})[i]=Date.now()-15*864e5}await saveProg('dalal',p)})()")
        await pg.click('#homeBtn'); await pg.click('[data-k="dalal"]'); await pg.wait_for_timeout(400)
        await pg.click('#postBtn'); await pg.wait_for_timeout(300)
        await take_test(pg)
        await pg.click('#h'); await pg.wait_for_timeout(300)
        ok('post test stored', (await ev("loadProg('dalal')"))['tests']['post']['done'] is True)
        ok('delayed test announced in 14 days', '١٤ يوم' in await view(pg))
        await ev("(async()=>{const p=await loadProg('dalal');p.tests.post.t-=15*864e5;await saveProg('dalal',p);await go('kid','dalal')})()"); await pg.wait_for_timeout(400)
        await pg.click('#delayBtn'); await pg.wait_for_timeout(300); await take_test(pg); await pg.click('#h'); await pg.wait_for_timeout(300)
        ok('delayed retention test stored', (await ev("loadProg('dalal')"))['tests']['delay']['done'] is True)

        # ---------- التصحيح الأعمى والتقرير ----------
        await pg.click('#homeBtn'); await pg.click('#pBtn'); await pg.wait_for_timeout(200); await answer_gate(pg); await pg.wait_for_timeout(700)
        await nohs(pg, 'parent+assessment')
        qn = await ev("oralQueue().then(q=>q.length)")
        kinds = await ev("oralQueue().then(q=>[...new Set(q.map(x=>x.kind))].sort())")
        ok('blind queue mixes pre + post + delay recordings', qn >= 15 and kinds == ['delay', 'post', 'pre'], f'{qn} items {kinds}')
        await pg.click('#scOral'); await pg.wait_for_timeout(300)
        vv = await view(pg); ok('scoring screen hides which test the answer came from', not any(k in vv for k in ['البداية', 'الختامي', 'التذكّر', 'pre', 'post']))
        for i in range(qn):
            await pg.click('[data-sc="%s"]' % ('2' if i % 3 else '1')); await pg.wait_for_timeout(120)
        ok('all oral answers scored', await ev("oralQueue().then(q=>q.length)") == 0)
        await pg.click('#bk'); await pg.wait_for_timeout(700)
        card = await pg.inner_text('#view')
        ok('report: story vs control words + net effect', 'كلمات المقارنة' in card and 'أثر التطبيق' in card and 'شفهي' in card)
        ok('report: usage log (days, minutes, what the child opens)', 'أيام النشاط' in card)
        async with pg.expect_download(timeout=30000) as d:
            await pg.click('#csvBtn')
        csv = open(await (await d.value).path(), encoding='utf-8-sig').read().splitlines()
        ok('assessment CSV: one row per item per test', len(csv) - 1 == 3 * 40 and csv[0].startswith('kid,lane,test,item,cond'), f'{len(csv)-1} rows')
        await pg.click('#homeBtn'); await pg.click('[data-k="dalal"]'); await pg.wait_for_timeout(400)
        await pg.click('[data-og="0,4"]')
        for i in range(5):
            await pg.click(f'[data-o="{i}"]'); await pg.wait_for_timeout(200)
        ok('order game reaches narration step', bool(await pg.query_selector('[data-rec]')))

        # ---------- المسرح ----------
        await pg.click('#homeBtn'); await pg.click('#thBtn'); await pg.click('#play'); await pg.wait_for_timeout(1500)
        ok('theater plays', 'المشهد' in await view(pg))
        await pg.click('#homeBtn'); await pg.wait_for_timeout(2500)
        ok('theater stops after leaving', 'الأطفال' in await view(pg))
        ok('no horizontal scrolling on any screen', not HS, '; '.join(HS))
        await b.close()

asyncio.run(main())
print('\n=== FAILED ===', FAIL or 'none')
print('=== ERRORS ===', ERR or 'none')
sys.exit(1 if FAIL or ERR else 0)

"""المراجعة الرابعة: فحص لكل إصلاح، ولثلاثة أخطاء لم تكشفها الاختبارات السابقة (اختبار الطفرات)."""
import asyncio, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from helpers import serve, new_page, view, answer_gate

URL = serve(8789)
ERR, FAIL = [], []


def ok(name, cond, detail=''):
    print(('✓ ' if cond else '✗ ') + name + (' — ' + detail if detail else ''))
    if not cond:
        FAIL.append(name)


AUD = "{blob:new Blob([new Uint8Array(900)],{type:'audio/webm'}),mime:'audio/webm',sec:2,t:1}"
PRE_DONE = "{v:2,k:999,done:true,t:Date.now()-20*864e5,t0:Date.now()-20*864e5,resp:{},lane:'C'}"


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', '--autoplay-policy=no-user-gesture-required'])
        pg = await new_page(b, ERR); ev = pg.evaluate
        await pg.goto(URL); await pg.wait_for_timeout(900)
        tmp = tempfile.mkdtemp()

        # ---------- طفرات لم تُكشف من قبل ----------
        ok('test-plan order is frozen (an in-progress test resumes on the same items)',
           await ev("[testPlan('dalal','pre').slice(0,6).map(x=>x[0]).join(','),testPlan('kareem','post').slice(0,6).map(x=>x[0]).join(',')]") == ['c1,c1,c9,c9,t9,t9', 't1,t1,c1,c1,t5,t5'])
        q = await ev("""(async()=>{const p=await loadProg('dalal');p.tests={pre:{v:2,k:999,done:true,t:1,t0:1,resp:{t0:{rec:{ok:0,dk:1},oral:{has:1,t:1}}}}};await saveProg('dalal',p);await sput('audio','test:dalal:pre:t0',""" + AUD + """);return (await oralQueue()).length})()""")
        ok('pre-test answers stay out of the scoring queue until the final test exists', q == 0, str(q))
        r = await ev("""(async()=>{const p=await loadProg('farah');p.tests={pre:""" + PRE_DONE + """};p.done={};p.doneT={};for(let i=0;i<10;i++){p.done[i]=true;p.doneT[i]=Date.now()}await saveProg('farah',p);await go('kid','farah');const a=!!document.querySelector('#postBtn');
            for(let i=0;i<10;i++)p.doneT[i]=Date.now()-2*864e5;await saveProg('farah',p);await go('kid','farah');return [a,!!document.querySelector('#postBtn')]})()""")
        ok('final test is not offered on the day of the last scene, and is offered after it', r == [False, True], str(r))

        # ---------- p1: كريم والاختبار الختامي، والمقدّمة قبل الختامي، والأسهم، والعدد والمعدود ----------
        await ev("""(async()=>{const p=await loadProg('kareem');p.tests={pre:{v:2,k:999,done:true,t:1,t0:1,resp:{},lane:'A'}};p.done={};p.doneT={};for(let i=0;i<10;i++){p.done[i]=true;p.doneT[i]=Date.now()-2*864e5}await saveProg('kareem',p);await go('kid','kareem')})()""")
        await pg.wait_for_timeout(400)
        ok('Kareem: the final-test button is on the page, not inside «المزيد»', await ev("(()=>{const b=document.querySelector('#postBtn');return !!b&&!b.closest('details')})()"))
        await pg.click('#postBtn'); await pg.wait_for_timeout(300)
        mc = await pg.query_selector('.mdl-c')
        ok('…the final test opens with the same «لا أعرف is fine» intro as the pre-test', bool(mc) and 'لا أعرف' in await mc.inner_text())
        if mc:
            await pg.click('.mdl-c button >> nth=0'); await pg.wait_for_timeout(500)
        ok('…then the test itself starts', bool(await pg.query_selector('#tdk')) or bool(await pg.query_selector('#tq')))
        ok('number agreement helper: ١ يوم / يومان / ٣ أيام / ١٢ يومًا',
           await ev("[nn(1,'يوم','يومان','أيام','يومًا'),nn(2,'يوم','يومان','أيام','يومًا'),nn(3,'يوم','يومان','أيام','يومًا'),nn(12,'يوم','يومان','أيام','يومًا')]") == ['يوم', 'يومان', '٣ أيام', '١٢ يومًا'])
        await ev("""(async()=>{const p=await loadProg('dalal');p.tests={pre:""" + PRE_DONE + """};p.done={};p.doneT={};p.scene=0;p.step=0;await saveProg('dalal',p);await go('kid','dalal')})()"""); await pg.wait_for_timeout(400)
        await pg.click('button[data-s] >> nth=0'); await pg.wait_for_timeout(600)
        v = await ev("document.querySelector('#view').innerText")
        ok('scene navigation arrows point the right-to-left way', 'التالي ⬅️' in v and '➡️' in v and '⬅️ رجوع' not in v)

        # ---------- p2: لعبة الضدّ والتلميح ----------
        syn = await ev("EXTRA.filter(e=>e.ant).flatMap(e=>e.ant.o.filter(o=>!o[1]).map(o=>o[0]))")
        bad = [w for w in ['يُدَقِّقُ', 'يَنْظُرُ', 'فَرَح', 'سُرُور', 'ضَخْمَة', 'قَدِيم', 'مَصُونَة', 'تَلْمَعُ', 'تُضِيءُ', 'نِهَايَة', 'خِتَام'] if w in syn]
        ok('antonym game no longer marks a synonym of the word as wrong', not bad, str(bad))
        h = await ev("""(async()=>{S.kid='dalal';const q={s:'ضدّ تتألق',o:[['تَنْطَفِئُ',1],['تَطِيرُ',0],['تَسْقُطُ',0]]};const z=quizHtml('qx',q);$('#view').innerHTML=z.html;bindQuiz('qx',z.opts,SCENES[8],()=>{},'ant');
            const w=[...document.querySelectorAll('#qx .opt')].find(b=>!z.opts[+b.dataset.i].c);w.click();return $('#qxh').innerText})()""")
        ok('antonym hint explains "opposite", addressed to Dalal in the feminine', 'عكس' in h and 'تذكّري' in h, h)

        # ---------- H1: المسرح والمسابقة على تابلت طفل واحد ----------
        await ev("""(async()=>{for(const k of ['dalal','farah','kareem'])await sdel('kv','prog:'+k);await sput('kv','owner','farah');const p=await loadProg('farah');p.tests={pre:""" + PRE_DONE + """};await saveProg('farah',p);await go('home')})()"""); await pg.wait_for_timeout(500)
        ok('H1: Farah\'s tablet hides theater and quiz while the others\' pre-tests are unknown', not await pg.query_selector('#thBtn') and not await pg.query_selector('#qzBtn'))
        await ev("go('parent')"); await pg.wait_for_timeout(300)
        if await pg.query_selector('.pinpad'):
            await answer_gate(pg); await pg.wait_for_timeout(800)
        await ev("document.querySelectorAll('details').forEach(d=>d.open=true)")
        await pg.check('#famPre'); await pg.wait_for_timeout(300)
        await ev("go('home')"); await pg.wait_for_timeout(500)
        ok('…the parent\'s "all three finished" switch shows them', bool(await pg.query_selector('#thBtn')) and bool(await pg.query_selector('#qzBtn')))
        await ev("(async()=>{await sdel('kv','famPre');await sdel('kv','owner')})()")

        # ---------- H2: تخطّي اختبار البداية ----------
        await ev("""(async()=>{const p=await loadProg('kareem');p.tests={pre:{v:2,k:6,done:false,t0:Date.now(),resp:{},lane:'A'}};p.done={};await saveProg('kareem',p);await go('kid','kareem')})()"""); await pg.wait_for_timeout(400)
        ok('H2: a half-done pre-test offers «أكمل» and no skip button', not await pg.query_selector('#preSkip') and 'أكمل' in await pg.inner_text('#pre'))
        await ev("""(async()=>{const p=await loadProg('kareem');p.tests={};await saveProg('kareem',p);await go('kid','kareem')})()"""); await pg.wait_for_timeout(400)
        ok('…before any answer the skip button says what it does', 'نهائيًا' in await pg.inner_text('#preSkip'))

        # ---------- M1: تغيير المستوى ----------
        await ev("""(async()=>{const p=await loadProg('farah');p.tests={pre:{v:2,k:45,done:false,t0:Date.now(),resp:{},lane:'C'}};await saveProg('farah',p);await go('parent')})()"""); await pg.wait_for_timeout(900)
        if await pg.query_selector('.pinpad'):
            await answer_gate(pg); await pg.wait_for_timeout(800)
        await ev("document.querySelectorAll('details').forEach(d=>d.open=true)")
        await pg.select_option('select[data-lane="farah"]', 'B'); await pg.wait_for_timeout(500)
        await ev("go('kid','farah')"); await pg.wait_for_timeout(500)
        await pg.click('#pre'); await pg.wait_for_timeout(700)
        t = (await ev("loadProg('farah')"))['tests']['pre']
        ok('M1: a level change mid-test keeps the test plan it started with', not t.get('done') and t.get('k') == 45 and await ev("testPlan('farah','pre',S.prog.tests.pre.lane).length") == 60, json.dumps({k: t.get(k) for k in ('done', 'k', 'lane')}))
        L2 = await ev("""(async()=>{const p=await loadProg('farah');p.tests={pre:""" + PRE_DONE + """};p.done={};p.doneT={};for(let i=0;i<10;i++){p.done[i]=true;p.doneT[i]=Date.now()-2*864e5}await saveProg('farah',p);S.kid='farah';S.prog=await loadProg('farah');await go('test','post');return (await loadProg('farah')).tests.post.lane})()""")
        ok('…and the final test takes the pre-test\'s level, so both have the same items', L2 == 'C', str(L2))
        await ev("(async()=>{const lv=(await sget('kv','lanes'))||{};lv.farah='C';await sput('kv','lanes',lv);await applyLanes()})()")

        # ---------- M2 + L1: التصحيح الأعمى ----------
        await ev("""(async()=>{const o={has:1,t:1};const p=await loadProg('dalal');p.tests={pre:{v:2,k:999,done:true,t:1,t0:1,lane:'C',resp:{t0:{rec:{ok:0,dk:1},oral:{...o}},t1:{rec:{ok:0,dk:1},oral:{...o}},t2:{rec:{ok:0,dk:1},oral:{...o}}}},
            post:{v:2,k:999,done:true,t:2,t0:2,lane:'C',resp:{t0:{rec:{ok:1,dk:0},oral:{...o}},t1:{rec:{ok:1,dk:0},oral:{...o}},t2:{rec:{ok:1,dk:0},oral:{...o}}}}};await saveProg('dalal',p);
            for(const kd of ['pre','post'])for(const i of ['t0','t1','t2'])await sput('audio','test:dalal:'+kd+':'+i,""" + AUD + """)})()""")
        card = await ev("assessCard('dalal')")
        ok('M2: while oral scoring is pending, the report shows 🔒 instead of oral means', '🔒' in card)
        await ev("go('score')"); await pg.wait_for_timeout(700)
        await pg.dblclick('[data-sc="2"]'); await pg.wait_for_timeout(700)
        n = await ev("(async()=>{const p=await loadProg('dalal');return ['pre','post'].flatMap(k=>Object.values(p.tests[k].resp)).filter(r=>typeof r.oral.score==='number').length})()")
        ok('L1: a double tap scores one answer, not two', n == 1, str(n))
        ok('…and the next answer is on screen', bool(await pg.query_selector('[data-sc]')))

        # ---------- H3: ختم «آخر حفظ» ----------
        r = await ev("""(async()=>{await sdel('kv','bk:dalal');window.AndroidBridge={saveFile:()=>false};await exportBackup('dalal');const a=await sget('kv','bk:dalal');
            window.AndroidBridge={saveFile:()=>true};await exportBackup('dalal');const b=await sget('kv','bk:dalal');delete window.AndroidBridge;return [!!a,!!b]})()""")
        ok('H3: a failed save on the tablet does not count as a backup; a successful one does', r == [False, True], str(r))

        # ---------- L9: إعادة اختيار الملف نفسه ----------
        await ev("go('kid','dalal')"); await pg.wait_for_timeout(500)
        pth = os.path.join(tmp, 'other.json'); open(pth, 'w', encoding='utf-8').write(json.dumps({'kid': 'farah', 'prog': {}}))
        if await pg.query_selector('#myRs'):
            await pg.set_input_files('#myRs', pth); await pg.wait_for_timeout(400)
            ok('L9: the child-page restore input is cleared after a rejected file', await ev("document.querySelector('#myRs').value") == '')
        else:
            ok('L9: child-page restore input exists', False)

        await b.close()

asyncio.run(main())
print('\n=== FAILED ===', FAIL or 'none')
print('=== ERRORS ===', ERR or 'none')
sys.exit(1 if FAIL or ERR else 0)

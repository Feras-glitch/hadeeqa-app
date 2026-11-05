"""المراجعة الخصمية الثانية: فحص لكل خلل أُصلح، وللتغييرات المعتمدة (مستوى فرح، شاشة «اسمع» لكريم،
أسئلة السقاية الجديدة، الرمز الإلزامي، عدّاد التسجيلات، معيار النجاح)."""
import asyncio, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from helpers import serve, new_page, view, answer_gate, skip_pre, take_test

URL = serve(8797)
ERR, FAIL = [], []


def ok(name, cond, detail=''):
    print(('✓ ' if cond else '✗ ') + name + (' — ' + detail if detail else ''))
    if not cond:
        FAIL.append(name)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', '--autoplay-policy=no-user-gesture-required'])
        pg = await new_page(b, ERR); ev = pg.evaluate
        await pg.goto(URL); await pg.wait_for_timeout(900)

        # ---------- مستوى فرح ----------
        ok('farah works on dalal\'s level (C)', await ev("KIDS.find(k=>k.id==='farah').lane") == 'C')
        await pg.click('[data-k="farah"]'); await pg.wait_for_timeout(400)
        ok('farah\'s pre-test includes the 20 bonus words', await ev("testPlan('farah','pre').filter(x=>x[0][0]==='b').length") == 20)
        await skip_pre(pg)
        ok('farah\'s scene has the bonus/form steps', await ev("(()=>{S.kid='farah';return stepsFor(0).includes('conj')})()"))
        ok('farah still reads his own lines (not dalal\'s)', await ev("roleOf('farah')") == 'farah')

        # ---------- #8 رجوع مزدوج ----------
        await ev("(async()=>{S.prog.scene=0;S.prog.step=3;await go('scene')})()"); await pg.wait_for_timeout(400)
        await ev("(()=>{const b=document.querySelector('#back');b.click();b.click()})()"); await pg.wait_for_timeout(700)
        ok('double tap on Back = one step', await ev("S.prog.step") == 2)

        # ---------- #6 شاشة قديمة فوق الجديدة ----------
        bad = []
        for d in [0, 5, 10, 30]:
            await ev(f"(async()=>{{go('parent');await new Promise(r=>setTimeout(r,{d}));go('home')}})()"); await pg.wait_for_timeout(1500)
            if await pg.query_selector('#pinSet') or await ev("S.view") != 'home':
                bad.append(d)
        ok('fast navigation never leaves an older screen on top', not bad, f'bad at {bad} ms')

        # ---------- #7 نافذة تُغلق بزر الرجوع تُحسم ----------
        r = await ev("(async()=>{const p=modal('x',[{t:'a',v:1}]);setTimeout(()=>window.__back(),50);return await Promise.race([p,new Promise(r=>setTimeout(()=>r('hung'),1500))])})()")
        ok('dialog closed by Android back resolves (no dead mic-help afterwards)', r is None, str(r))

        # ---------- #4 مشهد إضافي = مشهد واحد ----------
        await ev("(async()=>{const p=await loadProg('farah');p.done={0:true,1:true};p.doneT={0:Date.now(),1:Date.now()};p.lastNew=today();p.extraDay={d:today(),s:1};p.scene=2;p.step=0;await saveProg('farah',p);await go('kid','farah')})()"); await pg.wait_for_timeout(500)
        ok('after the extra scene is done, the next one waits for tomorrow', 'غدًا' in await view(pg))

        # ---------- عدّاد التسجيلات ----------
        await ev("go('home')"); await pg.wait_for_timeout(500)
        await pg.click('#pBtn'); await pg.wait_for_timeout(200); await answer_gate(pg); await pg.wait_for_timeout(800)
        t0 = await view(pg)
        ok('parent page counts model recordings (0 of 47)', 'سُجِّل ٠ من ٤٧' in t0 and '🎙️ ٠/٥' in t0)
        await ev("sput('audio','model:s0:word',{blob:new Blob([new Uint8Array(600)],{type:'audio/webm'}),mime:'audio/webm',sec:1,t:Date.now()})")
        await ev("go('parent')"); await pg.wait_for_timeout(800)
        ok('…and updates after a recording', 'سُجِّل ١ من ٤٧' in await view(pg))

        # ---------- #1 مسجّلان معًا (صفحة ولي الأمر فيها عشرات أزرار التسجيل) ----------
        keys = await ev("[...document.querySelectorAll('[data-rb]')].slice(0,2).map(b=>b.dataset.rb)")
        await ev("(()=>{const g=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);navigator.mediaDevices.getUserMedia=c=>new Promise(r=>setTimeout(()=>r(g(c)),300))})()")
        await ev("(()=>{const bs=document.querySelectorAll('[data-rb] [data-rec]');bs[0].click();bs[1].click()})()"); await pg.wait_for_timeout(1500)
        st = await ev("({key:Rec.active&&Rec.active.key,pending:!!Rec.pending})")
        ok('two quick taps on 🎙️: only the first recorder runs', st['key'] == keys[0] and not st['pending'], str(st))
        await ev("stopRec()"); await pg.wait_for_timeout(1200)
        ok('…its take is saved; nothing left recording', await ev(f"hasKey('{keys[0]}')") and not await ev("!!Rec.active"))

        # ---------- #9 ملف مصنوع لا يكسر صفحة ولي الأمر ----------
        tmp = tempfile.mkdtemp()
        evil = {'kid': 'farah', 'prog': {'scene': 99, 'step': -4, 'done': {}, 'leitner': {}, 'results': {}, 'order': {'<img src=x onerror=window.__pwn3=1>': {'wrong': 1}},
                'tests': {'pre': {'v': 2, 'k': 'x', 'done': True, 'resp': {'zz9': {'rec': {'ok': 1}}, 't0': {'rec': {'ok': 0, 'dk': 0}}}}}}, 'audio': {}, 'draw': {},
                'log': [[1, 'constructor'], ['x', 'scene']]}
        pth = os.path.join(tmp, 'evil.json'); open(pth, 'w', encoding='utf-8').write(json.dumps(evil))
        await pg.set_input_files('#bkin', pth); await pg.wait_for_timeout(800)
        if await pg.query_selector('.mdl-c'):
            await pg.click('.mdl-c button >> text=استعادة كاملة'); await pg.wait_for_timeout(1200)
        await ev("go('parent')"); await pg.wait_for_timeout(1000)
        fp = await ev("loadProg('farah')")
        ok('crafted file: parent page still renders', bool(await pg.query_selector('#csvBtn')))
        ok('…markup in order keys inert', not await ev("!!window.__pwn3"))
        ok('…unknown test ids dropped, scene/step clamped', 'zz9' not in fp['tests']['pre']['resp'] and fp['scene'] == 9 and fp['step'] == 0, str(fp['tests']['pre']['resp']))

        # ---------- #10 «الملف أقدم» يحسب نشاط الطفل ----------
        await ev("(async()=>{const p=await loadProg('dalal');p.doneT={0:Date.now()-3*864e5};p.done={0:true};await saveProg('dalal',p);await sput('kv','log:dalal',[[Date.now()-60e3,'game']])})()")
        old = {'kid': 'dalal', 'prog': {'scene': 0, 'step': 0, 'done': {'0': True}, 'doneT': {'0': await ev("Date.now()-3*864e5")}, 'leitner': {}, 'results': {}}, 'audio': {}, 'draw': {}, 'log': [[await ev("Date.now()-2*864e5"), 'scene']]}
        pth = os.path.join(tmp, 'old.json'); open(pth, 'w', encoding='utf-8').write(json.dumps(old))
        await pg.set_input_files('#bkin', pth); await pg.wait_for_timeout(800)
        mt = await pg.inner_text('.mdl-c') if await pg.query_selector('.mdl-c') else ''
        ok('older file detected from today\'s games (not only scenes/tests)', 'أقدم' in mt, mt[:50])
        if mt:
            await pg.click('.mdl-c button >> text=إلغاء'); await pg.wait_for_timeout(300)

        # ---------- #15 نجمة التحدي لكلمة لم يصلها المتلقّي ----------
        await ev("(async()=>{const p=await loadProg('kareem');p.done={};await saveProg('kareem',p);await sput('kv','challenges',[{id:'c1x',from:'dalal',to:'kareem',word:SCENES[5].word,t:Date.now(),a:Date.now(),judged:0}])})()")
        await ev("go('inbox')"); await pg.wait_for_timeout(600)
        if await pg.query_selector('[data-j="c1x"][data-v="1"]'):
            await pg.click('[data-j="c1x"][data-v="1"]'); await pg.wait_for_timeout(500)
        kp = await ev("loadProg('kareem')")
        ok('challenge star not counted for a word kareem has not reached', not (kp.get('results', {}).get(await ev("SCENES[5].word"), {}).get('chal')))

        # ---------- شاشة «اسمع» لكريم ----------
        await ev("(async()=>{S.kid='kareem';S.prog=await loadProg('kareem');S.prog.tests={pre:{v:2,skipped:1,t:Date.now(),resp:{}}};S.prog.scene=0;S.prog.step=0;await saveProg('kareem',S.prog);await go('scene')})()"); await pg.wait_for_timeout(500)
        v = await view(pg)
        ok('kareem listen: no fake green button', not await pg.query_selector('#tapW'))
        ok('kareem listen, nothing recorded yet: asks a parent to read, story text open for them', 'اطلب من ماما أو بابا' in v and await ev("document.querySelector('details').open"))
        await ev("sput('audio','model:s0:narr',{blob:new Blob([new Uint8Array(600)],{type:'audio/webm'}),mime:'audio/webm',sec:1,t:Date.now()})")
        await ev("go('scene')"); await pg.wait_for_timeout(500)
        ok('kareem listen, story recorded: one big 🔊 button, text folded away', bool(await pg.query_selector('button.b-w[data-pl="model:s0:narr"]')) and not await ev("document.querySelector('details').open"))
        await ev("sdel('audio','model:s0:narr')")

        # ---------- #2 تسجيل قديم لا يُحسب إجابة ----------
        await ev("(async()=>{const p=await loadProg('dalal');p.tests={};p.done={};await saveProg('dalal',p)})()")
        first = await ev("testPlan('dalal','pre')[0][0]")
        await ev(f"sput('audio','test:dalal:pre:{first}',{{blob:new Blob([new Uint8Array(900)],{{type:'audio/webm'}}),mime:'audio/webm',sec:2,t:1}})")
        await ev("go('kid','dalal')"); await pg.wait_for_timeout(500); await pg.click('#pre'); await pg.wait_for_timeout(700)
        ok('old test recording is not reused: Next stays locked until the child speaks', await pg.is_disabled('#tnx'))
        ok('resume label counts words', True)
        for _ in range(7):
            if await pg.query_selector('#tdk'): await pg.click('#tdk')
            else: await pg.click('#tq .opt >> nth=0')
            await pg.wait_for_timeout(650)
        await pg.click('#tpause'); await pg.wait_for_timeout(500)
        ok('…resume button: "الكلمة ٤ من ٤٠"', 'الكلمة ٤ من ٤٠' in await view(pg), (await view(pg))[:120])

        # ---------- #3 اختبار ختامي متوقّف: لا حديقة ولا سقاية حتى يكتمل ----------
        await ev("(async()=>{const p=await loadProg('dalal');p.tests.pre={v:2,k:0,resp:{},done:true,t:Date.now()-20*864e5,t0:Date.now()-20*864e5};for(let i=0;i<10;i++){p.done[i]=true;(p.doneT=p.doneT||{})[i]=Date.now()-2*864e5}p.tests.post={v:2,k:3,resp:{},t0:Date.now(),done:false};await saveProg('dalal',p);await go('kid','dalal')})()"); await pg.wait_for_timeout(600)
        ok('half-done post test: only "continue" is reachable', bool(await pg.query_selector('#tcont')) and not await pg.query_selector('svg.garden') and not await pg.query_selector('#revBtn'))

        # ---------- أسئلة السقاية الجديدة ----------
        await ev("(async()=>{const p=await loadProg('dalal');p.tests.post.done=true;p.leitner={};p.leitner[SCENES[0].word]={box:1,due:today()};p.bleit={};p.results={};await saveProg('dalal',p);await go('kid','dalal')})()"); await pg.wait_for_timeout(500)
        train = await ev("[SCENES[0].q1.s,SCENES[0].q2.s,EXTRA[0].ant.s]")
        await pg.click('#revBtn'); await pg.wait_for_timeout(400)
        s1 = await pg.inner_text('#q1 ~ *') if False else await ev("document.querySelector('.card .line')&&[...document.querySelectorAll('.line')].map(e=>e.textContent).join('|')")
        ok('watering asks a NEW question (not the training one)', not any(t in s1 for t in train), s1[:80])
        await ev("(async()=>{const p=await loadProg('dalal');(p.results[SCENES[0].word]=p.results[SCENES[0].word]||{})['rev'+(today()-1)]={first:true,attempts:1,t:Date.now()};p.leitner[SCENES[0].word]={box:1,due:today()};await saveProg('dalal',p);S.prog=p;await go('review')})()"); await pg.wait_for_timeout(400)
        s2 = await ev("[...document.querySelectorAll('.line')].map(e=>e.textContent).join('|')")
        ok('next watering of the same word uses a different question', s1 != s2 and not any(t in s2 for t in train))
        await ev("(async()=>{const p=await loadProg('kareem');p.done={0:true,1:true,2:true};p.leitner={};p.leitner[SCENES[0].word]={box:1,due:today()};p.results={};await saveProg('kareem',p);S.kid='kareem';S.prog=p;await go('review')})()"); await pg.wait_for_timeout(500)
        ok('kareem\'s watering: picture → which word (not the same picture task)', bool(await pg.query_selector('#kw [data-w]')))
        await pg.wait_for_timeout(400)
        ok('…and the picture is actually visible (sized, image drawn)', await ev("(()=>{const e=document.querySelector('#view .pan')||document.querySelector('#view .ph2');if(!e)return false;const r=e.getBoundingClientRect();return r.width>100&&r.height>100})()"))
        await pg.click(f'#kw [data-w="0"]'); await pg.wait_for_timeout(300)
        ok('…correct word accepted, meaning shown', 'تعني' in await pg.inner_text('#kf'))

        # ---------- معيار النجاح ----------
        await ev("""(async()=>{const p=await loadProg('dalal');const mk=(ok,dk)=>({rec:{ok,dk:dk?1:0},oral:dk?{dk:1}:{has:1,score:ok?2:0}});
          const pre={v:2,k:999,done:true,t:Date.now()-30*864e5,t0:0,resp:{}},post={v:2,k:999,done:true,t:Date.now()-20*864e5,t0:0,resp:{}},dl={v:2,k:999,done:true,t:Date.now(),t0:0,resp:{}};
          for(let i=0;i<10;i++){pre.resp['t'+i]=mk(0,1);pre.resp['c'+i]=mk(0,1);post.resp['t'+i]=mk(i<6?1:0,i>=6);post.resp['c'+i]=mk(i<1?1:0,i>=1);dl.resp['t'+i]=mk(i<5?1:0,i>=5);dl.resp['c'+i]=mk(i<1?1:0,i>=1)}
          p.tests={pre,post,delay:dl};await saveProg('dalal',p)})()""")
        c = await ev("loadProg('dalal').then(criterion)")
        ok('criterion: 6 vs 1 learned (post), 5 vs 1 (delay), oral up → pass', c['status'] == 'pass' and c['gap'] == 5 and c['gapD'] == 4, json.dumps(c))
        await ev("go('parent')"); await pg.wait_for_timeout(900)
        ok('parent report shows the pre-registered criterion', 'معيار النجاح' in await view(pg) and '🎯' in await view(pg))
        await b.close()

asyncio.run(main())
print('\n=== FAILED ===', FAIL or 'none')
print('=== ERRORS ===', ERR or 'none')
sys.exit(1 if FAIL or ERR else 0)

"""اختبارات المتانة: كل خلل وجدته المراجعة الخصمية له هنا فحص يمنع عودته."""
import asyncio, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from helpers import serve, new_page, view, solve_quiz, run_scene, record_all, answer_gate, skip_pre

URL = serve(8796)
ERR, FAIL = [], []


def ok(name, cond, detail=''):
    print(('✓ ' if cond else '✗ ') + name + (' — ' + detail if detail else ''))
    if not cond:
        FAIL.append(name)


async def to_step(pg, kid, scene, step):
    await pg.evaluate(f"(async()=>{{S.kid='{kid}';S.prog=await loadProg('{kid}');S.prog.scene={scene};S.prog.step={step};await go('scene')}})()")
    await pg.wait_for_timeout(500)


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', '--autoplay-policy=no-user-gesture-required'])
        pg = await new_page(b, ERR); ev = pg.evaluate
        await pg.goto(URL); await pg.wait_for_timeout(900)
        await pg.click('[data-k="dalal"]'); await pg.wait_for_timeout(300); await skip_pre(pg)

        # 1) replaying a scene never overwrites the first training result
        await to_step(pg, 'dalal', 0, 1)
        await pg.click('#guess')
        for _ in range(3):  # two wrong taps first
            opts = await pg.query_selector_all('#q1 .opt:not([disabled])')
            texts = [await o.inner_text() for o in opts]
            wrong = [o for o, t in zip(opts, texts) if 'الأوراق' not in t]
            if wrong:
                await wrong[0].click(); await pg.wait_for_timeout(120)
        await solve_quiz(pg, 'q1')
        first = await ev("S.prog.results['مُورِقَة'].q1")
        await to_step(pg, 'dalal', 0, 1); await pg.click('#guess')
        for o in await pg.query_selector_all('#q1 .opt'):
            if 'الأوراق' in await o.inner_text():
                await o.click(); break
        again = await ev("S.prog.results['مُورِقَة'].q1")
        ok('replay keeps the first-attempt result (only counts the replay)', again['first'] == first['first'] is False and again['attempts'] == first['attempts'] and again.get('n') == 2, f"{first} → {again}")

        # 2) taps after solving cannot flip a result (root chip, family intruder)
        await ev("(async()=>{const k=KIDS.find(x=>x.id==='farah');})()")
        await to_step(pg, 'farah', 0, 4)
        ok('lane B family step shows root chips', bool(await pg.query_selector('[data-r]')))
        if await pg.query_selector('[data-r]'):
            root = await ev("SCENES[0].root")
            await pg.click(f'[data-r="{root}"]'); await pg.wait_for_timeout(100)
            await pg.click(f'[data-r="{root}"]', force=True); await pg.wait_for_timeout(100)
            r = await ev("S.prog.results['مُورِقَة'].root")
            ok('root chip: second tap after solving ignored', r['first'] is True and r['attempts'] == 1, str(r))
        await to_step(pg, 'dalal', 0, 4)
        fam = await ev("SCENES[0].family"); intr = await ev("SCENES[0].intruder")
        for w in fam:
            await pg.click(f'[data-w="{w}"]'); await pg.wait_for_timeout(80)
        await pg.click(f'[data-w="{intr}"]', force=True); await pg.wait_for_timeout(150)
        r = await ev("S.prog.results['مُورِقَة'].family")
        ok('family: tapping the intruder after finishing changes nothing', r['first'] is True, str(r))

        # 3) re-recording then tapping Next does not unlock the next step's Next
        await to_step(pg, 'dalal', 0, 3)  # record step (lane C: fun at 2)
        await record_all(pg)
        rb = await pg.query_selector('[data-rec]'); key = await rb.get_attribute('data-rec')
        await rb.click(); await pg.wait_for_timeout(600)
        before = await ev(f"sget('audio','{key}').then(r=>r.sec)")
        await pg.click('#next'); await pg.wait_for_timeout(900)
        step = await pg.inner_text('#topSub')
        nxt_disabled = await pg.is_disabled('#next')
        after = await ev(f"sget('audio','{key}').then(r=>r.sec)")
        ok('Next during a re-recording: next step stays locked', nxt_disabled, step)
        ok('interrupted re-recording discarded; earlier good take kept', abs(before - after) < 0.01, f'{before:.2f}s → {after:.2f}s')

        # 4) double tap on Next advances exactly one step
        await to_step(pg, 'dalal', 0, 0)
        await pg.evaluate("(()=>{const b=document.querySelector('#next');b.click();b.click()})()"); await pg.wait_for_timeout(700)
        ok('double tap on Next = one step', await ev("S.prog.step") == 1)

        # 5) stale timer: leaving the hidden-word game right after solving does not pull the child back
        await ev("(async()=>{const p=await loadProg('dalal');p.done[0]=true;await saveProg('dalal',p);S.prog=p;await go('game','hide')})()"); await pg.wait_for_timeout(400)
        subs = await ev("EXTRA.map(e=>e.hide)")
        for sp in await pg.query_selector_all('#wt span'):
            if (await sp.inner_text()).rstrip('.,،؛:!؟') in subs:
                await sp.click(); await sp.click(); break
        await pg.click('#homeBtn'); await pg.wait_for_timeout(2300)
        ok('timer after leaving a game does nothing', await ev("S.view") == 'home')
        h = await ev("S.prog.results['مُورِقَة'].hide")
        ok('hidden word: double tap on the answer keeps first-try', h['first'] is True, str(h))

        # 6) parent mode is gated; a wrong answer locks for 30 s; PIN replaces the sum
        await pg.click('#pBtn'); await pg.wait_for_timeout(200)
        ok('parent mode asks the gate', bool(await pg.query_selector('.mdl-c')))
        btns = await pg.query_selector_all('.mdl-c button')
        t = await pg.inner_text('.mdl-c'); ar = '٠١٢٣٤٥٦٧٨٩'
        nums = [int(x) for x in ''.join(str(ar.index(c)) if c in ar else ' ' for c in t).split()]
        right = ''.join(ar[int(c)] for c in str(nums[0] * nums[1]))
        for bt in btns:
            if (await bt.inner_text()).strip() != right:
                await bt.click(); break
        await pg.wait_for_timeout(300)
        ok('wrong answer: stays outside parent mode', await ev("S.view") != 'parent')
        await pg.click('#pBtn'); await pg.wait_for_timeout(300)
        ok('…and is locked out for a while', not await pg.query_selector('.mdl-c') and await ev("S.view") != 'parent')
        await ev("parentGate.lock=0")
        await pg.click('#pBtn'); await pg.wait_for_timeout(200); await answer_gate(pg); await pg.wait_for_timeout(700)
        await pg.fill('#pinIn', '٢٤٦٨'); await pg.click('#pinSet'); await pg.wait_for_timeout(600)
        ok('PIN saved (Arabic digits accepted)', await ev("sget('kv','pin')") == '2468')
        await pg.click('#homeBtn'); await pg.click('#pBtn'); await pg.wait_for_timeout(300)
        ok('with a PIN the gate is a keypad', bool(await pg.query_selector('.pinpad')))
        for d in '2468':
            await pg.click(f'[data-pk="{d}"]')
        await pg.wait_for_timeout(700)
        ok('correct PIN opens parent mode', await ev("S.view") == 'parent')
        await pg.click('#pinDel'); await pg.wait_for_timeout(500)

        # 7) restore: older file warns; foreign/malformed files rejected; injected markup inert
        await ev("(async()=>{const p=await loadProg('farah');p.doneT={0:Date.now()};p.done={0:true};await saveProg('farah',p)})()")
        old = {'kid': 'farah', 'prog': {'scene': 0, 'step': 0, 'results': {}, 'leitner': {}, 'done': {}, 'doneT': {'0': 1000}}, 'audio': {}, 'draw': {}}
        evil = {'kid': 'farah', 'prog': {'scene': 0, 'step': 0, 'done': {}, 'leitner': {'<img src=x onerror=window.__pwn=1>': {'box': '<img src=x onerror=window.__pwn=1>', 'due': 0}}, 'results': {'w': {'<img src=x onerror=window.__pwn=1>': {'first': False, 'attempts': '<b>'}}}, 'stars': '<img src=x onerror=window.__pwn=1>'}, 'audio': {'rec:dalal:s9:narr': {'d': 'data:audio/webm;base64,AAAA', 'mime': 'audio/webm'}}, 'draw': {}}
        tmp = tempfile.mkdtemp()
        def wf(name, obj):
            pth = os.path.join(tmp, name); open(pth, 'w', encoding='utf-8').write(json.dumps(obj, ensure_ascii=False)); return pth
        dlg = []
        pg.on('dialog', lambda d: dlg.append(d.message))
        await pg.set_input_files('#bkin', wf('old.json', old)); await pg.wait_for_timeout(1200)
        ok('older backup triggers a clear warning before overwriting', any('أقدم' in m for m in dlg), '; '.join(m[:40] for m in dlg))
        dlg.clear()
        snap = await ev("loadProg('farah').then(p=>JSON.stringify(p))")
        await pg.set_input_files('#bkin', wf('bad.json', {'kid': 'farah', 'prog': None})); await pg.wait_for_timeout(800)
        ok('malformed backup rejected, progress untouched', await ev("loadProg('farah').then(p=>JSON.stringify(p))") == snap)
        await pg.set_input_files('#bkin', wf('evil.json', evil)); await pg.wait_for_timeout(1200)
        await ev("go('parent')"); await pg.wait_for_timeout(800)
        await ev("(async()=>{S.kid='farah';await go('kid','farah')})()"); await pg.wait_for_timeout(800)
        ok('markup inside a restored file is not executed', not await ev("!!window.__pwn"))
        ok('a backup cannot write another child\'s recordings', not await ev("hasKey('rec:dalal:s9:narr')"))

        # 8) Android back button maps to the app's own screens
        await ev("(async()=>{S.prog=await loadProg('dalal');S.kid='dalal';S.prog.scene=0;S.prog.step=0;await go('scene')})()"); await pg.wait_for_timeout(400)
        r1 = await ev("window.__back()"); await pg.wait_for_timeout(400)
        ok('back from a scene → the child\'s home', r1 is True and await ev("S.view") == 'kid')
        await ev("go('home')"); await pg.wait_for_timeout(300)
        ok('back from the main screen lets Android exit', await ev("window.__back()") is False)

        # 9) app goes to background while recording → clip discarded, child told
        await to_step(pg, 'dalal', 0, 3)
        rb = await pg.query_selector('[data-rec]'); key = await rb.get_attribute('data-rec')
        before = await ev(f"sget('audio','{key}').then(r=>r&&r.sec)")
        await rb.click(); await pg.wait_for_timeout(500)
        await ev("Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))")
        await pg.wait_for_timeout(700)
        await ev("Object.defineProperty(document,'hidden',{configurable:true,get:()=>false})")
        after = await ev(f"sget('audio','{key}').then(r=>r&&r.sec)")
        ok('recording stops when the app is hidden; old take kept', before == after and not await ev("!!Rec.active"))
        await b.close()

        # 10) microphone denied: explanation + parent-gated skip (no permanent dead end)
        b2 = await p.chromium.launch()
        ctx = await b2.new_context(viewport={'width': 412, 'height': 900})
        pg2 = await ctx.new_page(); pg2.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
        await pg2.add_init_script("if(navigator.mediaDevices)navigator.mediaDevices.getUserMedia=()=>Promise.reject(new DOMException('denied','NotAllowedError'))")
        await pg2.goto(URL); await pg2.wait_for_timeout(900)
        await pg2.click('[data-k="kareem"]'); await pg2.wait_for_timeout(300); await skip_pre(pg2)
        await to_step(pg2, 'kareem', 0, 3)
        await pg2.click('[data-rec] >> nth=0'); await pg2.wait_for_timeout(800)
        txt = await pg2.inner_text('.mdl-c') if await pg2.query_selector('.mdl-c') else ''
        ok('mic denied: tells how to allow it in Settings', 'الأذونات' in txt, txt[:60])
        if txt:
            await pg2.click('.mdl-c button >> text=تخطَّ'); await pg2.wait_for_timeout(200)
            await answer_gate(pg2); await pg2.wait_for_timeout(500)
            ok('…and a parent can skip this recording', not await pg2.is_disabled('#next'))
        await b2.close()

asyncio.run(main())
print('\n=== FAILED ===', FAIL or 'none')
print('=== ERRORS ===', [e for e in ERR if 'Permission' not in e] or 'none')
sys.exit(1 if FAIL or [e for e in ERR if 'Permission' not in e] else 0)

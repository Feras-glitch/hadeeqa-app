"""مساعدات اختبار المتصفح: تمشي أي مشهد لأي طفل وتحلّ ألعاب المفاجآت كما يفعل الطفل."""
import asyncio, os, http.server, threading, socketserver
from collections import deque

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'web')


def serve(port):
    class Q(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k): super().__init__(*a, directory=WEB, **k)
        def log_message(self, *a): pass
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(('127.0.0.1', port), Q)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{port}/index.html'


async def new_page(b, errs, **ctxkw):
    ctx = await b.new_context(viewport={'width': 412, 'height': 900}, permissions=['microphone', 'camera'], accept_downloads=True, **ctxkw)
    pg = await ctx.new_page()
    pg.on('pageerror', lambda e: errs.append('PAGEERROR: ' + str(e)))
    pg.on('console', lambda m: errs.append('CONSOLE: ' + m.text) if m.type == 'error' and 'sw.js' not in m.text else None)
    pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
    return pg


async def view(pg):
    return (await pg.inner_text('#view')).replace('\n', ' ')


async def solve_quiz(pg, box):
    for _ in range(4):
        opts = await pg.query_selector_all(f'#{box} .opt:not([disabled])')
        if not opts:
            return
        await opts[0].click()
        await pg.wait_for_timeout(120)
        if await pg.evaluate(f"[...document.querySelectorAll('#{box} .opt')].every(b=>b.disabled)"):
            return


async def understand(pg):
    await pg.click('#guess')
    for b in ['q1', 'q2']:
        if await pg.query_selector('#' + b):
            await solve_quiz(pg, b)
    if await pg.query_selector('.bw'):
        for k in ['0', '1']:
            el = await pg.query_selector(f'.bw[data-bk="{k}"]')
            if el:
                await el.click()
        await pg.wait_for_timeout(200)
        for b in ['qb0', 'qb1']:
            if await pg.query_selector('#' + b):
                await solve_quiz(pg, b)


async def solve_fun(pg):
    if await pg.query_selector('.jg'):
        for _ in range(40):
            vs = await pg.eval_on_selector_all('.jg button', 'els=>els.map(e=>+e.dataset.v)')
            if not vs or all(v == k for k, v in enumerate(vs)):
                break
            k = next(k for k, v in enumerate(vs) if v != k)
            j = vs.index(k)
            await pg.click(f'.jg button[data-k="{k}"]')
            await pg.click(f'.jg button[data-k="{j}"]')
    elif await pg.query_selector('#lc'):
        T = await pg.evaluate('window.__lens')
        r = await pg.evaluate("(()=>{const b=document.querySelector('#lc').getBoundingClientRect();return [b.left,b.top]})()")
        for t in T:
            await pg.mouse.move(r[0] + t['x'], r[1] + t['y'])
            await pg.wait_for_timeout(120)
    elif await pg.query_selector('#mz'):
        m = await pg.evaluate("(()=>{const z=window.__maze;return {C:z.C,n:z.n,p:z.p}})()")
        C, n, p = m['C'], m['n'], m['p']
        goal = n * n - 1
        prev = {p: None}
        dq = deque([p])
        while dq:
            c = dq.popleft()
            if c == goal:
                break
            for d, dd in (('n', -n), ('s', n), ('e', 1), ('w', -1)):
                if not C[c][d] and c + dd not in prev:
                    prev[c + dd] = (c, d)
                    dq.append(c + dd)
        path, c = [], goal
        while prev[c]:
            c0, d = prev[c]
            path.append(d)
            c = c0
        for d in reversed(path):
            await pg.click(f'.mzc [data-d="{d}"]')
    elif await pg.query_selector('[data-z]'):
        for k in range(10):
            el = await pg.query_selector(f'[data-z="{k}"]')
            if not el:
                break
            await el.click()
            await pg.wait_for_timeout(60)
    elif await pg.query_selector('#scv'):
        b = await pg.evaluate("(()=>{const r=document.querySelector('#scv').getBoundingClientRect();return [r.left,r.top,r.width,r.height]})()")
        for y in range(8, int(b[3]), 16):
            await pg.mouse.move(b[0] + 4, b[1] + y)
            await pg.mouse.down()
            await pg.mouse.move(b[0] + b[2] - 4, b[1] + y, steps=8)
            await pg.mouse.up()
            if await pg.query_selector('#sw.glow'):
                break
    await pg.wait_for_timeout(300)


async def record_all(pg):
    for rb in await pg.query_selector_all('[data-rec]'):
        key = await rb.get_attribute('data-rec')
        await rb.click()
        await pg.wait_for_timeout(1200)
        await pg.click(f'[data-stop="{key}"]')
        await pg.wait_for_timeout(800)


async def run_scene(pg, log=print, hs=None):
    """Walk the current scene from wherever it is to the celebration screen.
    hs: optional list collecting any step whose page is wider than the screen."""
    for _ in range(14):
        if await pg.query_selector('.cel, #mg'):
            return True
        step = await pg.inner_text('#topSub')
        log('   · ' + step)
        if hs is not None:
            w = await pg.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
            if w[0] > w[1] + 1:
                hs.append(f'scene step {step}: {w[0]}>{w[1]}')
        if step == 'اسمع':
            pass
        elif step == 'اختر الصورة':
            for _ in range(3):
                btns = await pg.query_selector_all('#kg button:not([disabled])')
                if not btns or not await pg.is_disabled('#next'):
                    break
                await btns[0].click()
                await pg.wait_for_timeout(120)
        elif step == 'افهم':
            await understand(pg)
        elif step == 'مفاجأة':
            await solve_fun(pg)
        elif step in ('اقرأ وسجّل', 'أنتج'):
            await record_all(pg)
        elif step == 'عائلة الكلمة':
            fam = await pg.evaluate('SCENES[S.prog.scene].family')
            root = await pg.evaluate('SCENES[S.prog.scene].root')
            if await pg.query_selector('[data-r]'):
                await pg.click(f'[data-r="{root}"]')
            else:
                for w in fam:
                    await pg.click(f'[data-w="{w}"]')
        elif step == 'صرّف الكلمة':
            await solve_quiz(pg, 'q3')
        elif step == 'أبدع':
            pass
        await pg.wait_for_timeout(250)
        if await pg.is_disabled('#next'):
            raise Exception('next still disabled at step ' + step)
        await pg.click('#next')
        await pg.wait_for_timeout(500)
    return bool(await pg.query_selector('#mg'))


async def answer_gate(pg):
    """Parent gate: read a × b from the modal and click the right number."""
    t = await pg.inner_text('.mdl-c')
    ar = '٠١٢٣٤٥٦٧٨٩'
    digits = ''.join(str(ar.index(c)) if c in ar else (c if c.isdigit() else ' ') for c in t)
    nums = [int(x) for x in digits.split() if x]
    a, b = nums[0], nums[1]
    target = ''.join(ar[int(c)] for c in str(a * b))
    for btn in await pg.query_selector_all('.mdl-c button'):
        if (await btn.inner_text()).strip() == target:
            await btn.click()
            return True
    return False

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


async def new_page(b, errs, seed_pin=True, **ctxkw):
    """seed_pin: the parent PIN is chosen on the home page before the children start (as on a real tablet);
    tests that check that first-time setup pass seed_pin=False."""
    ctx = await b.new_context(viewport={'width': 412, 'height': 900}, permissions=['microphone', 'camera'], accept_downloads=True, **ctxkw)
    pg = await ctx.new_page()
    pg.on('pageerror', lambda e: errs.append('PAGEERROR: ' + str(e)))
    pg.on('console', lambda m: errs.append('CONSOLE: ' + m.text) if m.type == 'error' and 'sw.js' not in m.text else None)
    pg.on('dialog', lambda d: asyncio.ensure_future(d.accept()))
    if seed_pin:
        orig = pg.goto

        async def goto(url, **kw):
            r = await orig(url, **kw)
            try:
                await pg.wait_for_selector('[data-k]', timeout=15000)
                await pg.evaluate("(async()=>{if(!(await sget('kv','pin'))){await sput('kv','pin','%s');await sput('kv','pinrc','123456');await go('home')}})()" % TEST_PIN)
            except Exception:
                pass
            return r
        pg.goto = goto
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
        key = await pg.evaluate("t=>{for(const [k,v] of Object.entries(STEP_NAME))if(v===t)return k;return t}", step)
        log('   · ' + step)
        if hs is not None:
            w = await pg.evaluate("[document.documentElement.scrollWidth, document.documentElement.clientWidth]")
            if w[0] > w[1] + 1:
                hs.append(f'scene step {step}: {w[0]}>{w[1]}')
        if key == 'listen':
            pass
        elif key == 'picture':
            for _ in range(3):
                btns = await pg.query_selector_all('#kg button:not([disabled])')
                if not btns or not await pg.is_disabled('#next'):
                    break
                await btns[0].click()
                await pg.wait_for_timeout(120)
        elif key == 'understand':
            await understand(pg)
        elif key == 'fun':
            await solve_fun(pg)
        elif key in ('record', 'produce'):
            await record_all(pg)
        elif key == 'family':
            fam = await pg.evaluate('SCENES[S.prog.scene].family')
            root = await pg.evaluate('SCENES[S.prog.scene].root')
            if await pg.query_selector('[data-r]'):
                await pg.click(f'[data-r="{root}"]')
            else:
                for w in fam:
                    await pg.click(f'[data-w="{w}"]')
        elif key == 'conj':
            await solve_quiz(pg, 'q3')
        elif key == 'create':
            pass
        await pg.wait_for_timeout(250)
        if await pg.is_disabled('#next'):
            raise Exception('next still disabled at step ' + step)
        await pg.click('#next')
        await pg.wait_for_timeout(500)
    return bool(await pg.query_selector('#mg'))


TEST_PIN = '2468'


async def answer_gate(pg, pin=TEST_PIN):
    """Parent gate: a PIN is now required. First time: choose it, confirm it, acknowledge the
    recovery code. Afterwards: type it on the keypad."""
    await pg.wait_for_timeout(150)
    for _ in range(6):
        if await pg.query_selector('.pinpad'):
            for d in pin:
                await pg.click(f'.pinpad [data-pk="{d}"]')
            await pg.wait_for_timeout(250)
            continue
        mc = await pg.query_selector('.mdl-c')
        if mc and 'رمز الاسترجاع' in await mc.inner_text():
            await pg.click('.mdl-c button >> nth=0'); await pg.wait_for_timeout(250)
            continue
        return True
    return True


async def take_test(pg, record_every=2):
    """Take a v2 test to the end: oral stage records an answer on every Nth word
    (otherwise 'لا أعرف'); recognition stage taps the first option. Returns steps done."""
    n = oral_i = 0
    for _ in range(200):
        if await pg.query_selector('#h'):
            return n
        mc = await pg.query_selector('.mdl-c')
        if mc and 'لا أعرف' in await mc.inner_text() and await pg.query_selector('.mdl-c button'):
            await pg.click('.mdl-c button >> nth=0'); await pg.wait_for_timeout(400)  # R4: post/delay intro
            continue
        if await pg.query_selector('#tdk'):
            oral_i += 1
            if oral_i % record_every == 1 or record_every == 1:
                rb = await pg.query_selector('[data-rec]')
                key = await rb.get_attribute('data-rec')
                await rb.click(); await pg.wait_for_timeout(1100)
                await pg.click(f'[data-stop="{key}"]'); await pg.wait_for_timeout(700)
                await pg.click('#tnx')
            else:
                await pg.click('#tdk')
        elif await pg.query_selector('#tq .opt'):
            await pg.click('#tq .opt >> nth=0')
        n += 1
        await pg.wait_for_timeout(650)
    raise Exception('test did not finish')


async def skip_pre(pg):
    """Pre-test skip is a parent decision: gate, then confirm (dialogs auto-accepted)."""
    await pg.click('#preSkip'); await pg.wait_for_timeout(200)
    await answer_gate(pg); await pg.wait_for_timeout(500)


async def start_next_scene(pg):
    """Start the current scene; if today's new scene was already done, unlock via the parent."""
    await pg.click('button[data-s] >> nth=0'); await pg.wait_for_timeout(400)
    if await pg.query_selector('.mdl-c'):
        await pg.click('.mdl-c button >> text=ولي الأمر'); await pg.wait_for_timeout(200)
        await answer_gate(pg); await pg.wait_for_timeout(500)
        await pg.click('button[data-s] >> nth=0'); await pg.wait_for_timeout(400)

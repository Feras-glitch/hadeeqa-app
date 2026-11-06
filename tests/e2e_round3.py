"""المراجعة الخصمية الثالثة: فحص لكل خلل أُصلح في هذه الجولة."""
import asyncio, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.async_api import async_playwright
from helpers import serve, new_page, view, answer_gate

URL = serve(8798)
ERR, FAIL = [], []


def ok(name, cond, detail=''):
    print(('✓ ' if cond else '✗ ') + name + (' — ' + detail if detail else ''))
    if not cond:
        FAIL.append(name)


AUD = "{blob:new Blob([new Uint8Array(900)],{type:'audio/webm'}),mime:'audio/webm',sec:2,t:1}"


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', '--autoplay-policy=no-user-gesture-required'])
        pg = await new_page(b, ERR); ev = pg.evaluate
        await pg.goto(URL); await pg.wait_for_timeout(900)
        await pg.click('#pBtn'); await pg.wait_for_timeout(200); await answer_gate(pg); await pg.wait_for_timeout(700)
        tmp = tempfile.mkdtemp()

        # ---------- الدرجات الشفهية لا تضيع عند استعادة حقيبة أحدث ----------
        # على هذا الجهاز (الحاسوب): صحّح ولي الأمر إجابتين. على التابلت: أكملت دلال اختبار التذكّر بعد ذلك.
        await ev("""(async()=>{const now=Date.now(),d=864e5;const o=(t,sc)=>Object.assign({has:1,t},sc===undefined?{}:{score:sc,st:now-d});
          const p=await loadProg('dalal');p.done={0:true};p.doneT={0:now-20*d};
          p.tests={pre:{v:2,k:999,done:true,t:now-30*d,t0:now-30*d,resp:{t0:{rec:{ok:0,dk:1},oral:o(111,0)},c0:{rec:{ok:0,dk:1},oral:o(112,1)}}},
                   post:{v:2,k:999,done:true,t:now-15*d,t0:now-15*d,resp:{t0:{rec:{ok:1,dk:0},oral:o(211,2)},c0:{rec:{ok:0,dk:1},oral:{dk:1,t:212}}}}};
          await saveProg('dalal',p);for(const k of ['pre:t0','pre:c0','post:t0'])await sput('audio','test:dalal:'+k,""" + AUD + """)})()""")
        now = await ev("Date.now()"); d = 864e5
        o = lambda t: {'has': 1, 't': t}
        tab = {'kid': 'dalal', 'prog': {'scene': 0, 'step': 0, 'done': {'0': True}, 'doneT': {'0': now - 20 * d}, 'leitner': {}, 'results': {},
               'tests': {'pre': {'v': 2, 'k': 999, 'done': True, 't': now - 30 * d, 't0': now - 30 * d, 'resp': {'t0': {'rec': {'ok': 0, 'dk': 1}, 'oral': o(111)}, 'c0': {'rec': {'ok': 0, 'dk': 1}, 'oral': o(112)}}},
                         'post': {'v': 2, 'k': 999, 'done': True, 't': now - 15 * d, 't0': now - 15 * d, 'resp': {'t0': {'rec': {'ok': 1, 'dk': 0}, 'oral': o(211)}, 'c0': {'rec': {'ok': 0, 'dk': 1}, 'oral': {'dk': 1, 't': 212}}}},
                         'delay': {'v': 2, 'k': 999, 'done': True, 't': now - 60e3, 't0': now - 3600e3, 'resp': {'t0': {'rec': {'ok': 1, 'dk': 0}, 'oral': o(311)}}}}},
               'audio': {}, 'draw': {}, 'log': [[now - 60e3, 'test']]}
        aud = await ev("(async()=>{const r=new FileReader();return await new Promise(res=>{r.onload=()=>res(r.result);r.readAsDataURL(new Blob([new Uint8Array(900)],{type:'audio/webm'}))})})()")
        for k in ['pre:t0', 'pre:c0', 'post:t0', 'delay:t0']:
            tab['audio']['test:dalal:' + k] = {'d': aud, 'mime': 'audio/webm', 'sec': 2, 't': 1}
        pth = os.path.join(tmp, 'tablet.json'); open(pth, 'w', encoding='utf-8').write(json.dumps(tab))
        await pg.set_input_files('#bkin', pth); await pg.wait_for_timeout(900)
        if await pg.query_selector('.mdl-c'):
            await pg.click('.mdl-c button >> text=استعادة كاملة'); await pg.wait_for_timeout(900)
        P = await ev("loadProg('dalal')")
        ok('newer tablet bag restored over the PC: the delay test arrives', bool(P['tests'].get('delay', {}).get('done')))
        sc = [P['tests']['pre']['resp']['t0']['oral'].get('score'), P['tests']['pre']['resp']['c0']['oral'].get('score'), P['tests']['post']['resp']['t0']['oral'].get('score')]
        ok('…and the oral scores entered on the PC are kept (0, 1, 2)', sc == [0, 1, 2], str(sc))
        await ev("go('parent')"); await pg.wait_for_timeout(900)
        ok('parent report shows when this child\'s bag last moved here', 'آخر حفظ أو استعادة لحقيبته هنا: اليوم' in await view(pg))

        # ---------- التصحيح: إجابة تسجيلها ليس على هذا الجهاز لا تُعرض ----------
        await ev("""(async()=>{const p=await loadProg('dalal');for(const kd of ['pre','post','delay'])for(const r of Object.values(p.tests[kd].resp))if(r.oral&&r.oral.has){delete r.oral.score;delete r.oral.na}await saveProg('dalal',p);await sdel('audio','test:dalal:pre:c0')})()""")
        await ev("go('score')"); await pg.wait_for_timeout(700)
        seen = []
        for _ in range(8):
            if not await pg.query_selector('[data-sc]'):
                break
            seen.append(await pg.inner_text('.word'))
            await pg.click('[data-sc="2"]'); await pg.wait_for_timeout(400)
        v = await view(pg)
        ok('scoring skips the answer whose recording is missing here (3 shown, not 4)', len(seen) == 3, str(seen))
        ok('…and says where to score it', 'ليس على هذا الجهاز' in v)
        P = await ev("loadProg('dalal')")
        ok('…without marking it inaudible', 'na' not in P['tests']['pre']['resp']['c0']['oral'] and 'score' not in P['tests']['pre']['resp']['c0']['oral'])

        # ---------- إلغاء رمز ولي الأمر عند نجمة كلمة اليوم لا يقول «الإجابة غير صحيحة» ----------
        await ev("(async()=>{const p=await loadProg('kareem');p.done={0:true};p.tests={pre:{v:2,skipped:1,t:Date.now(),resp:{}}};await saveProg('kareem',p);await go('kid','kareem')})()"); await pg.wait_for_timeout(600)
        if await pg.query_selector('#wotdStar'):
            await pg.click('#wotdStar'); await pg.wait_for_timeout(300)
            await ev("window.__back&&window.__back()"); await pg.wait_for_timeout(400)
            t = await ev("(document.querySelector('.toast')||{}).textContent||''")
            ok('cancelling the PIN on the word-of-the-day star shows no "wrong answer"', 'الإجابة غير صحيحة' not in t, t)
        else:
            ok('word-of-the-day star present for this check', False)

        # ---------- سؤال الإكمال في السقاية لا يكتب الإجابة فوقه ----------
        seen = {}
        for n in range(3):
            await ev(f"""(async()=>{{const p=await loadProg('farah');p.tests={{pre:{{v:2,skipped:1,t:Date.now(),resp:{{}}}}}};p.done={{0:true,1:true}};p.leitner={{}};p.leitner[SCENES[1].word]={{box:1,due:today()}};p.results={{}};p.results[SCENES[1].word]={{}};for(let k=0;k<{n};k++)p.results[SCENES[1].word]['rev'+(today()-10+k)]={{first:true,attempts:1,t:1}};await saveProg('farah',p);S.kid='farah';S.prog=p;await go('review')}})()""")
            await pg.wait_for_timeout(500)
            kind = await ev("revItem(1,revCount(S.prog,SCENES[1].word),'C')===REV[1].cz?'cz':'other'")
            seen[kind] = await ev("!!document.querySelector('#view .word')")
        ok('cloze watering: the answer word is not printed above the question', seen.get('cz') is False, str(seen))
        ok('…other watering questions still show the word', seen.get('other') is True)

        await b.close()

asyncio.run(main())
print('\n=== FAILED ===', FAIL or 'none')
print('=== ERRORS ===', ERR or 'none')
sys.exit(1 if FAIL or ERR else 0)

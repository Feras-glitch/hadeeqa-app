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
        ok('watering asks only meaning questions (the pattern question stays in the games)', await ev("[0,1,2,3,4,5].every(n=>{const q=revItem(1,n,'C');return q===REV[1].cz||q.o===REV[1].use})"))
        ok('near-synonym bonus definitions never compete in one question', await ev("bonusNear('بِحَذَرٍ','بِعِنَايَةٍ')&&!bonusNear('بِحَذَرٍ','آثَار')"))

        # ---------- F1: «من وضع ولي الأمر» في المسرح يمرّ بالرمز ----------
        await ev("(async()=>{for(const k of ['dalal','farah','kareem']){const p=await loadProg(k);p.done=Object.assign(p.done||{},{0:true,1:true,2:true});await saveProg(k,p)}})()")  # المسرح يعرض ما أنهاه الجميع (في المشهد ٣ سطر لماما)
        await ev("go('theater')"); await pg.wait_for_timeout(600)
        await pg.click('#rehearse'); await pg.wait_for_timeout(1200)
        if await pg.query_selector('[data-pp]'):
            await pg.click('[data-pp] >> nth=0'); await pg.wait_for_timeout(300)
            ok('theater → "from parent mode" asks for the PIN', bool(await pg.query_selector('.pinpad')))
            await pg.click('.pinpad [data-pk="x"]'); await pg.wait_for_timeout(300)
            ok('…and cancelling keeps the child out of parent mode', await ev("S.view") != 'parent')
        else:
            ok('theater shows the parent-recording button for this check', False)
        cast = await ev("(async()=>{await sdel('kv','theater');await go('theater');return [...document.querySelectorAll('[data-cast]')].map(s=>s.dataset.cast+'='+s.value)})()")
        ok('theater default cast: each child plays their own part', all(x in cast for x in ['dalal=dalal', 'farah=farah', 'kareem=kareem']), str(cast))

        # ---------- F2: نقرة أثناء فتح الميكروفون لا تترك تسجيلًا خفيًا في الاختبار ----------
        await ev("(async()=>{const p=await loadProg('dalal');p.tests={};p.done={};await saveProg('dalal',p);for(const k of await skeys('audio'))if(String(k).startsWith('test:dalal:'))await sdel('audio',k)})()")
        await ev("go('kid','dalal')"); await pg.wait_for_timeout(500); await pg.click('#pre'); await pg.wait_for_timeout(600)
        await ev("(()=>{const g=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);window.__slow=1;navigator.mediaDevices.getUserMedia=c=>new Promise(r=>setTimeout(()=>r(g(c)),700))})()")
        k0 = await ev("S.prog.tests.pre.k")
        await ev("(()=>{document.querySelector('[data-rec]').click();document.querySelector('#tdk').click()})()"); await pg.wait_for_timeout(1500)
        ok('«لا أعرف» while the mic is still opening is ignored (no hidden recording, same word)', await ev("S.prog.tests.pre.k") == k0 and await ev("!!Rec.active"))
        await ev("stopRec()"); await pg.wait_for_timeout(1000)
        key = await ev("'test:dalal:pre:'+testPlan('dalal','pre')[S.prog.tests.pre.k][0]")
        sec0 = await ev(f"sget('audio','{key}').then(r=>r&&r.sec)")
        await ev("(()=>{document.querySelector('[data-rec]').click();document.querySelector('#tnx').click()})()"); await pg.wait_for_timeout(1500)
        ok('«التالي» while a re-record is opening is ignored', await ev("S.prog.tests.pre.k") == k0)
        await ev("stopRec()"); await pg.wait_for_timeout(900)
        await pg.click('#tnx'); await pg.wait_for_timeout(700)
        await ev("(()=>{document.querySelector('#tq .opt').click()})()"); await pg.wait_for_timeout(900)
        ok('…moving on leaves nothing recording', not await ev("!!Rec.active||!!Rec.pending"))
        await ev("(()=>{if(window.__slow){location.reload()}})()"); await pg.wait_for_timeout(1500)

        # ---------- F3: الاستعادة الكاملة تحفظ ما أدخله ولي الأمر ----------
        await ev("""(async()=>{const p=await loadProg('farah');p.fluency={0:{errs:[],wpm:40,words:20,sec:30,t:5}};p.free={0:{t:6,0:true}};p.scrollPhrase='سر بابا';p.scrollPhraseT=Date.now();p.results={};p.results[SCENES[0].word]={life:{first:true,attempts:1,t:7}};p.stars=1;p.done={0:true};p.doneT={0:Date.now()-3600e3};await saveProg('farah',p)})()""")
        fb = {'kid': 'farah', 'prog': {'scene': 1, 'step': 0, 'done': {'0': True, '1': True}, 'doneT': {'0': now - 3600e3, '1': now - 60e3}, 'leitner': {}, 'results': {}, 'stars': 0}, 'audio': {}, 'draw': {}, 'log': [[now - 60e3, 'scene']]}
        pth = os.path.join(tmp, 'farah.json'); open(pth, 'w', encoding='utf-8').write(json.dumps(fb))
        await ev("go('parent')"); await pg.wait_for_timeout(800)
        await pg.set_input_files('#bkin', pth); await pg.wait_for_timeout(800)
        if await pg.query_selector('.mdl-c'):
            await pg.click('.mdl-c button >> text=استعادة كاملة'); await pg.wait_for_timeout(300)
            await answer_gate(pg); await pg.wait_for_timeout(900)
        F = await ev("loadProg('farah')")
        ok('full restore keeps reading-fluency marks, free-sentence marks, scroll phrase and word-of-the-day star',
           bool(F.get('fluency', {}).get('0')) and bool(F.get('free', {}).get('0')) and F.get('scrollPhrase') == 'سر بابا' and bool(F['results'].get(await ev("SCENES[0].word"), {}).get('life')) and F.get('stars') == 1 and F['done'].get('1'), json.dumps({k: F.get(k) for k in ['scrollPhrase', 'stars', 'fluency', 'free', 'done']}, ensure_ascii=False)+str(F['results']))

        # ---------- F4: أسماء الكلمات المتعلَّمة لا تظهر قبل التصحيح الشفهي ----------
        await ev("""(async()=>{const p=await loadProg('dalal');const o={has:1,t:9};const mk=(ok)=>({rec:{ok,dk:0},oral:Object.assign({},o)});
          p.tests={pre:{v:2,k:999,done:true,t:1,t0:1,resp:{t0:mk(0),c0:mk(0)}},post:{v:2,k:999,done:true,t:2,t0:2,resp:{t0:mk(1),c0:mk(0)}},delay:{v:2,k:999,done:true,t:3,t0:3,resp:{t0:mk(1),c0:mk(0)}}};await saveProg('dalal',p);await go('parent')})()""")
        await pg.wait_for_timeout(900)
        v = await view(pg)
        ok('results and learned words hidden while oral answers wait for blind scoring', 'من القصة:' not in v and 'النتائج تظهر بعد' in v)
        await ev("(async()=>{const p=await loadProg('dalal');for(const [kd,t] of Object.entries(p.tests))for(const r of Object.values(t.resp))r.oral.score=kd==='pre'?0:1;await saveProg('dalal',p);await go('parent')})()"); await pg.wait_for_timeout(900)
        ok('…and shown once the delay test is done and scoring is complete', 'من القصة:' in await view(pg))

        # ---------- F15: طفل تخطّى اختبار البداية مستبعد؛ والحكم ❌ حين يستحيل نجاح طفلين ----------
        r = await ev("""(async()=>{const mk=(ok,dk)=>({rec:{ok,dk:dk?1:0},oral:dk?{dk:1}:{has:1,score:ok?2:0}});
          const build=(tPost,cPost)=>{const pre={v:2,k:999,done:true,t:1,t0:0,resp:{}},post={v:2,k:999,done:true,t:2,t0:0,resp:{}};for(let i=0;i<10;i++){pre.resp['t'+i]=mk(0,1);pre.resp['c'+i]=mk(0,1);post.resp['t'+i]=mk(i<tPost?1:0,i>=tPost);post.resp['c'+i]=mk(i<cPost?1:0,i>=cPost)}return {pre,post}};
          const withDelay=t=>{t.delay={v:2,k:999,done:true,t:3,t0:0,resp:JSON.parse(JSON.stringify(t.post.resp))};return t};
          const a=await loadProg('dalal');a.tests=withDelay(build(1,1));await saveProg('dalal',a);
          const b=await loadProg('farah');b.tests=withDelay(build(6,1));await saveProg('farah',b);
          const c=await loadProg('kareem');c.tests={pre:{v:2,skipped:1,t:1,resp:{}}};await saveProg('kareem',c);
          return {k:stratum(c).status,d:stratum(a).status,f:stratum(b).status,p:strataP([stratum(a),stratum(b)]).p,v:await familyVerdict()}})()""")
        from math import comb
        def tail(N, K, n, x):
            return sum(comb(K, i) * comb(N - K, n - i) for i in range(x, min(n, K) + 1)) / comb(N, n)
        # التوزيع المجمَّع: دلال (٢ متعلَّمة، ١ منها قصة) + فرح (٧ متعلَّمة، ٦ منها قصة) ⇒ مجموع القصة ≥ ٧
        pmf = lambda N, K, n: [comb(K, i) * comb(N - K, n - i) / comb(N, n) for i in range(0, min(n, K) + 1)]
        d1, d2 = pmf(20, 10, 2), pmf(20, 10, 7)
        pe = sum(d1[i] * d2[j] for i in range(len(d1)) for j in range(len(d2)) if i + j >= 7)
        ok('skipped pre-test → child out of the criterion; the pooled exact test uses the other two', r['k'] == 'excluded' and r['d'] == 'ready' and r['f'] == 'ready' and abs(r['p'] - pe) < 1e-9 and 'مستبعد' in r['v'] and 'احتمال الصدفة' in r['v'], json.dumps({k: r[k] for k in 'kdfp'}) + f' expected {pe}')

        # ---------- F5 + F6: المسرح والمسابقة بعد اختبار البداية؛ الرمز يُختار من الصفحة الرئيسية فقط ----------
        pg2 = await new_page(b, ERR, seed_pin=False); ev2 = pg2.evaluate
        await pg2.goto(URL); await pg2.wait_for_timeout(900)
        ok('fresh device: home asks the parent to choose the PIN first', bool(await pg2.query_selector('#pinSetup')))
        ok('…family theater and quiz wait for the pre-tests', not await pg2.query_selector('#thBtn') and not await pg2.query_selector('#qzBtn'))
        await pg2.click('[data-k="dalal"]'); await pg2.wait_for_timeout(400)
        ok('R4: before the PIN exists, a child button stays on home', bool(await pg2.query_selector('#pinSetup')) and not await pg2.query_selector('#preSkip'))
        await ev2("go('kid','dalal')"); await pg2.wait_for_timeout(400); await pg2.click('#preSkip'); await pg2.wait_for_timeout(400)
        ok('a child cannot create the PIN from her own screen', not await pg2.query_selector('.pinpad') and not await ev2("sget('kv','pin')"))
        await ev2("go('home')"); await pg2.wait_for_timeout(400); await pg2.click('#pinSetup'); await pg2.wait_for_timeout(300)
        await answer_gate(pg2); await pg2.wait_for_timeout(600)
        ok('the home-page setup creates the PIN', await ev2("sget('kv','pin')") == '2468' and not await pg2.query_selector('#pinSetup'))
        await ev2("(async()=>{for(const k of ['dalal','farah','kareem']){const p=await loadProg(k);p.tests={pre:{v:2,skipped:1,t:1,resp:{}}};await saveProg(k,p)}await go('home')})()"); await pg2.wait_for_timeout(500)
        ok('…theater and quiz appear once every child has settled the pre-test', bool(await pg2.query_selector('#thBtn')) and bool(await pg2.query_selector('#qzBtn')))
        # F8: recovery then cancel keeps the old PIN
        await pg2.click('#pBtn'); await pg2.wait_for_timeout(300); await pg2.click('#pinForgot'); await pg2.wait_for_timeout(200)
        rc = await ev2("sget('kv','pinrc')"); await pg2.fill('#rcIn', rc); await pg2.click('#rcOk'); await pg2.wait_for_timeout(300)
        await pg2.click('.pinpad [data-pk="x"]'); await pg2.wait_for_timeout(300)
        ok('recovery code then cancel: the old PIN still protects parent mode', await ev2("sget('kv','pin')") == '2468')
        await pg2.context.close()

        # ---------- F7: استعادة ملف أقدم بالكامل من صفحة الطفل تحتاج الرمز ----------
        await ev("(async()=>{const p=await loadProg('farah');p.done={0:true,1:true,2:true};p.doneT={0:Date.now()-1e5,1:Date.now()-5e4,2:Date.now()};await saveProg('farah',p);await go('kid','farah')})()"); await pg.wait_for_timeout(600)
        oldf = {'kid': 'farah', 'prog': {'scene': 0, 'step': 0, 'done': {}, 'doneT': {}, 'leitner': {}, 'results': {}}, 'audio': {}, 'draw': {}, 'log': [[1000, 'scene']]}
        pth = os.path.join(tmp, 'farah_old.json'); open(pth, 'w', encoding='utf-8').write(json.dumps(oldf))
        await pg.set_input_files('#myRs', pth); await pg.wait_for_timeout(800)
        if await pg.query_selector('.mdl-c'):
            await pg.click('.mdl-c button >> text=استعادة كاملة'); await pg.wait_for_timeout(400)
        ok('child screen: full restore of an older file asks for the parent PIN', bool(await pg.query_selector('.pinpad')))
        if await pg.query_selector('.pinpad'):
            await pg.click('.pinpad [data-pk="x"]'); await pg.wait_for_timeout(400)
        ok('…and without it nothing is rolled back', len((await ev("loadProg('farah')"))['done']) == 3)

        # ---------- F9: صورة أُعيد التقاطها تظهر فورًا ----------
        u = await ev("""(async()=>{const mk=c=>new Promise(r=>{const cv=document.createElement('canvas');cv.width=cv.height=4;const x=cv.getContext('2d');x.fillStyle=c;x.fillRect(0,0,4,4);cv.toBlob(r)});await sput('img','plant:farah',await mk('blue'));const a=await imgSrc('plant:farah');await sput('img','plant:farah',await mk('red'));const b=await imgSrc('plant:farah');return [a,b]})()""")
        ok('a retaken photo is shown, not the cached old one', u[0] != u[1])

        # ---------- F10: الصوت السحري يتوقف عند مغادرة الشاشة ----------
        n = await ev("(async()=>{const c=actx();const s=c.createBufferSource();s.buffer=c.createBuffer(1,c.sampleRate*5,c.sampleRate);s.connect(c.destination);s.start();MAGIC_SRC.push(s);await go('home');return MAGIC_SRC.filter(x=>x instanceof AudioBufferSourceNode).length})()")
        ok('magic-voice audio stops when the child leaves the screen', n == 0)

        # ---------- F11: تغيير المستوى في منتصف المشهد لا يُنهيه ----------
        await ev("(async()=>{const p=await loadProg('farah');p.done={0:true};p.scene=1;p.step=5;await saveProg('farah',p);await go('parent')})()"); await pg.wait_for_timeout(800)
        await pg.click('summary >> text=رمز ولي الأمر'); await pg.select_option('[data-lane="farah"]', 'A'); await pg.wait_for_timeout(500)
        F = await ev("loadProg('farah')")
        ok('changing a level mid-scene restarts that scene instead of finishing it', F['step'] == 0 and not F['done'].get('1'))
        await pg.select_option('[data-lane="farah"]', 'C'); await pg.wait_for_timeout(300)

        # ---------- F12 + F13: مفاتيح صوت مصنوعة تُرفض؛ تسجيل ولي الأمر الأحدث يصل بالرسائل فقط ----------
        await ev("sput('audio','model:s0:word',{blob:new Blob([new Uint8Array(10)]),mime:'audio/webm',sec:1,t:1000})")
        mb = {'kid': 'farah', 'prog': {'scene': 0, 'step': 0, 'done': {}, 'leitner': {}, 'results': {}}, 'draw': {}, 'audio': {
            'model:s0:word': {'d': aud, 'mime': 'audio/webm', 'sec': 2, 't': 5000},
            'report:farah:"><img src=x onerror=window.__pwn4=1>': {'d': aud, 'mime': 'audio/webm', 'sec': 1, 't': 1}}}
        pth = os.path.join(tmp, 'msgs.json'); open(pth, 'w', encoding='utf-8').write(json.dumps(mb))
        await ev("go('parent')"); await pg.wait_for_timeout(700)
        await pg.set_input_files('#bkin', pth); await pg.wait_for_timeout(800)
        if await pg.query_selector('.mdl-c'):
            await pg.click('.mdl-c button >> text=الرسائل والتحديات فقط'); await pg.wait_for_timeout(900)
        ok('messages-only restore brings the newer parent recording', await ev("sget('audio','model:s0:word').then(r=>r.t)") == 5000)
        ok('…and drops audio keys that are not the app\'s own shape', not await ev("skeys('audio').then(k=>k.some(x=>String(x).includes('<')))"))

        # ---------- F14: إرجاع الساعة لا يفتح مشهد اليوم ----------
        await ev("(async()=>{const p=await loadProg('farah');p.done={0:true};p.step=0;p.lastNew=today()+1;await saveProg('farah',p);await go('kid','farah')})()"); await pg.wait_for_timeout(600)
        ok('clock moved back: today\'s new-scene lock still holds', 'غدًا' in await view(pg))

        # ---------- قرارات فراس (٦ نوفمبر) ----------
        # ق٢ (١٣ نوفمبر): لا حدّ أدنى ولا حكم بالشفهي وحده؛ طفل يعرف ٨ من ١٠ يدخل بكلمتيه المجهولتين
        r = await ev("""(async()=>{const mk=(ok,dk,sc)=>({rec:{ok,dk:dk?1:0},oral:dk?{dk:1}:{has:1,score:sc}});
          const pre={v:2,k:999,done:true,t:1,t0:0,resp:{}},post={v:2,k:999,done:true,t:2,t0:0,resp:{}};
          for(let i=0;i<10;i++){pre.resp['t'+i]=mk(i<8?1:0,i>=8,i<8?1:0);pre.resp['c'+i]=mk(0,1);post.resp['t'+i]=mk(1,0,2);post.resp['c'+i]=mk(0,1)}
          const delay=JSON.parse(JSON.stringify(post));const p=await loadProg('dalal');p.tests={pre,post,delay};await saveProg('dalal',p);const c=stratum(p);await go('parent');return {status:c.status,nT:c.nT,xT:c.xT,nC:c.nC,xC:c.xC}})()""")
        await pg.wait_for_timeout(900)
        ok('child who knew 8 of 10 story words still counts, with his 2 unknown story words (no floor, no oral-only route)', r == {'status': 'ready', 'nT': 2, 'xT': 2, 'nC': 10, 'xC': 0}, json.dumps(r))
        ok('…and the report shows the counts behind it', '٢ من ٢' in await view(pg) and '٠ من ١٠' in await view(pg))
        r = await ev("""(async()=>{const p=await loadProg('dalal');p.tests.pre.resp.t0={rec:{ok:0,dk:0},oral:{has:1,score:1}};p.tests.pre.resp.t1={rec:{ok:0,dk:0},oral:{has:1,na:1}};return stratum(p)})()""")
        ok('…a wrong answer with a partial oral meaning (1) is not «strictly unknown»; an inaudible one is left out', r['nT'] == 2 and r['und'] == 1, json.dumps({k: r[k] for k in ['nT', 'und']}))
        # ٤) «خشبي» و«الذهبية» خارج نسبة الكلمات الإضافية
        n = await ev("""(()=>{const resp={};for(let i=0;i<10;i++)for(let j=0;j<2;j++)resp['b'+i+'_'+j]={rec:{ok:1,dk:0}};return tSummary({tests:{pre:{v:2,done:true,resp}}},'pre').g.B.n})()""")
        ok('bonus percentage counts 18 words (the two answerable from the root are left out)', n == 18, str(n))
        # ٣) «هذا الجهاز لـ…»
        await pg.click('summary >> text=رمز ولي الأمر'); await pg.select_option('#ownerSel', 'dalal'); await pg.wait_for_timeout(400)
        await ev("go('home')"); await pg.wait_for_timeout(500)
        ks = await ev("[...document.querySelectorAll('[data-k]')].map(b=>b.dataset.k)")
        ok('a tablet set to Dalal shows only Dalal on the home page', ks == ['dalal'], str(ks))
        await pg.reload(); await pg.wait_for_timeout(1200)
        ok('…and stays so after restart', await ev("[...document.querySelectorAll('[data-k]')].map(b=>b.dataset.k)") == ['dalal'])
        await pg.click('#pBtn'); await pg.wait_for_timeout(200); await answer_gate(pg); await pg.wait_for_timeout(800)
        await pg.click('summary >> text=رمز ولي الأمر'); await pg.select_option('#ownerSel', ''); await pg.wait_for_timeout(400)
        await ev("go('home')"); await pg.wait_for_timeout(500)
        ok('…"all" brings the three children back', len(await ev("[...document.querySelectorAll('[data-k]')].map(b=>b.dataset.k)")) == 3)

        await b.close()

asyncio.run(main())
print('\n=== FAILED ===', FAIL or 'none')
print('=== ERRORS ===', ERR or 'none')
sys.exit(1 if FAIL or ERR else 0)

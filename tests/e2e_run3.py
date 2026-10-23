import asyncio, os, http.server, threading, socketserver, json
from playwright.async_api import async_playwright
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','web'))
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a): pass
srv=socketserver.TCPServer(('127.0.0.1',8767),Q); threading.Thread(target=srv.serve_forever,daemon=True).start()
ERR=[]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(args=['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream'])
        ctx=await b.new_context(viewport={'width':412,'height':900},permissions=['microphone'],accept_downloads=True)
        pg=await ctx.new_page(); pg.on('pageerror',lambda e:ERR.append(str(e))); pg.on('dialog',lambda d:asyncio.ensure_future(d.accept()))
        await pg.goto('http://127.0.0.1:8767/index.html'); await pg.wait_for_timeout(800)
        t=lambda: pg.inner_text('#view')
        await pg.click('[data-k="farah"]'); await pg.click('#preSkip'); await pg.wait_for_timeout(300)
        async with pg.expect_download() as dl: await pg.click('#myBk')
        path=await (await dl.value).path()
        # new context = new device
        ctx2=await b.new_context(viewport={'width':412,'height':900},accept_downloads=True); pg2=await ctx2.new_page(); pg2.on('pageerror',lambda e:ERR.append(str(e))); pg2.on('dialog',lambda d:asyncio.ensure_future(d.accept()))
        await pg2.goto('http://127.0.0.1:8767/index.html'); await pg2.wait_for_timeout(800)
        await pg2.click('[data-k="kareem"]'); await pg2.set_input_files('#preRs',path); await pg2.wait_for_timeout(600)
        print('wrong kid toast:', await pg2.inner_text('#toast'))
        await pg2.click('#homeBtn'); await pg2.click('[data-k="farah"]'); await pg2.set_input_files('#preRs',path); await pg2.wait_for_timeout(1200)
        print('farah on new device:', (await pg2.inner_text('#view')).replace('\n',' ')[:100])
        # ant game text sanity (regex fix)
        await pg2.evaluate("""async()=>{const p=await loadProg('farah');p.done[0]=true;p.leitner['مُورِقَة']={box:1,due:today()+1};await saveProg('farah',p)}""")
        await pg2.click('#homeBtn'); await pg2.click('[data-k="farah"]'); await pg2.click('#gmBtn'); await pg2.click('[data-g="ant"]'); await pg2.wait_for_timeout(300)
        print('ant text:', (await pg2.inner_text('#view')).replace('\n',' ')[:90])
        await b.close()
asyncio.run(main()); print('ERRORS:',ERR or 'none')

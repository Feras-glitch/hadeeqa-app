const { app, BrowserWindow, session, Menu } = require('electron');
if (!app.requestSingleInstanceLock()) app.quit();
const path = require('path');
app.commandLine.appendSwitch('lang', 'ar');
function create() {
  const win = new BrowserWindow({ width: 900, height: 760, minWidth: 420, autoHideMenuBar: true, backgroundColor: '#f0fdf4', title: 'حديقة الأسرار', webPreferences: { contextIsolation: true, sandbox: true, devTools: false } });
  Menu.setApplicationMenu(null);
  session.defaultSession.setPermissionRequestHandler((wc, permission, cb) => cb(['media', 'audioCapture', 'videoCapture', 'mediaKeySystem'].includes(permission)));
  session.defaultSession.setPermissionCheckHandler(() => true);
  // التطبيق لا ينتقل إلى أي صفحة أخرى أبدًا: سحب ملف إلى النافذة أو رابط عابر لا يستبدل التطبيق
  win.webContents.on('will-navigate', (e) => e.preventDefault());
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.loadFile(path.join(__dirname, 'www', 'index.html'));
}
app.on('second-instance', () => { const w = BrowserWindow.getAllWindows()[0]; if (w) { if (w.isMinimized()) w.restore(); w.focus(); } });
app.whenReady().then(create);
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) create(); });

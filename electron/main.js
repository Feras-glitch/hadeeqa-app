const { app, BrowserWindow, session } = require('electron');
const path = require('path');
app.commandLine.appendSwitch('lang', 'ar');
function create() {
  const win = new BrowserWindow({ width: 900, height: 760, minWidth: 420, autoHideMenuBar: true, backgroundColor: '#f0fdf4', title: 'حديقة الأسرار', webPreferences: { contextIsolation: true, sandbox: true } });
  session.defaultSession.setPermissionRequestHandler((wc, permission, cb) => cb(['media', 'audioCapture', 'videoCapture', 'mediaKeySystem'].includes(permission)));
  session.defaultSession.setPermissionCheckHandler(() => true);
  win.loadFile(path.join(__dirname, 'www', 'index.html'));
}
app.whenReady().then(create);
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) create(); });

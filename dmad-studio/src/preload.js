'use strict';

const { contextBridge, ipcRenderer } = require('electron');

// Narrow, explicit surface — the renderer gets no direct Node or IPC access.
contextBridge.exposeInMainWorld('dmad', {
  describe: () => ipcRenderer.invoke('dmad:describe'),
  pickFolder: () => ipcRenderer.invoke('dmad:pick-folder'),
  inspect: (target) => ipcRenderer.invoke('dmad:inspect', target),
  install: (options) => ipcRenderer.invoke('dmad:install', options),
  openFolder: (target) => ipcRenderer.invoke('dmad:open-folder', target),
});

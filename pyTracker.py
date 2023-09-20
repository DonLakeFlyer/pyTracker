from MavlinkThread import *
import AppGlobal
from Timer import *

import tkinter as tk
import logging
import threading

mavlinkThread = None

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        
        self._updateUIPending = False
        self.mainloopRunning = False

        self.geometry( "600x400" )
        self.controllerHeartbeatIndicator = tk.Frame(self, width = 50, bg = "red")
        self.controllerHeartbeatIndicator.pack(fill=tk.Y, side=tk.LEFT)
        self.detectorsFrame = tk.Frame(self, bg = "white")
        self.detectorsFrame.pack(expand=True, fill=tk.BOTH, side=tk.LEFT, padx=10, pady=10)

    def updateUI(self):
        # Allow multiple calls to updateUI() to be coalesced into a single call to _updateUI()
        if not self._updateUIPending:
            self._updateUIPending = True
            self.after(200, self._updateUI)

    def _updateUI(self):
        self._updateUIPending = False
        self.controllerHeartbeatIndicator.config(bg = "red" if mavlinkThread.commandHandler.controllerLostHeartbeat else "green")
        if len(self.detectorsFrame.winfo_children()) == 0:
            self._createDetectorUI()
        else:
            self._updateDetectorUI()

    def _createDetectorUI(self):
        logging.info("Creating detector UI")
        for detectorInfo in mavlinkThread.commandHandler.detectorInfoList:
            logging.info("Creating detector UI for detector id {0}".format(detectorInfo.tagId)) 
            detectorFrame = tk.Frame(self.detectorsFrame, bg="red", borderwidth=2, relief=tk.RAISED)
            detectorFrame.pack(expand=True, fill=tk.BOTH)

    def _updateDetectorUI(self):
        logging.info("Updating detector UI")
        pass

    def shutdown(self):
        self.destroy()

def startMavlinkThread():
    global mavlinkThread
    mavlinkThread = MavlinkThread()
    mavlinkThread.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s |  %(filename)s:%(lineno)d')
    AppGlobal.app = App()
    AppGlobal.app.after(500, startMavlinkThread)
    try:
        AppGlobal.app.mainloopRunning = True
        AppGlobal.app.mainloop()
    except:
        pass
    AppGlobal.app.mainloopRunning = False
    mavlinkThread.stop()
    mavlinkThread.join()
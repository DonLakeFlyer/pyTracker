import AppGlobal

import threading
import logging

class Timer:
    def __init__(self, msecsTimeout, callback):
        self._msecsTimeout  = msecsTimeout
        self._callback      = callback
        self._timer         = None

    def __del__(self):
        self.stop()

    def start(self):
        self.stop()
        if AppGlobal.app.mainloopRunning:
            self._timer = AppGlobal.app.after(self._msecsTimeout, self._callback)

    def stop(self):
        if self._timer:
            if AppGlobal.app.mainloopRunning:
                AppGlobal.app.after_cancel(self._timer)
            self._timer = None

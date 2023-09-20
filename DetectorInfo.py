from Timer import *
import AppGlobal

import logging

class DetectorInfo:
    def __init__(self, tagId, tagLabel, intraPulseMsecs, k):
        self.tagId                      = tagId
        self.tagLabel                   = tagLabel
        self.intraPulseMsecs            = intraPulseMsecs
        self.k                          = k
        self.heartbeatTimeout           = True
        self.lastPulseGroupSeqCtr       = -1
        self.lastPulseSNR               = 0.0
        self.lastPulseStale             = True
        self.heartbeatTimerInterval    = (k + 1) * intraPulseMsecs
        self.heartbeatTimeoutTimer     = Timer(self.heartbeatTimerInterval, self._heartbeatTimeoutCallback)
        self.stalePulseSNRTimer        = Timer(self.heartbeatTimerInterval, self._lastPulseStateTimeoutCallback)

    def _heartbeatTimeoutCallback(self):
        self.heartbeatTimeout = True
        AppGlobal.app.updateUI()

    def _lastPulseStateTimeoutCallback(self):
        self.lastPulseStale = True
        AppGlobal.app.updateUI()

    def handleTunnelPulse(self, pulseInfo):
        if pulseInfo.tag_id == self.tagId:
            isDetectorHeartbeat = pulseInfo.frequency_hz == 0
            if isDetectorHeartbeat:
                self.heartbeatLost = False
                self.heartbeatTimeoutTimer.start()
                AppGlobal.app.updateUI()
                logging.info("HEARTBEAT from Detector id {0}".format(self.tagId))
            elif pulseInfo.confirmed_status:
                logging.info("CONFIRMED tag_id:frequency_hz:seq_ctr:snr:noise_psd {0} {1} {2} {3} {4}".format(
                    pulseInfo.tag_id,
                    pulseInfo.frequency_hz,
                    pulseInfo.group_seq_counter,
                    pulseInfo.snr,
                    pulseInfo.noise_psd))

                # We track the max pulse in each K group
                if self.lastPulseGroupSeqCtr != pulseInfo.group_seq_counter:
                    self.lastPulseGroupSeqCtr = pulseInfo.group_seq_counter
                    self.lastPulseSNR = pulseInfo.snr
                else:
                    self.lastPulseSNR = max(pulseInfo.snr, self.lastPulseSNR)
                self.lastPulseStale = False

                self.stalePulseSNRTimer.start()
                AppGlobal.app.updateUI()

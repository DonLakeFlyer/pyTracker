from DetectorInfo import *

class DetectorInfoList(list):
    def populateFromTags(self, tagInfoList):
        for extTagInfo in tagInfoList:
            detectorInfo = DetectorInfo(extTagInfo.tagInfo.id, extTagInfo.ip_msecs_1_id, extTagInfo.tagInfo.intra_pulse1_msecs, extTagInfo.tagInfo.k)
            self.append(detectorInfo)

            if extTagInfo.tagInfo.intra_pulse2_msecs != 0:
                detectorInfo = DetectorInfo(extTagInfo.tagInfo.id + 1, extTagInfo.ip_msecs_2_id, extTagInfo.tagInfo.intra_pulse2_msecs, extTagInfo.tagInfo.k)
                self.append(detectorInfo)

    def handleTunnelPulse(self, pulseInfo):
        for detectorInfo in self:
            detectorInfo.handleTunnelPulse(pulseInfo)


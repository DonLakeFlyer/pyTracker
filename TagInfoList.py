from Settings import *
from TunnelMessage import *

import csv
import logging
import pathlib

class ExtendedTagInfo:
    def __init__(self):
        self._nChannels = 100
        self.tagInfo        = TunnelTagInfo()
        self.name           = "<undefined>"
        self.ip_msecs_1_id  = "<undefined>"
        self.ip_msecs_2_id  = "<undefined>"

class TagInfoList(list):
    def __init__(self):
        self._nChannels     = 100
        self.radioCenterHz  = 0
    
    def checkForTagFile(self):
        tagFilename = self._tagInfoFilePath()
        tagFile     = open(tagFilename)
        if not tagFile:
            raise FileNotFoundError("TagInfo.txt does not exist")

    def loadTags(self):
        self.clear()
        self._setupTunerVars()

        tagFilename = self._tagInfoFilePath()

        lineCount               = 0
        lineFormat              = "id, name, freq_hz, ip_msecs_1, ip_msecs_1_id, ip_msecs_2, ip_msecs_2_id, pulse_width_msecs, ip_uncertainty_msecs, ip_jitter_msecs"
        expectedValueCount      = len(lineFormat.split(","))
        k                       = Settings.k
        falseAlarmProbability   = Settings.falseAlarmProbability / 100.0

        with open(tagFilename) as tagFile:
            for tagLine in tagFile:
                lineCount += 1

                if tagLine.startswith("#"):
                    continue
                if len(tagLine) == 0:
                    continue

                tagValues = tagLine.split(",")
                if len(tagValues) != expectedValueCount:
                    raise Exception("TagInfoList: Line #{0} Does not contain {1} values".format(lineCount, expectedValueCount))

                extTagInfo = ExtendedTagInfo()

                tagValuePosition = 0

                extTagInfo.tagInfo.hdr_command = TunnelCommand.COMMAND_ID_TAG.value

                tagValueString          = tagValues[tagValuePosition]
                tagValuePosition        += 1
                try:
                    extTagInfo.tagInfo.id   = int(tagValueString)
                except ValueError:
                    raise ValueError("TagInfoList: Line #{0} Value:'{1}'. Unable to convert id to int.".format(lineCount, tagValueString))
                if extTagInfo.tagInfo.id <= 1:
                    raise ValueError("TagInfoList: Line #{0} Value:'{1}'. Tag ids must be greater than 1".format(lineCount, tagValueString))
                if extTagInfo.tagInfo.id % 2:
                    raise ValueError("TagInfoList: Line #{0} Value:'{1}'. Tag ids must be even numbers".format(lineCount, tagValueString))

                extTagInfo.name     = tagValues[tagValuePosition]
                tagValuePosition    += 1
                if len(extTagInfo.name) == 0:
                    extTagInfo.name = str(extTagInfo.tagInfo.id)

                tagValueString      = tagValues[tagValuePosition]
                tagValuePosition    += 1
                try:
                    extTagInfo.tagInfo.frequency_hz = int(tagValueString)
                except ValueError:
                    raise ValueError("TagInfoList: Line #{0} Value:'{1}'. Unable to convert freq_hz to uint.".format(lineCount, tagValueString))

                tagValueString      = tagValues[tagValuePosition]
                tagValuePosition    += 1
                try:
                    extTagInfo.tagInfo.intra_pulse1_msecs = int(tagValueString)
                except ValueError:
                    raise ValueError("TagInfoList: Line #{0} Value:'{1}'. Unable to convert ip_msecs_1 to uint.".format(lineCount, tagValueString))
                if extTagInfo.tagInfo.intra_pulse1_msecs == 0:
                    raise ValueError("TagInfoList: Line #{0} Value:'{1}'. ip_msecs_1 value cannot be 0".format(lineCount, tagValueString))

                extTagInfo.ip_msecs_1_id    = tagValues[tagValuePosition]
                tagValuePosition            += 1
                if len(extTagInfo.ip_msecs_1_id) == 0:
                    extTagInfo.ip_msecs_1_id = "-"

                tagValueString      = tagValues[tagValuePosition]
                tagValuePosition    += 1
                try:
                    extTagInfo.tagInfo.intra_pulse2_msecs  = int(tagValueString)
                except ValueError:
                    raise ValueError("TagInfoList: Line #{0} Value:'{1}'. Unable to convert ip_msecs_2 to uint.".format(lineCount, tagValueString))

                extTagInfo.ip_msecs_2_id    = tagValues[tagValuePosition]
                tagValuePosition            += 1
                if len(extTagInfo.ip_msecs_2_id) == 0:
                    extTagInfo.ip_msecs_2_id = "-"

                tagValueString      = tagValues[tagValuePosition]
                tagValuePosition    += 1
                try:
                    extTagInfo.tagInfo.pulse_width_msecs = int(tagValueString)
                except ValueError:
                    raise ValueError("TagInfoList: Line #{0} Value:'{1}'. Unable to convert pulse_width_msecs to uint.".format(lineCount, tagValueString))
                if extTagInfo.tagInfo.pulse_width_msecs == 0:
                    raise ValueError("TagInfoList: Line #{0} Value:'{1}'. pulse_width_msecs value cannot be 0".format(lineCount, tagValueString))

                tagValueString      = tagValues[tagValuePosition]
                tagValuePosition    += 1
                try:
                    extTagInfo.tagInfo.ip_uncertainty_msecs = int(tagValueString)
                except ValueError:
                    raise ValueError("TagInfoList: Line #{0} Value:'{1}'. Unable to convert ip_uncertainty_msecs to uint.".format(lineCount, tagValueString))
                if extTagInfo.tagInfo.ip_uncertainty_msecs == 0:
                    raise ValueError("TagInfoList: Line #{0} Value:'{1}'. ip_uncertainty_msecs value cannot be 0".format(lineCount, tagValueString))

                tagValueString      = tagValues[tagValuePosition]
                tagValuePosition    += 1
                try:
                    extTagInfo.tagInfo.intra_pulse_jitter_msecs = int(tagValueString)
                except ValueError:
                    raise ValueError("TagInfoList: Line #{0} Value:'{1}'. Unable to convert ip_jitter_msecs to uint.".format(lineCount, tagValueString))
                if extTagInfo.tagInfo.intra_pulse_jitter_msecs == 0:
                    raise ValueError("TagInfoList: Line #{0} Value:'{1}'. ip_jitter_msecs value cannot be 0".format(lineCount, tagValueString))

                extTagInfo.tagInfo.k                        = k
                extTagInfo.tagInfo.false_alarm_probability  = falseAlarmProbability

                self.append(extTagInfo)

            if not self._channelizerTuner():
                raise ValueError("TagInfoList: Unable to tune channelizer")

    def getTagInfo(self, id):
        for tagInfo in self:
            if tagInfo.tagInfo.id == id:
                return tagInfo
        return None

    def _setupTunerVars(self):
        self._sampleRateHz       = 3750000                      # Hardwired to mini
        self._fullBwHz           = self._sampleRateHz
        self._halfBwHz           = self._fullBwHz / 2
        self._channelBwHz        = self._sampleRateHz / self._nChannels
        self._halfChannelBwHz    = self._channelBwHz / 2

    def _channelizerTuner(self):
        if len(self) != 1:
            raise Exception("_channelizerTuner called with 0 or more than 1 tags")
        self._radioCenterHz = self[0].tagInfo.frequency_hz
        return True

    def _firstChannelFreqHz(self, centerFreqHz):
        return centerFreqHz - self._halfBwHz - self._halfChannelBwHz;

    def _tagInfoFilePath(self):
        return pathlib.Path.home() / "TagInfo.txt"

    def maxIntraPulseMsecs(self):
        maxIntraPulseMsecs = 0;
        k = 0
        for tagInfo in self:
            if tagInfo.tagInfo.intra_pulse1_msecs >= maxIntraPulseMsecs:
                maxIntraPulseMsecs = tagInfo.tagInfo.intra_pulse1_msecs
                k = max(k, tagInfo.tagInfo.k)
            if tagInfo.tagInfo.intra_pulse2_msecs >= maxIntraPulseMsecs:
                maxIntraPulseMsecs = tagInfo.tagInfo.intra_pulse2_msecs
                k = max(k, tagInfo.tagInfo.k)
        return [maxIntraPulseMsecs, k]

    def radioCenterHz(self):
        return self._radioCenterHz
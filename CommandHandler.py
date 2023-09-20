from TunnelMessage import *
from TagInfoList import *
from Timer import *
from DetectorInfoList import *
import AppGlobal

import threading
import logging

class CommandHandler:
    def __init__(self, mavlink, callbackQueue):
        self._mavlink                   = mavlink
        self._callbackQueue             = callbackQueue
        self._tunnelCommandAckTimer     = Timer(2000, self._tunnelCommandAckFailed)
        self._controllerHeartbeatTimer  = Timer(6000, self._controllerHeartbeatFailed)
        self._heartbeatCounter          = 1
        self._controllerLostHeartbeat   = True
        self._firstControllerHeartbeat  = True
        self._controllerStatus          = HeartbeatStatus.HEARTBEAT_STATUS_IDLE
        self.detectorInfoList           = DetectorInfoList()
        self._tunnelCommandAckExpected  = TunnelCommand.COMMAND_ID_ACK
        self._tagInfoList               = TagInfoList()
        self._tagInfoList.checkForTagFile()
        self._tagInfoList.loadTags()

    def stop(self):
        self._tunnelCommandAckTimer.stop()
        self._controllerHeartbeatTimer.stop()

    @property
    def controllerLostHeartbeat(self):
        return self._controllerLostHeartbeat
    
    @controllerLostHeartbeat.setter
    def controllerLostHeartbeat(self, value):
        if value != self._controllerLostHeartbeat:
            self._controllerLostHeartbeat = value
            AppGlobal.app.updateUI()

    def processMavlinkTunnelMessage(self, mavlinkTunnelMsg):
        [ command, tunnelObject ] = TunnelMessageHandler.processMavlinkMessage(mavlinkTunnelMsg)
        if command == TunnelCommand.COMMAND_ID_HEARTBEAT:
            self._handleTunnelHeartbeat(tunnelObject)
        elif command == TunnelCommand.COMMAND_ID_ACK:
            self._handleTunnelAck(tunnelObject)
        elif command == TunnelCommand.COMMAND_ID_PULSE:
            self._handleTunnelPulse(tunnelObject)
        else:
            logging.warning("processMavlinkTunnelMessage: Unknown command: %s", command.name)
            pass

    def _handleTunnelHeartbeat(self, heartbeat):
        if heartbeat.system_id == HeartbeatSystemId.HEARTBEAT_SYSTEM_ID_MAVLINKCONTROLLER:
            logging.info("HEARTBEAT from MavlinkTagController - counter:status {0} {1}".format(self._heartbeatCounter, heartbeat.status))
            self.controllerLostHeartbeat = False
            self._controllerHeartbeatTimer.start()
            self._controllerStatus = heartbeat.status
            if self._firstControllerHeartbeat:
                self._firstControllerHeartbeat = False
                self.sendTags()

    def _handleTunnelAck(self, ack):
        if ack.command == self._tunnelCommandAckExpected:
            self._tunnelCommandAckTimer.stop();
            self._tunnelCommandAckExpected = TunnelCommand.COMMAND_ID_ACK

            logging.info("Tunnel command ack received - command:result {0} {1}".format(ack.command, ack.result))

            if ack.result == CommandResult.COMMAND_RESULT_SUCCESS:
                if ack.command == TunnelCommand.COMMAND_ID_START_TAGS or ack.command == TunnelCommand.COMMAND_ID_TAG:
                    self._sendNextTag()
                elif ack.command == TunnelCommand.COMMAND_ID_END_TAGS:
                    self.detectorInfoList.populateFromTags(self._tagInfoList)
                    AppGlobal.app.updateUI()
                    self.startDetection()
            else:
                logging.warning("Tunnel command failed - command:result {0}".format(ack.command))
                raise Exception
        else:
            logging.warning("Tunnel command ack received for unexpected command - expected:actual {0} {1}".format(self._tunnelCommandAckExpected, ack.command))

    def _handleTunnelPulse(self, pulseInfo):
        if self._tagInfoList.isEmpty():
            logging.warning("Pulse received: No tags loaded, ignoring pulse")
            return

        self.detectorInfoList.handleTunnelPulse(pulseInfo);

        isDetectorHeartbeat = pulseInfo.frequency_hz == 0
        if isDetectorHeartbeat:
            logging.info("Detector heartbeat: tag_id {0}".format(pulseInfo.tag_id))
        else:
            knownTag = self._tagInfoList.getTagInfo(pulseInfo.tag_id) != None
            logging.info("Pulse received: tag_id:confirmed:known {0} {1} {2}".format(pulseInfo.tag_id, pulseInfo.confirmed_status, knownTag))

    def startDetection(self):
        startDetection = TunnelStartDetection()
        startDetection.hdr_command                  = TunnelCommand.COMMAND_ID_START_DETECTION
        startDetection.radio_center_frequency_hz    = self._tagInfoList.radioCenterHz()
        startDetection.sdr_type                     = SdrType.SDR_TYPE_AIRSPY_MINI
        self._sendTunnelCommand(startDetection)

    def stopDetection(self):
        stopDetection = TunnelStopDetection()
        stopDetection.hdr_command = TunnelCommand.COMMAND_ID_STOP_DETECTION
        self._sendTunnelCommand(stopDetection)

    def sendTags(self):
        if self._tagInfoList.isEmpty():
            logging.warning("No tags are available to send.")
            return

        self._nextTagToSend = 0

        startTags = TunnelStartTags()
        startTags.hdr_command   = TunnelCommand.COMMAND_ID_START_TAGS;
        startTags.sdr_type      = SdrType.SDR_TYPE_AIRSPY_MINI
        self._sendTunnelCommand(startTags)

    def _sendNextTag(self):
        if self._nextTagToSend == len(self._tagInfoList):
            self._sendEndTags()
        else:
            extTagInfo = self._tagInfoList[self._nextTagToSend]
            self._sendTunnelCommand(extTagInfo.tagInfo)
            self._nextTagToSend += 1

    def _sendEndTags(self):
        endTags = TunnelEndTags()
        endTags.hdr_command = TunnelCommand.COMMAND_ID_END_TAGS
        self._sendTunnelCommand(endTags)

    def _sendTunnelCommand(self, tunnelMsg):
        self._tunnelCommandAckTimer.start()
        self._tunnelCommandAckExpected = tunnelMsg.hdr_command
        TunnelMessageHandler.sendTunnelCommand(self._mavlink, tunnelMsg)

    def _tunnelCommandAckFailed(self):
        logging.warning("Tunnel command failed - no response from vehicle: command {0}".format(self._tunnelCommandAckExpected))
        self._tunnelCommandAckExpected = TunnelCommand.COMMAND_ID_ACK

    def _controllerHeartbeatFailed(self):
        logging.info("Controller heartbeat failed")
        self.controllerLostHeartbeat = True

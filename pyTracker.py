#!/usr/bin/env python

from TunnelMessage import *
from TagInfoList import *

import sys
import time
import logging
import struct

from pymavlink import mavutil

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s |  %(filename)s:%(lineno)d')

tagInfoList = TagInfoList()
tagInfoList.checkForTagFile()
tagInfoList.loadTags()

# create a mavlink serial instance
mavlink = mavutil.mavlink_connection("udpin:localhost:14550")

# wait for the heartbeat msg to find the system ID
mavlink.wait_heartbeat()
print("Heartbeat from APM (system %u component %u)" % (mavlink.target_system, mavlink.target_system))

logging.info("Using Mavlink 2.0 %s", mavutil.mavlink20())

lastHeartbeatTime = 0

while True:
    curTime = time.time()
    if curTime - lastHeartbeatTime > 1:
        logging.info("Sending heartbeat")
        mavlink.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
        lastHeartbeatTime = curTime

    tunnelMsg = mavlink.recv_match(type="TUNNEL", blocking=True, timeout=1)
    if tunnelMsg:
        if tunnelMsg.get_type() == "BAD_DATA":
            logging.warning("recv_match: Bad data")
        else:
            logging.info("TUNNEL received: length %d", tunnelMsg.payload_length)
            command = TunnelMessageHandler.commandFromMavlinkMessage(tunnelMsg)
            if command == TunnelCommand.COMMAND_ID_HEARTBEAT:
                heartbeat = TunnelMessageHandler.heartbeatFromMavlinkMessage(tunnelMsg)
                logging.info("Heartbeat: system_id %d, status %s", heartbeat.system_id, HeartbeatStatus(heartbeat.status).name)
            else:
                logging.info("Unprocessed command: %s", command.name)

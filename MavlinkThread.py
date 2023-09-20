from TunnelMessage import *
from TagInfoList import *
from CommandHandler import *
import AppGlobal

import sys
import time
import logging
import struct
import queue
import threading

from pymavlink import mavutil

class MavlinkThread(threading.Thread):
    def run(self):
        try:
            self._finished = False

            # create a mavlink serial instance
            mavlink = mavutil.mavlink_connection("udpin:localhost:14550")

            # wait for the heartbeat msg to find the system ID
            mavlink.wait_heartbeat()
            print("Heartbeat from APM (system %u component %u)" % (mavlink.target_system, mavlink.target_system))

            logging.info("Using Mavlink 2.0 %s", mavutil.mavlink20())

            lastHeartbeatTime = 0
            callbackQueue = queue.Queue()
            self.commandHandler = CommandHandler(mavlink, callbackQueue)

            while not self._finished:
                curTime = time.time()
                if curTime - lastHeartbeatTime > 1:
                    logging.info("Sending heartbeat")
                    mavlink.mav.heartbeat_send(mavutil.mavlink.MAV_TYPE_GCS, mavutil.mavlink.MAV_AUTOPILOT_INVALID, 0, 0, 0)
                    lastHeartbeatTime = curTime

                mavlinkTunnelMsg = mavlink.recv_match(type="TUNNEL", blocking=True, timeout=1)
                if mavlinkTunnelMsg:
                    if mavlinkTunnelMsg.get_type() == "BAD_DATA":
                        logging.warning("recv_match: Bad data")
                    else:
                        self.commandHandler.processMavlinkTunnelMessage(mavlinkTunnelMsg)

            self.commandHandler.stop()
        except:
            logging.exception("Exception in MavlinkThread")
            self.commandHandler.stop()
            AppGlobal.app.after(100, AppGlobal.app.shutdown)

    def stop(self):
        self._finished = True

from enum import IntEnum

import ctypes
import logging
import struct

class TunnelHeartbeat(ctypes.Structure):
    _fields_ = [ 
        ('hdr_command', ctypes.c_uint), 
	    ('system_id',   ctypes.c_ushort),
	    ('status',      ctypes.c_ushort)
        ]

class TunnelAck(ctypes.Structure):
    _fields_ = [ 
        ('hdr_command', ctypes.c_uint), 
	    ('command',     ctypes.c_uint),
	    ('result',      ctypes.c_uint)
        ]

class TunnelTagInfo(ctypes.Structure):
    _fields_ = [ 
        ('hdr_command',                             ctypes.c_uint),
        ('id',                                      ctypes.c_uint),
        ('frequency_hz',                            ctypes.c_uint),
        ('pulse_width_msecs',                       ctypes.c_uint),
        ('intra_pulse1_msecs',                      ctypes.c_uint),
        ('intra_pulse2_msecs',                      ctypes.c_uint),
        ('intra_pulse_uncertainty_msecs',           ctypes.c_uint),
        ('intra_pulse_jitter_msecs',                ctypes.c_uint),
        ('k',                                       ctypes.c_uint),
        ('false_alarm_probability',                 ctypes.c_double),
        ('channelizer_channel_number',              ctypes.c_uint),
        ('channelizer_channel_center_frequency_hz', ctypes.c_uint),
        ('ip1_mu',                                  ctypes.c_double),
        ('ip1_sigma',                               ctypes.c_double),
        ('ip2_mu',                                  ctypes.c_double),
        ('ip2_sigma',                               ctypes.c_double)
    ]

class TunnelStartDetection(ctypes.Structure):
    _fields_ = [ 
        ('hdr_command',                             ctypes.c_uint),
        ('radio_center_frequency_hz',               ctypes.c_uint),
        ('sdr_type',                                ctypes.c_uint)
    ]

class _tunnelHeaderOnly(ctypes.Structure):
    _fields_ = [ 
        ('hdr_command', ctypes.c_uint)
    ]

class TunnelStopDetection(_tunnelHeaderOnly):
    pass

class TunnelStartTags(ctypes.Structure):
    _fields_ = [ 
        ('hdr_command',                             ctypes.c_uint),
        ('sdr_type',                                ctypes.c_uint)
    ]

class TunnelEndTags(_tunnelHeaderOnly):
    pass


class TunnelPulseInfo(ctypes.Structure):
    _fields_ = [ 
        ('hdr_command',                             ctypes.c_uint),
        ('tag_id',                                  ctypes.c_uint),
        ('frequency_hz',                            ctypes.c_uint),
        ('start_time_seconds',                      ctypes.c_double),
        ('predict_next_start_seconds',              ctypes.c_double),
        ('snr',                                     ctypes.c_double),
        ('stft_score',                              ctypes.c_double),
        ('group_seq_counter',                       ctypes.c_ushort),
        ('group_ind',                               ctypes.c_ushort),
        ('group_snr',                               ctypes.c_double),
        ('noise_psd',                               ctypes.c_double),
        ('detection_status',                        ctypes.c_ubyte),
        ('confirmed_status',                        ctypes.c_ubyte),
        ('position_x',                              ctypes.c_double),
        ('position_y',                              ctypes.c_double),
        ('position_z',                              ctypes.c_double),
        ('orientation_x',                           ctypes.c_float),
        ('orientation_y',                           ctypes.c_float),
        ('orientation_z',                           ctypes.c_float),
        ('orientation_w',                           ctypes.c_float)
    ]

class TunnelRawCapture(ctypes.Structure):
    _fields_ = [ 
        ('hdr_command',                             ctypes.c_uint),
        ('sdr_type',                                ctypes.c_uint)
    ]

class TunnelCommand(IntEnum):
    COMMAND_ID_ACK              = 1     # Ack response to command
    COMMAND_ID_START_TAGS		= 2     # Previous tag set should be cleared, new tags are about to be uploaded
    COMMAND_ID_END_TAGS			= 3     # All new tags have been uploaded
    COMMAND_ID_TAG              = 4     # Tag info
    COMMAND_ID_START_DETECTION  = 5     # Start pulse detection
    COMMAND_ID_STOP_DETECTION   = 6     # Stop pulse detection
    COMMAND_ID_PULSE           	= 7     # Detected pulse value
    COMMAND_ID_RAW_CAPTURE      = 8 	# Capture raw sdr data
    COMMAND_ID_HEARTBEAT	   	= 9  	# Heartbeat message
    COMMAND_ID_START_ROTATION	= 10	# Start rotation, these ids are never sent as commands but are used to log the start and stop of rotation in the csv files
    COMMAND_ID_STOP_ROTATION	= 11	# Cancel rotation, these ids are never sent as commands but are used to log the start and stop of rotation in the csv files

class CommandResult(IntEnum):
    COMMAND_RESULT_SUCCESS		= 1
    COMMAND_RESULT_FAILURE		= 0

class HeartbeatSystemId(IntEnum):
    HEARTBEAT_SYSTEM_ID_MAVLINKCONTROLLER	= 1
    HEARTBEAT_SYSTEM_ID_CHANNELIZER			= 2

class HeartbeatStatus(IntEnum):
    HEARTBEAT_STATUS_IDLE			= 0	# Waiting for Tags to be sent
    HEARTBEAT_STATUS_RECEIVING_TAGS = 1	# In the middle fo tag receive sequence
    HEARTBEAT_STATUS_HAS_TAGS		= 2	# Tags are known, waiting for detection start
    HEARTBEAT_STATUS_DETECTING		= 3	# Detection is in progress
    HEARTBEAT_STATUS_CAPTURE		= 4	# Capturing raw data

class SdrType(IntEnum):
    SDR_TYPE_AIRSPY_MINI    = 1
    SDR_TYPE_AIRSPY_HF		= 2

class TunnelMessageHandler:
    def __init__(self, command, system_id, status):
        self.command = command
        self.system_id = system_id
        self.status = status

    @staticmethod
    def _payloadBytes(tunnelMsg):
        byteArray = bytearray(tunnelMsg.payload_length)
        for byteIndex in range(tunnelMsg.payload_length):
            byteArray[byteIndex] = tunnelMsg.payload[byteIndex].to_bytes(1, byteorder='big')[0]
        return byteArray

    @staticmethod
    def _commandFromPayloadBytes(payloadBytes):
        return TunnelCommand(struct.unpack("@I", payloadBytes[0:4])[0])

    @staticmethod
    def commandFromMavlinkMessage(tunnelMsg):
        logging.info("TUNNEL received: length %d", tunnelMsg.payload_length)
        byteArray = TunnelMessageHandler._payloadBytes(tunnelMsg)
        command = TunnelMessageHandler._commandFromPayloadBytes(byteArray)
        logging.info("Command: %s", command.name)
        return command

    @staticmethod
    def heartbeatFromMavlinkMessage(tunnelMsg):
        if tunnelMsg.payload_length != ctypes.sizeof(TunnelHeartbeat):
            logging.warning("TunnelMessageHandler.heartbeatFromMavlinkMessage: incorrect payload size")
            return None
        payloadBytes = TunnelMessageHandler._payloadBytes(tunnelMsg)
        command = TunnelMessageHandler._commandFromPayloadBytes(payloadBytes)
        if command != TunnelCommand.COMMAND_ID_HEARTBEAT:
            logging.warning("TunnelMessageHandler.heartbeatFromMavlinkMessage: incorrect command, actual: %s", command.name)
            return None
        return TunnelHeartbeat.from_buffer_copy(payloadBytes)
    
    @staticmethod
    def processMavlinkMessage(mavlinkTunnelMsg):
        logging.info("TUNNEL received: length %d", mavlinkTunnelMsg.payload_length)
        payloadBytes = TunnelMessageHandler._payloadBytes(mavlinkTunnelMsg)
        command = TunnelMessageHandler._commandFromPayloadBytes(payloadBytes)
        logging.info("Command: %s", command.name)
        if command == TunnelCommand.COMMAND_ID_HEARTBEAT:
            return [command, TunnelHeartbeat.from_buffer_copy(payloadBytes)]
        elif command == TunnelCommand.COMMAND_ID_ACK:
            return [command, TunnelAck.from_buffer_copy(payloadBytes)]
        elif command == TunnelCommand.COMMAND_ID_PULSE:
            return [command, TunnelPulseInfo.from_buffer_copy(payloadBytes)]
        else:
            return None
        
    @staticmethod
    def sendTunnelCommand(mavlink, tunnelMsg):
        logging.info("TUNNEL send: command %d", tunnelMsg.hdr_command)
        # tunnel_send requires the payload to b 128 bytes for some reason! It's not variable length
        tunnelBytes = bytearray(tunnelMsg) + bytearray(128 - ctypes.sizeof(tunnelMsg))
        mavlink.mav.tunnel_send(mavlink.target_system, 
                                191,                        # MAV_COMP_ID_ONBOARD_COMPUTER
                                0,                          # MAV_TUNNEL_PAYLOAD_TYPE_UNKNOWN
                                ctypes.sizeof(tunnelMsg),   # payload length
                                tunnelBytes)                # payload

# this file that handle socket connection in dialer interface

import socket
import json
import platform
import os
import sys
from pathlib import Path
import time


#=====================================globle_path===============================================
# Determine the absolute path of the directory containing this script
globle_path = Path(__file__).parent.absolute()
# Construct the absolute path to the 'Web' directory
scripts_dir = os.path.abspath(os.path.join(globle_path, '..', 'Web'))
# print(f"Hey this is path+++++++++++{scripts_dir}++++++")  # 📄 Print the absolute path to 'Web' directory

sys.path.insert(0, os.path.join(scripts_dir,'local_connection'))
# import logging

# logging.basicConfig(filename='/devinfraLocal/service_nextjs/scripts/DialerV1/socket_manager.log', level=logging.DEBUG)

from credentials import *

##this class manage all event that send message to web
class SocketManager:
    def __init__(self,logManager):
        # Initialize the socket object and server address
        self.logManager=logManager
        self.customer_communication_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = SocketListnerAddress

    # Method to establish connection with the server
    def connect_to_server(self):
        try:
            self.customer_communication_socket.connect(self.server_address)
            self.logManager.print_dialer_log("SocketManager",f"You Successfully connected to socket server ...")
            return True
        except Exception as e:
            print("Connection failed:", e)
            return False

    # Method to login to the server
    def login_to_server(self):
        login_data = {"subscriber": "dialer_28", "name": str(platform.node())}
        final_event = {"event_name": "REGISTER", "event_data": login_data}
        try:
            self.customer_communication_socket.send(json.dumps(final_event).encode())
            response = self.customer_communication_socket.recv(1024)
            self.logManager.print_dialer_log("SocketManager",f"Response from Socket Server: {response.decode()}")
            return response.decode() == "LoggedIn"
        except Exception as e:
            self.logManager.print_dialer_log("SocketManager",f"Login Failed:: {e}")
            return False

    # Method to check if the socket connection is still active
    def is_socket_connected(self):
        try:
            error_code = self.customer_communication_socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            return error_code == 0
        except socket.error:
            return False

    # Method to reconnect to the server
    def reconnect(self):
        # Close the existing socket
        self.customer_communication_socket.close()
        # Create a new socket and attempt to reconnect
        self.customer_communication_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if self.connect_to_server() and self.login_to_server():
            self.logManager.print_dialer_log("SocketManager",f"Socket Reconnect Successfully...")
            return True
        else:
            self.logManager.print_dialer_log("SocketManager",f"Socket Reconnect Failed...")
            return False

    # Method to send event data to the web application
    def send_event_to_web(self, agent_id, event_data):
        try:
            # Check if the socket connection is still active
            if not self.is_socket_connected():
                self.logManager.print_dialer_log("SocketManager",f"Socket Connection Closed...")
                # Attempt to reconnect if the connection is closed
                if not self.reconnect():
                    self.logManager.print_dialer_log("SocketManager",f"Failed to reconnect. Unable to send event.")
                    return

            # Prepare message data and send it to the web application
            self.logManager.print_dialer_log("SocketManager",f"Data sent to - {agent_id}++++ data - {event_data}")
            t = time.localtime()
            current_time = time.strftime("%H:%M:%S", t)
            message_data = {"event_name": "FIRE", "event_data": {"uid": str(agent_id), "message": event_data}}
            # logging.info(f"PANKAJ EVENT DATA -- {current_time} =+= {message_data}")
            message_json = json.dumps(message_data)
            message_with_newline = message_json + "aaabbb"  # Add newline delimiter
            self.logManager.print_dialer_log("SocketManager",f"Message With New Line:: {message_with_newline}++++")
            try:
                self.customer_communication_socket.send(message_with_newline.encode())
                self.logManager.print_dialer_log("SocketManager",f"Event sent to web application successfully")
            except (ConnectionResetError,ConnectionError, TimeoutError, OSError,socket.timeout, socket.error, BlockingIOError, UnicodeDecodeError,BrokenPipeError) as e:
                self.logManager.print_dialer_log("SocketManager",f"PANAKJ SOCKET ERROR :: {e}")
                self.reconnect()
                self.customer_communication_socket.send(message_with_newline.encode())
                self.logManager.print_dialer_log("SocketManager",f"Event sent to web application successfully after Exception")

        except Exception as e:
            self.logManager.print_dialer_log("SocketManager",f"Error sending event:: {e}")
            
    
    
    #function to send user_getnsts events
    def send_user_agent_events(self,agent_ids, event_data):
        try:
            # Check if the socket connection is still active
            if not self.is_socket_connected():
                # Attempt to reconnect if the connection is closed
                if not self.reconnect():
                    self.logManager.print_dialer_log("SocketManager",f"Failed to reconnect. Unable to send event.")
                    return
            #send events to user_agents
            for agent_id in agent_ids:
                self.logManager.print_dialer_log("SocketManager",f"Data sent to - {agent_id.id}+++++ data - {event_data}")
                t = time.localtime()
                current_time = time.strftime("%H:%M:%S", t)
                message_data = {"event_name": "FIRE", "event_data": {"uid": str(agent_id.id), "message": event_data}}
                message_json = json.dumps(message_data)
                message_with_newline = message_json + "aaabbb"  # Add newline delimiter
                self.logManager.print_dialer_log("SocketManager",f"Message With New Line:: {message_with_newline}++++")
                try:
                    self.customer_communication_socket.send(message_with_newline.encode())
                    self.logManager.print_dialer_log("SocketManager",f"Event sent to web application successfully")
                except (ConnectionResetError,ConnectionError, TimeoutError, OSError,socket.timeout, socket.error, BlockingIOError, UnicodeDecodeError,BrokenPipeError) as e:
                    self.logManager.print_dialer_log("SocketManager",f"PANAKJ SOCKET ERROR :: {e}")
                    self.reconnect()
                    self.customer_communication_socket.send(message_with_newline.encode())
                    self.logManager.print_dialer_log("SocketManager",f"Event sent to web application successfully after Exception")
        except Exception as e:
            self.logManager.print_dialer_log("SocketManager",f"Error sending event:: {e}")
            print(f"Error sending event to user_agent {e}")

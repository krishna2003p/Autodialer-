###########################################################
# File: customer_communication_socket.py
# Author:  "None"
# Created: "1 april"
# Description: 
#   this files maintion all the socket connection that need to operate with client
#   its use Event to determine the who and whcih type of data need to send to client and recieve from client
#   
#   Some Events 
#   1. "login" - when any end user need to connect woth socket server fisrt send this event
#   2. "REGISTER" - When any Internal server need to connect woth socket server fisrt send this event
#   3. "SendChat" -  This is use Recive from client , its use for recive app/web message 
#   3. "FIRE" -  When any message need to send to client then use FIRE event (used from - sendWab,Dialer events)
#   4. "SendReport" -  its to send whatsapp report to client 
#
# Usage:
#   For whatsapp Bot ,Dialer Events 
###########################################################


#import module 
import socket
import json
import threading
import asyncio
import websockets
from pathlib import Path
import os
import sys
import jwt
import traceback
import concurrent.futures
import time


# add global directory to access credential file
globle_path = Path(__file__).parent.absolute()
scripts_dir = os.path.abspath(os.path.join(globle_path, '..', '..'))
sys.path.insert(1, os.path.join(scripts_dir, 'local_connection'))
from credentials import *

#logging system
import logging as log
from logging.handlers import RotatingFileHandler
log_level=log.INFO
log_formatter = log.Formatter(fmt='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S', style='%')
logging = log.getLogger(__name__)
logging.setLevel(log.DEBUG)
# Add the log message handler to the logger
handler = log.handlers.RotatingFileHandler(f'{log_dir}/{Path(__file__).stem}.log', maxBytes=50048576, backupCount=50)
logging.addHandler(handler)
handler.setFormatter(log_formatter)
handler.setLevel(log.INFO)
logging.addHandler(handler)


#this fucntion to print and dump logs 
def my_print(msg):
    print(f" :: {msg}")
    logging.info(f" :: {msg}")

#a empty Dict to store all connected used according his user_id
allUserList = {}
InterUsers  = {}
#For get socket to user_id
userSocketMappping = {}
userSocketMappping["socket"] = {}
userSocketMappping["websocket"] = {}


#function to check socket connnection status
def is_socket_connected(sock):
    try:
        error_code = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        return error_code == 0
    except OSError as e:
        my_print(f"Error while checking socket connection status: {e}")
        return False



# Perform authentication for socket connection client
def socket_login(sockettype, login_data, socketObject):
    try:
        if "token" not in login_data:#in case of dialer mainuser login 
            my_print("User Not Send token there for not able to login -- {login_data}")
            return False
        
        token = login_data["token"]
        #decode JWT Token and get data
        userdata = jwt.decode(
                jwt=token,
                key='DRV8hYcDxc+x5nbaHVF0CB2C68yMrxYVHoQKW0zc5J4=',
                algorithms=["HS256"]
            )
    #Now store User in Local arrays `socketIds array use to store agent_id with socektid <socketIds['socket_id'] = 'agent_id'> and Same agentIds store socket Ids <agentIds['agent_id'] = socket_id>
        if userdata is not None:
            if sockettype == 'websocket':
                transport = socketObject.transport
                sock = transport.get_extra_info('socket')
            else:
                sock = socketObject.get_extra_info('socket')
            client_file_id = str(sock.fileno())
            user_id = str(userdata["userId"])
            #insert in socketid to get userid dict 
            userSocketMappping[sockettype][client_file_id] = user_id
            if user_id  not  in allUserList:
                allUserList[user_id]= {}
            if sockettype not in allUserList[user_id]:
                allUserList[user_id][sockettype] =  []
            allUserList[user_id][sockettype].append(socketObject)
            return True
        else:
            return False
    except Exception as e:
        my_print(f"Your Token is not valid  -- {login_data['token']} , error:{e} ,Detailed Error : {traceback.format_exc()} <||")
        return False        

#This fucntion use to Subscribe socket client #Internal User ✍️  
def subscribeUser(sockettype, login_data, socketObject):
    try:
         my_print(f"INTERNAL USERS :: {login_data} client start registering with server ...")
         subscriber = login_data['subscriber']
         list_name = subscriber
         if list_name not in InterUsers:
            InterUsers[list_name] = []
         InterUsers[list_name].append(socketObject)
         my_print(f"INTERNAL USERS :: {InterUsers}")
         my_print(f"INTERNAL USERS :: Total {login_data['subscriber']} subscriber :: {len(InterUsers[list_name])}")
         return True
    except Exception as e:
        my_print(f"INTERNAL USERS ::Error in Registering:{e} ,Detailed Error : {traceback.format_exc()}")
         
 # Function to send a message to a single socket client
async def sendSocketMessage(writer, final_message, i):
    try:
        writer.write(final_message.encode())
        await writer.drain()
        my_print(f"** Message sent to client {i}")
    except (socket.error, BrokenPipeError, ConnectionError, socket.timeout) as ce:
        my_print(f"** SOCKET: client {i} Because it's not Connected, {writer}",level=logging.ERROR)
        return writer
    except Exception as e:
        #(os.path.basename(__file__), e, str(traceback.format_exc()))
        my_print(f"** SOCKET: client {i} Because it's not Connected, {writer} ::  Exception :: {ce}")
        return writer
    return None



# For sending messages into socket and websockets this function is use to  
async def sendMessage(data):
    try:
        #get user id where need to send Data
        user_id =  str(data["event_data"]["uid"])
        if user_id == '':
            my_print("SOCKET :: Recipient is empty ")
            return
        
        if user_id not in allUserList:
            my_print(f"SOCKET :: This User {user_id} is not registered with us")
        socket_client_users = allUserList.get(user_id)
        if not socket_client_users:
            my_print(f"SOCKET :: This User {user_id} is not registered with us")
        else:
            #forclient is use socket connection like mobile app    
            socketclients = allUserList[user_id].get('socket', [])
            websocketUsers = allUserList[user_id].get('websocket', [])
            message = data["event_data"]["message"]
            final_message = json.dumps(message)  
            my_print(f"Total socket clients {len(socketclients)} and websocket clients {len(websocketUsers)} for {user_id}.")
            if socketclients:
                # Create a list of futures for concurrent execution
                try: 
                    my_print(f"** Total Socket Client for user_id {user_id} is {len(socketclients)}")
                    tasks = []
                    for i, writer in enumerate(socketclients, start=1):
                        my_print(f"** Sending Message to Client - {i}")
                        task = sendSocketMessage(writer,final_message, i)
                        tasks.append(task)
                    socketclientsremove = await asyncio.gather(*tasks)
                    socketclientsremove = [writer for writer in socketclientsremove if writer]
                    if len(socketclientsremove) > 0:
                        my_print(f"** The {len(socketclientsremove)} Socket Client Disconnected and We need to remove them from user's socket array")
                        for writer in socketclientsremove:
                            if writer in allUserList[user_id]["socket"]:
                                allUserList[user_id]["socket"].remove(writer)
                        
                    socketclients = allUserList[user_id].get('socket', [])
                    my_print(f"** SOCKET: Message sent to count of  {len(socketclients)} socket client for user_id - {user_id}")
                except Exception as e:
                    #(os.path.basename(__file__), e, str(traceback.format_exc()))
                    my_print(f"** SOCKET ERROR : Message sent to {e}")
            
            #forclient is use webSocket connection like web app 
            if websocketUsers:
                websockets.broadcast(websocketUsers,final_message, raise_exceptions=False)
                for websocketuser in websocketUsers:
                    try:
                        # Check if the WebSocket connection is in the connected state
                        if websocketuser.state != websockets.protocol.State.OPEN:
                            # If not connected, remove the WebSocket user from the list
                            my_print(f"WEBSOCKET :: Removing Object Because it's not Connected , {websocketuser}")
                            allUserList[user_id]["websocket"].remove(websocketuser) # remove client who lost connection websocket
                    except Exception as e:
                        my_print(f"WEBSOCKET :: Error in Checking health message {e}")
                websocketclients = allUserList[user_id].get('websocket', [])        
                my_print(f"WEBSOCKET :: Message Send to  {len(websocketclients)} socket agents for {user_id} || Message - {final_message}")        
    except Exception as e:
        my_print(f"BIG ERROR :: {traceback.format_exc()}")
        my_print(f"BIG ERROR :: Error inn sending Event - {e}")

async def sendInternalMessage(sockettype,socketObject,data):
    try:
        if "event_name" in data:
            subscribers = InterUsers.get(data["event_name"], [])
            my_print("INTERNAL ::  Total Internal clients {len(subscribers)}  {data['event_name']}") 
            if subscribers:
                #get data of sender means web if subscriver is available
                message = data.get("event_data",[])
                if message is None:
                    my_print("INTERNAL :: There is not Event Data in {data['event_name']}")
                    return
                if sockettype == 'websocket':
                    transport = socketObject.transport
                    sock = transport.get_extra_info('socket')
                else:
                    sock = socketObject.get_extra_info('socket')
                client_file_id = str(sock.fileno())
                final_message = json.dumps(data["event_data"])
                for writer in subscribers:
                    try:
                        writer.write(final_message.encode())
                        await writer.drain()
                    except (socket.error, BrokenPipeError, ConnectionError, socket.timeout) as ce:
                        my_print(f"INTERNAL SOCKET:: Removing Object Because its not Connected , {writer}") 
                        InterUsers[data["event_name"]].remove(writer)  # remove client who lost connection socket
                    except Exception as e:
                        my_print(f"INTERNAL :: Error in sending message {e}")
            else:
                my_print(f"INTERNAL Message :: There is no subscriber for {subscriberName}")            
        else:
            my_print(f"INTERNAL Data is not Connect that Why Messane not send, {data}")             
    except Exception as e:
        my_print(f"BIG ERROR Internal:: {traceback.format_exc()}")
        my_print(f"BIG ERROR Internal:: Error inn sending Message - {e}")

#Handle Websocket client that connect with login 
async def echo(websocket, path):
    try:
        async for message in websocket:
            my_print(f"WEBSOCKET :: Received message from client : {message}")
            data = json.loads(message)

            if "event_name" in data:
                if data["event_name"] == "login":
                    if "event_data" in data:
                        if socket_login('websocket', data['event_data'], websocket):
                            my_print(f"WEBSOCKET :: New Web User Login Successfully")
                            my_print(f"WEBSOCKET :: TOTAL LOGIN AGENTS == {allUserList}")
                            await websocket.send(json.dumps("LoggedIn"))
                        else:
                            my_print("WEBSOCKET :: Invalid credentials")
                            await websocket.send(json.dumps("Invalid credentials"))
                            await websocket.close()
                            return
                elif data["event_name"] == "SendChat":
                    # check Agent is Logged IN  
                    ##TODO this NEDDED 
                    await sendInternalMessage("websocket", websocket, data)
                    continue  # Skip to next iteration
                else:
                    await sendMessage(data)  # in case of Stop Chat send Direct Message to Client
    except websockets.exceptions.ConnectionClosed as e:
        my_print(f"WEBSOCKET :: A client just disconnected {websocket}")
        my_print(f"WEBSOCKET :: Error: {e}")

    except Exception as e:
        my_print(f"WEBSOCKET :: DETAIL ERROR :: {traceback.format_exc()}")
        my_print(f"WEBSOCKET :: Error: {e}")



#async def echo(websocket, path):
#    try:
#        # Prompt the client for login information
#        login_info = await websocket.recv()
#        print("Received login information:", login_info)
#        login_data = json.loads(login_info)
#        my_print(f" WEBSOCKET ::  New Client Connection Started - {login_info} ")
#        if 'event_name' in login_data and login_data['event_name'] == 'login':
#            if socket_login('websocket', login_data['event_data'], websocket):
#                my_print(f"WEBSOCKET :: New Web User Login Successfully")
#                msg = json.dumps("LoggedIn")
#                await websocket.send(msg)
#            else:
#                msg = json.dumps("Invalid credentials")
#                await websocket.send(msg)
#                await websocket.close()
#                my_print("WEBSOCKET ::Invalid credentials")
#                return
#        else:
#            msg = json.dumps("You sent wrong data. Please try again...")
#            await websocket.send(msg)
#            await websocket.close()
#            return 
#
#    except Exception as e:
#        my_print(f"WEBSOCKET :: DETAIL ERROR :: {traceback.format_exc()}")
#        my_print(f"WEBSOCKET :: Error in login  - {e}")
#
#    try:
#        async for message in websocket:
#            my_print(f"WEBSOCKET :: Received message from client : {message}")
#            data = json.loads(message)
#            if "event_name" in data and data["event_name"] == "SendChat":
#                await sendInternalMessage("websocket",websocket,data)
#            else:
#                await sendMessage(data) #in case of Stop Chat send Direct Message to Client
#    except websockets.exceptions.ConnectionClosed as e:
#        my_print(f"WEBSOCKET :: A client just disconnected {websocket}")
#    except Exception as e :
#        my_print(f"WEBSOCKET :: DETAIL ERROR :: {traceback.format_exc()}")
#        my_print(f"WEBSOCKET :: ERROR :: {e}")      

# WebSocket server function
async def webSocketStart():
    webSocketPort = WebSocketPort[env]
    my_print("WEBSOCKET :: Server listening on Port " + str(webSocketPort))
    start_server = await websockets.serve(echo, server_ip, webSocketPort)
    await start_server.wait_closed()

#Handle Socket client that connect with login 
async def socketStart():
    socketPort = SocketListner[env]
    server_address = (server_ip, socketPort)
    my_print("SOCKET :: Server listening on Port " + str(socketPort))

    async def handle_client(reader, writer):
        client_address = writer.get_extra_info('peername')
        my_print(f"SOCKET :: New Connection Request :: {client_address}")
        while True:
            data = await reader.read(65536)
            if not data:
                break
            message = data.decode().strip()
            try:
                data = json.loads(message)
                my_print(f"SOCKET :: Received message from client : {data}")
                if "event_name" in data and data["event_name"] == 'login':
                    if socket_login('socket', data["event_data"], writer):
                        try:
                            message = {'type': 'Auth', "status":"success"}
                            message_json = json.dumps(message)
                            writer.write(message_json.encode())
                        except Exception as e:
                            my_print(f"SOCKET :: Exception :: {e}")
                        my_print(f"SOCKET :: Login Successfully :: {data}")
                        my_print(f"SOCKET :: Total logged In Users => :: {allUserList} ::")
                        await writer.drain()
                        while True:
                            data = await reader.readuntil(b'aaabbb')  # Read until newline delimiter
                            if not data:
                                my_print("SOCKET :: Client disconnected == Not Able to do Something")
                                break
                            my_print(f"SOCKET :: Received message from client : {data}")
                            message = data.decode().strip()
                            data = json.loads(message)
                            await sendInternalMessage("socket",writer,data)
                    else:
                        message = {'type': 'Auth', "status":"Invalid Credentials"}
                        message_json = json.dumps(message)
                        writer.write(message_json.encode())
                        await writer.drain()
                else:
                    writer.write("You sent wrong data. Please try again...".encode())
                    await writer.drain()
            except Exception as e :
                my_print(f"SOCKET :: DETAIL ERROR :: {traceback.format_exc()}")
                my_print(f"SOCKET :: Error - {e}")
        writer.close()


    #async def handle_client(reader, writer):
    #    client_address = writer.get_extra_info('peername')
    #    my_print(f"SOCKET :: New Connection Request :: {client_address}")
    #    while True:
    #        data = await reader.read(65536)
    #        if not data:
    #            break
    #        message = data.decode()
    #        try:
    #            data = json.loads(message)
    #            my_print(f"SOCKET :: Login data :: {data}")
    #            if "event_name" in data and data["event_name"] == 'login':
    #                if socket_login('socket', data["event_data"], writer):
    #                    try:
    #                        message = {'type': 'Auth', "status":"success"}
    #                        message_json = json.dumps(message)
    #                        writer.write(message_json.encode())
    #                    except Exception as e:
    #                        my_print(f"SOCKET :: Exception :: {e}")
    #                    my_print(f"SOCKET :: Login Successfully :: {data}")
    #                    my_print(f"SOCKET :: Total logged In Users => :: {allUserList} ::")
    #                    await writer.drain()
    #                    while True:
    #                        data = await reader.read(65536)
    #                        if not data:
    #                            my_print("SOCKET :: Client disconnected == Not Able to do Something")
    #                            #break
    #                        my_print(f"SOCKET :: Received message from client : {data}")
    #                        message = data.decode()
    #                        data = json.loads(message)
    #                        await sendInternalMessage("socket",writer,data)    
    #                else:
    #                    message = {'type': 'Auth', "status":"Invalid Credentials"}
    #                    message_json = json.dumps(message)
    #                    writer.write(message_json.encode())
    #                    await writer.drain()        
    #            else:
    #                writer.write("You sent wrong data. Please try again...".encode())
    #                await writer.drain()             
    #        except Exception as e :
    #            my_print(f"SOCKET :: DETAIL ERROR :: {traceback.format_exc()}")
    #            my_print(f"SOCKET :: Error - {e}") 
    #    writer.close()
    server = await asyncio.start_server(handle_client, *server_address)
    async with server:
        await server.serve_forever()        
      
#listerner server that handle inter server messages thats need to send direct to web/app
async def socketListnerStart():
    #socketPort = 8012
    socketPort = SocketPort[env]
    server_address = (server_ip, socketPort)
    my_print("LISTENER :: Server listening on Port " + str(socketPort))

    async def handle_Listner(reader, writer):
        client_address = writer.get_extra_info('peername')
        my_print(f"LISTENER :: New Internal Socket client Connected -- {client_address}")
        while True:
            data = await reader.read(65536)
            #data = await reader.readuntil(b'aaabbb')
            if not data:
                break
            message = data.decode()
            data = json.loads(message)
            my_print(f"LISTENER :: Data recieved :: {data}")
            try:
                if "event_name" in data and data["event_name"] == "REGISTER":
                     if subscribeUser("socket",data["event_data"],writer):
                        writer.write("LoggedIn".encode())
                        my_print(f"LISTENER :: Total logged in INternal  Users => :: {InterUsers} ::")
                        await writer.drain()
                        while True:
                            #data = await reader.read(65536)
                            data = await reader.readuntil(b'aaabbb')
                            if not data:
                                my_print("LISTENER :: Client disconnected")
                                #break
                            message = data.decode()
                            # Remove the delimiter 'aaabbb'
                            message = message.replace('aaabbb', '')
                            my_print(f"KRISHNA+++++++++++{message}+++++++++++++++++++++")
                            my_print(f"KRISHNA DATA++++++++++++++++{data}+++++++++++++++++")
                            data = json.loads(message)
                            if "event_name" in data and(data["event_name"] == 'FIRE' or data["event_name"] == "sendReport" or data["event_name"] == "stopChat"):
                                     await sendMessage(data)
                if "event_name" in data and(data["event_name"] == 'FIRE' or data["event_name"] == "sendReport" or data["event_name"] == "stopChat"):
                    await sendMessage(data)
                else:
                    my_print("LISTENER :: PLEASE SEND RIGHT DATA YOU SEND WRONG ..")
                    response = json.dumps("YOU SEND WRONG DATA PLEASE SEND RIGHT ..")
                    writer.write(response.encode())
                    await writer.drain()
            except Exception as e:
                my_print(f"LISTENER :: DETAIL ERROR :: {traceback.format_exc()}")
                my_print(f"LISTENER :: Error in socket Listner - {e}")
                break
        writer.close()

    server = await asyncio.start_server(handle_Listner, *server_address)
    async with server:
        await server.serve_forever()


# Main function to start both servers
async def main():
    # Create tasks for both servers
    socket_task = asyncio.create_task(socketStart())
    websocket_task = asyncio.create_task(webSocketStart())
    socketListner = asyncio.create_task(socketListnerStart())
    # Wait for both servers to start
    await asyncio.gather(socket_task, websocket_task,socketListner)

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())


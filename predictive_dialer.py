import threading
import EventManager
# import DialerInterface
import CampaignManager
import AgentManager
import AdminManager
import websocket
import json
import CallManager
import sys
import traceback
import ARIInterface
import requests
import SocketManager
import ReportManager
import time
import LogManager
import uvicorn
import os
import socket 
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Form, Query
from typing import Dict


#=====================================globle_path===============================================
# Determine the absolute path of the directory containing this script
globle_path = Path(__file__).parent.absolute()
# Construct the absolute path to the 'Web' directory
scripts_dir = os.path.abspath(os.path.join(globle_path, '..', 'Web'))
# print(f"Hey this is path+++++++++++{scripts_dir}++++++")  # 📄 Print the absolute path to 'Web' directory

sys.path.insert(0, os.path.join(scripts_dir,'local_connection'))
from setting_credentials import * 
from credentials import *

#get sbc ip
setting_credentials = sbc_ip


debug=False
logManager=LogManager.LogManager()
callManager=CallManager.CallManager(logManager)
agentManager=AgentManager.AgentManager(logManager)
adminManager=AdminManager.AdminManager()
campaignManager=CampaignManager.CampaignManager(logManager)
socketManager=SocketManager.SocketManager(logManager)
reportManager=ReportManager.ReportManager(logManager)
ariInterface=ARIInterface.ARIInterface(server_addr,ARI_USERNAME,ARI_PASSWORD,environment_name,setting_credentials[0],logManager)
eventManager=EventManager.EventManager(ariInterface,agentManager,campaignManager,callManager,socketManager,reportManager,logManager,adminManager)

#get filename to send filename in logmanager 
filename = os.path.splitext(os.path.basename(__file__))[0]

#create fast api object 
app = FastAPI()


def is_blacklist(user_id,mobile):
    try:
        checkBlackList = f"{blackListUrl}/singlevalidateblacklist/"
        form_data = { 'user_id': user_id, 'number': mobile }
        response = requests.post(url, data=form_data)
        logManager.print_dialer_log("AdminManager",f"BalcList Response  :: {response.text} ")
        response_json = json.loads(response.text)
        if response_json['is_blacklist']:
            ariInterface.play_text(agent.channel_id,"Number is blacklisted")
            return True
        return False       
    except Exception as e:
        logManager.print_dialer_log("AdminManager",f"BlackList Checking  Error   :: {e} ")
        return False 


"""
Handle the hangup request from the web panel.
"""
@app.post("/hangup")
async def hangup(agent_id: int = Form(...), command: str = Form(...), number: str = Form(...), channel_id: str = Form(...)):
    try:
        # Log received parameters for debugging
        recieved_data = json.dumps({"agent_id":agent_id,"command":command,"number":number,"channel_id":channel_id})
        logManager.insertLogInElastic(serverty="Info",message="Hangup Request Recived",command_data=recieved_data)
        agent = agentManager.getAgentById(agent_id)   # Get Agent Object by agent id
        call = callManager.getCall(filename,agent.currentCall.id) # Get the current call for the agent
        logManager.print_dialer_log("Dialer",f"HANGUP :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
        call.DisconnectedBy = 'Agent'
        ariInterface.hangup(agent.currentCall.id) # Disconnect the current call
        logManager.insertLogInElastic(serverty="Info",message="Hangup Request Recived",command_data=recieved_data)
        return {"Message": "Success", "Code": 200}
    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="Hangup Error",command_data=data)
        raise HTTPException(status_code=500, detail="Failed to hang up the call")

"""
Mute the agent from the web panel.
"""
@app.post("/mute")
async def mute(agent_id: int = Form(...), command: str = Form(...), number: str = Form(...), channel_id: str = Form(...)):
    try:
        # Log received parameters for debugging
        recieved_data = {"agent_id":agent_id,"command":command,"number":number,"channel_id":channel_id}
        logManager.insertLogInElastic(serverty="Info",message="Mute Request Recived",command_data=json.dumps(recieved_data))
        agent = agentManager.getAgentById(agent_id) #Get Agent Object by agent id
        call = callManager.getCall("Mute",agent.currentCall.id) #Get the current call for the agent
        logManager.print_dialer_log("Dialer",f"MUTE :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
        call.mute = True
        #ariInterface.Mute(agent.channel_id) # Mute the agent's channel
        ariInterface.Mute(agent.currentCall.id)
        return {"Message": "Success", "Code": 200}
    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="Mute Error",command_data=data)
        raise HTTPException(status_code=500, detail="Failed to mute the agent")

"""
Unmute the agent from the web panel.
"""
@app.post("/unmute")
async def unmute(agent_id: int = Form(...), command: str = Form(...), number: str = Form(...), channel_id: str = Form(...)):
    try:
        # Log received parameters for debugging
        recieved_data = json.dumps({"agent_id":agent_id,"command":command,"number":number,"channel_id":channel_id})
        logManager.insertLogInElastic(serverty="Info",message="Unmute Request Recived",command_data=recieved_data)
        agent = agentManager.getAgentById(agent_id) # Get Agent Object by agent id
        call = callManager.getCall("Unmute",agent.currentCall.id) # Get the current call for the agent
        logManager.print_dialer_log("Dialer",f"UNMUTE :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
        call.mute = False
        ariInterface.Unmute(agent.currentCall.id) # Unmute the agent's channel
        return {"Message": "Success", "Code": 200}
    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="Unmute Error",command_data=data)
        raise HTTPException(status_code=500, detail="Failed to unmute the agent")

"""
Call whispering with agent caller and admin from the web panel feature.
"""
@app.post("/callwhispering")
async def call_whispering(agent_id: int = Form(...)):
    try:
        # Log received parameters for debugging
        recieved_data = json.dumps({"agent_id":agent_id})
        logManager.insertLogInElastic(serverty="Info",message="Call whispering Request Recived",command_data=recieved_data)
        agent = agentManager.getAgentById(agent_id)
        admin = adminManager.getAdminById(agent.main_user)
        if admin!=None:
            ariInterface.stop_moh(admin.bridge_id)
            ariInterface.CallWhispering(agent.channel_id,admin)
            return {"Message": "Success", "Code": 200}
        else:
            return {"Message": "Admin LoggedOut", "Code": 500}
    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="CallWhispering Error",command_data=json.dumps(data))
        raise HTTPException(status_code=500, detail="Failed to perform call barging")

"""
Hold function if agent holds the caller from the web panel.
"""
@app.post("/hold")
async def hold(agent_id: int = Form(...), command: str = Form(...), number: str = Form(...), channel_id: str = Form(...)):
    try:
        # Log received parameters for debugging
        recieved_data = json.dumps({"agent_id":agent_id,"command":command,"number":number,"channel_id":channel_id})
        logManager.insertLogInElastic(serverty="Info",message="Hold Request Recived",command_data=recieved_data)
        agent = agentManager.getAgentById(agent_id) # Get Agent Object by agent id
        ariInterface.Hold(agent.channel_id) # Hold the agent's channel 
        ariInterface.Hold(agent.currentCall.id)
        call = callManager.getCall("Hold",agent.currentCall.id) # Get the agent's current call object
        logManager.print_dialer_log("Dialer",f"HOLD :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
        # Update call attributes
        call.hold = True
        call.holdtime_start = int(time.time())
        # Send event
        eventManager.EventAgentHold(agent, call.campaign)
        return {"Message": "Success", "Code": 200}
    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="Hold Error",command_data=json.dumps(data))
        raise HTTPException(status_code=500, detail="Failed to put the call on hold")

"""
Unhold function: agent unholds the caller.
"""
@app.post("/unhold")
async def unhold(agent_id: int = Form(...), command: str = Form(...), number: str = Form(...), channel_id: str = Form(...)):
    try:
        # Log received parameters for debugging
        recieved_data = json.dumps({"agent_id":agent_id,"command":command,"number":number,"channel_id":channel_id})
        logManager.insertLogInElastic(serverty="Info",message="Hold Request Recived",command_data=recieved_data)

        agent = agentManager.getAgentById(agent_id) # Get Agent Object by agent id
        call = callManager.getCall("Unhold",agent.currentCall.id) # Get the agent's current call object
        logManager.print_dialer_log("Dialer",f"UNHOLD :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
        campaign=campaignManager.getCampaign(agent.campaign.id)
        # Update call attributes
        call.hold = False
        hold_time = int(time.time() - call.holdtime_start) + int(call.hold_time)
        call.hold_time = str(hold_time)

        # Unhold the agent's channel
        ariInterface.Unhold(agent.channel_id)
        ariInterface.Unhold(agent.currentCall.id)
        eventManager.EventAgentUnhold(agent,campaign)
        return {"Message": "Success", "Code": 200}
    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="Unhold Error",command_data=json.dumps(data))
        raise HTTPException(status_code=500, detail="Failed to unhold the call")

"""
Dial number for manual dialer when agent is on manual dialer.
"""
@app.post("/manualdial")
async def manualdial(agent_id: int = Form(...), command: str = Form(...), number: str = Form(...)):
    try:

        recieved_data = json.dumps({"agent_id":agent_id,"command":command,"number":number})
        logManager.print_dialer_log("Predective_dailer",f"Manual dialer Request Recived {recieved_data}")

        agent = agentManager.getAgentById(agent_id) # Get Agent Object by agent id
        campaign = campaignManager.getCampaign(agent.dialer_campaign) # Get campaign object
        if is_blacklist(agent.main_user,int(number)):
            ariInterface.play_text(agent.channel_id,"Number is blacklisted")
            return {"Message": "Success", "Code": 200}
               
        temp = f"manual_caller,{str(agent.id)}" # Prepare additional information for the call
        current_time_millis = int(time.time() * 1000)
        random_file_digit = str(current_time_millis)[-5:]
        new_channel_id = f"{current_time_millis}{number}"
        call = callManager.getCall("ManualDial",new_channel_id)
        call.type = "manual_caller"
        call.agent = agent
        call.number = str(number)
        call.campaign = campaign
        # Get or create call Object
        channel_id = ariInterface.dial(number, temp, agent.dedicated_number,new_channel_id) # Dial the number using ARI interface
        # Set call attributes
        agent.currentCall=call
        agent.caller_number=number
        logManager.print_dialer_log("Predective_dailer",f"MANAUAL DIALER Started channel ID for number {number}: {channel_id} call_object: {call} ==  call_str: {str(call)}")
        return {"Message": "Success", "Code": 200}
    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="Manual Dial Error",command_data=json.dumps(data))
        raise HTTPException(status_code=500, detail="Failed to dial the number")

"""
Set agent status to inactive when agent is on break or marked themselves inactive.
"""
@app.post("/inactive")
async def inactive(agent_id: int = Form(...), command: str = Form(...), channel_id: str = Form(...)):
    try:
        # Log received parameters for debugging
        recieved_data = json.dumps({"agent_id":agent_id,"command":command,"channel_id":channel_id})
        logManager.insertLogInElastic(serverty="Info",message="Inactive Request Recived",command_data=recieved_data)

        agent = agentManager.getAgentById(agent_id) # Get Agent Object by agent id
        # Update agent status
        agent.status = "Inactive"
        ariInterface.hangup(agent.channel_id) # Disconnect agent channel as requested by API
        return {"Message": "Success", "Code": 200}
    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="Inactive Error",command_data=json.dumps(data))
        raise HTTPException(status_code=500, detail="Failed to set agent status to inactive")

"""
Set agent status to active when agent off break or marked themselves active.
"""
@app.post("/active")
async def active(agent_id: int = Form(...), command: str = Form(...), channel_id: str = Form(...)):
    try:
        # Log received parameters for debugging

        recieved_data = json.dumps({"agent_id":agent_id,"command":command,"channel_id":channel_id})
        logManager.insertLogInElastic(serverty="Info",message="Active Request Recived",command_data=recieved_data)

        agent = agentManager.getAgentById(agent_id) # Get Agent Object by agent id
        agent.status = "Active"  # Update agent status
        return {"Message": "Success", "Code": 200}
    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="Active Error",command_data=json.dumps(data))
        raise HTTPException(status_code=500, detail="Failed to set agent status to active")

"""
Agent switches to autodialer from manual dialer.
"""
@app.post("/switch_to_autodialer")
async def switch_to_autodialer(agent_id: int = Form(...), command: str = Form(...), number: str = Form(...), channel_id: str = Form(...)):
    try:
        # Log received parameters for debugging
        recieved_data = json.dumps({"agent_id":agent_id,"command":command,"number":number,"channel_id":channel_id})
        logManager.insertLogInElastic(serverty="Info",message="Switch to autodialer Request Recived",command_data=recieved_data)
        event_data = {"channel": {"id": channel_id}}

        agent = agentManager.getAgentById(agent_id) # Get Agent object by agent id
        agent.dialer_type = 'autodialer' # Set agent's dialer type to 'autodialer'
        print(f"Hey this is agent data:: {vars(agent)}")
        
        # After dial call from manual dialer and switch to auto then call disconnect of manual dialer
        ariInterface.hangup(agent.currentCall.id)

        # Get campaign object
        campaign = campaignManager.getCampaign(agent.dialer_campaign)

        # Add agent to available agent list to generate calls for that agent
        campaign.addAvailableAgent(agent)

        # Add agent to available agent list to generate calls for that agent
        eventManager.tryDispatch(event_data,campaign)


        return {"Message": "Success", "Code": 200}
    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="switch_to_autodialer Error",command_data=json.dumps(data)) 
        raise HTTPException(status_code=500, detail="Failed to switch to autodialer")

"""
Agent switches to manual dialer from autodialer.
"""
@app.post("/switch_to_manual_dialer")
async def switch_to_manual_dialer(agent_id: int = Form(...), command: str = Form(...), number: str = Form(...), channel_id: str = Form(...)):
    try:
        # Log received parameters for debugging
        recieved_data = json.dumps({"agent_id":agent_id,"command":command,"number":number,"channel_id":channel_id})
        logManager.insertLogInElastic(serverty="Info",message="Switch to Manual Dialer Request Recived",command_data=recieved_data)
        agent = agentManager.getAgentById(agent_id) # Get Agent object by agent id
        agent.dialer_type = 'manual_dialer' #Set agent's dialer type to 'manual_dialer'
        if agent.call_type == 'autodialer':
            campaign = campaignManager.getCampaign(agent.dialer_campaign) # Get campaign object
            campaign.removeAvailableAgent(agent) # Remove agent from available list due to agent switching to manual dialer
        return {"Message": "Success", "Code": 200}
    except Exception as e:
        # Log the exception traceback
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="switch_to_manual_dialer Error",command_data=json.dumps(data))         
        raise HTTPException(status_code=500, detail="Failed to switch to manual dialer")

"""
Caller barging with agent and caller and admin feature from the web panel.
"""
@app.post("/call_barging")
async def call_barging(agent_id: int = Form(...)):
    try:
        # Log received parameters for debugging
        recieved_data = json.dumps({"agent_id":agent_id})
        logManager.insertLogInElastic(serverty="Info",message="Call barging Request Recived",command_data=recieved_data)
        agent = agentManager.getAgentById(agent_id)
        admin = adminManager.getAdminById(agent.main_user)
        if admin!=None:
            print(f"Hey I am admin in call_barging++++++++++++{admin}+++++++")
            ariInterface.stop_moh(admin.bridge_id)
            ariInterface.CallBarging(agent.channel_id,admin)
            return {"Message": "Success", "Code": 200}
        else:
            return {"Message": "Admin LoggedOut", "Code":500}
        #return {"Message": "Success", "Code": 200}
    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="switch_to_manual_dialer Error",command_data=json.dumps(data))         
        raise HTTPException(status_code=500, detail="Failed to perform call barging")



"""
In edit campaign we can edit the campaign at run time.
"""
@app.post("/edit_camp")
async def edit_camp(campaign_id: int = Form(...),changeable_items: str = Form(...)):
    try:
        # Log received parameters for debugging
        changeable_items = json.loads(changeable_items)
        recieved_data = json.dumps({"campaign_id":campaign_id,"changeAble_Items":changeable_items})
        logManager.insertLogInElastic(serverty="Info",message="Edit Campign Request Recived",command_data=recieved_data)
        campaign = campaignManager.getCampaign(campaign_id) # Get campaign object     
        for item in changeable_items:
            campaign.item = changeable_items[item]
        return {"Message": "Success", "Code": 200}
    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="Edit_camp Error",command_data=json.dumps(data))         
        raise HTTPException(status_code=500, detail="Failed to perform edit campaign")

"""
Redialing call again same number.
"""
@app.post("/redialing")
async def redialing(agent_id: int = Form(...), command: str = Form(...), number: str = Form(...), channel_id: str = Form(...)):
    try:
        
        recieved_data = json.dumps({"agent_id":agent_id,"command":command,"number":number,"channel_id":channel_id})
        logManager.insertLogInElastic(serverty="Info",message="Redialing Request Recived",command_data=recieved_data)

        agent = agentManager.getAgentById(agent_id) # Get Agent Object by agent id

        campaign = campaignManager.getCampaign(agent.dialer_campaign) # Get campaign object
        if is_blacklist(agent.main_user,int(number)):
            ariInterface.play_text(agent.channel_id,"Number is blacklisted")
            return {"Message": "Success", "Code": 200}
        
        
        campaign.removeAvailableAgent(agent)
        current_time_millis = int(time.time() * 1000)
        random_file_digit = str(current_time_millis)[-5:]
        new_channel_id = f"{current_time_millis}{int(channel_id)}" 
        call = callManager.getCall("Redialing",new_channel_id)
        
        # Set call attributes
        call.campaign = campaign
        call.agent = agent
        call.agent.on_wrapup = False
        call.agent.on_pacing = False
        agent.call_type = "Redialing"
        call.type = "redialing"
        agent.currentCall=call
        agent.caller_number=number


        temp = f"redialing,{str(agent.id)}" # Prepare additional information for the call
        ariInterface.dial(number, temp, agent.dedicated_number,new_channel_id) # Dial the number using ARI interface

        logManager.print_dialer_log("Dialer",f"Redialing  :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
        
        return {"Message": "Success", "Code": 200}
    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="Redialing Error",command_data=json.dumps(data))         
        raise HTTPException(status_code=500, detail="Failed to perform redialing.")

"""
Blacklist the numbers on active campaign.
"""    
@app.post("/blacklist_number")
async def blacklist_number(agent_id: int = Form(...), command: str = Form(...), number: str = Form(...)):
    try:
        recieved_data = json.dumps({"agent_id":agent_id,"command":command,"number":number})
        logManager.insertLogInElastic(serverty="Info",message="Blacklist number Request Recived",command_data=recieved_data)

        # Log received parameters for debugging
        agent = agentManager.getAgentById(agent_id) # Get Agent object by agent id
        campaign = campaignManager.getCampaign(agent.dialer_campaign) # Get campaign object
        campaign.blacklist.append(number)
        return {"Message": "Success", "Code": 200}
    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="Blacklist_number Error",command_data=json.dumps(data))         
        raise HTTPException(status_code=500, detail="Failed to hang up the agent")


"""
Hangup the agent in some cases automatically.
"""    
@app.post("/agent_hangup")
async def agent_hangup(agent_id: int = Form(...), command: str = Form(...), number: str = Form(...), channel_id: str = Form(...)):
    try:
        # Log received parameters for debugging
        recieved_data = json.dumps({"agent_id":agent_id,"command":command,"number":number,"channel_id":channel_id})
        logManager.insertLogInElastic(serverty="Info",message="Agent hangup number Request Recived",command_data=recieved_data)
        agent = agentManager.getAgentById(agent_id) # Get Agent object by agent id
        ariInterface.hangup(agent.channel_id) # Disconnect agent channel as requested by API
        return {"Message": "Success", "Code": 200}
    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="agent_hangup Error",command_data=json.dumps(data))         
        raise HTTPException(status_code=500, detail="Failed to hang up the agent")
"""
Agent Data refetch or change the existing data.
"""
@app.post("/update_agent")
async def update_agent(agent_id: int = Form(...), adminHangUp: bool = Form(False)):
    """
    Agent Data refetch or change the existing data.
    """
    try:
        # Log received parameters for debugging
        recieved_data = json.dumps({"agent_id":agent_id})
        logManager.insertLogInElastic("EventManager", f"Agent refetch number Request Recived recieved_data==> {recieved_data}")
        agent = agentManager.getAgentById(agent_id)
        if agent and agent.agent_login_status == 'LoggedIn': 
            t = datetime.datetime.now()
            logout_time = time.mktime(t.timetuple())
            reportManager.updateAgentLoginStatus(agent,logout_time)

            #remove agent 
            campaign=campaignManager.getCampaign(agent.currentCampaign)
            campaign.removeAvailableAgent(agent)
            agent.on_wrapup = False
            agent.agent_login_status='LoggedOut'
            if adminHangUp:   #in case of Admin Want to loggedOut the Agent
                ariInterface.play_text(agent.channel_id,f"You’ve been logged out by an admin")
            else:
                ariInterface.play_text(agent.channel_id,f"You have new campaign assigned")
                agent.currentCampaign = 0 
            ariInterface.hangup(agent.channel_id)
            agentManager.removeAgent(agent_id,agent.mobile)
                #agent_data = agentManager.getAgentFromDbId(agent_id)

            eventManager.EventAgentLoggedOut(agent,campaign)

            # We need to discoonect the call of the callr when agent call is disconnected.
            if hasattr(agent, "currentCall"):
                ariInterface.hangup(agent.currentCall.id)
        else:
            # Get Agent data from the database by agent id
            agent_data = agentManager.getAgentFromDbId(agent_id)
        
        return {"Message": "Success", "Code": 200}

    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="Agent_refetch Error",command_data=json.dumps(data))         
        raise HTTPException(status_code=500, detail="Failed to refetch agent data")

"""
Retrieve agent status details. This API returns the agent's current status, including campaign login details, and if the agent is on a call, it provides the call's relevant information
"""
@app.post("/get_agent_status")
async def get_agent_status(agent_id: int = Form(...)):
    try:
        recieved_data = json.dumps({"agent_id":agent_id})
        logManager.insertLogInElastic(serverty="Info",message="Agent get status number Request Recived",command_data=recieved_data)
        if not agent_id:
            raise ValueError("Invalid agent_id provided") 
        
        agent = agentManager.getAgentById(agent_id)
        call_details = {}
        progressBar = {}
        

        #if agent have not assign any campaign then return | or agent never loggedIn in this Dialer
        if not agent:
            agent_data = {"agent_login_status": "LoggedOut"}
        else:
            agent_data = {
                "start_wraping_time": agent.start_wraping,
                "start_pacing_time": agent.start_pacing,
                "agent_status": agent.agent_status,
                "agent_login_status":agent.agent_login_status,
                "status": agent.status,
                "current_campaign_id": agent.dialer_campaign,
                "first_login_time": agent.first_login_time,
                "logintime": agent.logintime,
                "total_session_time": agent.total_session_time,
                "total_oncall_duration": agent.total_oncall_duration,
                "last_connected_number" :agent.last_connected_number,
                "break_start": agent.break_start,
                "channel_id": "",
                'dialer_type': agent.dialer_type,
                "answer_calls": agent.answer_calls
            }
  
            if agent.agent_login_status == 'LoggedIn': #if agent loggedIn then Return campaign current Active Campaign details.     
                campaign = campaignManager.getCampaign(agent.dialer_campaign)
                progressBar = {"campaign_id": campaign.id, "total": campaign.total, "done": int(campaign.total) - len(campaign.data) - int(campaign.Invalid), "left": len(campaign.data)}

                if hasattr(agent, 'currentCall'): #if Agent on Call then Retun current Call details.
                    call = callManager.getCall("get_agent_status",agent.currentCall.id)
                    logManager.print_dialer_log("Dialer",f"ANGET STATUS GET  :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
                    call_details = {key: value for key, value in vars(call).items() if key not in ["agent", "campaign"]}
                    agent_data["channel_id"] = agent.channel_id
                    call_details["number"] = call.agent.caller_number
            
        data = {"agent_data": agent_data, "detail_current_call": call_details, "progressBar": progressBar}        
        return data

    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="Get Agent Status Error",command_data=json.dumps(data))         
        raise HTTPException(status_code=500, detail="Failed to retrieve agent status details")

"""
Endpoint to stop wrapup.
"""
@app.post("/stop_wrapup")
async def stop_wrapup(agent_id: int = Form(...)):
    try:
        recieved_data = json.dumps({"agent_id":agent_id})
        logManager.insertLogInElastic(serverty="Info",message="Agent hangup number Request Recived",command_data=recieved_data)
        if not agent_id:
            raise ValueError("Invalid agent_id provided")
        
        agent = agentManager.getAgentById(agent_id)
        if agent != None:
            call = callManager.getCall("StopWrapup",agent.currentCall.id)
            logManager.print_dialer_log("Dialer",f"STOP WRAPUP  :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
            call.agent.on_wrapup = False
        return {"Message": "Success", "Code": 200}
    except Exception as e:
        data = {"error":e,"error_details":str(traceback.format_exc())}
        logManager.insertLogInElastic(serverty="Critical",message="Stop wrapup Error",command_data=json.dumps(data))         
        raise HTTPException(status_code=500, detail="Failed to stop wrapup")

"""
Reconnect to WebSocket .
"""
def reCreateConnection(server_addr,app_name,username,password):
    try:
        global ws
        url = "ws://"+server_addr+"/ari/events?app="+app_name+"&api_key="+username+":"+password #% (server_addr, app_name, username, password)
        ws = websocket.create_connection(url)
        return {'status':True,'ws':ws}
    except Exception as e:
        return {'status':False,'error':str(e)}


#function to start fast api endpint in another thread 
def start_app():
    global app
    mc_address = socket.gethostname()
    uvicorn_ip = socket.gethostbyname(mc_address)
    uvicorn.run(app, host=uvicorn_ip,port=uvicorn_port)

#start thread to  start api 
thread = threading.Thread(target=start_app)
thread.start()


#it for test dialer autometically by  read event from event store and send this to event manager one by one
if debug == True:
    #We just need test the applicatio only
    eventstore = open('/etc/cloudshope/NewDialer/Dialer/Dialer/event.db', 'r')
    event_datas=eventstore.readlines()
    i=0;
    for event_data in event_datas:
        i=i+1
        if i==10:
            break
        eventManager.handleEvents(event_data.rstrip())
else:
    # Run Dialer Interface with asterisk ari
    app_name = str(environment_name)+'_newpredictive_login'
    logManager.print_dialer_log(filename,f"Statis Application Start with app name - {app_name}")
    url = "ws://"+server_addr+"/ari/events?app="+app_name+"&api_key="+ARI_USERNAME+":"+ARI_PASSWORD #% (server_addr, app_name, username, password)
    ws = websocket.create_connection(url)
    logManager.print_dialer_log(filename,f"Web Socket Connected Successfully at - {ws}")
    try:
        make_agent_loggedOut = True
        while True:
            try:
                for event_str in iter(lambda: ws.recv(), None):
                    try:
                        event_json = json.loads(event_str)
                        if event_json['type'] not in ['StasisStart','ChannelDtmfReceived','StasisEnd','ChannelDestroyed','Dial']:
                            continue
                        json.dump(event_json, sys.stdout, indent=2, sort_keys=True,separators=(',', ': '))
                        if hasattr(eventManager,str(event_json['type'])):
                            function_name=getattr(eventManager,event_json['type'])
                            thread=threading.Thread(target=function_name,args=(event_json,))
                            thread.start()

                    except Exception as e:
                        logManager.print_dialer_log(filename,f"Error in event listing - {e} - {traceback.format_exc()}   <=||",level=logging.ERROR)
            except websocket.WebSocketConnectionClosedException:
                logManager.print_dialer_log(filename,f"Web Socket Connection Closed Exception1  =  <=||",level=logging.ERROR)
                connect_response =  reCreateConnection(server_addr,app_name,ARI_USERNAME,ARI_PASSWORD)
                if connect_response['status']:
                    ws = connect_response['ws']
                    make_agent_loggedOut = True
                    logManager.print_dialer_log(filename,f"connection successfully created ari response=> {connect_response}")
                    pass
                else:
                    logManager.print_dialer_log(filename,f"waiting for 5 sec and response of ari reconnection {connect_response}")
                    time.sleep(5)
            except Exception as e:
                logManager.print_dialer_log(filename,f"CRETICAL ERROR  ==> {e}  =  <=||",level=logging.ERROR)
    except websocket.WebSocketConnectionClosedException:
        logManager.print_dialer_log(filename,f"Web Socket Connection Closed Exception2 =  <=||",level=logging.ERROR)
        os.system('kill -9 ' + str(os.getpid()))
        sys.exit()
    except KeyboardInterrupt:
        logManager.print_dialer_log(filename,f"File Killed Manually",level=logging.ERROR)
    except Exception as e:
        logManager.print_dialer_log(filename,f"{e}",level=logging.CRITICAL)
    finally:
        if ws:
            ws.close()




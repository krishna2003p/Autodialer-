from datetime import datetime
import time
import sys
import json
import datetime
from threading import *
import traceback
from confluent_kafka import Producer
from json import JSONEncoder
import json
import logging as log
from logging.handlers import RotatingFileHandler
from confluent_kafka import Producer
from confluent_kafka import Consumer, KafkaError
import requests
import os
import sys
import datetime
from datetime import  timedelta
import traceback
from pathlib import Path
from datetime import  timedelta

from concurrent.futures import ThreadPoolExecutor

#=====================================globle_path===============================================
# Determine the absolute path of the directory containing this script
globle_path = Path(__file__).parent.absolute()
# Construct the absolute path to the 'Web' directory
scripts_dir = os.path.abspath(os.path.join(globle_path, '..', 'Web'))

sys.path.insert(0, os.path.join(scripts_dir,'local_connection'))

from credentials import *

class DateTimeEncoder(JSONEncoder):
        #Override the default method
        def default(self, obj):
            if isinstance(obj, (datetime.date, datetime.datetime)):
                return obj.isoformat()

class EventManager:
    obj = Semaphore(1)
    def __init__(self,ariInterface,agentManager,campaignManager,callManager,socketManager,reportManager,logManager,adminManager):
        self.agentManager=agentManager
        self.adminManager=adminManager
        self.campaignManager=campaignManager
        self.ariInterface=ariInterface  
        self.callManager=callManager
        self.socket = socketManager
        self.socket.connect_to_server() # connect to socket server
        self.socket.login_to_server()   # login to socket server
        self.reportManager = reportManager
        self.logManager = logManager # log manager to insert logs in elasticsearch  

    def handleEvents(self,event_name):
        try:
            self.logManager.insertLogInElastic(serverty="Info handle Event function", message=str(event_name)) 
            json_str=event_name[21:].replace("\'", "\"")
            event_data=json.loads(json_str)
            function_name=event_data['type']
            func = getattr(self, function_name)
            if callable(func):
                func(event_data);
            return
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Info handle Event Error",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
            
    def StasisStart(self,event_data):
        try:
            self.logManager.print_dialer_log("EventManager",f"STATIS STRAT  :: Start ==> {event_data}")
            #self.logManager.insertLogInElastic(serverty="Info Statis Start function", message=str(event_name))
            #handleStasisStart
            type = event_data["channel"]["dialplan"]["app_data"].split(",")[1]
            call=self.callManager.getCall("StatisStart",event_data["channel"]["id"])
            self.logManager.print_dialer_log("EventManager",f"StatisStart :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
            self.ariInterface.answer_call(event_data["channel"]["id"])
            call.type = type
            self.logManager.insertLogInElastic("Info","Statis Start Call Object",call=call)

            if type == "caller":
                #Caller is connected
                call.campaign=self.campaignManager.getCampaign(event_data["channel"]["dialplan"]["app_data"].split(",")[2])
                self.logManager.insertLogInElastic("Info","New Call Connected",call=call)
                self.callerConnected(event_data)
            elif type == "agent":
                #agent is connected
                self.agentLogin(event_data)
                pass
            elif type == "admin":
                #admin is connected
                self.adminLogin(event_data)
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error Statis Start Error",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
    
    def AgentPacingTime(self,agent,campaign):
        try:
            ### Send login Event to we whenever agent logged in
            self.logManager.insertLogInElastic("Info","Agent Pacing Time",agent=agent,campaign=campaign)
            if agent.agent_login_status=='LoggedOut' or agent.call_type == 'Redialing':
                return
            agent.agent_status = "On Pacing"
            agent.start_pacing = str(int(time.time()))
            pacing_time = campaign.pacing_time
            #agent.total_onpacing_duration = int(call.agent.total_onpacing_duration) + int(pacing_time)
            while pacing_time > 0:
                time.sleep(1)
                pacing_time=pacing_time-1
            agent.agent_status = "FREE"
            campaign.addAvailableAgent(agent)
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error Agent Pacing Time",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
    
    def agentLogin(self,event_data):
        try:
            self.logManager.print_dialer_log("EventManager", f"Agent Login :: EventData :{event_data}")
            channel_id=event_data["channel"]["id"]
            agent_number = str(event_data['channel']['caller']['number']).split("_")[0][-10:]
            agent=self.agentManager.getAgentByMobile(agent_number)
            self.logManager.print_dialer_log("EventManager", f"Agent Login ::  AgentObj: {agent}")
            if agent is None:
                self.ariInterface.play_text(event_data["channel"]["id"],"You are not registered with us..")
                self.ariInterface.hangup(event_data["channel"]["id"])
                return
            if agent.predictive_license != 'True':
                self.ariInterface.play_text(channel_id,"You do not have App Licence Please contact to your Account Manager..")
                self.ariInterface.hangup(channel_id)
                return
            if agent.dialer_campaign == 0:
                self.ari.play_text(channel_id,"There is no any Active Campaign Id Please contact to your Account Manager..")
                self.ari.hangup(channel_id)
                return
            if agent.status == "Inactive":
                self.ariInterface.play_text(channel_id,"Your are in Inactive state Please Try Again Thank You ")
                self.ariInterface.hangup(channel_id)
                return
            
            #get current Active campign for the respective Agent from CampaignManager 
            campaign=self.campaignManager.getCampaign(agent.dialer_campaign)
            self.logManager.print_dialer_log("EventManager",f"Agent Login :: Campaign Details When LoggedIn agent:{agent}, campaign:{campaign}")
            if campaign is None:
                self.ariInterface.play_text(channel_id,f"Your campaign  {agent.dialer_campaign} is already Completed . Thank You Bye Bye")
                self.ariInterface.hangup(channel_id)
                return
            
            #Add Agent in AvailableAgentList in respective campaign and update other agent attributes 
            self.ariInterface.play_text(channel_id,"You are logged in campaign ID"+str(agent.dialer_campaign))
            campaign.addAvailableAgent(agent)
            agent.bridge_id=self.ariInterface.create_bridge()
            agent.channel_id=channel_id
            agent.agent_login_status='LoggedIn'
            agent.on_wrapup=False
            agent.currentCampaign = agent.dialer_campaign
            agent.campaign=campaign
            t = datetime.datetime.now()
            login_time = time.mktime(t.timetuple())
            self.reportManager.insertAgentLoginStatus(agent,login_time) #call report agent to store agent status in elasticsearch
            self.logManager.print_dialer_log("EventManager",f"agent object==> {agent}")
            agent.snoop_id=self.ariInterface.Snoop(channel_id)
            agent.whisper_id=self.ariInterface.Whisper(channel_id)
            self.EventAgentLogin(agent,campaign)
            time.sleep(5) #Time Break beacause of 'the Agent LoggedIn Clip play Completly'
            self.sendProgressBarEvent(agent,campaign)
            self.ariInterface.add_to_bridge(agent.bridge_id,channel_id)
            self.ariInterface.start_moh(agent.bridge_id,agent.dialer_mohclass)
            self.logManager.print_dialer_log("EventManager",f"LoggedIN PANKAJ  ==> Agent Deatils : {vars(agent)} , CampaignDeatils:=> Active_number {campaign.activeNumbers} , Available Agent :{campaign.availableAgent}")
            self.tryDispatch(event_data,campaign)
            self.logManager.insertLogInElastic("Info","After Login Agent Call tryDispatch",agent=agent,campaign=campaign)
            return
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error Agent Login Time",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")

    #Handle admin login here ||  create call object and update type , bridge_id and channel_id in call object 
    def adminLogin(self,event_data):
        try:
            self.logManager.print_dialer_log("EventManager",f"Admin Login Function :: Event Data : {event_data}")
            channel_id=event_data["channel"]["id"]
            call=self.callManager.getCall("TryDispatch", channel_id)
            self.logManager.print_dialer_log("EventManager",f"Admin Login Function :: Call_data : {vars(call)}")
            admin_number = str(event_data['channel']['caller']['number']).split("_")[0][-10:]
            call.number =str(admin_number) 
            admin=self.adminManager.getAdminByMobile(admin_number) 
            self.logManager.print_dialer_log("EventManager",f"Admin Login Function Start  :: Admin_data : {vars(admin)} , Call_data: {vars(call)}")
            if admin is None:
                self.ariInterface.play_text(event_data["channel"]["id"],"You are not valid admin..")
                self.ariInterface.hangup(event_data["channel"]["id"])
                return
            self.ariInterface.play_text(channel_id,"Admin logged in successfully..")
            bridge_id=self.ariInterface.create_bridge()
            channel_id=event_data["channel"]["id"]
            admin.bridge_id=bridge_id
            admin.channel_id=channel_id
            admin.admin_login_status='LoggedIn'
            self.ariInterface.add_to_bridge(bridge_id,channel_id)
            self.ariInterface.start_moh(bridge_id,'bydefault')
            self.logManager.print_dialer_log("EventManager",f"Admin Login Function Final:: Admin_data : {vars(admin)}")
            #self.logManager.insertLogInElastic("Info",f"Admin Login Done",campaign=campaign,call=call)
            return
        except Exception as e:
            self.logManager.print_dialer_log("EventManager",f"Admin Login Function Error:: error:{e}, detail_error:{traceback.format_exc()} ")
    
    #Handle dialing || This function is used to initiate a call || 
    def tryDispatch(self,event_data,campaign,agent_status='LoggedIn'):
        try:
            self.logManager.print_dialer_log("EventManager",f"Try Dispatch EventData  ==> {event_data}")
            if agent_status != 'LoggedIn':
                self.logManager.print_dialer_log("EventManager",f"Try Dispatch ::  Agent LoggedOut ")
            self.logManager.print_dialer_log("EventManager",f"Try Dispatch Call Counting ::   , Available Agent :{campaign.availableAgent}, CallSpeed : {campaign.call_speed} , active_calls: {campaign.activeNumbers}")
            campaign_id=campaign.id
            call_count=campaign.getRequiredCallCount()
            active_calls=len(campaign.activeNumbers) 
            self.logManager.print_dialer_log("EventManager",f"Try Dispatch Counted  ::  , Available Agent :{campaign.availableAgent}, CallSpeed : {campaign.call_speed}, Campaign_id: {campaign_id} ,call_count: {call_count} , active_calls: {active_calls}")
            index = 0
            while index < call_count:
                self.logManager.print_dialer_log("EventManager",f"Try Dispatch Calling Dispatching ::, call_count:{call_count}, call_send:{index},")
                index += 1
                data=campaign.getData()
                self.logManager.print_dialer_log("EventManager",f"Try Dispatch Calling Dispatching :: details_data :{data},")
                if data is not None:
                    try:
                        details_call_id  = data['id']
                        call=self.callManager.getCall("TryDispatch", details_call_id)
                        call.number = data['number']
                        call.campaign=campaign
                        call.detail_data=data
                        self.logManager.print_dialer_log("EventManager",f"tryDispatch :: PANKAJ CALL OBJECT ==> new_detail_id: {details_call_id},  details_data : {data} ::  call_object: {call} ==  call_str: {str(call)}   , calls_detaisl = {vars(call)}")
                        channel_id = self.ariInterface.dial(data['number'],"caller,"+str(campaign.id),campaign.masked_caller_id,details_call_id)
                        self.logManager.print_dialer_log("EventManager",f"tryDispatch :: PANKAJ CALL OBJECT ==>channel_id: {channel_id}  , calls_detaisl = {vars(call)}")
                        self.logManager.insertLogInElastic("Info",f"In tryDispatch Start New Call",campaign=campaign,call=call)
                    except Exception as e:
                        self.logManager.insertLogInElastic(serverty="Error tryDispatch Campaign Not Completed",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
                else:
                    try:
                        channel_id=event_data["channel"]["id"]
                        call=self.callManager.getCall("TryDispatch2",channel_id)
                        self.logManager.print_dialer_log("EventManager",f"TryDispatch2 :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
                        agents=campaign.getAllableAgent()
                        for agent in agents:
                            self.ariInterface.play_text(agent.channel_id,"Your Campaign has been Completed successfully. Thank You.")
                            t = datetime.datetime.now()
                            logout_time = time.mktime(t.timetuple()) 
                            self.reportManager.updateAgentLoginStatus(agent,logout_time)
                            self.ariInterface.hangup(agent.channel_id)
                        self.logManager.insertLogInElastic("Info",f"In tryDispatch Campaign Completed",agent=agent,campaign=campaign,call=call)
                    except Exception as e:
                        self.logManager.insertLogInElastic(serverty="Error tryDispatch Campaign Completed",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
            pass
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error tryDispatch",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
    
    
    def callerConnected(self,event_data):
        try:
            self.logManager.print_dialer_log("EventManager",f"Caller_Connected ::  Started  ==> {event_data}")
            campaign_id = event_data["channel"]["dialplan"]["app_data"].split(",")[2]
            campaign=self.campaignManager.getCampaign(campaign_id)
            call=self.callManager.getCall("Caller_Connected",event_data["channel"]["id"])
            self.logManager.print_dialer_log("EventManager",f"Caller_Connected :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
            self.logManager.print_dialer_log("EventManager",f"Caller_Connected ::  Number: {call.number}, campaign_id: {campaign_id} ,channel_id: {event_data['channel']['id']}")
            self.logManager.insertLogInElastic("Info",f"Caller Connected Function",campaign=campaign,call=call)
            if campaign.extension_transfer_clip != 0:
                try:
                    call.play_id=self.ariInterface.play_extension_clip(campaign.extension_transfer_clip)
                    while call.extension=="" and call.status != "Disconnected":
                        time.sleep(1)
                    if call.status == "Disconnected":
                        return
                    self.ariInterface.stop_play_sound(call.play_id)
                except Exception as e:
                    self.logManager.insertLogInElastic("Info",f"Last Call Status",agent=call.agent,campaign=campaign,call=call)

            #Either extension clip was enabled and extension is pressed or extension clip is not enabled, mean direct transfer
            if call.type in ["manual_caller", "redialing"]:
                agent=call.agent
            else:
                agent=campaign.getAvailableAgent()

            if agent == "":
                try:
                    self.logManager.print_dialer_log("EventManager",f"Caller_Connected :: ABANDONED ::  Agent not available  =>  Number: {call.number},  campaign_id: {campaign_id} ,channel_id: {event_data['channel']['id']} , abandant_clip : {campaign.abandon_clip}")
                    if str(campaign.abandon_clip) !='0':
                        self.ariInterface.play_sound(call.id, "/etc/asterisk_operations/voice/all/"+campaign.abandon_clip,'wav')
                    self.logManager.print_dialer_log("EventManager",f"Caller_Connected  :: ABANDONED ::  => channel_id: {call.id} ,CampaignDeatils:=> Active_number {campaign.activeNumbers} , Available Agent :{campaign.availableAgent} ")    
                    #campaign.reduceActiveCalls(number)
                    call.status='ABANDONED'
                    self.logManager.print_dialer_log("EventManager",f"Caller_Connected  :: ABANDONED ::  => channel_id: {call.id} ,CampaignDeatils:=>  {vars(call)} ")
                    call.call_duration=0
                    self.ariInterface.hangup(call.id)
                    #self.sendProgressBarEvent(call.agent,campaign)
                    #self.reportManager.SendReportDataKafka(call,campaign.campaign_name,campaign.campaign_type,campaign.user_id)
                    #self.logManager.print_dialer_log("EventManager",f"Statis End  :: ABANDONED ::  => channel_id: {call.id} ,CampaignDeatils:=> Active_number {campaign.activeNumbers} , Available Agent :{campaign.availableAgent} ")
                except Exception as e:
                    self.logManager.insertLogInElastic(serverty="Error caller Connected 1 ABANDONED",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
            else:
                try:
                    self.logManager.print_dialer_log("EventManager",f"Caller_Connected :: Call Assign to agent =>  Number: {call.number}, campaign_id: {campaign_id} ,channel_id: {event_data['channel']['id']}, agent_id: {agent.id} ")
                    call.status='Connected'
                    self.logManager.print_dialer_log("EventManager",f"Caller_connected   :: Call Assign Completelty  Channel_id ==> {call.id} , Status : {call.status} ")
                    agent.currentCall=call
                    agent.caller_number=call.number
                    agent.answer_calls = int(agent.answer_calls) + 1
                    agent.last_connected_number = call.number
                    call.agent=agent
                    self.ariInterface.Unmute(agent.channel_id)
                    self.ariInterface.Unhold(agent.channel_id)
                    self.ariInterface.stop_moh(agent.bridge_id)
                    current_time = datetime.datetime.now()
                    datetime_l = agent.mobile+'_'+call.number+'_'+str(current_time.year)+'_'+str(current_time.month)+'_'+str(current_time.day)+'_'+str(current_time.hour)+'_'+str(current_time.minute)+'_'+str(current_time.second)
                    record_name = '/etc/asterisk_operations/recordings/'+str(datetime_l)
                    call.record_name= str(datetime_l) # record_name
                    self.ariInterface.start_record(agent.bridge_id,record_name)
                    self.ariInterface.add_to_bridge(agent.bridge_id,call.id)
                    call.start_time=time.time()
                    self.logManager.print_dialer_log("EventManager",f"Caller_connected   :: Sending Event   Channel_id ==> {call.id} , Status : {call.status} , Available Agent :{campaign.availableAgent}, CallSpeed : {campaign.call_speed} , active_calls: {campaign.activeNumbers} ")
                    self.EventAgentConnected(agent,campaign,call)
                    self.logManager.insertLogInElastic("Info",f"Caller Connected Function",agent=agent,campaign=campaign,call=call)
                except Exception as e:
                    self.logManager.insertLogInElastic(serverty="Error caller connected 2",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
            return
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error Caller Connected",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")

    def WraupTime(self,call,campaign):
        self.logManager.print_dialer_log("EventManager",f"Wraup Time Start For ::  campaign_id: {campaign.id} ,channel_id: {call.id} ,  Wrapup_time: {campaign.wrapup_time}")
        wrapup_time = campaign.wrapup_time
        call.agent.on_wrapup=True
        call.agent.start_wraping = int(time.time())
        self.logManager.insertLogInElastic("Info",f"Statis End Function In type Caller",agent=call.agent,campaign=campaign,call=call)
        while wrapup_time > 0:
            if call.agent.on_wrapup == False or call.agent.agent_login_status=='LoggedOut':
                call.agent.last_wrapup_time=campaign.wrapup_time-wrapup_time
                break
            time.sleep(1)
            wrapup_time=wrapup_time-1
        if call.status == 'Connected' and call.agent.agent_login_status!='LoggedOut':
            call.agent.on_wrapup == False

        call.agent.total_onwrapup_duration = int(call.agent.total_onwrapup_duration) + (campaign.wrapup_time - wrapup_time)


    def StasisEnd(self,event_data):
        try:
            self.logManager.print_dialer_log("EventManager",f"Statis End  :: event_data => {event_data}")
            agentNumber = str(event_data['channel']['caller']['number']).split("_")[0][-10:]
            type = event_data["channel"]["dialplan"]["app_data"].split(",")[1]
            channel_id=event_data["channel"]["id"]

            call=self.callManager.getCall("StatisEnd",channel_id)
            self.logManager.print_dialer_log("EventManager",f"StatisEnd :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
            campaign = call.campaign
            #self.logManager.print_dialer_log("EventManager",f"STATIS END PANKAJ  channel_id-{channel_id} , number {agentNumber} ==>  CampaignDeatils:=> Active_number {campaign.activeNumbers} , Available Agent :{campaign.availableAgent}")
            self.logManager.insertLogInElastic("Info",f"Statis End Function",campaign=campaign,call=call)
            #in this case agent hangup || pressed Red Button by agent Thats Login||
            if type=="agent":
                try:
                    self.logManager.print_dialer_log("EventManager",f"Statis End  :: Agent loggedOut Request  AgentNumber: {agentNumber}")
                    call.DisconnectedBy='Agent'
                    agent=self.agentManager.getAgentByMobile(str(event_data['channel']['caller']['number']).split("_")[0][-10:])
                    if not agent:
                        self.logManager.print_dialer_log("EventManager",f"Agent Not Registered ::: {agentNumber}")
                        return  
                    t = datetime.datetime.now()
                    logout_time = time.mktime(t.timetuple())
                    self.reportManager.updateAgentLoginStatus(agent,logout_time)

                    #remove agent from campaign available list
                    campaign=self.campaignManager.getCampaign(agent.dialer_campaign)
                    campaign.removeAvailableAgent(agent)
                    agent.on_wrapup = False
                    agent.agent_login_status='LoggedOut'
                    agent.currentCampaign = 0
                    
                    #Delete the bridge
                    self.ariInterface.delete_bridge(agent.bridge_id)
                    
                    self.EventAgentLoggedOut(agent,campaign)
                    self.logManager.insertLogInElastic("Info",f"Caller Connected Function In type Agent",agent=agent,campaign=campaign,call=call)

                    # We need to discoonect the call of the callr when agent call is disconnected.
                    if hasattr(agent, "currentCall"):
                        self.ariInterface.hangup(agent.currentCall.id)
                except Exception as e:
                    self.logManager.insertLogInElastic(serverty="Error Statis End When type = agent",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
                
            #in this case caller call is disconnected || agent press ⑨  or 📞 hangup button || caller pressed red button 🛑 📞✂️. to hangup
            elif type=="caller":
                try:
                    self.logManager.print_dialer_log("EventManager",f"STATIS END PANKAJ before reduce   channel_id-{channel_id} , number {agentNumber}   ==>  CampaignDeatils:=> Active_number {campaign.activeNumbers} , Available Agent :{campaign.availableAgent}")
                    self.logManager.print_dialer_log("EventManager",f"Statis End  :: Caller Disconntion Request: {agentNumber} ,call_status: {call.status}")
                    campaign.reduceActiveCalls(str(call.number))
                    self.logManager.print_dialer_log("EventManager",f"STATIS END PANKAJ 2 After Reduced  ==> number:{agentNumber} ,  CampaignDeatils:=> Active_number {campaign.activeNumbers} , Available Agent :{campaign.availableAgent}")
                    if call.status == 'Connected' and call.agent.agent_login_status!='LoggedOut':
                        call.call_duration = int(time.time())-int(call.start_time)
                        call.DisconnectedBy='Agent' if call.DisconnectedBy=='Agent' else 'Caller'
                        try:
                            self.EventAgentDisConnected_Answer(call.agent,call,campaign.campaign_name,call.detail_data)
                        except:
                            self.logManager.print_dialer_log("EventManager",f"Statis End  :: Detail Data => {call}")

                        record_name = self.reportManager.uploadRecording(call.record_name)
                        self.logManager.print_dialer_log("EventManager",f"Statis End  :: Recoding Uploaded => agent_number: {agentNumber} , record_name: {record_name} ")
                        record_name = json.loads(record_name)
                        recording_url = record_name['data'][0]['url']
                        self.reportManager.createTimeline(call.agent.id,call.agent.caller_number,call.status,call.call_duration,recording_url)
                        self.reportManager.SendReportDataKafka(call,campaign.campaign_name,campaign.campaign_type,campaign.user_id,call.agent)
                        self.ariInterface.start_moh(call.agent.bridge_id,call.agent.dialer_mohclass)
                        self.WraupTime(call,campaign)
                        if  call.agent.call_type == "Redialing":
                             call.agent.call_type = "autodialer"

                        if call.agent.agent_login_status == 'LoggedIn':
                            self.EventAgentFree(call.agent,campaign.campaign_name,campaign.campaign_type,campaign) 
                            call.agent.total_onpacing_duration = int(call.agent.total_onpacing_duration) + int(campaign.pacing_time)
                            self.AgentPacingTime(call.agent,campaign)
                        call.status='ABANDONED'
                        call.call_duration=0
                        self.sendProgressBarEvent(call.agent,campaign)
                        self.logManager.print_dialer_log("EventManager",f"Statis End  :: New call Dispatching Start => agent_number: {agentNumber} ,CampaignDeatils:=> Active_number {campaign.activeNumbers} , Available Agent :{campaign.availableAgent} ")
                        self.tryDispatch(event_data,campaign,agent_status=call.agent.agent_login_status)
                        self.logManager.insertLogInElastic("Info",f"Statis End Function After call tryDispatch",agent=call.agent,campaign=campaign,call=call)
                        pass
                except Exception as e:
                    self.logManager.insertLogInElastic(serverty="Error Statis End When type=caller",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")

            elif type in ["manual_caller", "redialing"]:
                try:
                    #manual_caller report 
                    print(f"Hi i am manual_caller call:: {call}")
                    call.call_duration = int(time.time())-int(call.start_time)
                    call.end_time = time.time()
                    call.type = type
                    call.status='ANSWER'
                    call.DisconnectedBy='Caller'
                    record_name = self.reportManager.uploadRecording(call.record_name)
                    record_name = json.loads(record_name)
                    recording_url = record_name['data'][0]['url']
                    print(f"recording_url+++++++{recording_url}+++++++")
                    self.reportManager.createTimeline(call.agent.id,call.agent.caller_number,call.status,call.call_duration,recording_url)
                    #self.reportManager.createTimeline(call,campaign,recording_url)
                    self.EventAgentDisConnected_Answer(call.agent,call,'Outbound Call','NA')
                    #self.reportManager.SendReportDataKafka(call,'Outbound Call','1',call.agent.id,call.agent)
                    self.ariInterface.start_moh(call.agent.bridge_id,call.agent.dialer_mohclass)
                    if type == "manual_caller":
                        self.reportManager.ManualDialerReport(call,call.agent,call.campaign)
                    else:
                        #call.agent.call_type == "Redialing":
                        call.agent.call_type = "autodialer"
                        self.reportManager.SendReportDataKafka(call,'autodialer','1',call.agent.id,call.agent)
                        campaign = self.campaignManager.getCampaign(call.agent.dialer_campaign)
                        self.WraupTime(call,campaign)

                        #print(f"++++++agent status in caller++++++++++++{call.agent.agent_login_status}+++++")
                        if call.agent.agent_login_status == 'LoggedIn':
                            self.EventAgentFree(call.agent,campaign.campaign_name,campaign.campaign_type,campaign)
                            call.agent.total_onpacing_duration = int(call.agent.total_onpacing_duration) + int(campaign.pacing_time)
                            self.AgentPacingTime(call.agent,campaign)
                            self.tryDispatch(event_data,campaign,agent_status=call.agent.agent_login_status)

                    self.logManager.insertLogInElastic("Info",f"manual Dialer",agent=call.agent,campaign=campaign,call=call)
                    pass
                except Exception as e:
                    self.logManager.insertLogInElastic(serverty="Error Statis End When type=manual/redial",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
            else:
                self.logManager.print_dialer_log("EventManager",f"StatisEnd IN ELSE  {type}  channel_id-{channel_id} , number {agentNumber} ==>  EventData:=>  {event_data}")
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error Statis End",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
            

    def ChannelDestroyed(self,event_data):
        try:
            self.logManager.print_dialer_log("EventManager",f"ChannelDestroyed1:: Start => event_data: {event_data} ")
            if event_data["channel"]["dialplan"]["app_name"] == '' and event_data["channel"]["dialplan"]["app_data"] == '':
                self.logManager.insertLogInElastic("Info",f"ChannelDestroyed2 Egnoring this Event as this called from asterisk dialplan not from stasis Application")
                return
            channel_id=event_data["channel"]["id"]
            self.logManager.print_dialer_log("EventManager",f"ChannelDestroyed2 :: ==> {channel_id}  ")
            call=self.callManager.getCall("ChannelDestroyed",channel_id)
            number=str(call.number)
            self.logManager.print_dialer_log("EventManager",f"ChannelDestroyed :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}  , call_details_data : {vars(call)}")
            campaign=call.campaign
            self.logManager.print_dialer_log("EventManager",f"ChannelDestroyed ::  PANKAJ 1 channel_id:{channel_id}  get_campaign:{campaign}  ==>  CampaignDeatils:=> Event_Data:: {event_data}")
            self.logManager.insertLogInElastic("Info",f"ChannelDestroyed - {number} - {channel_id}",campaign=campaign,call=call)
            if call.status == 'ABANDONED' and call.type not in ["manual_caller", "redialing"]:
                self.logManager.print_dialer_log("EventManager",f"ChannelDestroyed :: ABANDONED CONDITION :: channel_id: {call.id} ")
                call.DisconnectedBy='NA'
                self.reportManager.createTimeline(campaign.user_id,number,call.status,0)
                self.EventAgentDisConnected_Failed(call,campaign.campaign_name,'none',call.detail_data['number'],campaign.campaign_type,campaign)        
                self.reportManager.SendReportDataKafka(call,campaign.campaign_name,campaign.campaign_type,campaign.user_id)
                self.logManager.print_dialer_log("EventManager",f"ChannelDestroyed :: ABANDONED CONDITION :: channel_id: {call.id} REPORT SEND")
            elif call.status!='Connected' and call.type not in ["manual_caller", "redialing"]:
                call.DisconnectedBy='NA'
                if call.status in ['RINGING','PROGRESS','DIALLING']:
                    self.logManager.print_dialer_log("EventManager",f"ChannelDestroyed :: Call Failed Manually  => channel_id: {channel_id}, number: {number}, campaign_id: {campaign} ")
                    call.status = 'FAILED'
                    setattr(call,'Time_'+str(call.status)+'_Start' , int(time.time()))
                #self.logManager.print_dialer_log("EventManager",f"ChannelDestroyed :: PANKAJ 2  channel_id-{channel_id} ,   ==>  CampaignDeatils:=> Active_number {campaign.activeNumbers} , Available Agent :{campaign.availableAgent}")    
                campaign.reduceActiveCalls(number)
                self.reportManager.createTimeline(campaign.user_id,number,call.status,0)
                #self.reportManager.createTimeline(call,campaign)
                self.EventAgentDisConnected_Failed(call,campaign.campaign_name,'none',call.detail_data['number'],campaign.campaign_type,campaign)
                self.reportManager.SendReportDataKafka(call,campaign.campaign_name,campaign.campaign_type,campaign.user_id)
                self.logManager.print_dialer_log("EventManager",f"ChannelDestroyed ::  PANKAJ 3  channel_id:{channel_id}   ==>  CampaignDeatils:=> Active_number {campaign.activeNumbers} , Available Agent :{campaign.availableAgent}")
                self.tryDispatch(event_data,campaign)
                self.logManager.insertLogInElastic("Info",f"ChannelDestroyed Function",campaign=campaign,call=call)

            elif call.status!='Connected' and call.status!='ANSWER' and call.type in ["manual_caller", "redialing"]:
                self.logManager.print_dialer_log("EventManager",f"ChannelDestroyed :: Manuual Dialer  => channel_id: {channel_id}, number: {number}, campaign_id: {campaign.id} ")
                if call.status in ['RINGING','PROGRESS','DIALLING']:
                    call.status = 'FAILED'
                call.DisconnectedBy='NA'
                campaign.reduceActiveCalls(number)
                #self.reportManager.createTimeline(call,campaign)
                self.reportManager.createTimeline(call.agent.id,number,call.status,0)
                # self.MergeTimeLine(number,call.status,'none',0)
                self.EventAgentDisConnected_Failed(call,'Outbound call',call.type,call.agent.caller_number,'')
                if call.type == 'redialing':
                    self.reportManager.SendReportDataKafka(call,'autodialer','1',call.agent.id,call.agent)
                else:
                    self.reportManager.ManualDialerReport(call,call.agent,call.campaign)
                self.logManager.insertLogInElastic("Info",f"ChannelDestroyed Function in manual/redialing",campaign=campaign,call=call)
            else:
                self.logManager.print_dialer_log("EventManager",f"ChannelDestroyed ::  IN ELASE CONDITION  EventData: {event_data}, CampaignDeatils:=> Active_number {campaign.activeNumbers} , Available Agent :{campaign.availableAgent}")
                
            pass
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error Channel Destroyed",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")


    # 🎛️ Define a function to handle DTMF events received from channels.
    def ChannelDtmfReceived(self,event_data):
        try:
            call=self.callManager.getCall("ChannelDTMFRecvied",event_data["channel"]["id"])
            self.logManager.print_dialer_log("EventManager",f"ChannelDtmfReceived :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
            self.logManager.print_dialer_log("EventManager",f"Dtmf Pressed   :: event_data :: {event_data}")
            call.extension=event_data['digit']
            self.logManager.insertLogInElastic("Info",f"Dtmf Pressed - {call.extension}",call=call)
            if call.type == 'agent':
                try:
                    agent=self.agentManager.getAgentByMobile(str(event_data['channel']['caller']['number']).split("_")[0][-10:])
                     
                    # Handle DTMF input '9' for hangup: 📞
                    if call.extension == 9 or call.extension == '9':
                        print("ChannelDtmfReceived 9 "+str(event_data))
                        self.logManager.insertLogInElastic("Info",f"HangUp By 9",agent=agent,call=call)
                        #we need to disconnect the caller
                        call.DisconnectedBy='Agent'
                        self.ariInterface.hangup(agent.currentCall.id)
                        self.ariInterface.start_moh(agent.bridge_id,agent.dialer_mohclass)
                    
                    # Handle DTMF input '0': 📞
                    if call.extension == 0 or call.extension == '0':
                        print("ChannelDtmfReceived 0 "+str(event_data))
                        agent.on_wrapup=False
                except Exception as e:
                    self.logManager.insertLogInElastic(serverty="Error ChannelDtmfRecieved When call.type=agent",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
            pass
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error ChannelDtmfRecieved ",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")

    def Dial(self,event_data):
        try:
            self.logManager.print_dialer_log("EventManager",f"DIAL  :: Start => event_data: {event_data} ")
            if "peer" in event_data and "connected" in event_data["peer"] and "caller" not in event_data:
                call=self.callManager.getCall("Dial",event_data["peer"]["id"])
                self.logManager.print_dialer_log("EventManager",f"DIAL  :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
                number=str(call.number)
                #number=str(event_data["peer"]["connected"]["number"][-10:])
                self.logManager.insertLogInElastic("Info",f"Dial - {number}",call=call)
                if event_data['dialstatus'] == '' or event_data['dialstatus'] is None:
                    event_data['dialstatus'] = 'DIALLING' 
                if call.status != "Connected":    
                    call.status=event_data['dialstatus']
                if event_data['dialstatus'] in ["DIALLING","RINGING","PROGRESS"]:
                    self.sendCallingEvent(number,call)
                
                print(f"-==================================----------  {event_data['dialstatus']}  ----------==========================------------------------===========================")
                setattr(call,'Time_'+str(event_data['dialstatus'])+'_Start' , int(time.time()))
                print("Start Channel Id For Number "+str(number)+" "+str(event_data["peer"]["id"]))
                status=event_data["dialstatus"]
                self.logManager.print_dialer_log("EventManager",f"DIAL NUMBER STATUS SET ::  => channel_id : {call.id} ,  number: {number} , call.status : {call.status}  , ")
                if status=="ANSWER" and (call.type == "manual_caller" or call.type == "redialing"):
                    call.status='Connected'
                    self.logManager.print_dialer_log("EventManager",f"DIAL NUMBER MAKE ANSWERED MAUNAL  :: channel_id : {call.id}  number:{number}  - call.status : {call.status} ")
                    setattr(call.agent,'caller_number',number)
                    #call.agent.caller_number=number
                    current_time = datetime.datetime.now()
                    call.start_time=time.time()
                    record_name = '/etc/asterisk_operations/recordings/'+call.id
                    call.record_name=call.id  #record_name
                    self.ariInterface.stop_moh(call.agent.bridge_id)
                    call.agent.currentCall=call
                    self.ariInterface.start_record(call.agent.bridge_id,record_name)
                    self.ariInterface.add_to_bridge(call.agent.bridge_id,call.id)
                    self.logManager.insertLogInElastic("Info",f"Dial Function In manual/redialing",call=call)
                    print("HI  PANAKJ  Callling CONNEECTED EVETN  -> ")

                    try:
                        self.EventAgentConnected(call.agent,'',call)
                    except Exception as e:
                        self.logManager.insertLogInElastic(serverty="Error Dial When status=Answer and call.type=manual/redialing",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
                    
            pass
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error Dial function",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")


    # 📤 Define a function to send a progress bar event to a web socket for a specific agent.
    def sendProgressBarEvent(self,agent_id,campaign):
        try:
            # Log the event in ElasticSearch: ℹ️
            self.logManager.insertLogInElastic("Info",f"Send ProgressBar Event {agent_id.id}",agent=agent_id,campaign=campaign)
            
            # Prepare data for sending a progress bar event to the web socket.
            print(f"++++++++++This is sendProgressBarEvent {agent_id}++++++++++")
            AgentData={
                    "event_name": "ProgressBar",  # 📊 Event name for progress bar update.
                    "event_data": {
                       "campaign_id": campaign.id,  # 🆔 ID of the campaign.
                       "total": campaign.total,  # 🎯 Total number of tasks in the campaign.
                       "done": int(campaign.total) - int(len(campaign.data)) - int(campaign.Invalid),  # ✅ Number of tasks completed.
                       "left": len(campaign.data)  # ⏳ Number of tasks remaining.
                    }
                   }
            
            # Send the formatted event data to the web socket for the specified agent: 📤
            self.socket.send_event_to_web(str(agent_id.id),AgentData)

        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error sendProgressBarEvent function",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")



    # 🚪 Define a function to handle events when an agent logs in.
    def EventAgentLogin(self,agent,campaign):
        try:
            # Set agent status to "FREE" upon login: 🔓
            agent.agent_status = "FREE"

            # Extract and format login time for logging purposes: ⏰
            logintime = datetime.datetime.strptime(agent.logintime, "%Y-%m-%d %H:%M:%S")

            # Log the event in ElasticSearch: ℹ️
            self.logManager.print_dialer_log("EventManager",f"LoggedIN Agent  ==>  CampaignDeatils:=> Active_number {campaign.activeNumbers} , Available Agent :{campaign.availableAgent}")
            self.logManager.insertLogInElastic("Info",f"Send LoggedIn Event",agent=agent,campaign=campaign)

            # Prepare data for sending a "Logged In" event to the web socket.
            EventDatas = {
            "agent_id": agent.id,  # 🆔 Agent's unique identifier.
            "total_break_time": agent.total_break_time,  # ⏸️ Total break time taken by the agent.
            "agent_status": agent.agent_status,  # ⚡ Current status of the agent (e.g., FREE).
            "answer_calls": agent.answer_calls,  # 📞 Number of calls answered by the agent.
            "last_connected_number": agent.last_connected_number,  # 📞 Last connected number by the agent.
            "agent_name": agent.name,  # 👤 Name of the agent.
            "caller_number": agent.caller_number,  # 📞 Caller number associated with the agent.
            "campaign_id": agent.dialer_campaign,  # 📞 ID of the campaign associated with the agent.
            "campaign_name": campaign.campaign_name,  # 📞 Name of the campaign associated with the agent.
            "failed_calls": agent.failed_calls,  # 📞 Number of failed calls handled by the agent.
            "first_login_time": agent.first_login_time,  # 🕒 Time of agent's first login.
            "channel_id": agent.channel_id,  # 🆔 ID of the communication channel used by the agent.
            "name": agent.name,  # 👤 Name of the agent.
            "number": agent.mobile,  # 📱 Mobile number of the agent.
            "server_id": server_id,  # 🖥️ ID of the server.
            "total_hold_duration": agent.total_hold_duration,  # ⏳ Total duration the agent has put calls on hold.
            "total_oncall_duration": agent.total_oncall_duration,  # ⏳ Total duration the agent has been on calls.
            "wrapup_time": campaign.wrapup_time,  # 🕒 Wrap-up time configured for the campaign.
            "pacing_time": campaign.pacing_time,  # ⏰ Pacing time configured for the campaign.
            "dialer_type": agent.dialer_type,  # 📞 Type of dialer used by the agent.
            "total_login_time": (datetime.datetime.now() - logintime).total_seconds(),  # ⏱️ Total time since agent's login.
            "total_pacing_time": agent.total_onpacing_duration,  # ⏰ Total pacing time used by the agent.
            "total_wrapup_time": agent.total_onwrapup_duration  # ⏱️ Total wrap-up time used by the agent.
            }

            # Prepare the complete event data for sending to the web socket:
            AgentData={
                    "event_name": "LoggedIn",  # 🚪 Event name for agent login.
                    "event_data": EventDatas # 📊 Detailed event data.
            }

            # Send the formatted event data to the web socket for the specified agent: 📤
            self.socket.send_event_to_web(str(agent.id),AgentData)
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error EventAgentLogin function",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
    
    def EventAgentLoggedOut(self,agent,campaign):
        try:
            self.logManager.print_dialer_log("EventManager",f"LoggedOut Agent  ==>  CampaignDeatils:=> Active_number {campaign.activeNumbers} , Available Agent :{campaign.availableAgent}")
            agent.agent_login_status = "LoggedOut"
            
            logintime = datetime.datetime.strptime(agent.logintime, "%Y-%m-%d %H:%M:%S")
            self.logManager.insertLogInElastic("Info",f"Send LoggedOut Event",agent=agent,campaign=campaign)
            EventDatas={"agent_id":agent.id,"total_break_time":agent.total_break_time,"agent_login_status":agent.agent_login_status,"last_connected_number":agent.last_connected_number,"agent_status":agent.agent_login_status,"agent_name":agent.name,"answer_calls":agent.answer_calls,"caller_number":agent.caller_number,"total_login_time": (datetime.datetime.now() - logintime).total_seconds(),"number": agent.mobile,"total_pacing_time":agent.total_onpacing_duration,"total_wrapup_time":agent.total_onwrapup_duration,"total_oncall_duration":agent.total_oncall_duration}

            AgentData={
                    "event_name": "LoggedOut",
                    "event_data": EventDatas
            }
            self.socket.send_event_to_web(str(agent.id),AgentData)
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error EventAgentLoggedOut function",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
    

    def EventAgentDisConnected_Answer(self,agent,call,campaign_name,detail_data):
        try:
            print("Hey I am eventagentdisconnected_answer()...............")
            agent.agent_status = "On WrapUp"
            logintime = datetime.datetime.strptime(agent.logintime, "%Y-%m-%d %H:%M:%S")
            agent.total_oncall_duration = int(agent.total_oncall_duration) + int(call.call_duration)
            self.logManager.insertLogInElastic("Info",f"Send Disconnected_Answer Event",agent=agent,call=call)
            EventDatas={"agent_id":agent.id,"caller_status":"DisConnected_Answer","total_break_time":agent.total_break_time,"agent_name":agent.name,"agent_status":agent.agent_status,"caller_number":agent.caller_number,"last_connected_number":agent.last_connected_number,"call_duration":call.call_duration,"total_oncall_duration":agent.total_oncall_duration,"answer_calls":agent.answer_calls,"first_login_time":agent.first_login_time,"total_hold_duration":agent.total_hold_duration,"agent_login_status": agent.agent_login_status,"campaign_type":"Predictive","dialer_type":agent.dialer_type,"disconnected_by":call.DisconnectedBy,"number": agent.mobile ,"total_login_time": (datetime.datetime.now() - logintime).total_seconds() ,"total_wrapup_time":agent.total_onwrapup_duration,"campaign_name":campaign_name,"campaign_data":{"campaign_data": detail_data}}
            AgentData = {
                "event_name": "DisConnected_Answer",
                "event_data": EventDatas
            }            
            self.socket.send_event_to_web(str(agent.id),AgentData)
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error EventAgentDisConnecte_Anwer Function",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
    
    def EventAgentConnected(self,agent,campaign,call):
        try:
            self.logManager.insertLogInElastic("Info",f"Event Agent Connected",agent=agent,campaign=campaign,call=call)
            agent.agent_status = "On Call"
            logintime = datetime.datetime.strptime(agent.logintime, "%Y-%m-%d %H:%M:%S")
            EventDatas={"agent_id": agent.id,"channel_id":agent.channel_id,"total_break_time":agent.total_break_time,"agent_name":agent.name,"answer_calls":agent.answer_calls,"last_connected_number":agent.last_connected_number,"caller_status":call.status,"caller_number":agent.caller_number,"agent_status":"On Call","total_oncall_duration":agent.total_oncall_duration,"first_login_time":agent.first_login_time,"total_hold_duration":agent.total_hold_duration,"agent_login_status": "LoggedIn" ,"dialer_type":agent.dialer_type,"number": agent.mobile,"total_login_time": (datetime.datetime.now() - logintime).total_seconds(),"total_wrapup_time":agent.total_onwrapup_duration}
            print(f"calller type -- {call.type}")
            if call.type in ["manual_caller", "redialing"]:
                print("IN manual Agent Dialer -----------------------|------------------------|--------------")
                EventDatas['dialer_type']  = call.type
                AgentData={
                     #"event": "dialer_user_"+str(agent.id),
                         "event_name": "CONNECTED",
                         "event_data": EventDatas,
                 }
            else:
                EventDatas['campaign_name']  = campaign.campaign_name
                EventDatas['campaign_type']  = campaign.campaign_type
                AgentData={
                         "event_name": "CONNECTED",
                         "event_data": EventDatas,
                         "campaign_data":call.detail_data
                 }
            print(f"PANAKJ MANUAL AGENT DATA :: {AgentData}")
            self.socket.send_event_to_web(str(agent.id),AgentData)
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error EventAgentConnected Function",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
     
     
    def EventAgentDisConnected_Failed(self,call,campaign_name,dialer_type,caller_number,campaign_type,campaign=None):
        try:
            self.logManager.insertLogInElastic("Info",f"Send Disconneted_Faild Event",campaign=campaign,call=call) 
            EventDatas = {"agent_status": "DisConnected_Failed","caller_status":call.status,"dialer_type":dialer_type,"campaign_name":campaign_name,"caller_number":caller_number,"campaign_type":campaign_type}
            
            AgentData={
                     "event_name": "DisConnected_Failed",
                     "event_data": EventDatas,
             }
            
            if call.type in ["manual_caller", "redialing"]:
                self.socket.send_event_to_web(str(call.agent.id),AgentData)
            else:
                print(f"++++++++++++Parent Socket Id {str(call.detail_data['user_id'])}+++++++++++")
                agent_ids = campaign.getAllableAgent()
                self.socket.send_event_to_web(str(call.detail_data['user_id']),AgentData)
                print(f"++++++++++++agent_user_events+++++++++++{agent_ids}++++++++++")
                self.socket.send_user_agent_events(agent_ids,AgentData)
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error EventAgentDisConnected_Failed Function",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
    
    
    #Hanlde  Free Event 
    def EventAgentFree(self,agent,campaign_name,campaign_type,campaign):
        try:
            logintime = datetime.datetime.strptime(agent.logintime, "%Y-%m-%d %H:%M:%S")
            call=self.callManager.getCall("EventAgentFree",agent.currentCall.id)
            self.logManager.print_dialer_log("EventManager",f"EventAgentFree :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
            self.logManager.insertLogInElastic("Info",f"Send FREE Event",agent=agent,campaign=campaign)
            EventDatas={"agent_id":agent.id, "agent_status":"FREE","agent_name":agent.name,"total_break_time":agent.total_break_time,"number": agent.mobile,"answer_calls":agent.answer_calls,"last_connected_number":agent.last_connected_number, "total_login_time": (datetime.datetime.now() - logintime).total_seconds(),"total_pacing_time":agent.total_onpacing_duration,"total_wrapup_time":agent.total_onwrapup_duration ,"total_oncall_duration":agent.total_oncall_duration,"dialer_type":call.type,"campaign_name":campaign_name,"campaign_type":campaign_type}
          
            AgentData={
                    "event_name": "FREE",
                    "event_data": EventDatas
            }
            self.socket.send_event_to_web(str(agent.id),AgentData)
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error EventAgentFree Function",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")
    
    #Sending UnHold Event to user and agent both....
    def EventAgentUnhold(self,agent,campaign):
        try:
            self.logManager.insertLogInElastic("Info",f"Send Hold Event",agent=agent,campaign=campaign)
            logintime = datetime.datetime.strptime(agent.logintime, "%Y-%m-%d %H:%M:%S")
            EventDatas={"agent_id":agent.id, "agent_status":"On Call","caller_number":agent.caller_number,"total_break_time":agent.total_break_time,"last_connected_number":agent.last_connected_number,"caller_status": "On Call","answer_calls":agent.answer_calls,"agent_name":agent.name,"number": agent.mobile,"total_login_time": str(datetime.datetime.now() - logintime),"total_pacing_time":agent.total_onpacing_duration,"total_wrapup_time":agent.total_onwrapup_duration}
            call=self.callManager.getCall("EventUnhold",agent.currentCall.id)
            self.logManager.print_dialer_log("EventManager",f"EventAgentUnhold :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
            if call.type in ["manual_caller", "redialing"]:
                EventDatas['dialer_type']  = call.type
            else:
                EventDatas['campaign_name']  = campaign.campaign_name
                EventDatas['campaign_type']  = campaign.campaign_type

            AgentData={
                    "event_name": "UNHOLD",
                    "event_data": EventDatas
            }

            self.socket.send_event_to_web(str(agent.id),AgentData)
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error EventAgentUnhold Function",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")


    def EventAgentHold(self,agent,campaign):
        try:
            self.logManager.insertLogInElastic("Info",f"Send Hold Event",agent=agent,campaign=campaign)
            logintime = datetime.datetime.strptime(agent.logintime, "%Y-%m-%d %H:%M:%S")
            EventDatas={"agent_id":agent.id, "agent_status":"ON HOLD","caller_number":agent.caller_number,"total_break_time":agent.total_break_time,"last_connected_number":agent.last_connected_number,"caller_status": "ON HOLD","answer_calls":agent.answer_calls,"agent_name":agent.name,"number": agent.mobile,"total_login_time": str(datetime.datetime.now() - logintime),"total_pacing_time":agent.total_onpacing_duration,"total_wrapup_time":agent.total_onwrapup_duration}
            call=self.callManager.getCall("EventHOld",agent.currentCall.id)
            self.logManager.print_dialer_log("EventManager",f"EventAgentHold :: PANKAJ CALL OBJECT ==> call_object: {call} ==  call_str: {str(call)}")
            if call.type in ["manual_caller", "redialing"]:
                EventDatas['dialer_type']  = call.type
            else:
                EventDatas['campaign_name']  = campaign.campaign_name
                EventDatas['campaign_type']  = campaign.campaign_type

            AgentData={
                    "event_name": "HOLD",
                    "event_data": EventDatas
            }
            
            self.socket.send_event_to_web(str(agent.id),AgentData)    
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error EventAgentHold",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")


    def sendCallingEvent(self,number,call):
        try:
            time.sleep(1)
            self.logManager.print_dialer_log("EventManager", f"sendCallingEvent function  ::  Number:{number} ,Call_object :{call} , call_details_data:{vars(call)}")
            EventDatas={"caller_status":call.status,"caller_number":number,"agent_status":"FREE"}
            agent_ids = {}
            
            if call.type in ["manual_caller", "redialing"]:
                EventDatas['dialer_type']  = call.type
                EventDatas['agent_name']  = call.agent.name
            else:
                if hasattr(call.campaign,"campaign_name"):
                    EventDatas['campaign_name']  = call.campaign.campaign_name
                    EventDatas['campaign_type']  = call.campaign.campaign_type
                    agent_ids = call.campaign.getAllableAgent()
            AgentData={
                     "event_name": "DIALLING",
                     "event_data": EventDatas,
             }
    
            if call.type in ["manual_caller", "redialing"]:
                self.socket.send_event_to_web(str(call.agent.id),AgentData)
            else:
                self.socket.send_event_to_web(str(call.detail_data['user_id']),AgentData)
                self.socket.send_user_agent_events(agent_ids,AgentData)
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Error sendCallingEvent",message=f"Error:{e} , Detail_error: {traceback.format_exc()}")


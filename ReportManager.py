import time 
import requests
import traceback
from confluent_kafka import Producer
import json
import datetime
from GoogleDriveUploader import GoogleDriveUploader
import os
import sys
from pathlib import Path

#=====================================globle_path===============================================
# Determine the absolute path of the directory containing this script
globle_path = Path(__file__).parent.absolute()
# Construct the absolute path to the 'Web' directory
scripts_dir = os.path.abspath(os.path.join(globle_path, '..', 'Web'))
# print(f"Hey this is path+++++++++++{scripts_dir}++++++")  # 📄 Print the absolute path to 'Web' directory

sys.path.insert(0, os.path.join(scripts_dir,'local_connection'))

from credentials import *

##this class manage all Agent Reports

class ReportManager:
     
     def __init__(self,logManager):
        self.logManager = logManager
        print("I am Report Manager Is start  -- , ")

     #function to push report in kafka || to store report in Non volatile storage
     def SendReportDataKafka(self,call,campaign_name,campaign_type,user_id,agent=None):
        try:
            print("Hey I am SendReportDataKafka() function inside ReportManager file............")
            
            if agent is not None:
                agent_id = agent.id
            else:
                agent_id = user_id
            if agent_id != user_id:
                call.status = "ANSWER"
                one = {**vars(call),'agent_id':agent_id,'total_session_time':agent.total_session_time,'last_extension':'0',"campaign_name":campaign_name,"last_wrapup_time":"0","campaign_type":campaign_type}
            else:
                one = {**vars(call),'agent_id':agent_id,"campaign_name":campaign_name,"campaign_type":campaign_type,'total_session_time':0,'last_wrapup_time':0,'last_extension':'0','hold_time':0}
                del one['campaign']
            if 'agent' in one: del one['agent']
            if 'campaign' in one: del one['campaign']
            one['call_disconnect_time']=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            report_data= json.dumps(one).encode('utf-8')
            topic=f'sequential_autodialer_report_H_{env}'
            p = KafkaDictP['predictive_dialer']
            p.poll(0)
            p.produce(topic,report_data)
            p.flush()
            self.logManager.insertLogInElastic(serverty="Info - Report Start",message=f"{topic} == {report_data}")
            
            print(" Produced :: In Topic :: "+ str(topic)+" Data :: "+str(report_data))
            self.logManager.insertLogInElastic(serverty="Info - Report Stop",message=f"{topic} ==  {report_data}")
            print(" End of SendReportDataKafka() .........................................")
        except Exception as e:
            self.logManager.insertLogInElastic(serverty="Report Error",message=f"{topic} ==  {report_data}")
     




     #function to push report in kafka || to store report in Non volatile storage
     def ManualDialerReport(self,call=None,agent=None,campaign=None):
        try:
            self.logManager.print_dialer_log("ReportManager", f"Hey I am ManualDialerReport() function inside ReportManager file Call==>{vars(call)} ,  Agent==>{vars(agent)} , Campaign==> {vars(call.campaign)}")
            recording_url = "NA"
            data_obj = time.time()
            current_time = datetime.datetime.fromtimestamp(data_obj).strftime('%Y-%m-%d %H:%M:%S')
            if call.status == 'ANSWER':
                recording_url = f"https://wab.nx4.in/wab_chat_media/1_{call.record_name}.wav"
                one = {"UNIQUEID":call.id,"start_time":call.start_time,"ANSWEREDTIME":call.call_duration,"DIALSTATUS":call.status,"exact_src":agent.dedicated_number,"to_number":call.number,"dlurl":"NA","user_id":agent.main_user,"current_time":current_time,"recording_url":recording_url,"link_url":recording_url,"is_masking":campaign.hide_from_agent,"end_time":call.end_time,"ring_time":call.Time_PROGRESS_Start,"hangup_by":call.DisconnectedBy,"talk_time":call.call_duration,"max_second":0,"masked_caller_id":agent.dedicated_number}
            else:
                one = {"UNIQUEID":call.id,"start_time":"NA","ANSWEREDTIME":call.call_duration,"DIALSTATUS":call.status,"exact_src":agent.dedicated_number,"to_number":call.number,"dlurl":"NA","user_id":agent.main_user,"current_time":current_time,"recording_url":recording_url,"link_url":recording_url,"is_masking":campaign.hide_from_agent,"end_time":"NA","ring_time":call.Time_PROGRESS_Start,"hangup_by":call.DisconnectedBy,"talk_time":call.call_duration,"max_second":0,"masked_caller_id":agent.dedicated_number}

            report_data= json.dumps(one).encode('utf-8')
            topic=f'outbound_report_{env}'
            p = KafkaDictP['predictive_dialer']
            p.poll(0)
            p.produce(topic,report_data)
            p.flush()

            self.logManager.print_dialer_log("ReportManager", f"Produced Manual Dialer Report :: In Topic :: "+ str(topic)+" Data :: "+str(report_data))
        except Exception as e:
            self.logManager.print_dialer_log("ReportManager", f"Error occured during produce manual dialer report {e} Detail_Error=> {traceback.format_exc()}")
 







     #Insert data in agent login history
     def insertAgentLoginStatus(self,agent,login_time):
            url = f"{ES_URL}/agent_login_histories_version1/_doc"
            payload = json.dumps({"user_id": agent.parent, "agent_id": agent.id, "campaign_id": agent.campaign.id, "agent_login_time":login_time, "agent_logout_time":'0',"type":'Predictive',"created_at":time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time()))})
            headers = {
              'Content-Type': 'application/json'
            }
            response = requests.request("POST", url, headers=headers, data=payload)
            print("Elastic Search Response => "+str(response.text))
            elastic_doc_id=json.loads(response.text)['_id'] #update elastic_doc_id in agent object 
            agent.elastic_doc_id = elastic_doc_id
     
     def updateAgentLoginStatus(self,agent,logout_time):
         try:
             if str(agent.elastic_doc_id) == "":
                 return
             url = f"{ES_URL}/agent_login_histories_version1/_update_by_query?refresh=true"
             updation_query = json.dumps({
                "query": {
                  "bool": {
                    "must": [
                      {
                        "term": {
                          "_id": str(agent.elastic_doc_id)
                        }
                      }
                    ]
                  }
                },
                "script": {
                  "source": f"ctx._source.agent_logout_time = "+ str(logout_time)+ ";"
                }
              })
             headers = {
             'Content-Type': 'application/json'
             }
             print(updation_query)
             response = requests.request("POST", url, headers=headers, data=updation_query)
             response_data = json.loads(response.text)
             print(f"Response From Elastic Update -- {response_data}")
         except Exception as e:
             print(f"Error in Updaitng report --- {e}")
     
     def createTimeline(self,agent_id,mobile,call_status,call_duration,recording="NA"):
         report_data = json.dumps({"agent_id":agent_id,"mobile":mobile,"call_status":call_status,"recording":recording,"call_duration":call_duration})
         topic = f"timeline_history_{env}"
         p = KafkaDictP['predictive_dialer']
         p.poll(0)
         p.produce(topic,report_data)
         p.flush()
         print("+++++++++++++++++++++ Produced :: In Topic :: "+ str(topic)+" Data :: "+str(report_data))

     def uploadRecording(self,record_name):
         topic=f'drive_upload_{env}'
         
         report_data = json.dumps({"record_name":record_name})
         p = KafkaDictP['predictive_dialer']
         p.poll(0)
         p.produce(topic,report_data)
         p.flush()
         print("+++++++++++++++++++++ Produced :: In Topic :: "+ str(topic)+" Data :: "+str(report_data))
         print("Hey this is uploadRecording function...")
        
         url = f"{API_URL}sendWabChatMedia?file"

         payload = {}
         files=[
           ('file',(f'{record_name}.wav',open('/var/spool/asterisk/recording/etc/asterisk_operations/recordings/'+str(record_name)+'.wav', 'rb'),'audio/wav'))
         ]
         headers = {
           'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjEsInVzZXJuYW1lIjoiY3Nfc2hpdmFuaSIsIm1haW5fdXNlciI6MSwiaWF0IjoxNzE1MDY5NDE0fQ.rNbs3v-5ysKp-KLWT-bPXNSUAFRcdaG1HwHLU9r3sCU'
         }
         
         response = requests.request("POST", url, headers=headers, data=payload, files=files)
         print(f"hi PANAJK RECORDING UPLOADED  -- {response.text}")
         return response.text 


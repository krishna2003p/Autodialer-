import redis  # 🗝️ Import Redis client library
import time  # ⏱️ Import time module for time-related functions
import os
import sys
from pathlib import Path
import json
#=====================================globle_path===============================================
# Determine the absolute path of the directory containing this script
globle_path = Path(__file__).parent.absolute()
# Construct the absolute path to the 'Web' directory
scripts_dir = os.path.abspath(os.path.join(globle_path, '..', 'Web'))
# print(f"Hey this is path+++++++++++{scripts_dir}++++++")  # 📄 Print the absolute path to 'Web' directory

sys.path.insert(0, os.path.join(scripts_dir,'local_connection'))

from credentials import *

class Agent:
    # Redis_Obj = redis_connection = redis.StrictRedis(
    #                                      host="182.18.144.40",
    #                                      port=9023,
    #                                      password="vnfkjdof90s9820"
    #                                  )
    #redis.StrictRedis(host="182.18.144.40",username=f'default',port=9023, password="vnfkjdpf90s9820") 
    def __init__(self, agent_datas):
        """
        Initialize an Agent object.

        Args:
        - agent_datas (dict): Dictionary containing agent data to initialize instance variables.

        """
        print("PRINT FROM AGENT --- ", agent_datas)
        
        # Set instance variables dynamically from agent_datas
        for instance_variable in agent_datas:
            setattr(self, instance_variable, agent_datas[instance_variable])
        post_call_url = f"{ES_URL}/post_call_analysis_version1/_search"
        post_call_analysis = payload = json.dumps({ "query": { "term": { "agent_id": self.id } }, "aggs": { "total_hold_time": { "sum": { "field": "hold_time" } }, "answered_call_count": { "filter": { "bool": { "must_not": { "term": { "call_status": "NOANSWER" } } } } }, "total_answer_time": { "sum": { "field": "answer_time" } } }, "size": 0 })
        headers = { 'Content-Type': 'application/json' }
        post_call_analysis_response = requests.request("POST", post_call_url, headers=headers, data=payload)
        post_call_analysis_json = json.loads(post_call_analysis_response.text)
        # Extracting data with None checks
        total_hold_time = post_call_analysis_json['aggregations'].get('total_hold_time', {}).get('value')
        answered_call_count = post_call_analysis_json['aggregations'].get('answered_call_count', {}).get('doc_count')
        total_answer_time = post_call_analysis_json['aggregations'].get('total_answer_time', {}).get('value')
        

        agent_login_history_url = f"{ES_URL}/agent_login_histories_version1/_search"
        payload = json.dumps({ "size": 1, "query": { "bool": { "must": [ { "match": { "agent_id": self.id } }, { "range": { "created_at": { "gte": "now/d", "lte": "now/d" } } } ] } }, "sort": [ { "agent_login_time": { "order": "asc" } } ] })
        response = requests.request("POST", agent_login_history_url, headers=headers, data=payload)
        response_agent_first_login_time = json.loads(response.text)
        if response_agent_first_login_time['hits']['hits']:
            agent_first_login_time =  response_agent_first_login_time['hits']['hits'][0]['_source']['agent_login_time']
            print(agent_first_login_time)
            agent_first_login_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(agent_first_login_time))
        else:
            agent_first_login_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))

        last_payload = json.dumps({ "query": { "bool": { "filter": [ { "term": { "agent_id": self.id } }, { "term": { "call_status": "answer" } } ] } }, "sort": [ { "created_at": { "order": "desc" } } ], "size": 1 })   
        last_response = requests.request("GET", post_call_url, headers=headers, data=last_payload)
        last_res_json = json.loads(last_response.text)
        print(f"LAST -- {last_payload} -- {last_res_json}")
        agent_last_connected_number = "N/A"
        if last_res_json['hits']['hits']:
            agent_last_connected_number  =  last_res_json['hits']['hits'][0]['_source']['customer_number']
        
        agent_login_payload = json.dumps({ "size": 1, "query": { "bool": { "must": [ { "match": { "agent_id": self.id } } ] } }, "sort": [ { "agent_login_time": { "order": "desc" } } ], "size": 1  })
        response = requests.request("POST", agent_login_history_url, headers=headers, data=agent_login_payload)
        response_agent_login = json.loads(response.text)
        agent_status = "LoggedOut"
        agent_login_status = "LoggedOut"
        if response_agent_first_login_time['hits']['hits']:
            agent_loggedout_time =  response_agent_login['hits']['hits'][0]['_source']['agent_logout_time']
            if agent_loggedout_time == '0':
                agent_status = "FREE"
                agent_login_status = "LoggedIn"



        # Set default values for additional instance variables
        self.agent_status = agent_status
        self.start_wraping = 0
        selfcurrentCampaign = 0
        self.start_pacing = ""
        self.channel_id = 0
        self.answer_calls = int(answered_call_count)
        self.last_connected_number = agent_last_connected_number
        self.total_break_time = 'NA'
        self.caller_number = 'NA'
        self.failed_calls = 0
        self.total_login_time = 0
        self.total_onwrapup_duration = 0
        self.total_onpacing_duration = 0
        self.total_break_duration = 0
        self.first_login_time = agent_first_login_time  #time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        self.last_logout_session = 'NA'
        self.total_hold_duration = int(total_hold_time)
        self.total_oncall_duration = int(total_answer_time)
        self.total_session_time = 0
        self.last_wrapup_time = 0
        self.logintime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
        self.elastic_doc_id = ''
        self.dialer_type = 'autodialer'
        self.call_type = 'autodialer'
        self.agent_login_status = agent_login_status
        
    def __str__(self):
        """
        Return a string representation of the Agent object.
        """
        data = json.dumps({ 'id': self.id,'agent_login_status':self.agent_login_status,'answer_calls':self.answer_calls,'last_connected_number':self.last_connected_number,'dialer_type':self.dialer_type,'call_type':self.call_type,'agent_status': self.agent_status,'status': self.status, 'extension': self.extension })
        return data

    def getMobile(self):
        """
        Return the mobile number of the agent.
        """
        return self.number

    def updateStatus(self, status):
        """
        Update the agent status in the object.

        Args:
        - status (str): New status to update.
        """
        # 🔄 Placeholder function; actual implementation depends on specific requirements.
        pass

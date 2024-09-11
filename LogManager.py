import time
import requests
from confluent_kafka import Producer
import json
import traceback
import sys
import os
from pathlib import Path
filename = os.path.splitext(os.path.basename(__file__))[0]
print(f"I AM {filename}")

#=====================================globle_path===============================================
globle_path = Path(__file__).parent.absolute()
scripts_dir = os.path.abspath(os.path.join(globle_path, '..', 'Web'))

sys.path.insert(0, os.path.join(scripts_dir,'local_connection'))

from credentials import *


# Logging system
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


log_file = Path(log_dir) / f'{Path(__file__).stem}.log'
log_formatter = logging.Formatter(fmt='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(log_file, maxBytes=50048576, backupCount=1000)
handler.setFormatter(log_formatter)
handler.setLevel(logging.INFO)
logger.addHandler(handler)


##this class manage all Logs 
class LogManager:
     def __init__(self):
        print("I am Log Manager , Started ")
        self.producer_conf = Producer({'bootstrap.servers': '182.18.144.40:9030'})
     
     # Function to print and dump logs
     def print_dialer_log(self,file_name,msg, level=logging.INFO, log_to_file=True):
         """
         Logs and prints the given message.
     
         Parameters:
         - filename: from which file this log dump
         - msg: The message to be logged and printed.
         - level: The logging level (default: logging.INFO).
         - log_to_file: Whether to log the message to a file (default: True).
         """
         # Print he message to console
         print(f"|> {file_name} ::  {msg}")
     
         # Log the message
         if log_to_file:
             logger.log(level, f"[{file_name} - {level} ]  =>  {msg}")
             #logger.log(level, f"{filename} :::  {msg_info}")
         
     def insertLogInElastic(self,serverty,message,agent=None,call=None,campaign=None,command_data=None,report_data=None):
         try:
            current_time = datetime.datetime.now().isoformat()
            #Handle all logs and insert in elasticsearch accordingly object data
            call_data = agent_data = campaign_data = {}
            if call is None:
                if hasattr(agent, 'currentCall'):
                    call = agent.currentCall
            if call is not  None:
                call_data = json.loads(str(call)) if call else None
            
            if agent is None:
                if call and hasattr(call, 'agent'):
                    agent = call.agent
                    
            if agent is not None:
                agent_data = json.loads(str(agent)) if agent else None
            

            if campaign is None:
                if call and hasattr(call, 'campaign'):
                     campaign = call.campaign
                elif agent  and hasattr(agent, 'campaign'):
                     campaign = agent.campaign    
                    
            if campaign is not None:
                campaign_data = json.loads(str(campaign)) if campaign else None
            if report_data is not None:
                report_data = json.loads(report_data)
            else:
                report_data = {}
            if command_data is not None:
                command_data  = json.loads(command_data)
            else:
                command_data = {}

            log_data = {"serverty":serverty,"message":message,"call_data":call_data,"agent_data":agent_data,"campaign_data":campaign_data,"report_data":report_data,"command_data":command_data,"current_time":current_time}
            self.print_dialer_log(filename,f"LOG DATA -- {log_data}")
            report_data= json.dumps(log_data).encode('utf-8')
            topic=f'predictive_dialer_log_{env}'
            self.producer_conf.poll(0)
            self.producer_conf.produce(topic,report_data)
            self.producer_conf.flush()
            self.print_dialer_log(filename,f"Produced :: In Topic :: {topic} :: {log_data}")
         except Exception as e:
            self.print_dialer_log(filename,f"Error in Log Publish -- {e}  == {traceback.format_exc()}", level=logging.ERROR) 
         
         
     



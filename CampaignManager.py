import json
import elasticsearch.helpers
from elasticsearch import Elasticsearch
import requests
import traceback
import Campaign
import sys 
from pathlib import Path  # 📁 Import Path class from pathlib module for working with file paths
import os

#=====================================globle_path===============================================
# Determine the absolute path of the directory containing this script
globle_path = Path(__file__).parent.absolute()
# Construct the absolute path to the 'Web' directory
scripts_dir = os.path.abspath(os.path.join(globle_path, '..', 'Web'))
print(scripts_dir)  # 📄 Print the absolute path to 'Web' directory

sys.path.insert(0, os.path.join(scripts_dir,'local_connection'))

from credentials import *

class CampaignManager:
    CampaignsById={}
    CampaignByNumber={}
    def __init__(self,logManager):
        self.logManager = logManager
        pass
    # def register(self,campaign):
    #     if not campaign.getId() in self.CampaignsById.keys():
    #         self.CampaignsById[campaign.getId()]=campaign
    # def unregister(self,campaign):
    #     if campaign.getId() in self.CampaignsById.keys():
    #         del self.CampaignsById[campaign.getId()]
    def setCampaignByNumber(self,number,campaign):
        try:
            self.CampaignByNumber[number]=campaign
            self.logManager.print_dialer_log("CampaignManager",f"setCampaignByNumber function +++++++++number::{number}++campaign::{campaign}++")
        except Exception as e:
            self.logManager.print_dialer_log("CampaignManager",f"Error in setCampaignByNumber {e}")
    
    def getCampaignByNumber(self,number):
        try:
            return self.CampaignByNumber[number]
        except Exception as e:
            self.logManager.print_dialer_log("CampaignManager",f"Error in getCampaignByNumber {e}")

    def getCampaign(self,cid):
        try:
            self.logManager.print_dialer_log("CampaignManager",f"Request Campaign ID {cid}++++Store:::{self.CampaignsById.keys()}++++")
            if int(cid) in self.CampaignsById.keys():
                return self.CampaignsById[int(cid)]
            else:
                #campaign do not exists
                self.logManager.print_dialer_log("CampaignManager",f"Campaign doesn't exists. Getting from Elastic.")
                #Get data from elastic
                payload = json.dumps({
                "from": 0,
                "size": 1,
                "query": {
                    "bool": {
                    "must": [
                        {
                        "term": {
                            "status": "queued"
                        }
                        },
                        {
                        "term": {
                            "id": str(cid)
                        }
                        }
                    ]
                    }
                }
                })
                index = "autodialer_entries_version1"
                # ES_URL = "http://182.18.144.40:9018"
                url = f"{ES_URL}/"+index+"/_search"
                headers = { 'Content-Type': 'application/json' }
                self.logManager.print_dialer_log("CampaignManager",f"Payload In CampaignManager:: {payload}")

                response = requests.request("POST", url, headers=headers, data=payload)
                # Parse the JSON response
                response_data = json.loads(response.text)

                # Extract ID and entire campaign data mappings
                self.logManager.print_dialer_log("CampaignManager",f"Response_data In CampaignManager:: {response_data}")
                campaign_data = None
                for hit in response_data['hits']['hits']:
                    entry_id = hit['_source']['id']
                    campaign_data = hit['_source']  # Entire campaign data 
                if campaign_data is None:
                    return
                campaign=Campaign.Campaign(campaign_data)
                campaign.availableAgent=[]
                campaign.activeCalls=0
                campaign.activeNumbers=[]

                # Get Detail Data from Elastic 
                #payload = json.dumps({"from": 0,"size": 100000, "query": {"bool": {"must": [{"term": {"agent_id": 42610}},{"term": {"dialer_entry_id": 8742}}]}}})
                payload = json.dumps({"from": 0,"size": 100000, "query": {"bool": {"must": [{"term": {"dialer_entry_id": cid}},{"term": {"call_status": "pending"}}]}}})
                print(payload)
                index = "autodialer_details_version1"
                #ES_URL = "http://182.18.144.42:9045"
                # ES_URL = "http://182.18.144.40:9018"
                url = f"{ES_URL}/"+index+"/_search"
                headers = { 'Content-Type': 'application/json' }
                response = requests.request("POST", url, headers=headers, data=payload)
                # Parse the JSON response
                response_data = json.loads(response.text)
                detail_data=[]
                for hit in response_data['hits']['hits']:
                    detail_data.append(hit['_source'])
                campaign.data=detail_data
                self.CampaignsById[entry_id] = campaign
                return campaign
        except Exception as e:
            self.logManager.print_dialer_log("CampaignManager",f"Error in getCampaign {e}+++++++++++++Details Error:: {traceback.print_exc()}")
            print(e)
            print(traceback.print_exc())

        

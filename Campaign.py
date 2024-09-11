import sys
import json

class Campaign:
    def __init__(self,campaign_datas):
            self.blacklist=[]
            print("campaign Data: "+str(campaign_datas))
            for column_name in campaign_datas:
                setattr(self,column_name, campaign_datas[column_name])
            return
    #this function is use when we print campaign object 
    def __str__(self):
        data =  json.dumps({'id':self.id,'activeNumbers':self.activeNumbers})
        return data
    
    #for retrun campaign id
    def getId(self):
        return self.id
    def getCampaignData(cid):
        return
    
    #for add agent object in available Agent when agent on autodialer mode
    def addAvailableAgent(self,agent):
        print("Add Available list agent id "+str(agent.id))
        if agent.dialer_type == 'autodialer':
            self.availableAgent.append(agent)
        else:
            print("Agent Is on manual dialer")
        print(str(self.id)+ " Adding Agent to Available Agents List After "+str(self.availableAgent))
        return
    
    #get available agent  list
    def getAvailableAgent(self):
        print(str(self.id)+ "GET AVAILABALE -- Checking Available Agents "+str(self.availableAgent))
        for one in self.availableAgent:
            print("All Available agent id "+str(one.id))
        if len(self.availableAgent) > 0:
            return self.availableAgent.pop(0)
        else:
             return ""
    
    def getAllableAgent(self):
        print(str(self.id)+ "GET ALL AGENT -- Checking Available Agents "+str(self.availableAgent))
        if len(self.availableAgent) > 0:
            return self.availableAgent
        else:
             return ""
    
    #remove agent from available agent || if agent connected and switch to manual agent transfer and logedout
    def removeAvailableAgent(self,agent):
        try:
            print(str(self.id)+ "Remove Available Agents List Before "+str(self.availableAgent))
            if self.availableAgent:
                if agent in self.availableAgent:
                    self.availableAgent.remove(agent)    
            else:
                print("Available Agent Allready Empty")
            print(str(self.id)+ "Remove Available Agents List After "+str(self.availableAgent))
        except Exception as e:
            print(f"Error in Remove Agent :: {self.id}")
        return
    
    #
    def getRequiredCallCount(self):
         #no_of_available_agent=self.availableAgent.count()
         new_calls=0
         if len(self.availableAgent) > 0:
             no_of_available_agent=len(self.availableAgent)
             print("no_of_available_agent "+str(no_of_available_agent))
             #active_calls=self.activeCalls
             active_calls=len(self.activeNumbers)
             print("active_calls "+str(active_calls))
             print("call_speed "+str(self.call_speed))
             new_calls=int(int(no_of_available_agent)*int(self.call_speed))-int(active_calls)
             #new_calls=int(int(no_of_available_agent)*int(1))-int(active_calls)
             print("new_calls "+str(new_calls))
         return new_calls
    
    def getData(self):
        try:
            data=self.data.pop(0)
            self.activeNumbers.append(str(data['number']))
            return data
        except:
            return 

        #return self.data.pop(0)
    
    def reduceActiveCalls(self,number):
        if number in self.activeNumbers:
           print("ActiveNumber list before "+str(self.activeNumbers))
           self.activeNumbers.remove(number)
           print("ActiveNumber list after "+str(self.activeNumbers))
        pass
         

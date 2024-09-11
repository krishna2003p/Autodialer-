import json

class Call:
    def __init__(self,callid):
        self.id=callid
        self.type=""
        self.agent=""
        self.status=""
        self.extension=""
        self.campaign=""
        self.DisconnectedBy=""
        self.hold_time=0
        self.holdtime_start = 0
        self.call_duration = '0'
        self.hold = False
        self.mute = False
        self.number = ''
        self.detail_data = {}
        
        return
    def __str__(self):
        #data = "{'channel_id': " + str(self.id) + ", 'Type': '" + self.type + "', 'agent': '" + self.agent + "', 'status': '" + self.status + "', 'extension': '" + str(self.extension) + "'}"
        print("Hey I am __str__ function inside Call.py file.............................")
        print(f"HEY i am calll -- 'channel_id': {self.id}, 'Type': {self.type}, 'agent': {self.agent}, 'status': {self.status}, 'extension': {self.extension} ")
        data = json.dumps({ 'channel_id': self.id, 'type': self.type, 'status': self.status, 'extension': self.extension, 'DisconnectedBy':self.DisconnectedBy })

        return data


    #def __init__(self, channel_id, Type, agent, status, extension):
    #    self.channel_id = channel_id
    #    self.Type = Type
    #    self.agent = agent
    #    self.status = status
    #    self.extension = extension

    #def __str__(self):
    #    data = json.dumps({
    #        'channel_id': self.channel_id,
    #        'Type': self.Type,
    #        'agent': self.agent.to_json(),  # Serialize agent object to JSON
    #        'status': self.status,
    #        'extension': self.extension
    #    })
    #    return data


    def addExtension():
        return

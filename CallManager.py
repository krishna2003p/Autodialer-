import Call

class CallManager:
    callStore={}
    def __init__(self,logManager):
        self.logManager=logManager
        pass
    def tryDispatch(self):
        pass
    def getCall(self,whocalled,id):
        try:
            id = str(id)
            self.logManager.print_dialer_log("CallManager",f"Request1 from :: {whocalled} Finding call in call store :: {id}")
            if id in self.callStore.keys():
                return self.callStore[id]
            else:
                #ANUJ:: TODO :: This should not happen. Report
                self.logManager.print_dialer_log("CallManager",f"Request2 from :: {whocalled} call's channel id not in call store :: {id}")
                call=Call.Call(id)
                self.callStore[id]=call
                return call
        except Exception as e:
            self.logManager.print_dialer_log("CallManager",f"Request3 from :: {whocalled} id == {id} Error in getCall {e}")
        

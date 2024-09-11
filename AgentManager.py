import pymysql  # 🐍 Import MySQL connector library for database interaction
import logging as log  # 📝 Import logging library with alias 'log' for logging operations
from logging.handlers import RotatingFileHandler  # 🔄 Import RotatingFileHandler from logging.handlers for log rotation
import os  # 📂 Import os module for operating system functionalities
import sys  # 🖥️ Import sys module for system-specific parameters and functions
import datetime  # 📅 Import datetime module for date and time manipulation
from pathlib import Path  # 📁 Import Path class from pathlib module for working with file paths
import atexit  # 🚪 Import atexit module for registering cleanup functions

# Import Agent class from Agent module (assuming Agent module exists)
import Agent

#=====================================globle_path===============================================
# Determine the absolute path of the directory containing this script
globle_path = Path(__file__).parent.absolute()
# Construct the absolute path to the 'Web' directory
scripts_dir = os.path.abspath(os.path.join(globle_path, '..', 'Web'))
print(scripts_dir)  # 📄 Print the absolute path to 'Web' directory
#=======================================End=====================================================

# Add the 'Auto_Reply_Whatsapp' directory to the Python path
# sys.path.insert(1, os.path.join(scripts_dir, 'Auto_Reply_Whatsapp'))
sys.path.insert(0, os.path.join(scripts_dir,'local_connection'))

from credentials import *

#---------Log Setup-------------
log_level = log.INFO  # ℹ️ Set logging level to INFO
log_formatter = log.Formatter(fmt='%(asctime)s.%(msecs)03d - %(message)s', datefmt='%d-%b-%y %H:%M:%S', style='%')
# Create a logger instance
logging = log.getLogger('MyLogger')
logging.setLevel(log.DEBUG)  # 🛠️ Set logger level to DEBUG
# Set up a rotating file handler for logging
handler = log.handlers.RotatingFileHandler(str(__file__) + '.log', maxBytes=1048576000, backupCount=10)
handler.setFormatter(log_formatter)
handler.setLevel(log.INFO)  # 🔄 Set handler level to INFO
logging.addHandler(handler)


class AgentManager:
    """
    A class to manage Agent objects, including registration, retrieval, and database interaction.
    """

    agentsByMobile = {}  # 📱 Dictionary to store Agent objects by mobile number
    agentsById = {}  # 🆔 Dictionary to store Agent objects by ID

    def __init__(self,logManager):
        try:
            self.logManager=logManager
            """
            Initializes AgentManager with empty dictionaries for storing agents.
            """
            pass  # 🛠️ Initialize AgentManager class
        except Exception as e:
            self.logManager.print_dialer_log("AgentManager",f"Error in __init__ {e}")

    def register(self, agent):
        try:
            """
            Registers an agent in the AgentManager.

            Args:
            - agent (Agent): The Agent object to register.
            """
            self.agentsByMobile[agent.getMobile()] = agent
            self.agentsById[agent.id] = agent
        except Exception as e:
            self.logManager.print_dialer_log("AgentManager",f"Error in register {e}")

    def unregister(self, agent):
        try:
            """
            Unregisters an agent from the AgentManager.

            Args:
            - agent (Agent): The Agent object to unregister.
            """
            del self.agentsByMobile[agent.getMobile()]
            del self.agentsById[agent.id]
        except Exception as e:
            self.logManager.print_dialer_log("AgentManager",f"Error in unregister {e}")

    def getAgentById(self, id):
        try:
            """
            Retrieves an agent object by ID from AgentManager.

            Args:
            - id (str): The ID of the agent to retrieve.

            Returns:
            - Agent or None: The Agent object if found, otherwise None.
            """
            if id in self.agentsById:
                return self.agentsById[id]
            else:
                return self.getAgentFromDbId(id)
        except Exception as e:
            self.logManager.print_dialer_log("AgentManager",f"Error in getAgentById {e}")

    def updateAgentById(self, id):
        try:
            """
            Updates agent details by ID.

            Args:
            - id (str): The ID of the agent to update.

            Returns:
            - Agent or None: The updated Agent object if found, otherwise None.
            """
            if id in self.agentsById:
                print("STARTING UPDATING USERS")
                self.getAgentFromDbId(id)
                print("COMPLETED UPDATING USERS")
                return self.getAgentFromDbId(id)
        except Exception as e:
            self.logManager.print_dialer_log("AgentManager",f"Error in updateAgentById {e}")

    def getAgentFromDbMobile(self, mobile):
        try:
            """
            Retrieves agent details from the database by mobile number.

            Args:
            - mobile (str): The mobile number of the agent to retrieve.

            Returns:
            - Agent or None: The Agent object if found, otherwise None.
            """
            # connection = mysql_manager.get_connection()
            self.logManager.print_dialer_log("AgentManager",f"Agent Mobile Number for login dialer {mobile}")
            query = f"SELECT * FROM users WHERE mobile = '{str(mobile)}' AND dialer_campaign != 0"
            agentdata = fetchoneExeDict(query)
            self.logManager.print_dialer_log("AgentManager",f"GET NEW AGENT FROM DB :: mobile: {mobile}, AgentData: {agentdata}") # 🖋️ Print fetched agent data for debugging
            if agentdata:
                agent = Agent.Agent(agentdata)
                self.agentsById[agentdata["id"]] = agent
                self.agentsByMobile[agentdata["mobile"]] = agent
                return agent
            else:
                return None
        except Exception as e:
            self.logManager.print_dialer_log("AgentManager",f"Error in getAgentFromDbMobile {e}")

    def getAgentFromDbId(self, id):
        try:
            """
            Retrieves agent details from the database by ID.

            Args:
            - id (str): The ID of the agent to retrieve.

            Returns:
            - Agent or None: The Agent object if found, otherwise None.
            """
            # connection = mysql_manager.get_connection()
            self.logManager.print_dialer_log("AgentManager",f"Agent ID for Request to login {id}")
            query = f"SELECT * FROM users WHERE id = '{str(id)}' AND dialer_campaign != 0"
            agentdata = fetchoneExeDict(query)
            self.logManager.print_dialer_log("AgentManager",f"Agent Login Data --- {agentdata}")# 📝 Print fetched agent data for debugging
            if agentdata:
                agent = Agent.Agent(agentdata)
                self.agentsById[agentdata["id"]] = agent
                self.agentsByMobile[agentdata["mobile"]] = agent
                return agent
            else:
                return None
        except Exception as e:
            self.logManager.print_dialer_log("AgentManager",f"Error in getAgentFromDbId {e}")

    def getAgentByMobile(self, mobile):
        try:
            """
            Retrieves an agent object from AgentManager by mobile number.

            Args:
            - mobile (str): The mobile number of the agent to retrieve.

            Returns:
            - Agent or None: The Agent object if found, otherwise None.
            """
            if mobile in self.agentsByMobile:
                return self.agentsByMobile[mobile]
            else:
                return self.getAgentFromDbMobile(mobile)
        except Exception as e:
            self.logManager.print_dialer_log("AgentManager",f"Error in getAgentByMobile {e}")

    
    def removeAgent(self,agentId,mobile):
        try:
            self.logManager.print_dialer_log("AgentManager",f"Hey I am removeAgent function request mobile==> {mobile}")
            
            del self.agentsById[agentId]
            self.logManager.print_dialer_log("AgentManager",f"After delete ID==> {agentId}")

            del self.agentsByMobile[mobile]
            self.logManager.print_dialer_log("AgentManager",f"After delete mobile==> {mobile}")

        except Exception as e:
            self.logManager.print_dialer_log("AgentManager",f"Error in removeAgent {e}")


import redis
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

class Admin:
    # 🗝️ Redis connection object for Admin class
    # Redis_Obj = redis.StrictRedis(
    #     host="182.18.144.40",
    #     port=9023,
    #     password="vnfkjdof90s9820"
    # )
    
    def __init__(self, admin_datas):
        """
        Initialize an Admin object.

        Args:
        - admin_datas (dict): Dictionary containing admin data to initialize instance variables.

        """
        print("PRINT FROM ADMIN --- ", admin_datas)
        
        # Set instance variables dynamically from admin_datas
        for instance_variable in admin_datas:
            setattr(self, instance_variable, admin_datas[instance_variable])
        
        # Set default values for additional instance variables
        self.admin_login_status = "LoggedIn"
        self.channel_id = 0
        self.bridge_id = 0

    def __str__(self):
        """
        Return a string representation of the Admin object.
        """
        return " Admin :: ID = " + str(self.id) + " Number=" + self.mobile + " Name=" + self.name + " " + self.__repr__()

    def getMobile(self):
        """
        Return the mobile number of the admin.
        """
        return self.number

    def updateStatus(self, status):
        """
        Update the admin status in the object.

        Args:
        - status (str): New status to update.
        """
        # 🔄 Placeholder function; actual implementation depends on specific requirements.
        pass

import pymysql  # 🐍 Import MySQL connector library for database interaction
import logging as log  # 📝 Import logging library with alias 'log' for logging operations
from logging.handlers import RotatingFileHandler  # 🔄 Import RotatingFileHandler from logging.handlers for log rotation
import os  # 📂 Import os module for operating system functionalities
import sys  # 🖥️ Import sys module for system-specific parameters and functions
import redis  # 🗝️ Import Redis client library for caching and messaging
from pathlib import Path  # 📁 Import Path class from pathlib module for working with file paths
import atexit  # 🚪 Import atexit module for registering cleanup functions

# Import Admin class from Admin module (assuming Admin module exists)
import Admin

#=====================================globle_path===============================================
# Determine the absolute path of the directory containing this script
globle_path = Path(__file__).parent.absolute()
# Construct the absolute path to the 'Web' directory
scripts_dir = os.path.abspath(os.path.join(globle_path, '..', 'Web'))
print(scripts_dir)  # 📄 Print the absolute path to 'Web' directory

from credentials import *
#=======================================End=====================================================

# Add the 'Auto_Reply_Whatsapp' directory to the Python path
# sys.path.insert(1, os.path.join(scripts_dir, 'Auto_Reply_Whatsapp'))

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


class AdminManager:
    adminByMobile = {}  # 📱 Dictionary to store Admin objects by mobile number
    adminById = {}  # 🆔 Dictionary to store Admin objects by ID

    def __init__(self):
        pass  # 🛠️ Initialize AdminManager class

    def register(self, admin):
        # Register an admin by mobile number and admin ID
        self.adminByMobile[admin.getMobile()] = admin
        self.adminById[admin.id] = admin

    def unregister(self, admin):
        # Unregister an admin by removing from dictionaries
        del self.adminByMobile[admin.getMobile()]
        del self.adminById[admin.id]

    def getAdminById(self, id):
        # Retrieve an admin object by ID
        if id in self.adminById:
            return self.adminById[id]
        else:
            return self.getAdminFromDbId(id)

    def updateAdminById(self, id):
        # Update admin details by ID
        if id in self.adminById:
            print("STARTING UPDATING USERS")
            self.getAdminFromDbId(id)
            print("COMPLETED UPDATING USERS")
            return self.getAdminFromDbId(id)

    def getAdminFromDbMobile(self, mobile):
        # Retrieve admin details from database by mobile number
        # connection = mysql_manager.get_connection()
        query = f"SELECT * FROM users WHERE mobile = '{str(mobile)}'"
        print(query)  # 📝 Print SQL query for debugging
        admindata = fetchoneExeDict(query)
        # with connection.cursor() as cur:
        #     cur.execute(query)
        #     admindata = cur.fetchone()

        print(f"Adding New data  is  {admindata}")  # 🖋️ Print fetched admin data for debugging
        if admindata:
            admin = Admin.Admin(admindata)
            self.adminById[admindata["id"]] = admin
            self.adminByMobile[admindata["mobile"]] = admin
            return admin
        else:
            return None

    def getAdminFromDbId(self, id):
        # Retrieve admin details from database by ID
        # connection = mysql_manager.get_connection()
        query = f"SELECT * FROM users WHERE id = '{str(id)}' AND dialer_campaign != 0"
        admindata = fetchoneExeDict(query)
        # connection.commit()
        # with connection.cursor() as cur:
        #     cur.execute(query)
        #     admindata = cur.fetchone()

        print(f"Admin Login Data --- {admindata}")  # 📝 Print fetched admin data for debugging
        if admindata:
            admin = Admin.Admin(admindata)
            self.adminById[admindata["id"]] = admin
            self.adminByMobile[admindata["mobile"]] = admin
            return admin
        else:
            return None

    def getAdminByMobile(self, mobile):
        # Retrieve admin object by mobile number
        if mobile in self.adminByMobile:
            return self.adminByMobile[mobile]
        else:
            return self.getAdminFromDbMobile(mobile)

# Ensure the MySQL connection is closed on exit
# atexit.register(mysql_manager.close)

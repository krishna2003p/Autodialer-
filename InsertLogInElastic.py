from confluent_kafka import Consumer, KafkaError
import json
from datetime import datetime
import os
import sys
from pathlib import Path
from elasticsearch import Elasticsearch, helpers

#=====================================globle_path===============================================
# Determine the absolute path of the directory containing this script
globle_path = Path(__file__).parent.absolute()
# Construct the absolute path to the 'Web' directory
scripts_dir = os.path.abspath(os.path.join(globle_path, '..', 'Web'))
# print(f"Hey this is path+++++++++++{scripts_dir}++++++")  # 📄 Print the absolute path to 'Web' directory

sys.path.insert(0, os.path.join(scripts_dir,'local_connection'))

from credentials import *


# Logging system
import logging
from logging.handlers import RotatingFileHandler

log_file = Path(log_dir) / f'{Path(__file__).stem}.log'
log_formatter = logging.Formatter(fmt='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(log_file, maxBytes=50048576, backupCount=50)
handler.setFormatter(log_formatter)
handler.setLevel(logging.INFO)
logger.addHandler(handler)


#es = Elasticsearch([{'host': '182.18.144.40', 'port':9018,'scheme': 'http' }])


class KafkaConsumer:
    def __init__(self, topic):
        #self.consumer = Consumer({
        #   'bootstrap.servers': brokers,
        #  'group.id': group_id,
        #  'auto.offset.reset': 'earliest'
        #})
        self.topic = topic

    def consume_messages(self):
        #self.consumer.subscribe([self.topic])
        data_temp = []
        counter = 0
        try:
            while True:
                msg = KafkaDict[f"Consumer_{self.topic}"].poll(0.0001)
                if msg is None:
                    print("Empty")
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        print(msg.error())
                        break
                print('Received message: {}'.format(msg.value().decode('utf-8')))
                counter = counter +1 
                col_toSync = json.loads(msg.value().decode('utf-8'))
                keys_to_check = ['call_data', 'agent_data', 'campaign_data']
                for key in keys_to_check:
                    if not col_toSync.get(key):
                        del col_toSync[key]
                col_toSync["current_time"] = datetime.datetime.now().isoformat()
                 
                temp =  { '_op_type': 'index', '_index' : 'dialer_log_details_version1','_source':json.dumps(col_toSync, default=str)}
                print(5,f"Elastic Insert Payload Temp == {temp}")
                data_temp.append(temp)
                if len(data_temp) % 1 == 0:
                    print(5,f"Elastic Insert Payload  == {data_temp}")
                    # ES_URL = "http://182.18.144.40:9018"
                    Elastic_client = elasticsearch.Elasticsearch([ES_URL])
                    try:
                        #res = helpers.bulk(es, data_temp, refresh='false', request_timeout=60000)
                        res = elasticsearch.helpers.bulk(Elastic_client,data_temp,refresh='false',request_timeout=60000)
                        print(5,f"ELastic INsert Response  ---  {res}")
                        data_temp = []
                    except Exception as e:
                        data_temp = []
                        print(e)

        except Exception as e:
            print(e)
        #finally:
            #self.consumer.close()


if __name__ == "__main__":
    #brokers = "182.18.144.40:9030"  # Kafka broker address
    #group_id = "predictive_dialer_log_nextjs_2"  # Consumer group ID
    topic = f"predictive_dialer_log_{env}"  # Kafka topic to consume from

    consumer = KafkaConsumer(topic)
    consumer.consume_messages()


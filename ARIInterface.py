import contextlib
import wave
import os , sys
import time
import requests
import json
from gtts import gTTS
from mutagen.mp3 import MP3
from pathlib import Path

class ARIInterface:
        def __init__(self, server_addr, username, password,environment_name,setting_credentials,logManager):  
            self._req_base = "http://"+server_addr+"/ari/"
            self._username = username
            self._password = password
            self._environment_name = environment_name
            self.logManager = logManager
            self._sbc_ip = setting_credentials[0]
            self._pilot_number = setting_credentials[4]
            self.filename = os.path.splitext(os.path.basename(__file__))[0]

        def Mute(self,channel_id):
            try:
                self.logManager.print_dialer_log(self.filename,f"Mute Request {channel_id}  => Started ")
                req_str = self._req_base+"channels/"+channel_id+"/mute?direction=out"
                data = self._send_post_request(req_str)
            except Exception as e:
                self.logManager.print_dialer_log(self.filename,f"Mute Error {channel_id} => error:{e}, Detail-Error:{traceback.format_exc()}")
        def Snoop(self,channel_id):
            try:
                self.logManager.print_dialer_log(self.filename,f"Snoop Request {channel_id}  => Started ")
                req_str = self._req_base+"channels/"+channel_id+"/snoop?spy=both&appArgs=00,snoop&app="+str(self._environment_name)+"_newpredictive_login,snoop"
                data=self._send_post_request(req_str)
                return json.loads(data)["id"]
            except Exception as e:
                self.logManager.print_dialer_log(self.filename,f"Snoop Error {channel_id} => error:{e}, Detail-Error:{traceback.format_exc()}")

        def Whisper(self,channel_id):
            try:
                self.logManager.print_dialer_log(self.filename,f"Whisper Request {channel_id}  => Started ")
                req_str = self._req_base+"channels/"+channel_id+"/snoop?whisper=out&spy=both&appArgs=00,snoop&app="+str(self._environment_name)+"_newpredictive_login,snoop"
                data=self._send_post_request(req_str)
                return json.loads(data)["id"]
            except Exception as e:
                self.logManager.print_dialer_log(self.filename,f"Whisper Error {channel_id} => error:{e}, Detail-Error:{traceback.format_exc()}")

        def CallBarging(self,agent_channel_id,admin):
            try:
                self.logManager.print_dialer_log(self.filename,f"Call Barging Started  => agent_channel_id : {agent_channel_id} ,admin_channel_id :{admin.channel_id} ")
                snoop_id = self.Snoop(agent_channel_id)
                bridge_id = admin.bridge_id
                self.add_to_bridge(bridge_id,admin.channel_id)
                self.add_to_bridge(bridge_id,agent_channel_id)
            except Exception as e:
                self.logManager.print_dialer_log(self.filename,f"Call Barging  Error {channel_id} => error:{e}, Detail-Error:{traceback.format_exc()}")

        def CallWhispering(self,agent_channel_id,admin):
            try:
                self.logManager.print_dialer_log(self.filename,f"Call Whispering Started  => agent_channel_id : {agent_channel_id} ,admin_channel_id :{admin.channel_id} ")
                snoop_id = self.Whisper(agent_channel_id)
                bridge_id = admin.bridge_id
                self.add_to_bridge(bridge_id,admin.channel_id)
                self.add_to_bridge(bridge_id,agent_channel_id)
            except Exception as e:
                self.logManager.print_dialer_log(self.filename,f"Call Whispering Error {channel_id} => error:{e}, Detail-Error:{traceback.format_exc()}")

        def Unmute(self,channel_id):
            try:
                self.logManager.print_dialer_log(self.filename,f"Unmute Request {channel_id}  => Started")
                req_str = self._req_base+"channels/"+channel_id+"/mute?direction=out"
                data=self._send_delete_request(req_str)
            except Exception as e:
                self.logManager.print_dialer_log(self.filename,f"Unmute Error {channel_id} => error:{e}, Detail-Error:{traceback.format_exc()}")

        def Hold(self,channel_id):
            try:
                self.logManager.print_dialer_log(self.filename,f"Hold Request {channel_id}  => Started")
                req_str = self._req_base+"channels/"+channel_id+"/hold"
                data=self._send_post_request(req_str)
            except Exception as e:
                self.logManager.print_dialer_log(self.filename,f"Hold Error {channel_id} => error:{e}, Detail-Error:{traceback.format_exc()}")

        def Unhold(self,channel_id):
            try:
                self.logManager.print_dialer_log(self.filename,f"Unhold Request {channel_id}  => Started")
                req_str = self._req_base+"channels/"+channel_id+"/hold"
                data=self._send_delete_request(req_str)
            except Exception as e:
                self.logManager.print_dialer_log(self.filename,f"Unhold Error {channel_id} => error:{e}, Detail-Error:{traceback.format_exc()}")


        def stop_record(self,bridge_id):
            try:
                self.logManager.print_dialer_log(self.filename,f"Stop Record Request {bridge_id}  => Started")
                req_str = self._req_base+"bridges/"+bridge_id+"/record"
                data=self._send_delete_request(req_str)
            except Exception as e:
                self.logManager.print_dialer_log(self.filename,f"Stop Record Error {bridge_id} => error:{e}, Detail-Error:{traceback.format_exc()}")

        def start_record(self,bridge_id,name):
            try:
                self.logManager.print_dialer_log(self.filename,f"Start Record Request {bridge_id}  => Started name:{name} ")
                req_str = self._req_base+"bridges/"+bridge_id+"/record?name="+name+"&format=wav&beep=True"
                data=self._send_post_request(req_str)
            except Exception as e:
                self.logManager.print_dialer_log(self.filename,f"Start Record  Error {bridge_id} => error:{e}, Detail-Error:{traceback.format_exc()}")

        def stop_moh(self,bridge_id):
            try:
                self.logManager.print_dialer_log(self.filename,f"Stop MOH Request {bridge_id}  => Started")
                req_str = self._req_base+"bridges/"+bridge_id+"/moh"
                data=self._send_delete_request(req_str)
            except Exception as e:
                self.logManager.print_dialer_log(self.filename,f"Stop MOH  Error {bridge_id} => error:{e}, Detail-Error:{traceback.format_exc()}")

        def start_moh(self,bridge_id,mohclass):
            try:
                self.logManager.print_dialer_log(self.filename,f"Start MOH Request {bridge_id}  => Started")
                req_str = self._req_base+"bridges/"+bridge_id+"/moh?mohClass="+str(mohclass)
                data=self._send_post_request(req_str)
            except Exception as e:
                self.logManager.print_dialer_log(self.filename,f"Start MOH  Error {bridge_id} => error:{e}, Detail-Error:{traceback.format_exc()}")

        def delete_bridge(self,bridge_id):
            try:
                self.logManager.print_dialer_log(self.filename,f"Delete Bridge Request {bridge_id}  => Started")
                req_str = self._req_base+"bridges/"+bridge_id
                data=self._send_delete_request(req_str)
            except Exception as e:
                self.logManager.print_dialer_log(self.filename,f"Delete Bridge Error {bridge_id} => error:{e}, Detail-Error:{traceback.format_exc()}")


        def create_bridge(self):
            try:
                self.logManager.print_dialer_log(self.filename, "Create Bridge Request => Started")
                req_str = self._req_base + "bridges?type=mixing"
                data = self._send_post_request(req_str)
                return json.loads(data)["id"]
            except Exception as e:
                self.logManager.print_dialer_log(self.filename, f"Create Bridge Error => error: {e}, Detail-Error: {traceback.format_exc()}", level=logging.ERROR)

        def add_to_bridge(self, bridge_id, channel_id):
            try:
                self.logManager.print_dialer_log(self.filename, f"Add to Bridge Request {bridge_id} => Channel: {channel_id} => Started")
                req_str = self._req_base + f"bridges/{bridge_id}/addChannel?channel={channel_id}"
                data = self._send_post_request(req_str)
            except Exception as e:
                self.logManager.print_dialer_log(self.filename, f"Add to Bridge Error {bridge_id} => error: {e}, Detail-Error: {traceback.format_exc()}", level=logging.ERROR)

        def answer_call(self, channel_id):
            try:
                self.logManager.print_dialer_log(self.filename, f"Answer Call Request {channel_id} => Started")
                req_str = self._req_base + f"channels/{channel_id}/answer"
                data = self._send_post_request(req_str)
                self.logManager.print_dialer_log(self.filename, f"Answer Call Completed {channel_id} => payload: {req_str}, Response: {data}")
            except Exception as e:
                self.logManager.print_dialer_log(self.filename, f"Answer Call Error {channel_id} => error: {e}, Detail-Error: {traceback.format_exc()}", level=logging.ERROR)

        def play_digits(self, channel_id, digits, blocking=True):
            try:
                self.logManager.print_dialer_log(self.filename, f"Play Digits Request {channel_id} => Digits: {digits} => Started")
                req_str = self._req_base + f"channels/{channel_id}/play?media=digits:{digits}"
                data = self._send_post_request(req_str)
                self.logManager.print_dialer_log(self.filename, f"Play Digits Completed {channel_id} => payload: {req_str}, Response: {data}")

                if blocking:
                    self.logManager.print_dialer_log(self.filename, f"Blocking Operation => Sleeping for {len(str(digits))} seconds")
                    time.sleep(len(str(digits)))
            except Exception as e:
                self.logManager.print_dialer_log(self.filename, f"Play Digits Error {channel_id} => error: {e}, Detail-Error: {traceback.format_exc()}", level=logging.ERROR)
                

        def make_clip(self, mytext, name):
            try:
                self.logManager.print_dialer_log(self.filename, f"Make Clip Request => Text: {mytext}, Name: {name} => Started")
                myobj = gTTS(text=mytext, lang="en", slow=False)
                file_path = f"/etc/cloudshope/sounds/{name}.mp3"
                myobj.save(file_path)
                self.logManager.print_dialer_log(self.filename, f"Make Clip Completed => Saved at {file_path}")
            except Exception as e:
                self.logManager.print_dialer_log(self.filename, f"Make Clip Error => Text: {mytext}, Name: {name}, error: {e}, Detail-Error: {traceback.format_exc()}", level=logging.ERROR)

        def play_text(self, channel_id, text, blocking=True):
            try:
                self.logManager.print_dialer_log(self.filename, f"Play Text Request => Text: {text}, Channel ID: {channel_id} => Started")
                new_text = text.replace(" ", "_")
                sound_path = f"/etc/cloudshope/sounds/{new_text}.mp3"
                
                if not os.path.exists(sound_path):
                    self.make_clip(text, new_text)

                self.logManager.print_dialer_log(self.filename, f"Text converted to sound file at: {sound_path}")
                self.play_sound(channel_id, f"/etc/cloudshope/sounds/{new_text}")
            except Exception as e:
                self.logManager.print_dialer_log(self.filename, f"Play Text Error => Text: {text}, Channel ID: {channel_id}, error: {e}, Detail-Error: {traceback.format_exc()}", level=logging.ERROR)
                

        def stop_play_sound(self, channel_id, playback_id, clip_format="mp3", blocking=True):
            try:
                self.logManager.print_dialer_log(self.filename, f"Stop Play Sound Request => Channel ID: {channel_id}, Playback ID: {playback_id} => Started")
                req_str = self._req_base + f"playbacks/{str(playback_id)}"
                self._send_delete_request(req_str)
            except Exception as e:
                self.logManager.print_dialer_log(self.filename, f"Stop Play Sound Error => Channel ID: {channel_id}, Playback ID: {playback_id}, error: {e}, Detail-Error: {traceback.format_exc()}", level=logging.ERROR)
                

        def play_extension_clip(self, channel_id, sound_name, clip_format="mp3", blocking=True):
            try:
                self.logManager.print_dialer_log(self.filename, f"Play Extension Clip Request => Sound Name: {sound_name}, Channel ID: {channel_id} => Started")
                req_str = self._req_base + f"channels/{channel_id}/play?media=sound:{sound_name}"
                self._send_post_request(req_str)
                return json.loads(data)["id"]
            except Exception as e:
                self.logManager.print_dialer_log(self.filename, f"Play Extension Clip Error => Sound Name: {sound_name}, Channel ID: {channel_id}, error: {e}, Detail-Error: {traceback.format_exc()}", level=logging.ERROR)
                

        def play_sound(self, channel_id, sound_name, clip_format="mp3", blocking=True):
            try:
                self.logManager.print_dialer_log(self.filename, f"Play Sound Request => Sound Name: {sound_name}, Channel ID: {channel_id} => Started")
                req_str = self._req_base + f"channels/{channel_id}/play?media=sound:{sound_name}"
                data = self._send_post_request(req_str)
                self.logManager.print_dialer_log(self.filename, f"Play Sound Completed => Request: {req_str}, Response: {data}")
                if blocking==True and clip_format=="mp3":
                       time.sleep(MP3(sound_name+"."+clip_format).info.length)
                elif blocking==True and clip_format=="wav":
                        with contextlib.closing(wave.open(sound_name+".wav",'r')) as wavfile:
                            frames = wavfile.getnframes()
                            rate = wavfile.getframerate()
                            duration = frames / float(rate)
                            time.sleep(duration)
            except Exception as e:
                self.logManager.print_dialer_log(self.filename, f"Play Sound Error => Sound Name: {sound_name}, Channel ID: {channel_id}, error: {e}, Detail-Error: {traceback.format_exc()}", level=logging.ERROR)
                

        def get_variable(self, channel_id, variable):
            try:
                self.logManager.print_dialer_log(self.filename, f"Get Variable Request => Variable: {variable}, Channel ID: {channel_id} => Started")
                req_str = self._req_base + f"channels/{channel_id}/variable?variable={variable}"
                self.logManager.print_dialer_log(self.filename, f"Get Variable Request => Request: {req_str}")
                response = self._send_get_request(req_str)
                return response
            except Exception as e:
                self.logManager.print_dialer_log(self.filename, f"Get Variable Error => Variable: {variable}, Channel ID: {channel_id}, error: {e}, Detail-Error: {traceback.format_exc()}", level=logging.ERROR)
                

        def set_variable(self, channel_id, variable, value):
            try:
                self.logManager.print_dialer_log(self.filename, f"Set Variable Request => Variable: {variable}, Value: {value}, Channel ID: {channel_id} => Started")
                req_str = self._req_base + f"channels/{channel_id}/variable?variable={variable}&value={value}"
                response = self._send_post_request(req_str)
                return response
            except Exception as e:
                self.logManager.print_dialer_log(self.filename, f"Set Variable Error => Variable: {variable}, Value: {value}, Channel ID: {channel_id}, error: {e}, Detail-Error: {traceback.format_exc()}", level=logging.ERROR)
                

        def dial(self, number, args, masked_caller_id,channel_id=None):
            try:
                self.logManager.print_dialer_log(self.filename, f"Dial Request => Number: {number}, Masked Caller ID: {masked_caller_id} => Started")
                req_str = f"{self._req_base}channels?app={self._environment_name}_newpredictive_login&callerId={masked_caller_id[-7:]}&appArgs={args}"
                if channel_id is not None:
                    req_str = f"{self._req_base}channels?app={self._environment_name}_newpredictive_login&callerId={masked_caller_id[-7:]}&appArgs={args}&channelId={channel_id}"

                body = {
                    'variables': {
                    "PJSIP_HEADER(add,P-Asserted-Identity)": f"sip:{masked_caller_id[-7:]}@{self._sbc_ip}",
                    "PJSIP_HEADER(add,P-Preferred-Identity)": f"sip:{self._pilot_number}@{self._sbc_ip}"
                        },
                "endpoint": f"PJSIP/0{number}@RSipOut0",
                "alwaysDelete": "yes"

                    }
                self.logManager.print_dialer_log(self.filename, f"Dial Request => Request: {req_str}, Payload: {body}")
                data = requests.request("POST", req_str, auth=("emanthon", "emanthonIndia123"), json=body)
                response = json.loads(data.text)
                self.logManager.print_dialer_log(self.filename, f"Dial Completed => Response: {data.text}")
                channel_id = response['id']
                return channel_id
            except Exception as e:
                self.logManager.print_dialer_log(self.filename, f"Dial Error => Number: {number}, Masked Caller ID: {masked_caller_id}, error: {e}, Detail-Error: {traceback.format_exc()}", level=logging.ERROR)
                

        def hangup(self, channel_id):
            try:
                self.logManager.print_dialer_log(self.filename, f"Hangup Request => Channel ID: {channel_id} => Started")
                req_str = self._req_base + f"channels/{channel_id}"
                data = self._send_delete_request(req_str)
            except Exception as e:
                self.logManager.print_dialer_log(self.filename, f"Hangup Error => Channel ID: {channel_id}, error: {e}, Detail-Error: {traceback.format_exc()}", level=logging.ERROR)
                

        def _send_get_request(self, req_str):
            try:
                self.logManager.print_dialer_log(self.filename, f"Send GET Request => Request: {req_str} => Started")
                data = requests.get(req_str, auth=(self._username, self._password))
                self.logManager.print_dialer_log(self.filename, f"Send GET Request Completed => Response: {data.content}")
                return json.loads(data.content)
            except Exception as e:
                self.logManager.print_dialer_log(self.filename, f"Send GET Request Error => Request: {req_str}, error: {e}, Detail-Error: {traceback.format_exc()}", level=logging.ERROR)
                

        def _send_post_request(self, req_str):
            try:
                self.logManager.print_dialer_log(self.filename, f"Send POST Request => Request: {req_str} => Started")
                data = requests.post(req_str, auth=(self._username, self._password))
                self.logManager.print_dialer_log(self.filename, f"Send POST Request Completed => Response: {data.content}")
                return data.content
            except Exception as e:
                self.logManager.print_dialer_log(self.filename, f"Send POST Request Error => Request: {req_str}, error: {e}, Detail-Error: {traceback.format_exc()}", level=logging.ERROR)
                

        def _send_delete_request(self, req_str):
            try:
                self.logManager.print_dialer_log(self.filename, f"Send DELETE Request => Request: {req_str} => Started")
                data = requests.delete(req_str, auth=(self._username, self._password))
                self.logManager.print_dialer_log(self.filename, f"Send DELETE Request Completed => Response: {data.content}")
                return data.content
            except Exception as e:
                self.logManager.print_dialer_log(self.filename, f"Send DELETE Request Error => Request: {req_str}, error: {e}, Detail-Error: {traceback.format_exc()}", level=logging.ERROR)






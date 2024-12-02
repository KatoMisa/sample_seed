#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import actionlib
import rospy
from std_msgs.msg import String
from pygame import mixer
import rospy
import threading
from modules.srv import *
from rois_ros.msg import *
from rois_ros.srv import *

#発話用(クラス追加)

OHAYO = "おはようございます"
MOVE = "今から移動を開始します。"

class Speech_SynthesisService:
    def __init__(self):
        self.comp_state = "UNINITIALIZED"
        print(self.comp_state)

        self.comp_ref = "Speech_Synthesis"

        state_name = '/get_state/' + self.comp_ref
        self.state_service = rospy.Service(state_name, component_status, self.component_status)   #
        rospy.loginfo("component status server is ready")  

        self.directory="/home/rsdlab/catkin_ws/src/sample_seed/voice_kenkou/"
        self.text ="hello"
        self._words =self.directory +"hello.mp3"
            

        exe_name = '/execute/' + self.comp_ref
        self.server = actionlib.SimpleActionServer(exe_name, executeAction, self.execute, False)
        print(exe_name)
        self.server.start()     

        self.set = rospy.Service('/speech_set_param', speech_set_param, self.set_parameter)  
        self.get = rospy.Service('/speech_get_param', speech_get_param, self.get_parameter)


        self.pub = rospy.Publisher('/completed_command', completed , queue_size=1)
        # self.pub = rospy.Publisher('/completed', String,queue_size=1)



        self.state = "idle"
        #self.goal_sent = False
        self.current_goal = None

        self.comp_state = "READY"
        rospy.loginfo(f'Componemt status: {self.comp_state}')  #コンポーネントをREADY状態にする


        self.playback_thread = None 


    def set_parameter(self, s_req):
        print("set parameter")
        
        self.text = s_req.speech_text
        
        if self.text == "hello":#おはようございます
            self._words = self.directory + "hello.mp3"

        elif self.text == "measure1": #~さん今から計ります
            self._words = self.directory + "check_measure.mp3"

        elif self.text == "yorosiku": #よろしく（腕をおいてください）
            self._words = self.directory + "yorosiku.mp3"

        elif self.text == "check": #体調をチェックしますね、そのままお待ちください
            self._words = self.directory + "check_start.mp3"

        elif self.text == "ask1": #体調はどうですか？
            self._words = self.directory + "how_health.mp3"

        elif self.text == "bad_high": #体調悪andリスク高
            self._words = self.directory + "bad_high.mp3"

        elif self.text == "hand": #手を握りましたか
            self._words = self.directory + "check_hand.mp3"

        elif self.text == "thank": #計測が終わりました、ありがとう
            self._words = self.directory + "check_ok.mp3"


        elif self.text == "ask2": #体調はどうですか？
            self._words = self.directory + "how_health.mp3"



        # elif self.text == "check": #体調をチェックしますね
        #     self._words = self.directory + "check_start.mp3"

        # elif self.text == "move_start": #今から移動を開始します
        #     self._words = self.directory + "move_start.mp3"



        # elif self.text == "Squeeze finger": #指を握ってください
        #     self._words = self.directory + "hand_finger.mp3"

        # elif self.text == "put arm": #腕をおいてください
        #     self._words = self.directory + "put_arm.mp3"

        # elif self.text == "ask": #体調はどうですか？
        #     self._words = self.directory + "how_health.mp3"

        # elif self.text == "bad_high": #体調悪andリスク高
        #     self._words = self.directory + "bad_high.mp3"



        # elif self.text == "long test":
        #     self._words = self.directory + "longtest1.mp3"

        else:
            self._words = "no"
            set_return = "BAD_PARAMATER"
            return speech_set_paramResponse(set_return)
        
        if os.path.isfile(self._words):
            print(f"{self.text} File exists.")
            keep = "yes"
            self.keep_word(keep)
            set_return = "OK"
            return speech_set_paramResponse(set_return) 

        else:
            print(f"{self.text} File does not exist")
            keep = "no"
            self.keep_word(keep)
            set_return = "BAD_PARAMATER"
            return speech_set_paramResponse(set_return)

        print("speech_words: ",self.text)
           

    def keep_word(self,keep):
        if keep == "yes":
            self.past_path = self._words
            self.path_word = self.text
        elif keep =="no":
            self._words = self.past_path
            self.text = self.path_word          

    def get_parameter(self,g_req):
        print("get_parameter")
        print(self.text)
        return speech_get_paramResponse(self.text)


    def execute(self, goal):
        self.comp_state = "BUSY"
        rospy.loginfo(f'Componemt status: {self.comp_state}')  #コンポーネントをREADY状態にする

        command = goal.command_name
        rospy.loginfo("Received command: %s", command)

        self.feedback = executeFeedback()
        self.result = executeResult()

        if command == "start":
            self.start()    
            
        elif command == "stop":
            self.stop()

        elif command == "suspend":
            self.suspend()

        elif command == "resume":
            self.resume()

        else:
            rospy.loginfo("No valid command received.")
            self.result.success = "False"
            self.server.set_aborted(self.result)
        


    def start(self):
        self.state = "playing"

        # 音楽再生を監視するスレッドを開始
        self.playback_thread = threading.Thread(target=self.monitor_playback)
        self.playback_thread.start()

        self.result.success = "True"
        self.server.set_succeeded(self.result)




    def monitor_playback(self):
        rospy.loginfo("Monitoring playback.")

        try:
            pygame.mixer.init()
            pygame.mixer.music.load(self._words)
            pygame.mixer.music.play()


            while self.state == "playing":
                rospy.sleep(0.1)

                if not pygame.mixer.music.get_busy():
                    rospy.loginfo("Playback completed.")
                    self.state = "OK"
                    # self.completed_command()
                    return

        except pygame.error as e:
            print(f"Pygame error occurred: {e}")
            self.state = "ERROR"

            self.comp_state = "ERROR"
            rospy.loginfo(f'Componemt status: {self.comp_state}') 
        except FileNotFoundError as e:
            print(f"File error: {e}")
            self.state = "ERROR"

            self.comp_state = "ERROR"
            rospy.loginfo(f'Componemt status: {self.comp_state}') 
        except Exception as e:
            print(f"Unexpected error: {e}")
            self.state = "ERROR"
            self.comp_state = "ERROR"
            rospy.loginfo(f'Componemt status: {self.comp_state}') 
        
        finally:
            self.completed_command()


    # 再生が終了したらこのメソッドが呼ばれる
    def completed_command(self):
        rospy.loginfo("Playback completed successfully.")
        pub_data = completed()
        pub_data.command_id = "Speech_Synthesis"
        pub_data.status = self.state
        print(f"{pub_data.command_id}:{pub_data.status}")
        self.pub.publish(pub_data)
        
        self.comp_state = "READY"
        rospy.loginfo(f'Componemt status: {self.comp_state}') 
       



    def stop(self):
        if self.state == "playing":
            pygame.mixer.music.stop()
            self.state = "stopped"
            self.feedback.status = "playing stopped."
            
            pub_data = completed()
            pub_data.command_id = "speech_synthesis"
            pub_data.status = "stoped"
            self.pub.publish(pub_data)
            
            self.result.success = "True"
            self.server.set_succeeded(self.result)
            self.comp_state = "READY"
            rospy.loginfo(f'Componemt status: {self.comp_state}') 
        else:
            rospy.logwarn("No active playing.")
            self.feedback.status = "No active goal to stop."
            self.result.success = "False"
            self.server.set_aborted(self.result)


    def suspend(self):
        if self.state == "playing":
            pygame.mixer.music.pause()
            self.state = "suspended"
            self.feedback.status = "play suspended."
            self.result.success = "True"
            self.server.set_succeeded(self.result)
        else:
            rospy.logwarn("Cannot suspend; not playing.")
            self.result.success = "False"
            self.server.set_aborted(self.result)


    def resume(self):
        if self.state == "suspended":
            pygame.mixer.music.unpause()
            self.state = "playing"
            self.feedback.status = "Playing resumed."
            self.result.success = "True"
            self.server.set_succeeded(self.result)
              # 音楽再生を監視するスレッドを開始
            if not self.playback_thread or not self.playback_thread.is_alive():
                self.playback_thread = threading.Thread(target=self.monitor_playback)
                self.playback_thread.start()
        else:
            rospy.logwarn("No previous goal to resume.")
            self.result.success = "False"
            self.server.set_aborted(self.result)



    def component_status(self, req):
        # 現在の状態を返答
        if (req.component_name == "Speech_Synthesis"):
            rospy.loginfo("Current state requested: %s", self.comp_state)
            return component_statusResponse(self.comp_state)
        else:
            pass


    def run(self):
        rospy.loginfo("Service node is running...")
        rospy.spin()



if __name__ == "__main__":
    rospy.init_node('Speech_Synthesis')
    print("time")
    service = Speech_SynthesisService()
    service.run()




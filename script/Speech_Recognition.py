#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import rospy
import os
import subprocess
import rosparam
from std_msgs.msg import String
import pygame
import speech_recognition as sr
from rois_ros.srv import *
from rois_ros.msg import *
import actionlib
import threading
from datetime import datetime

#eventにも挑戦



class Speech_RecognitionService():
    def __init__(self):

        #初期化できていないためコンポーネントの状態をUNINITIALIZEDにする
        self.comp_state = "UNINITIALIZED"
        print(self.comp_state)        
        
        #コンポーネント名を設定する
        self.comp_ref = "Speech_Recognition"

        #コンポーネントの状態確認のサービス設定
        state_name = '/get_state/' + self.comp_ref
        self.state_service = rospy.Service(state_name, component_status, self.component_status)


        #聞き取り時に使用する音源
        self.directory="/home/rsdlab/catkin_ws/src/sample_seed/voice_kenkou/"
        self.start_sound =self.directory +"kaishi.mp3"
        self.stop_sound =self.directory +"shuryo.mp3"
        self.retry_sound = self.directory +"retry.mp3"

        #Command用のアクション通信の設定
        exe_name = '/execute/' + self.comp_ref
        self.server = actionlib.SimpleActionServer(exe_name, executeAction, self.execute, False)
        self.server.start()
        rospy.loginfo(f"{exe_name} Service is ready.")
        
        # #Event用のサービス通信の設定
        # exe_name = '/Subscribe/' + self.comp_ref
        # self.sub_server = rospy.Service(exe_name, subscribe_set, self.subs)
        # rospy.loginfo(f"{exe_name} Service is ready.")

        #パラメータ操作用のサービス通信の設定
        self.set = rospy.Service('/s_recognition_set_param', s_recognition_set_param, self.set_parameter)  
        self.get = rospy.Service('/s_recognition_get_param', s_recognition_get_param, self.get_parameter)

        #パラメータの初期値
        self.recognizable_list = ["japanese"]  #認識可能な言語
        self.set_language = "japanese"
        self.languages = "ja-JP"               #認識を行う言葉の言語
        self.recognized_text = ""              #認識した言葉

        #Thread用の設定
        self.state = "idle"
        self.recognized_thread = None

        #音声認識ライブラリ用        
        self.recognizer = sr.Recognizer()
        self.audio = None
        self.listening = False
        self.suspended = False


        #イベント通知するためのトピック通信の設定
        # self.pub = rospy.Publisher('/event_speechrec', notify_speechrec , queue_size=1)
        self.pub = rospy.Publisher('/event_speechrec', notify_speechrec3 , queue_size=1)

        #コマンド終了の通知用のトピックの設定
        self.pub1 = rospy.Publisher('/completed_event', completed , queue_size=1)

        #イベント通知のトピックを送信するか判断する変数の設定
        self.SEND_STARTTIME = False    #speech_input_startedメソッド用
        self.SEND_FINISHTIME = False   #speech_input_finishedメソッド用
        self.SEND_TEXT = False         #speech_recognizedメソッド用

        #準備できたらコンポーネントの状態をREADYにする
        self.comp_state = "READY"
        rospy.loginfo(f'Componemt status: {self.comp_state}')  #コンポーネントをREADY状態にする



    #オプション関数(リスト更新用)
    def add_lang_item(self, _list, item):
        if item not in _list:
            _list.append(item)
            return f"{item} を追加しました"
        else:
            return f"{item} は既にリストに存在します"


    #コンポーネントが持つパラメータを設定するためのset_parameter()
    def set_parameter(self, s_req):
        print("set parameter")
        
        #認識させる言語を設定
        self.set_language = s_req.languages
 
        try:
            if self.set_language == "japanese":
                self.languages = "ja-JP"
                print(self.add_lang_item(self.recognizable_list, self.set_language))


            elif self.set_language == "english":
                self.languages = "en-US"
                print(self.add_lang_item(self.recognizable_list, self.set_language))

            elif self.set_language == "french":
                self.languages = "fr-FR"
                print(self.add_lang_item(self.recognizable_list, self.set_language))

            set_return = "OK"
            return s_recognition_set_paramResponse(set_return) 

        except:
            set_return = "BAD_PARAMATER"
            return test_set_paramResponse(set_return)


    def get_parameter(self,g_req):
        print("get_parameter")

        _recognizable_languages = self.recognizable_list
        _languages = self.set_language
        print(_recognizable_languages)
        print(_languages)
        return s_recognition_get_paramResponse(_recognizable_languages, _languages)


    def execute(self, goal):
        self.comp_state = "BUSY"
        rospy.loginfo(f'Componemt status: {self.comp_state}')  #コンポーネントをBUSY状態にする

        self.command = goal.command_name
        rospy.loginfo("Received command: %s", self.command)

        self.feedback = executeFeedback()
        self.result = executeResult()

        if self.command == "start":
            self.start()    
            
        elif self.command == "stop":
            self.stop()

        elif self.command == "suspend":
            self.suspend()

        elif self.command == "resume":
            self.resume()

        else:
            rospy.loginfo("No valid command received.")
            self.result.success = "False"
            self.server.set_aborted(self.result)



    def start(self):
        print("start")

        self.state = "playing"

        self.result.success = "True"
        self.server.set_succeeded(self.result)

        self.recognized_thread = threading.Thread(target=self.recognize)
        self.recognized_thread.start()


    def stop(self):
        print("stop")
        # if self.state == "playing":
        #     self.state = "stopped"
        #     print("音声認識は停止しました")

        #     self.feedback.status = "playing stopped."
            
        #     pub_data = completed()
        #     pub_data.command_id = "start"
        #     pub_data.status = "stopped"
        #     self.pub.publish(pub_data)
            
        #     self.result.success = "True"
        #     self.server.set_succeeded(self.result)

        #     self.comp_state = "READY"
        #     rospy.loginfo(f'Componemt status: {self.comp_state}') 
        # else:
        #     rospy.logwarn("No active playing.")
        #     self.feedback.status = "No active goal to stop."
        #     self.result.success = "False"
        #     self.server.set_aborted(self.result)


    def suspend(self):
        print("suspend")
        # if self.state == "playing":
        #     pygame.mixer.music.pause()
        #     self.state = "suspended"
        #     self.feedback.status = "play suspended."
        #     self.result.success = "True"
        #     self.server.set_succeeded(self.result)
        # else:
        #     rospy.logwarn("Cannot suspend; not playing.")
        #     self.result.success = "False"
        #     self.server.set_aborted(self.result)


    def resume(self):
        print("resume")
        # if self.state == "suspended":
        #     pygame.mixer.music.unpause()
        #     self.state = "playing"
        #     self.feedback.status = "Playing resumed."
        #     self.result.success = "True"
        #     self.server.set_succeeded(self.result)

        #     if not self.recognized_thread or not self.recognized_thread.is_alive():
        #         self.recognized_thread = threading.Thread(target=self.recognize)
        #         self.recognized_thread.start()
        # else:
        #     rospy.logwarn("No previous goal to resume.")
        #     self.result.success = "False"
        #     self.server.set_aborted(self.result)




    #認識完了を通知する
    def speech_recognized(self,text):
        completed_time= rospy.get_time()
        self.completed_time ='recognized time: '+ str(datetime.fromtimestamp(completed_time))
        print(self.completed_time)
        
        self.comp_state = "READY"
        rospy.loginfo(f'Componemt status: {self.comp_state}') 


        #通知するトピックの設定
        pub_data = notify_speechrec3()
        pub_data.event_type = "speech_recognized"
        pub_data.timestamp = self.completed_time
        #認識結果を格納
        pub_data.recognized_text = text


        print("pub")
        self.pub.publish(pub_data)

        self.comp_state = "READY"
        rospy.loginfo(f'Componemt status: {self.comp_state}') 

    #認識開始を通知する
    def speech_input_started(self):
        start_time= rospy.get_time()
        self.start_time = 'start time: '+str(datetime.fromtimestamp(start_time))
        print(self.start_time)

        pub_data = notify_speechrec3()
        pub_data.event_type = "speech_input_started"
        pub_data.timestamp = self.start_time
        
        self.pub.publish(pub_data)

    #認識終了を通知する
    def speech_input_finished(self):
        finish_time= rospy.get_time()
        self.finish_time = 'finish time: '+ str(datetime.fromtimestamp(finish_time))
        print(self.finish_time)

        pub_data = notify_speechrec3()
        pub_data.event_type = "speech_input_finished"
        pub_data.timestamp = self.finish_time

        self.pub.publish(pub_data)
        


    #実際に音声認識をする関数
    def recognize(self):
        
        # self.Recognizerオブジェクトを作成
        retry_limit = 2
        attempts = 0
        
        while attempts < retry_limit:
            if self.state == "stopped":
                print(self.state)
                print("音声認識は停止中です。")
                break
            try:
                with sr.Microphone() as source:
                    print("マイクを調整しています...")
                    self.recognizer.adjust_for_ambient_noise(source)  # 周囲のノイズを調整
                    print("話しかけてください...")
                    
                    pygame.mixer.init()
                    pygame.mixer.music.load(self.start_sound)
                    
                    #認識を開始した時間を通知するメソッド
                    self.speech_input_started()
                    pygame.mixer.music.play()

                    audio = self.recognizer.listen(source,phrase_time_limit=5)  # 音声をキャプチャ

                    pygame.mixer.init()
                    pygame.mixer.music.load(self.stop_sound)
                    pygame.mixer.music.play()
                
                rospy.sleep(0.5)
                #認識が終わった時間を通知するメソッド
                self.speech_input_finished()    
                
                text = '>> 音声認識しています...'
                print('\r' + '　' * 40 + '\r', end='', flush=True)
                print(text)
                self.recognized_text = self.recognizer.recognize_google(audio, language=self.languages)  # 日本語認識
                # self.recognized_text = self.recognizer.recognize_google(audio, language="ja-JP")  # 日本語認識
                
                
                print(f"認識された内容: {self.recognized_text}")
                self.speech_recognized(self.recognized_text)

                #完了したら呼び出す関数
                # self.on_recognize_complete()

                # 認識に成功したら、テキストを返して終了
                return 

            except sr.UnknownValueError:
                text = "上手く聞き取れませんでした．もう一度お願いします"
                print('\r' + '　' * 40 + '\r', end='', flush=True)
            
            except sr.RequestError as e:
                text = "結果をリクエストできませんでした.\n"
                print('\b' * 20, end='', flush=True)
                print('　' * 20 + '\n', end='', flush=True)
                print(f"結果をリクエストできませんでした．; {e}")
                self.comp_state = "READY"
                rospy.loginfo(f'Componemt status: {self.comp_state}')

            except Exception as e:
                print(f"予期しないエラーが発生しました: {e}")
                self.comp_state = "ERROR"
                rospy.loginfo(f'Componemt status: {self.comp_state}')
                result = "error"
                return result

            attempts += 1
            print(f"再試行回数: {attempts}/{retry_limit}")

        if self.state != "stopped":
            print("リトライの上限に達しました。認識に失敗しました。")

        self.speech_recognized(self.recognized_text)
        # リトライ上限に達した場合は None を返す
        return None  

    # #完了したら呼び出される関数
    # def on_recognize_complete(self):
    #     rospy.loginfo("recognize completed successfully.")

    #     #認識が完了した時間と認識結果を通知するメソッド
    #     self.speech_recognized()

    #     #READY状態にする
    #     self.comp_state = "READY"
    #     rospy.loginfo(f'Componemt status: {self.comp_state}') 



    def component_status(self, req):
        # 現在の状態を返答
        if (req.component_name == self.comp_ref):
            rospy.loginfo("Current state requested: %s", self.comp_state)
            return component_statusResponse(self.comp_state)
        else:
            pass

    def run(self):
        rospy.loginfo("Service node is running...")
        rospy.spin()



if __name__ == "__main__":
    rospy.init_node('speech_recognition')
    print("time")
    service = Speech_RecognitionService()
    service.run()

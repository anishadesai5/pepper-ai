
import time
import threading
import os
import sharedVars
import SimpleHTTPServer
import SocketServer
import socket
from naoqi import ALProxy
from myPepper import myPepper
from recordAudio4 import manageAudio
from chatGPT import chatGPTInteract
from dotenv import load_dotenv
from naoqi import ALBroker
from naoqi import ALModule
try:
    import OverrideBtn
except ImportError:
    pass


# Load environment variables from the .env file
load_dotenv()

# Access the environment variables
API_KEY = os.getenv("CHATGPT_KEY")
PIP = os.getenv("PIP")
PPORT = int(os.getenv("PPORT"))
BEHAVIOR = "animationMode"
IMAGEURL = os.getenv("IMAGEURL")
IS_MANUAL_CONVERSATION = False
LOCAL = os.getenv("LOCAL")
IMAGE_PREPROMPT = os.getenv("IMAGE_PREPROMPT")


# Define website location and address info
WEBPORT = 8000
WEBDIRECTORY = "website"

# Create a broker
broker = ALBroker("myBroker", "0.0.0.0", 0, PIP, PPORT)

my_pepper = myPepper(PIP=PIP, PPORT=PPORT, LOCAL=LOCAL)
chatGPT_interact = chatGPTInteract(APIKEY=API_KEY)

# Used to determine when to take image and update preprompt
last_run_time = None
interval = 900  # Interval in seconds

# Stops pepper from talking when head touched
class HeadTapped(ALModule):
    def __init__(self, name):
        ALModule.__init__(self, name)
        self.tts = ALProxy("ALTextToSpeech")
        self.memory = ALProxy("ALMemory")

        self.memory.subscribeToEvent("FrontTactilTouched", self.getName(), "onTactilTouched")
        #self.memory.subscribeToEvent("MiddleTactilTouched", self.getName(), "onTactilTouched")
        #self.memory.subscribeToEvent("RearTactilTouched", self.getName(), "onTactilTouched")

    def onTactilTouched(self, key, value, message):
        print("--- MAIN -> onTactilTouched -> value = " + str(value))

        if value == 1.0:  # Tactile sensor is pressed
            
            if sharedVars.ISNEAR == True:
                # Stop talking and stop listening
                print("------ GOOD BYE  -------------- ")
                sharedVars.ISNEAR = False

                self.tts.stopAll()
                global thread_event
                thread_event.set()
                my_pepper.start_behavior("ht_animation_lib/tickle_1")
                
                time.sleep(2)
                
            else :
                # Start listening
                print("------ HELLO --------------- - ")
            
                #Stop everything prior
                self.tts.stopAll()
                global thread_event
                thread_event.set()

                #Setup for a new chat
                chatGPT_interact.reset_chat()
                my_pepper.have_pepper_say("Ahh")
                my_pepper.start_behavior("animations/Stand/Reactions/TouchHead_3")
                my_pepper.stop_all_behaviors()

                sharedVars.ISNEAR = True
                time.sleep(2)
        
        '''
        if value == 1.0:  # Tactile sensor is pressed
            
            # if ISNEAR:

            print("Head tapped, stopping speech.")
            self.tts.stopAll()

            #ISNEAR = False
        '''
            

class PersonDetector(ALModule):
    def __init__(self, name):
        ALModule.__init__(self, name)
        self.people_perception = ALProxy("ALPeoplePerception", PIP, PPORT)
        self.memory = ALProxy("ALMemory", PIP, PPORT)
        self.tts = ALProxy("ALTextToSpeech", PIP, PPORT)
        self.people_perception.setMaximumDetectionRange(0.5)

        # Subscribe to the PeoplePerception/PeopleDetected event
        self.memory.subscribeToEvent("PeoplePerception/JustArrived", self.getName(), "onJustArrived")
        self.memory.subscribeToEvent("PeoplePerception/JustLeft", self.getName(), "onJustLeft")


    def onJustArrived(self, value ):
        print("--- MAIN -> ON_JUST_ARRIVED -> value = " + str(value))
        #check_for_vision() # Take image when someone comes into view.
        '''
        global ISNEAR 
        if ISNEAR == False:
            
            ISNEAR = True
            print("--- MAIN -> ON_JUST_ARRIVED -> value = " + str(value))
            print("------ HELLO --------------- - ")
            #self.tts.say("Hello new person.")
            
            #Stop everything prior
            self.tts.stopAll()
            global thread_event
            thread_event.set()

            #Setup for a new chat
            chatGPT_interact.reset_chat()
            chatbot_response = chatGPT_interact.chat_with_gpt("Hello.")
            cleaned_response = chatGPT_interact.filter_text(chatbot_response)
            my_pepper.have_pepper_say(cleaned_response)
            '''
            

    def onJustLeft(self, value):  
        print("--- MAIN -> ON_JUST_LEFT -> value = " + str(value))
        '''
        if ISNEAR == True:
            print("------ GOOD BYE  -------------- ")
            
            self.tts.stopAll()
            global thread_event
            thread_event.set()

            global ISNEAR 
            ISNEAR = False

            chatbot_response = chatGPT_interact.chat_with_gpt("In a short sentence say 'Good bye'.")
            cleaned_response = chatGPT_interact.filter_text(chatbot_response)
            my_pepper.have_pepper_say(cleaned_response)
            self.people_perception.resetPopulation()
        '''

class CustomHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = SimpleHTTPServer.SimpleHTTPRequestHandler.translate_path(self, path)
        relpath = os.path.relpath(path, os.getcwd())
        fullpath = os.path.join(os.getcwd(), WEBDIRECTORY, relpath)
        return fullpath

''' 4/2/24 - replaced with thinking below per GPT       
def thinking():
    print("--- MAIN - THINKING")
     # Record the start time
    start_time = time.time()
    
    #12/27 my_pepper.have_pepper_say("Let me think.")
    #my_pepper.show_what_pepper_says("Let me think.")

    # Have Pepper say a random thinking phrase if more than 2 seconds have passed
    while not thread_event.is_set():

        if elapsed_time > 3:
            my_pepper.pepper_thinking()
            start_time = time.time()  # Reset the start time
        time.sleep(0.1)  # Sleep for a short time to avoid busy waiting
'''  
def thinking():
    print("--- MAIN - THINKING")
    start_time = time.time()
    
    #Sometimes the head wanders to look at the presenter.
    #When we start thinking, center the head so that it is looking at the audience.   
    #This will run under the thread this is triggered under so it should not delay the response
    center_head()

    #Take a snapshot while processing audio
    #check_for_vision_on_arrival()

    print("Thinking - vision checked")
    while not thread_event.is_set():
        
        
        
        elapsed_time = time.time() - start_time
        if elapsed_time > 3:
            my_pepper.pepper_thinking()
            start_time = time.time()  # Reset the start time
        time.sleep(0.1)  # Sleep for a short time to avoid busy waiting

def center_head():
    my_pepper.center_pepper_head()

# 4/2/24 - Added to roate eyes while pepper is waiting to get a response
def rotate_eyes(): 
    while not thread_event.is_set():
        print("--- MAIN - rotate_eyes")
        my_pepper.change_eye_color_with_turn(200, 200, 200, 1, 1)
        #time.sleep(0.1)  # Wait for 1 second before repeating


def wake_pepper_up():
    try:
        # Create a proxy to ALMotion
        motion_proxy = ALProxy("ALMotion", PIP, PPORT)
        
        # Wake Pepper up
        motion_proxy.wakeUp()
        print("Pepper is now awake.")
        
    except Exception as e:
        print("Error when waking Pepper up: ", e)


def check_for_vision():
    print("check_for_vision")
    current_time = time.time()
    global last_run_time
    # Run the following code once every 120 seconds
    if last_run_time is None or current_time - last_run_time >= interval:
        # Fetch image as image string
        image_str = my_pepper.get_pepper_image_as_base64()
        # Send image string to new thread to update .env
        getimagethread = threading.Thread(target=chatGPT_interact.get_description_of_image_as_base64_threaded, args=(image_str,))
        getimagethread.start()

        # Update last run time
        last_run_time = current_time

def check_for_vision_on_arrival():
    print("check_for_vision_on_arrival")
    # Fetch image as image string
    image_str = my_pepper.get_pepper_image_as_base64()
    # Send image string to new thread to update .env
    getimagethread = threading.Thread(target=chatGPT_interact.get_description_of_image_as_base64_threaded, args=(image_str,))
    getimagethread.start()


def find_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def serve_website():
    # Automatically detect the IP
    ip_address = find_ip()

    httpd = SocketServer.TCPServer((ip_address, WEBPORT), CustomHandler)
    web_address = "http://{}:{}".format(ip_address, WEBPORT)
    print("Serving at {}".format(web_address))

    # Start the server in a new thread
    server_thread = threading.Thread(target=httpd.serve_forever)
    server_thread.daemon = True  # This ensures that the thread will close when the main program exits
    server_thread.start()

    return web_address


#Wake PEPPER Up

wake_pepper_up()


#Service Website
''' 5/12/24 - Activate when ready to fix website issue
# this code starts the website service in python so that it can serve the web page with the text.
# mypepper.have_pepper_say has code silenced to alter the web page and then serve it to the user. 
get_address = serve_website()
my_pepper.show_what_pepper_says(get_address, "hello")
'''



# Stop the speech recognition service
my_pepper.toggle_speech_recognition(True)  # This will disable speech recognition
            

# Create an instance of the class to manage person detection
global PersonDetectorInstance
_run_id = str(int(time.time()))
PersonDetectorInstance = PersonDetector("PersonDetectorInstance" + _run_id)

# Create an instance of the class to manage watching out for head taps
global HeadTappedInstance
HeadTappedInstance = HeadTapped("HeadTappedInstance" + _run_id)

#Take the first image
check_for_vision()

#get a sound check for ambient noise
manage_audio = manageAudio()



print(my_pepper.tts.getVoice())
my_pepper.tts.setVoice('naoenu')
# Default is naoenu
#['anna', 'naoenu', 'naomnc']

my_pepper.have_pepper_say("ahem")
#5/12/24 silenced as get_address isn't available until web server is figured out
'''
my_pepper.show_what_pepper_says(get_address, "Please be quiet for a moment as I check the room for noise.")
'''
annimation_status = my_pepper.pepperAnnimation(False) # make pepper quiet by not moving
manage_audio.ambient_sound_check()
annimation_status = my_pepper.pepperAnnimation(True) # alive again

#If settings indicate manual conversation without proximity detection...
if IS_MANUAL_CONVERSATION :
    
    #Pepper  will automatically think a person is near and wont trigger detection processes.
    sharedVars.ISNEAR = True

    # Initial greeting to get the conversation started
    firstResponse = chatGPT_interact.chat_with_gpt_stream_behaviors("Introduce yourself.")
    print(firstResponse)

    # Replace existing view with image
    
    # Silence the next 2 lines as the function will say it.
    #cleaned_firstResponse = chatGPT_interact.filter_text(firstResponse)
    #my_pepper.have_pepper_say(cleaned_firstResponse)
    #my_pepper.show_what_pepper_says(cleaned_firstResponse)


#my_pepper.tabletImage(IMAGEURL)
#print(IMAGEURL)
                      
                      
#setup thread event
thread_event = threading.Event()


#Get rid of the pesky downloaded package.
try:
    my_pepper.uninstallDefaultPackage("ht_cms_1_5")
    my_pepper.uninstallDefaultPackage("automatic-update")
    behavior_manager = ALProxy("ALBehaviorManager", PIP, PPORT)
    behavior_manager.stopAllBehaviors()

    # Connect to the package manager on the robot
    package_manager = ALProxy("PackageManager", PIP, PPORT)
    package_name = "ht_cms_1_5"  # replace with the actual package name
    package_manager.removePkg(package_name)
    installed_packages = package_manager.packages()
    if package_name not in installed_packages:
        print("Package %s has been successfully uninstalled.", package_name)
    else:
        print("Failed to uninstall package %s. , ", package_name)
except Exception:
    print("Package has been successfully uninstalled.")


print("FIRST CHECK BEFORE MAIN LOOP :" + str(sharedVars.ISNEAR))
try:
    while True:

        print("MAIN LOOP :" + str(sharedVars.ISNEAR))
        if sharedVars.ISNEAR:

            # stop prior chat if there is overlap
            #my_pepper.tts.stopAll()

            
            #setup thread event
            thread_event = threading.Event()

            # ---- Image Capture every 2 minutes ---
            #check_for_vision()
            print("vision checked")

            # change eye color to indicate recording for 5 seconds
            #eye_thread = threading.Thread(target=my_pepper.change_eye_color_with_turn, args=(0,255,0,2, 7))
            #eye_thread.start()

            # Record an audio file
            annimation_status = my_pepper.pepperAnnimation(False) # make pepper quiet by not moving
            file_path = manage_audio.record_audio()
            annimation_status = my_pepper.pepperAnnimation(True)  # make pepper animated again.
            
            '''#Eye rotation now handled in chat processes so that the eyes will stop when the chatting starts.
            # Start the rotate_eyes thread
            rotate_eyes_thread = threading.Thread(target=rotate_eyes)
            rotate_eyes_thread.start()
            '''
            
            # start the thinking thread
            thinking_thread  = threading.Thread(target=thinking)
            thinking_thread.start()

            # Perform transcription
            print("TRANSCRIPTION :" + str(sharedVars.ISNEAR))
            if sharedVars.ISNEAR: #ISNEAR might have been made false by this time if head tapped. 
                if file_path:
                    transcription_response = chatGPT_interact.transcribe_audio_file(file_path)
                    

                    #output the response
                    #if transcription_response:

                    transcription_text = transcription_response.text
                    #cleaned_transcription_text = chatGPT_interact.filter_text(transcription_text)
                    if transcription_text:
                        print("I said :" + transcription_text)

                    #12/27 chatbot_response = chatGPT_interact.chat_with_gpt(transcription_text)
                    #12/27 cleaned_chatbot_response = chatGPT_interact.filter_text(chatbot_response)
                    #12/27 print("Pepper said : " + chatbot_response)

                    # if the user has said something that indicates the conversation has come to an end
                    # make it seem that the user has left and reset conversation.
                    #if chatGPT_interact.isGoodbye(cleaned_chatbot_response) == "yes":
                    #    ISNEAR = False
                    #    chatGPT_interact.reset_chat()
                    #    print("***** END OF CONVERSATION *****")

                    #delete file and print the response
                    is_audio_file_deleted = str(manage_audio.delete_file(file_path))
                    print("audio deleted? - " + is_audio_file_deleted)

                    #else:
                    #    print("API request failed.")
                    #    cleaned_chatbot_response = "say 'uh oh.  Something didn't work quite right.' "

                    # Stop the thinking thread

            thread_event.set()
            thinking_thread.join()

            
            '''  #Eye rotation now handled in chat processes so that the eyes will stop when the chatting starts.
            rotate_eyes_thread.join()
            eye_thread.join()
            '''
            print("All threads should be stopped now")
            
            if sharedVars.ISNEAR: #it is possible that ISNEAR might be false if head tapped.
                # Have pepper say the response
                #try:
                    #12/27 added the following as the saying aspect is wrapped into the gpt streaming
                    chatbot_response = chatGPT_interact.chat_with_gpt_stream_behaviors(transcription_text)
                    #12/27 my_pepper.have_pepper_say(cleaned_chatbot_response)
                #except:
                    #my_pepper.have_pepper_say("Say 'Sorry I didn't get that, please say again.' ")
                    #chatGPT_interact.reset_chat()

        time.sleep(.5)

except KeyboardInterrupt:
    print("---Interrupted by user, stopping script----------------")
    print(IMAGE_PREPROMPT)
    #my_pepper.tts.stopAll()
    HeadTappedInstance.memory.unsubscribeToEvent("FrontTactilTouched", HeadTappedInstance.getName())
    #HeadTappedInstance.memory.unsubscribeToEvent("MiddleTactilTouched", HeadTappedInstance.getName())
    #HeadTappedInstance.memory.unsubscribeToEvent("RearTactilTouched", HeadTappedInstance.getName())
    PersonDetectorInstance.memory.unsubscribeToEvent("PeoplePerception/PeopleDetected", PersonDetectorInstance.getName())
    PersonDetectorInstance.memory.unsubscribeToEvent("PeoplePerception/JustArrived", PersonDetectorInstance.getName())
    PersonDetectorInstance.memory.unsubscribeToEvent("PeoplePerception/JustLeft", PersonDetectorInstance.getName())

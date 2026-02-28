
import random
import time
from naoqi import ALProxy
import base64
import cv2
import numpy as np
import string
import os
import socket
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

HTML_TOP = os.getenv("HTML_TOP")
HTML_BOTTOM = os.getenv("HTML_BOTTOM")

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
LOCAL = find_ip()

class myPepper:
    def __init__(self, PIP, PPORT, LOCAL):
        self.tts = ALProxy("ALTextToSpeech", PIP, PPORT)
        self.animated_tts = ALProxy("ALAnimatedSpeech", PIP, PPORT)
        self.behavior_manager = ALProxy("ALBehaviorManager", PIP, PPORT)
        self.leds = ALProxy("ALLeds",PIP,PPORT)
        self.PIP = PIP
        self.PPORT = PPORT
        
        self.HTML_TOP = HTML_TOP
        self.HTML_BOTTOM = HTML_BOTTOM
        
        
        # Get a proxy for the ALSpeechRecognition module
        self.asr_service = ALProxy("ALSpeechRecognition", self.PIP, self.PPORT)
        self.tablet_manager = ALProxy("ALTabletService", self.PIP, self.PPORT)
        self.package_manager = ALProxy("PackageManager", self.PIP, self.PPORT)
        self.autonomous_life = ALProxy("ALAutonomousLife", PIP, PPORT)
        self.motion = ALProxy("ALMotion", PIP, PPORT)

        self.last_phrase = None
        self.thinking_phrases = ["thinking", "processing", "contemplating","reflecting","Deliberating","considering","pondering","mulling"]
        
        self.resolution = 2    # VGA
        self.colorSpace = 11   # RGB
        self.alpha = 1.5 # Contrast control (1.0-3.0)
        self.beta = 50    # Brightness control (0-100)

    def initialize_autonomous_life(self):
        print("--> initialize_autonomous_life --")
        self.autonomous_life = ALProxy("ALAutonomousLife", self.PIP, self.PPORT)

    def initialize_leds(self):
        self.leds = ALProxy("ALLeds", self.PIP, self.PPORT)

    def is_module_running(self):
        print("--> is_module_running --")
        try:
            return self.autonomous_life.getState() is not None
        except Exception:
            return False
        
    def is_leds_module_running(self):
        try:
            self.leds.fadeRGB("FaceLeds", "white", 0.1)
            return True
        except Exception:
            return False
        


    def center_pepper_head(self, speed=0.15, wait=True):
        """
        Smoothly returns Pepper's head to the center (front-facing) position.
        
        :param robot_ip: IP address of the Pepper robot
        :param port: Port number (default is 9559)
        :param speed: Fraction of max speed (0.0 to 1.0), default 0.15 for smoothness
        :param wait: Whether to wait for motion to complete (default True)
        """
        try:
            
            self.motion.wakeUp()

            names = ["HeadYaw", "HeadPitch"]
            angles = [0.0, 0.0]  # radians
            fractionMaxSpeed = speed

            self.motion.setAngles(names, angles, fractionMaxSpeed)

            if wait:
                time.sleep(2)  # Adjust based on expected motion duration
            
            print("center_pepper_head SUCCESS")

        except Exception as e:
            print("Error in center_pepper_head:", e)

    def get_pepper_image_as_base64(self):
        video_service = ALProxy("ALVideoDevice", self.PIP, self.PPORT)
        resolution = self.resolution    # VGA
        colorSpace = self.colorSpace   # RGB

        videoClient = video_service.subscribe("python_client", resolution, colorSpace, 5)
        nao_image = video_service.getImageRemote(videoClient)

        video_service.unsubscribe(videoClient)

        # Step 2: Encode the Image
        image_width = nao_image[0]
        image_height = nao_image[1]
        array = nao_image[6]
        im = np.frombuffer(array, dtype=np.uint8).reshape((image_height, image_width, 3))

        # Adjust brightness and contrast
        alpha = self.alpha  # Contrast control (1.0-3.0)
        beta = self.beta    # Brightness control (0-100)

        adjusted = cv2.convertScaleAbs(im, alpha=alpha, beta=beta)

        # Save image to file in the 'envImages' directory
        random_filename = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10)) + '.jpg'
        env_images_dir = 'envImages'
        if not os.path.exists(env_images_dir):
            os.makedirs(env_images_dir)

        cv2.imwrite(os.path.join(env_images_dir, random_filename), adjusted)

        # Convert the image to base64
        _, buffer = cv2.imencode('.jpg', adjusted)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        #print(jpg_as_text)
        return jpg_as_text   
     
    def tabletImage(self, imageURL):
        print("--- MYPEPPER -> TABLETIMAGE -> IMAGEURL = " + str(imageURL))

        self.tablet_manager.showWebview(imageURL)
        #self.tablet_manager.reloadPage(True)
        print(self.tablet_manager.loadUrl(imageURL)) # showWebview

    def tabletShowSpeech(self, text):
        print("--- MYPEPPER -> TABLETSHOWSPEECH -> TEXT = " + str(text))

        html_content = str(self.HTML_TOP) + str(text) + str(self.HTML_BOTTOM)
        self.tablet_manager.showWebview("data:text/html," + html_content)
        print("WEB HTML SENT!")

    ''' pepperAnnimation - Old code - 6/27/24
    def pepperAnnimation(self, active):
        print("--- MYPEPPER -> PEPPERANNIMATION -> ACTIVE = " + str(active))

        # Set the state to "interactive" if true, or "solitary" if false
        set_state = "solitary"
        if active: 
            set_state = "interactive"
        
        self.autonomouse_life.setState(set_state)  

        return set_state
    '''
    
    def pepperAnnimation(self, active):
        print("--- MYPEPPER -> PEPPERANNIMATION -> ACTIVE = " + str(active))

        set_state = "solitary"
        
        if active: 
            set_state = "interactive"
            print("interactive")

        if not self.is_module_running():
            print("Module is not running, reinitializing...")
            self.initialize_autonomous_life()

        print("Ready1")
        try:
            self.autonomous_life.setState(set_state)  # Ensure 'autonomous_life' is used correctly
        except RuntimeError as e:
            if "module destroyed" in str(e):
                print("Module destroyed, reinitializing...")
                self.initialize_autonomous_life()
                self.autonomous_life.setState(set_state)
            else:
                print("Failed to set autonomous life state: {}".format(e))
        print("Ready2")
        return set_state
    
    def have_pepper_say(self, speaktext):
        print("--- MYPEPPER -> HAVE_PEPPER_SAY -> SPEAKTEXT = " + str(speaktext))
        try:
            # Connect to the Pepper's ALTextToSpeech module
            #tts = ALProxy("ALTextToSpeech", self.PIP, self.PPORT)
            
            # set the local configuration
            #12/29 configuration = {"bodyLanguageMode":"contextual"}

            # Stop any current talking.
            #12/29 self.tts.stopAll()

            # say the text with the local configuration
            ''' 5/12/24 - Activate when ready to fix website issue
            self.show_what_pepper_says(LOCAL, str(speaktext) )
            '''
            self.tabletShowSpeech(str(speaktext)) # Shhow the text being said.
            self.animated_tts.say(str(speaktext))  #, configuration


            
            # Set the desired speech parameters (optional)
            # tts.setParameter("speed", 80)  # Adjust the speed of speech (0-100)
            #tts.setParameter("pitchShift", 1.1)  # Adjust the pitch of speech (0.5-2.0)

            # Send text to be spoken
            #tts.say(speaktext)

        except (RuntimeError, ImportError) as e:
            # Handle specific exceptions
            print("An error occurred:", str(e))


    
    def show_what_pepper_says(self, getAddress, toSay):
        #need to create a web page that is hosted locally and then pepper can reference it.

        # Create HTML content to display the text
        html_content = """
        <!DOCTYPE html>
        <html lang='en'>
        <head>
            <meta charset='UTF-8'>
            <meta name='viewport' content='width=device-width, initial-scale=1.0'>
            <title>Document Title</title>
            <!-- Favicon link goes here -->
            <link rel='icon' href='favicon.ico' type='image/x-icon'>
            <!-- You can use a base64 image to have a blank favicon -->
            <link rel='icon' href='data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7' type='image/gif'>
        </head>
        <body>
            <h1>{}</h1>
        </body>
        </html>
        """.format(toSay)


        # Write this HTML content to a file
        with open("c:/Users/chris/vs_code_projects/genai/website/index.html", "w") as f:
            f.write(html_content)

        # Show the HTML on the tablet
        websiteAddress = getAddress+"/index.html"
        self.tablet_manager.showWebview(websiteAddress)
        self.tablet_manager.loadUrl(websiteAddress)
        print(websiteAddress)
        

    def pepper_thinking(self):
        print("--- MYPEPPER -> PEPPER_THINKING")

        # Get a random phrase that was not used previously
        new_phrase = random.choice(self.thinking_phrases)
        #while new_phrase == self.last_phrase:
        #    new_phrase = random.choice(self.thinking_phrases)
        
        self.last_phrase = new_phrase

        self.have_pepper_say(new_phrase)

        thinking_behaviors = []
        thinking_behaviors = [
            "animations/Stand/Gestures/Thinking_1",
            "animations/Stand/Gestures/Thinking_2",
            "animations/Stand/Gestures/Thinking_3",
            "animations/Stand/Gestures/Thinking_4",
            "animations/Stand/Gestures/Thinking_5",
            "animations/Stand/Gestures/Thinking_6",
            "animations/Stand/Gestures/Thinking_7",
            "animations/Stand/Gestures/Thinking_8"
        ]
        behavior = random.choice(thinking_behaviors)
        #self.behavior_manager.runBehavior(behavior, _async=True)



    def launchAndStopBehavior(self, behavior_name):
        print("--- MYPEPPER -> LAUNCHANDSTOPBEHAVIOR -> BEHAVIOR_NAME = " + str(behavior_name))

        """
        Launch and stop a behavior, if possible.
        """
        # Check that the behavior exists.
        if (self.behavior_manager.isBehaviorInstalled(behavior_name)):
            # Check that it is not already running.
            if (not self.behavior_manager.isBehaviorRunning(behavior_name)):
                # Launch behavior. This is a blocking call, use _async=True if you do not
                # want to wait for the behavior to finish.
                self.behavior_manager.runBehavior(behavior_name, _async=True)
                time.sleep(0.5)
            else:
                print("Behavior is already running.")

        else:
            print("Behavior not found.")

        return

    def start_behavior(self, behavior_name):
         # Stop all the behaviors
        #self.behavior_manager.stopAllBehaviors()

        # Check if the behavior is running before attempting to stop it
        if behavior_name in self.behavior_manager.getInstalledBehaviors():
        
            #start a new one
            self.behavior_manager.runBehavior(behavior_name)
            print("Behavior '{}' Started.".format(behavior_name))
            self.behavior_manager.stopAllBehaviors() # so it doesnt loop
        else:
            print("Behavior '{}' is not available.".format(behavior_name))

    def stop_all_behaviors(self):
        print("--- MYPEPPER -> STOP_ALL_BEHAVIORS ")

        """
        Stop all running behaviors.
        """
        # Get the list of running behaviors
        running_behaviors = self.behavior_manager.getRunningBehaviors()

        if running_behaviors:
            print("--- Stopping all behaviors-----------")

            # Stop each running behavior
            for behavior in running_behaviors:
                self.behavior_manager.stopBehavior(behavior)

            # Wait for some time to ensure the behaviors are stopped
            time.sleep(2.0)

            # Check if any behaviors are still running after stopping
            running_behaviors = self.behavior_manager.getRunningBehaviors()

            if not running_behaviors:
                print("All behaviors have been stopped.")
            else:
                print("Some behaviors could not be stopped.")
                print("Still running behaviors:")
                print(running_behaviors)
        else:
            print("No behaviors are currently running.")

    def fade_eyes(self, color_name, duration=0.1):
        """
        Fades the robot's eyes to the specified color.
        
        Parameters:
        color_name (str): The name of the color ("white", "red", "green", "blue", "yellow", "magenta", "cyan").
        duration (float): Time in seconds over which the color transition occurs.
        """
        try:

            # Fade the eyes to the specified color
            self.leds.fadeRGB("FaceLeds", color_name, duration)
            print("Fading eyes to {} over {} seconds.".format(color_name, duration))
        except Exception as e:
            print("Failed to fade eyes: {}".format(e))

    ''' change_eye_color_with_turn - OLD
    def change_eye_color_with_turn(self, red, green, blue, rotate_seconds, total_seconds):
        print("--- MYPEPPER -> CHANGE_EYE_COLOR_WITH_TURN ")

        red_value = red
        green_value = green
        blue_value = blue

        # Convert RGB to hexadecimal
        RGB_hex = (red_value << 16) + (green_value << 8) + blue_value

        print(hex(RGB_hex))
        self.leds.rotateEyes(RGB_hex, rotate_seconds, total_seconds)

        # To set eyes to white, set R,G,B to max intensity (1.0)
        self.leds.reset("FaceLeds")
    '''
    def change_eye_color_with_turn(self, red, green, blue, rotate_seconds, total_seconds):
        print("--- MYPEPPER -> CHANGE_EYE_COLOR_WITH_TURN ")

        red_value = red
        green_value = green
        blue_value = blue

        # Convert RGB to hexadecimal
        RGB_hex = (red_value << 16) + (green_value << 8) + blue_value

        print(hex(RGB_hex))

        if not self.is_leds_module_running():
            print("LEDs module is not running, reinitializing...")
            self.initialize_leds()
        
        try:
            self.leds.rotateEyes(RGB_hex, rotate_seconds, total_seconds)
        except RuntimeError as e:
            if "module destroyed" in str(e):
                print("LEDs module destroyed, reinitializing...")
                self.initialize_leds()
                self.leds.rotateEyes(RGB_hex, rotate_seconds, total_seconds)
            else:
                print("Failed to rotate eyes: {}".format(e))
        
        # To set eyes to white, set R,G,B to max intensity (1.0)
        self.leds.reset("FaceLeds")

    def toggle_speech_recognition(self, enable):
        print("--- MYPEPPER -> TOGGLE_SPEECH_RECOGNITION -> ENABLE = " + str(enable))
        
        if enable:
            # Enable the speech recognition service
            self.asr_service.setAudioExpression(True)
            self.asr_service.setVisualExpression(True)
            self.asr_service.pause(False)
            print("Speech recognition enabled")
        else:
            # Disable the speech recognition service
            self.asr_service.pause(True)
            print("Speech recognition disabled")

    def uninstallDefaultPackage(self, package_name):

        #Check to see if it is installed
        installed_packages = self.package_manager.packages()
        if package_name not in installed_packages:
            print("Package is not installed  - " + package_name) 
        else: #try to uninstall it
            self.package_manager.removePkg(package_name)
            installed_packages = self.package_manager.packages()
            if package_name not in installed_packages:
                print("Package was uninstalled - " + package_name)
            else:
                print("Failed to uninstall package - " + package_name) 


if __name__ == "__main__":

    import time

    PIP = "192.168.8.204"
    PPORT = 9559
    LOCAL = "192.168.8.226:8000"

    #Trigger thinking for a moment, then have pepper say something.
    myPepper = myPepper(PIP=PIP, PPORT=PPORT, LOCAL=LOCAL)
    myPepper.pepper_thinking()
    myPepper.change_eye_color_with_turn(200,200,200,2,1)
    time.sleep(0.1)
    myPepper.have_pepper_say(" oh, oh, oh, oh... stayin alive")
    myPepper.show_what_pepper_says(LOCAL, "oh, oh, oh, oh... stayin alive")

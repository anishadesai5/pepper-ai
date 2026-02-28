"""
Improved Main Application with Signal Disconnect Detection and Recovery
This version includes robust connection monitoring, automatic recovery, and graceful shutdown.
"""

import time
import threading
import os
import sharedVars
import SimpleHTTPServer
import SocketServer
import socket
from naoqi import ALProxy
from naoqi import ALBroker
from myPepper import myPepper
from recordAudio4 import manageAudio
from chatGPT import chatGPTInteract
from dotenv import load_dotenv
import OverrideBtn
from connectionMonitor import create_robust_pepper_system, RobustALModule
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

# Global variables for cleanup
connection_monitor = None
event_handler = None
my_pepper = None
chatGPT_interact = None
manage_audio = None
thread_event = None
HeadTappedInstance = None
PersonDetectorInstance = None
broker = None

# Used to determine when to take image and update preprompt
last_run_time = None
interval = 900  # Interval in seconds


class ImprovedHeadTapped(RobustALModule):
    """Enhanced HeadTapped class with robust connection handling."""
    
    def __init__(self, name, connection_monitor, event_handler):
        super(ImprovedHeadTapped, self).__init__(name, connection_monitor, event_handler)
        self.initialize()
    
    def initialize(self):
        """Initialize the head tapped handler."""
        try:
            # Subscribe to events using safe subscription
            self.safe_subscribe("FrontTactilTouched", "onTactilTouched")
            logger.info("HeadTapped module initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing HeadTapped: {e}")
    
    def onTactilTouched(self, key, value, message):
        """Handle tactile touch events with error handling."""
        try:
            logger.info(f"onTactilTouched: value = {value}")
            
            if value == 1.0:  # Tactile sensor is pressed
                if sharedVars.ISNEAR:
                    # Stop talking and stop listening
                    logger.info("GOODBYE - Head tapped while person near")
                    sharedVars.ISNEAR = False
                    
                    try:
                        tts = self.get_safe_proxy("ALTextToSpeech")
                        tts.stopAll()
                    except Exception as e:
                        logger.error(f"Error stopping TTS: {e}")
                    
                    global thread_event
                    if thread_event:
                        thread_event.set()
                    
                    try:
                        my_pepper.start_behavior("ht_animation_lib/tickle_1")
                    except Exception as e:
                        logger.error(f"Error starting tickle behavior: {e}")
                    
                    time.sleep(2)
                    
                else:
                    # Start listening
                    logger.info("HELLO - Head tapped while person not near")
                    
                    try:
                        tts = self.get_safe_proxy("ALTextToSpeech")
                        tts.stopAll()
                    except Exception as e:
                        logger.error(f"Error stopping TTS: {e}")
                    
                    if thread_event:
                        thread_event.set()
                    
                    # Setup for a new chat
                    try:
                        chatGPT_interact.reset_chat()
                        my_pepper.have_pepper_say("Ahh")
                        my_pepper.start_behavior("animations/Stand/Reactions/TouchHead_3")
                        my_pepper.stop_all_behaviors()
                    except Exception as e:
                        logger.error(f"Error during chat reset: {e}")
                    
                    sharedVars.ISNEAR = True
                    time.sleep(2)
                    
        except Exception as e:
            logger.error(f"Error in onTactilTouched: {e}")


class ImprovedPersonDetector(RobustALModule):
    """Enhanced PersonDetector class with robust connection handling."""
    
    def __init__(self, name, connection_monitor, event_handler, pip, pport):
        super(ImprovedPersonDetector, self).__init__(name, connection_monitor, event_handler)
        self.pip = pip
        self.pport = pport
        self.initialize()
    
    def initialize(self):
        """Initialize the person detector."""
        try:
            # Get proxies safely
            people_perception = self.get_safe_proxy("ALPeoplePerception")
            people_perception.setMaximumDetectionRange(0.5)
            
            # Subscribe to events using safe subscription
            self.safe_subscribe("PeoplePerception/JustArrived", "onJustArrived")
            self.safe_subscribe("PeoplePerception/JustLeft", "onJustLeft")
            
            logger.info("PersonDetector module initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing PersonDetector: {e}")
    
    def onJustArrived(self, value):
        """Handle person arrival events."""
        try:
            logger.info(f"ON_JUST_ARRIVED: value = {value}")
            # Additional logic can be added here as needed
        except Exception as e:
            logger.error(f"Error in onJustArrived: {e}")
    
    def onJustLeft(self, value):
        """Handle person departure events."""
        try:
            logger.info(f"ON_JUST_LEFT: value = {value}")
            # Additional logic can be added here as needed
        except Exception as e:
            logger.error(f"Error in onJustLeft: {e}")


class CustomHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = SimpleHTTPServer.SimpleHTTPRequestHandler.translate_path(self, path)
        relpath = os.path.relpath(path, os.getcwd())
        fullpath = os.path.join(os.getcwd(), WEBDIRECTORY, relpath)
        return fullpath


def thinking():
    """Enhanced thinking function with error handling."""
    logger.info("THINKING")
    start_time = time.time()
    
    try:
        center_head()
        logger.info("Thinking - vision checked")
        
        while not thread_event.is_set():
            elapsed_time = time.time() - start_time
            if elapsed_time > 3:
                try:
                    my_pepper.pepper_thinking()
                except Exception as e:
                    logger.error(f"Error in pepper_thinking: {e}")
                start_time = time.time()
            time.sleep(0.1)
            
    except Exception as e:
        logger.error(f"Error in thinking function: {e}")


def center_head():
    """Center pepper's head with error handling."""
    try:
        my_pepper.center_pepper_head()
    except Exception as e:
        logger.error(f"Error centering head: {e}")


def rotate_eyes():
    """Rotate eyes while waiting for response."""
    try:
        while not thread_event.is_set():
            logger.info("rotate_eyes")
            my_pepper.change_eye_color_with_turn(200, 200, 200, 1, 1)
    except Exception as e:
        logger.error(f"Error in rotate_eyes: {e}")


def wake_pepper_up():
    """Wake Pepper up with enhanced error handling."""
    try:
        if connection_monitor and connection_monitor.is_connected("ALMotion"):
            motion_proxy = connection_monitor.get_proxy("ALMotion")
            motion_proxy.wakeUp()
            logger.info("Pepper is now awake.")
        else:
            logger.warning("Motion proxy not available, using fallback method")
            motion_proxy = ALProxy("ALMotion", PIP, PPORT)
            motion_proxy.wakeUp()
            logger.info("Pepper is now awake (fallback).")
            
    except Exception as e:
        logger.error(f"Error when waking Pepper up: {e}")


def check_for_vision():
    """Enhanced vision checking with error handling."""
    try:
        logger.info("check_for_vision")
        current_time = time.time()
        global last_run_time
        
        if last_run_time is None or current_time - last_run_time >= interval:
            image_str = my_pepper.get_pepper_image_as_base64()
            getimagethread = threading.Thread(
                target=chatGPT_interact.get_description_of_image_as_base64_threaded, 
                args=(image_str,)
            )
            getimagethread.start()
            last_run_time = current_time
            
    except Exception as e:
        logger.error(f"Error in check_for_vision: {e}")


def find_ip():
    """Find local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP


def serve_website():
    """Start the website server."""
    try:
        ip_address = find_ip()
        httpd = SocketServer.TCPServer((ip_address, WEBPORT), CustomHandler)
        web_address = "http://{}:{}".format(ip_address, WEBPORT)
        logger.info(f"Serving at {web_address}")
        
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        return web_address
        
    except Exception as e:
        logger.error(f"Error starting web server: {e}")
        return None


def graceful_shutdown():
    """Perform graceful shutdown with proper cleanup."""
    global connection_monitor, event_handler, HeadTappedInstance, PersonDetectorInstance, broker
    
    logger.info("Starting graceful shutdown...")
    
    try:
        # Stop main loop
        if thread_event:
            thread_event.set()
        
        # Stop TTS if available
        try:
            if connection_monitor and connection_monitor.is_connected("ALTextToSpeech"):
                tts = connection_monitor.get_proxy("ALTextToSpeech")
                tts.stopAll()
        except Exception as e:
            logger.error(f"Error stopping TTS during shutdown: {e}")
        
        # Unsubscribe from events safely
        handlers = []
        if HeadTappedInstance:
            handlers.append(HeadTappedInstance)
        if PersonDetectorInstance:
            handlers.append(PersonDetectorInstance)
        
        if event_handler and handlers:
            event_handler.unsubscribe_all(handlers)
        
        # Stop connection monitoring
        if connection_monitor:
            connection_monitor.stop_monitoring()
        
        # Stop broker if it exists
        if broker:
            try:
                broker.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down broker: {e}")
        
        logger.info("Graceful shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during graceful shutdown: {e}")


def initialize_system():
    """Initialize the entire system with robust connection handling."""
    global connection_monitor, event_handler, my_pepper, chatGPT_interact, manage_audio
    global HeadTappedInstance, PersonDetectorInstance, broker, thread_event
    
    try:
        # Create broker
        broker = ALBroker("myBroker", "0.0.0.0", 0, PIP, PPORT)
        
        # Create robust connection system
        connection_monitor, event_handler = create_robust_pepper_system(PIP, PPORT)
        
        # Initialize core components
        my_pepper = myPepper(PIP=PIP, PPORT=PPORT, LOCAL=LOCAL)
        chatGPT_interact = chatGPTInteract(APIKEY=API_KEY)
        manage_audio = manageAudio()
        
        # Wake Pepper up
        wake_pepper_up()
        
        # Initialize modules with robust connection handling
        HeadTappedInstance = ImprovedHeadTapped("HeadTappedInstance", connection_monitor, event_handler)
        PersonDetectorInstance = ImprovedPersonDetector("PersonDetectorInstance", connection_monitor, event_handler, PIP, PPORT)
        
        # Setup speech and other components
        my_pepper.toggle_speech_recognition(True)
        
        # Initial vision check
        check_for_vision()
        
        # Voice setup
        try:
            my_pepper.tts.setVoice('naoenu')
            my_pepper.have_pepper_say("ahem")
        except Exception as e:
            logger.error(f"Error in voice setup: {e}")
        
        # Animation and audio setup
        annimation_status = my_pepper.pepperAnnimation(False)
        manage_audio.ambient_sound_check()
        annimation_status = my_pepper.pepperAnnimation(True)
        
        # Manual conversation setup if enabled
        if IS_MANUAL_CONVERSATION:
            sharedVars.ISNEAR = True
            try:
                firstResponse = chatGPT_interact.chat_with_gpt_stream_behaviors("Introduce yourself.")
                logger.info(firstResponse)
            except Exception as e:
                logger.error(f"Error in manual conversation setup: {e}")
        
        # Setup thread event
        thread_event = threading.Event()
        
        # Clean up pesky packages
        try:
            my_pepper.uninstallDefaultPackage("ht_cms_1_5")
            my_pepper.uninstallDefaultPackage("automatic-update")
        except Exception as e:
            logger.error(f"Error uninstalling packages: {e}")
        
        logger.info("System initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during system initialization: {e}")
        return False


def main_loop():
    """Enhanced main loop with robust error handling."""
    logger.info(f"FIRST CHECK BEFORE MAIN LOOP: {sharedVars.ISNEAR}")
    
    try:
        while True:
            logger.info(f"MAIN LOOP: {sharedVars.ISNEAR}")
            
            if sharedVars.ISNEAR:
                try:
                    # Setup thread event
                    thread_event.clear()
                    
                    # Vision check
                    check_for_vision()
                    logger.info("vision checked")
                    
                    # Record audio
                    annimation_status = my_pepper.pepperAnnimation(False)
                    file_path = manage_audio.record_audio()
                    annimation_status = my_pepper.pepperAnnimation(True)
                    
                    # Start thinking thread
                    thinking_thread = threading.Thread(target=thinking)
                    thinking_thread.start()
                    
                    # Process audio if available
                    if sharedVars.ISNEAR and file_path:
                        try:
                            transcription_response = chatGPT_interact.transcribe_audio_file(file_path)
                            
                            if transcription_response and transcription_response.text:
                                transcription_text = transcription_response.text
                                logger.info(f"User said: {transcription_text}")
                                
                                # Delete audio file
                                is_audio_file_deleted = manage_audio.delete_file(file_path)
                                logger.info(f"Audio deleted: {is_audio_file_deleted}")
                                
                                # Stop thinking
                                thread_event.set()
                                thinking_thread.join()
                                
                                logger.info("All threads should be stopped now")
                                
                                if sharedVars.ISNEAR:
                                    # Get chatbot response
                                    chatbot_response = chatGPT_interact.chat_with_gpt_stream_behaviors(transcription_text)
                                    
                        except Exception as e:
                            logger.error(f"Error processing audio: {e}")
                            thread_event.set()
                            thinking_thread.join()
                    
                except Exception as e:
                    logger.error(f"Error in main loop iteration: {e}")
                    # Ensure threads are cleaned up
                    if 'thinking_thread' in locals():
                        thread_event.set()
                        thinking_thread.join()
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user, stopping script...")
        graceful_shutdown()
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
        graceful_shutdown()


def main():
    """Main entry point."""
    logger.info("Starting improved Pepper application...")
    
    if initialize_system():
        main_loop()
    else:
        logger.error("Failed to initialize system")
        graceful_shutdown()


if __name__ == "__main__":
    main()

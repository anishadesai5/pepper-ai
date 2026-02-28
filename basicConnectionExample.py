"""
Basic Connection Monitoring Example for Python 2.7
Shows how to integrate connection monitoring into your existing main.py
"""

import time
import threading
import os
import sharedVars
from naoqi import ALBroker
from myPepper import myPepper
from recordAudio4 import manageAudio
from chatGPT import chatGPTInteract
from dotenv import load_dotenv
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
LOCAL = os.getenv("LOCAL")

# Global variables
connection_monitor = None
event_handler = None
my_pepper = None
chatGPT_interact = None
manage_audio = None
thread_event = None
HeadTappedInstance = None
PersonDetectorInstance = None
broker = None


class SafeHeadTapped(RobustALModule):
    """Enhanced HeadTapped class with robust connection handling."""
    
    def __init__(self, name, connection_monitor, event_handler):
        super(SafeHeadTapped, self).__init__(name, connection_monitor, event_handler)
        self.initialize()
    
    def initialize(self):
        """Initialize the head tapped handler."""
        try:
            # Subscribe to events using safe subscription
            self.safe_subscribe("FrontTactilTouched", "onTactilTouched")
            logger.info("HeadTapped module initialized successfully")
        except Exception as e:
            logger.error("Error initializing HeadTapped: {}".format(e))
    
    def onTactilTouched(self, key, value, message):
        """Handle tactile touch events with error handling."""
        try:
            logger.info("onTactilTouched: value = {}".format(value))
            
            if value == 1.0:  # Tactile sensor is pressed
                if sharedVars.ISNEAR:
                    # Stop talking and stop listening
                    logger.info("GOODBYE - Head tapped while person near")
                    sharedVars.ISNEAR = False
                    
                    try:
                        tts = self.get_safe_proxy("ALTextToSpeech")
                        tts.stopAll()
                    except Exception as e:
                        logger.error("Error stopping TTS: {}".format(e))
                    
                    global thread_event
                    if thread_event:
                        thread_event.set()
                    
                    time.sleep(2)
                    
                else:
                    # Start listening
                    logger.info("HELLO - Head tapped while person not near")
                    
                    try:
                        tts = self.get_safe_proxy("ALTextToSpeech")
                        tts.stopAll()
                    except Exception as e:
                        logger.error("Error stopping TTS: {}".format(e))
                    
                    if thread_event:
                        thread_event.set()
                    
                    # Setup for a new chat
                    try:
                        chatGPT_interact.reset_chat()
                        my_pepper.have_pepper_say("Hello")
                    except Exception as e:
                        logger.error("Error during chat reset: {}".format(e))
                    
                    sharedVars.ISNEAR = True
                    time.sleep(2)
                    
        except Exception as e:
            logger.error("Error in onTactilTouched: {}".format(e))


class SafePersonDetector(RobustALModule):
    """Enhanced PersonDetector class with robust connection handling."""
    
    def __init__(self, name, connection_monitor, event_handler, pip, pport):
        super(SafePersonDetector, self).__init__(name, connection_monitor, event_handler)
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
            logger.error("Error initializing PersonDetector: {}".format(e))
    
    def onJustArrived(self, value):
        """Handle person arrival events."""
        try:
            logger.info("ON_JUST_ARRIVED: value = {}".format(value))
        except Exception as e:
            logger.error("Error in onJustArrived: {}".format(e))
    
    def onJustLeft(self, value):
        """Handle person departure events."""
        try:
            logger.info("ON_JUST_LEFT: value = {}".format(value))
        except Exception as e:
            logger.error("Error in onJustLeft: {}".format(e))


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
            logger.error("Error stopping TTS during shutdown: {}".format(e))
        
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
        
        logger.info("Graceful shutdown completed")
        
    except Exception as e:
        logger.error("Error during graceful shutdown: {}".format(e))


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
        
        # Initialize modules with robust connection handling
        HeadTappedInstance = SafeHeadTapped("HeadTappedInstance", connection_monitor, event_handler)
        PersonDetectorInstance = SafePersonDetector("PersonDetectorInstance", connection_monitor, event_handler, PIP, PPORT)
        
        # Setup thread event
        thread_event = threading.Event()
        
        logger.info("System initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error("Error during system initialization: {}".format(e))
        return False


def main():
    """Main entry point."""
    logger.info("Starting basic connection monitoring example...")
    
    if not initialize_system():
        logger.error("Failed to initialize system")
        graceful_shutdown()
        return
    
    try:
        # Simple test loop
        logger.info("System running. Connection status:")
        status = connection_monitor.get_connection_status()
        for service, connected in status.items():
            status_icon = "OK" if connected else "FAIL"
            logger.info("  {} {}".format(service, status_icon))
        
        logger.info("Press Ctrl+C to stop...")
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user, stopping...")
        graceful_shutdown()
    except Exception as e:
        logger.error("Unexpected error: {}".format(e))
        graceful_shutdown()


if __name__ == "__main__":
    main()

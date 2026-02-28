"""
Connection Monitor and Recovery System for Pepper Robot
Provides comprehensive signal disconnect detection and automatic recovery mechanisms.
Python 2.7 compatible version.
"""

import time
import threading
import traceback
from naoqi import ALProxy
from naoqi import ALBroker
from naoqi import ALModule
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ConnectionMonitor:
    """
    Monitors connections to Pepper robot and provides automatic recovery mechanisms.
    """
    
    def __init__(self, pip, pport, monitoring_interval=5):
        self.pip = pip
        self.pport = pport
        self.monitoring_interval = monitoring_interval
        self.is_monitoring = False
        self.monitor_thread = None
        self.connections = {}
        self.connection_status = {}
        self.reconnect_attempts = {}
        self.max_reconnect_attempts = 3
        self.callbacks = {}
        
        # Initialize connection status tracking
        self.proxy_types = [
            "ALTextToSpeech", "ALAnimatedSpeech", "ALBehaviorManager", 
            "ALLeds", "ALSpeechRecognition", "ALTabletService", 
            "PackageManager", "ALAutonomousLife", "ALMotion", 
            "ALMemory", "ALVideoDevice", "ALPeoplePerception"
        ]
        
        for proxy_type in self.proxy_types:
            self.connection_status[proxy_type] = False
            self.reconnect_attempts[proxy_type] = 0
    
    def add_disconnect_callback(self, proxy_type, callback):
        """Add a callback to be executed when a specific proxy disconnects."""
        if proxy_type not in self.callbacks:
            self.callbacks[proxy_type] = []
        self.callbacks[proxy_type].append(callback)
    
    def test_connection(self, proxy_type):
        """Test if a specific proxy connection is working."""
        try:
            if proxy_type not in self.connections:
                self.connections[proxy_type] = ALProxy(proxy_type, self.pip, self.pport)
            
            # Test the connection with a safe method call
            proxy = self.connections[proxy_type]
            
            if proxy_type == "ALTextToSpeech":
                proxy.getAvailableLanguages()
            elif proxy_type == "ALMotion":
                proxy.getSummary()
            elif proxy_type == "ALMemory":
                proxy.getEventList()
            elif proxy_type == "ALBehaviorManager":
                proxy.getInstalledBehaviors()
            elif proxy_type == "ALLeds":
                proxy.listGroups()
            elif proxy_type == "ALVideoDevice":
                proxy.getCameraName(0)
            elif proxy_type == "ALAutonomousLife":
                proxy.getState()
            elif proxy_type == "ALTabletService":
                proxy.robotIp()
            elif proxy_type == "PackageManager":
                proxy.packages()
            elif proxy_type == "ALSpeechRecognition":
                proxy.getAvailableLanguages()
            elif proxy_type == "ALAnimatedSpeech":
                proxy.getTagsConfiguration()
            elif proxy_type == "ALPeoplePerception":
                proxy.getCurrentPeriod()
            
            return True
            
        except Exception as e:
            logger.warning("Connection test failed for {}: {}".format(proxy_type, e))
            return False
    
    def recover_connection(self, proxy_type):
        """Attempt to recover a failed connection."""
        try:
            logger.info("Attempting to recover connection for {}".format(proxy_type))
            
            # Remove the failed connection
            if proxy_type in self.connections:
                del self.connections[proxy_type]
            
            # Wait a moment before attempting reconnection
            time.sleep(1)
            
            # Create new connection
            self.connections[proxy_type] = ALProxy(proxy_type, self.pip, self.pport)
            
            # Test the new connection
            if self.test_connection(proxy_type):
                logger.info("Successfully recovered connection for {}".format(proxy_type))
                self.reconnect_attempts[proxy_type] = 0
                self.connection_status[proxy_type] = True
                return True
            else:
                logger.error("Failed to recover connection for {}".format(proxy_type))
                return False
                
        except Exception as e:
            logger.error("Error during connection recovery for {}: {}".format(proxy_type, e))
            return False
    
    def handle_disconnect(self, proxy_type):
        """Handle a detected disconnect."""
        self.connection_status[proxy_type] = False
        self.reconnect_attempts[proxy_type] += 1
        
        logger.warning("Disconnect detected for {} (attempt {})".format(proxy_type, self.reconnect_attempts[proxy_type]))
        
        # Execute callbacks
        if proxy_type in self.callbacks:
            for callback in self.callbacks[proxy_type]:
                try:
                    callback(proxy_type)
                except Exception as e:
                    logger.error("Error in disconnect callback for {}: {}".format(proxy_type, e))
        
        # Attempt recovery if within limits
        if self.reconnect_attempts[proxy_type] <= self.max_reconnect_attempts:
            if self.recover_connection(proxy_type):
                logger.info("Connection recovered for {}".format(proxy_type))
            else:
                logger.error("Failed to recover connection for {}".format(proxy_type))
        else:
            logger.error("Max reconnection attempts reached for {}".format(proxy_type))
    
    def monitor_connections(self):
        """Main monitoring loop."""
        logger.info("Starting connection monitoring...")
        
        while self.is_monitoring:
            for proxy_type in self.proxy_types:
                if not self.test_connection(proxy_type):
                    if self.connection_status[proxy_type]:  # Was connected, now disconnected
                        self.handle_disconnect(proxy_type)
                else:
                    # Connection is good
                    if not self.connection_status[proxy_type]:  # Was disconnected, now connected
                        logger.info("Connection restored for {}".format(proxy_type))
                        self.reconnect_attempts[proxy_type] = 0
                    self.connection_status[proxy_type] = True
            
            time.sleep(self.monitoring_interval)
    
    def start_monitoring(self):
        """Start the connection monitoring in a separate thread."""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self.monitor_connections)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            logger.info("Connection monitoring started")
    
    def stop_monitoring(self):
        """Stop the connection monitoring."""
        if self.is_monitoring:
            self.is_monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join()
            logger.info("Connection monitoring stopped")
    
    def get_proxy(self, proxy_type):
        """Get a proxy with automatic connection handling."""
        if proxy_type not in self.connections or not self.connection_status[proxy_type]:
            if not self.recover_connection(proxy_type):
                raise RuntimeError("Unable to establish connection to {}".format(proxy_type))
        
        return self.connections[proxy_type]
    
    def is_connected(self, proxy_type):
        """Check if a specific proxy is connected."""
        return self.connection_status.get(proxy_type, False)
    
    def get_connection_status(self):
        """Get the status of all connections."""
        return self.connection_status.copy()


class SafeEventHandler:
    """
    Provides safe event subscription and unsubscription with automatic recovery.
    """
    
    def __init__(self, connection_monitor):
        self.connection_monitor = connection_monitor
        self.subscriptions = {}  # event -> (handler, method_name)
        self.active_subscriptions = set()
    
    def subscribe_to_event(self, event_name, handler, method_name):
        """Safely subscribe to an event with automatic recovery."""
        try:
            memory = self.connection_monitor.get_proxy("ALMemory")
            
            # Store subscription info
            self.subscriptions[event_name] = (handler, method_name)
            
            # Subscribe to the event
            memory.subscribeToEvent(event_name, handler.getName(), method_name)
            self.active_subscriptions.add(event_name)
            
            logger.info("Successfully subscribed to event: {}".format(event_name))
            return True
            
        except Exception as e:
            logger.error("Failed to subscribe to event {}: {}".format(event_name, e))
            return False
    
    def unsubscribe_from_event(self, event_name, handler):
        """Safely unsubscribe from an event."""
        try:
            if event_name in self.active_subscriptions:
                memory = self.connection_monitor.get_proxy("ALMemory")
                
                # Check if the memory module is still available
                if self.connection_monitor.is_connected("ALMemory"):
                    memory.unsubscribeToEvent(event_name, handler.getName())
                    logger.info("Successfully unsubscribed from event: {}".format(event_name))
                else:
                    logger.warning("Memory module unavailable, skipping unsubscribe for: {}".format(event_name))
                
                self.active_subscriptions.discard(event_name)
                if event_name in self.subscriptions:
                    del self.subscriptions[event_name]
                
            return True
            
        except Exception as e:
            logger.error("Error unsubscribing from event {}: {}".format(event_name, e))
            # Still remove from our tracking even if unsubscribe failed
            self.active_subscriptions.discard(event_name)
            if event_name in self.subscriptions:
                del self.subscriptions[event_name]
            return False
    
    def resubscribe_all(self):
        """Resubscribe to all previously active events after a reconnection."""
        logger.info("Resubscribing to all events after reconnection...")
        
        for event_name, (handler, method_name) in self.subscriptions.items():
            if event_name not in self.active_subscriptions:
                self.subscribe_to_event(event_name, handler, method_name)
    
    def unsubscribe_all(self, handlers):
        """Safely unsubscribe from all events."""
        logger.info("Unsubscribing from all events...")
        
        for event_name in list(self.active_subscriptions):
            for handler in handlers:
                try:
                    self.unsubscribe_from_event(event_name, handler)
                except Exception as e:
                    logger.error("Error during cleanup unsubscribe: {}".format(e))


class RobustALModule(ALModule):
    """
    Base class for AL modules with built-in disconnect handling.
    """
    
    def __init__(self, name, connection_monitor, event_handler):
        try:
            ALModule.__init__(self, name)
            self.connection_monitor = connection_monitor
            self.event_handler = event_handler
            self.module_name = name
            logger.info("Initialized robust module: {}".format(name))
        except Exception as e:
            logger.error("Error initializing module {}: {}".format(name, e))
            raise
    
    def safe_subscribe(self, event_name, method_name):
        """Safely subscribe to an event."""
        return self.event_handler.subscribe_to_event(event_name, self, method_name)
    
    def safe_unsubscribe(self, event_name):
        """Safely unsubscribe from an event."""
        return self.event_handler.unsubscribe_from_event(event_name, self)
    
    def get_safe_proxy(self, proxy_type):
        """Get a proxy with automatic connection handling."""
        return self.connection_monitor.get_proxy(proxy_type)


def create_robust_pepper_system(pip, pport):
    """
    Factory function to create a robust Pepper system with connection monitoring.
    """
    # Create connection monitor
    connection_monitor = ConnectionMonitor(pip, pport)
    
    # Create event handler
    event_handler = SafeEventHandler(connection_monitor)
    
    # Set up ALMemory reconnection callback to resubscribe to events
    connection_monitor.add_disconnect_callback("ALMemory", lambda proxy_type: event_handler.resubscribe_all())
    
    # Start monitoring
    connection_monitor.start_monitoring()
    
    return connection_monitor, event_handler


if __name__ == "__main__":
    # Test the connection monitor
    pip = "192.168.8.204"
    pport = 9559
    
    monitor, handler = create_robust_pepper_system(pip, pport)
    
    try:
        # Monitor for 30 seconds
        time.sleep(30)
        print("Connection status:", monitor.get_connection_status())
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        monitor.stop_monitoring()
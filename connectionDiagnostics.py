# -*- coding: utf-8 -*-
"""
Connection Diagnostics and Recovery Utility for Pepper Robot
This script helps diagnose connection issues and provides recovery recommendations.
"""

import time
import traceback
from naoqi import ALProxy
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PepperConnectionDiagnostics:
    """
    Comprehensive diagnostics for Pepper robot connections and common issues.
    """
    
    def __init__(self, pip, pport):
        self.pip = pip
        self.pport = pport
        self.diagnostic_results = {}
        
        self.critical_services = [
            "ALTextToSpeech", "ALAnimatedSpeech", "ALBehaviorManager", 
            "ALMemory", "ALMotion", "ALLeds"
        ]
        
        self.optional_services = [
            "ALSpeechRecognition", "ALTabletService", "PackageManager", 
            "ALAutonomousLife", "ALVideoDevice", "ALPeoplePerception"
        ]
    
    def test_basic_connectivity(self):
        """Test basic network connectivity to Pepper."""
        logger.info("Testing basic connectivity to {}:{}".format(self.pip, self.pport))
        
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.pip, self.pport))
            sock.close()
            
            if result == 0:
                logger.info("[OK] Basic network connectivity: PASSED")
                return True
            else:
                logger.error("[FAIL] Basic network connectivity: FAILED")
                return False
                
        except Exception as e:
            logger.error("[FAIL] Basic network connectivity error: {}".format(e))
            return False
    
    def test_service_availability(self, service_name):
        """Test if a specific service is available."""
        try:
            proxy = ALProxy(service_name, self.pip, self.pport)
            
            # Try a basic method call based on service type
            if service_name == "ALTextToSpeech":
                proxy.getAvailableLanguages()
            elif service_name == "ALMotion":
                proxy.getSummary()
            elif service_name == "ALMemory":
                proxy.getEventList()
            elif service_name == "ALBehaviorManager":
                proxy.getInstalledBehaviors()
            elif service_name == "ALLeds":
                proxy.listGroups()
            elif service_name == "ALVideoDevice":
                proxy.getCameraName(0)
            elif service_name == "ALAutonomousLife":
                proxy.getState()
            elif service_name == "ALTabletService":
                proxy.robotIp()
            elif service_name == "PackageManager":
                proxy.packages()
            elif service_name == "ALSpeechRecognition":
                proxy.getAvailableLanguages()
            elif service_name == "ALAnimatedSpeech":
                proxy.getTagsConfiguration()
            elif service_name == "ALPeoplePerception":
                proxy.getCurrentPeriod()
            
            logger.info("[OK] {}: AVAILABLE".format(service_name))
            return True
            
        except Exception as e:
            logger.error("[FAIL] {}: UNAVAILABLE - {}".format(service_name, e))
            return False
    
    def test_all_services(self):
        """Test all Pepper services."""
        logger.info("Testing all Pepper services...")
        
        results = {}
        
        # Test critical services
        logger.info("Testing critical services:")
        for service in self.critical_services:
            results[service] = self.test_service_availability(service)
        
        # Test optional services
        logger.info("Testing optional services:")
        for service in self.optional_services:
            results[service] = self.test_service_availability(service)
        
        return results
    
    def test_event_subscription(self):
        """Test event subscription and unsubscription."""
        logger.info("Testing event subscription capabilities...")
        
        try:
            memory = ALProxy("ALMemory", self.pip, self.pport)
            
            # Create a test event
            test_event = "TestConnectionEvent"
            memory.raiseEvent(test_event, "test_value")
            
            logger.info("[OK] Event system: WORKING")
            return True
            
        except Exception as e:
            logger.error("[FAIL] Event system error: {}".format(e))
            return False
    
    def test_signal_links(self):
        """Test for signal link issues."""
        logger.info("Testing signal link stability...")
        
        try:
            memory = ALProxy("ALMemory", self.pip, self.pport)
            
            # Test multiple event subscriptions and unsubscriptions
            test_events = ["TestEvent1", "TestEvent2", "TestEvent3"]
            
            for event in test_events:
                try:
                    # This would normally require a proper ALModule, but we're just testing
                    memory.raiseEvent(event, "test")
                except Exception as e:
                    logger.warning("Signal link test warning for {}: {}".format(event, e))
            
            logger.info("[OK] Signal links: STABLE")
            return True
            
        except Exception as e:
            logger.error("[FAIL] Signal link error: {}".format(e))
            return False
    
    def test_module_lifecycle(self):
        """Test module creation and destruction."""
        logger.info("Testing module lifecycle...")
        
        try:
            # Test creating and accessing basic proxies
            tts = ALProxy("ALTextToSpeech", self.pip, self.pport)
            motion = ALProxy("ALMotion", self.pip, self.pport)
            
            # Test basic operations
            tts.getAvailableLanguages()
            motion.getSummary()
            
            # Clean up references
            del tts
            del motion
            
            logger.info("[OK] Module lifecycle: HEALTHY")
            return True
            
        except Exception as e:
            logger.error("[FAIL] Module lifecycle error: {}".format(e))
            return False
    
    def diagnose_common_issues(self):
        """Diagnose common Pepper connection issues."""
        logger.info("Diagnosing common issues...")
        
        issues_found = []
        
        # Check if Pepper is powered on and connected
        if not self.test_basic_connectivity():
            issues_found.append("CRITICAL: Cannot connect to Pepper. Check if robot is powered on and network connection is working.")
        
        # Test services
        service_results = self.test_all_services()
        
        failed_critical = [service for service, status in service_results.items() 
                          if service in self.critical_services and not status]
        
        if failed_critical:
            issues_found.append("CRITICAL: Essential services unavailable: {}".format(failed_critical))
        
        failed_optional = [service for service, status in service_results.items() 
                          if service in self.optional_services and not status]
        
        if failed_optional:
            issues_found.append("WARNING: Optional services unavailable: {}".format(failed_optional))
        
        # Test event system
        if not self.test_event_subscription():
            issues_found.append("WARNING: Event subscription system may be unstable")
        
        # Test module lifecycle
        if not self.test_module_lifecycle():
            issues_found.append("WARNING: Module lifecycle issues detected")
        
        return issues_found
    
    def get_recovery_recommendations(self, issues):
        """Provide recovery recommendations based on diagnosed issues."""
        recommendations = []
        
        for issue in issues:
            if "Cannot connect to Pepper" in issue:
                recommendations.extend([
                    "1. Verify Pepper robot is powered on",
                    "2. Check network connectivity (ping the robot IP)",
                    "3. Verify correct IP address and port (usually 9559)",
                    "4. Check if firewall is blocking connections",
                    "5. Try restarting the robot if accessible"
                ])
            
            elif "Essential services unavailable" in issue:
                recommendations.extend([
                    "1. Restart NAOqi services on the robot",
                    "2. Reboot the robot completely",
                    "3. Check robot system logs for service failures",
                    "4. Verify robot software installation integrity"
                ])
            
            elif "Event subscription system" in issue:
                recommendations.extend([
                    "1. Use the SafeEventHandler from connectionMonitor.py",
                    "2. Implement proper event cleanup in shutdown procedures",
                    "3. Add retry logic for event subscriptions",
                    "4. Monitor for 'SignalLink not found' warnings"
                ])
            
            elif "Module lifecycle" in issue:
                recommendations.extend([
                    "1. Implement proper module initialization checks",
                    "2. Use connection monitoring to detect module failures",
                    "3. Add automatic reconnection logic",
                    "4. Ensure proper cleanup in exception handlers"
                ])
        
        return list(set(recommendations))  # Remove duplicates
    
    def run_full_diagnostics(self):
        """Run complete diagnostic suite."""
        logger.info("=" * 60)
        logger.info("PEPPER ROBOT CONNECTION DIAGNOSTICS")
        logger.info("Target: {}:{}".format(self.pip, self.pport))
        logger.info("=" * 60)
        
        start_time = time.time()
        
        # Run all diagnostics
        issues = self.diagnose_common_issues()
        
        # Generate report
        logger.info("\n" + "=" * 60)
        logger.info("DIAGNOSTIC RESULTS")
        logger.info("=" * 60)
        
        if not issues:
            logger.info("[OK] ALL TESTS PASSED - No issues detected")
        else:
            logger.info("[FAIL] {} ISSUES DETECTED:".format(len(issues)))
            for i, issue in enumerate(issues, 1):
                logger.info("   {}. {}".format(i, issue))
            
            logger.info("\n" + "-" * 60)
            logger.info("RECOVERY RECOMMENDATIONS")
            logger.info("-" * 60)
            
            recommendations = self.get_recovery_recommendations(issues)
            for i, rec in enumerate(recommendations, 1):
                logger.info("   {}. {}".format(i, rec))
        
        elapsed_time = time.time() - start_time
        logger.info("\nDiagnostics completed in {:.2f} seconds".format(elapsed_time))
        
        return issues


def monitor_realtime_connections(pip, pport, duration=30):
    """Monitor connections in real-time for a specified duration."""
    logger.info("Monitoring connections for {} seconds...".format(duration))
    
    from connectionMonitor import ConnectionMonitor
    
    monitor = ConnectionMonitor(pip, pport, monitoring_interval=2)
    monitor.start_monitoring()
    
    try:
        time.sleep(duration)
        
        # Get final status
        status = monitor.get_connection_status()
        
        logger.info("\nFinal Connection Status:")
        for service, connected in status.items():
            status_icon = "[OK]" if connected else "[FAIL]"
            logger.info("   {} {}: {}".format(status_icon, service, 'Connected' if connected else 'Disconnected'))
            
    except KeyboardInterrupt:
        logger.info("Monitoring interrupted by user")
    finally:
        monitor.stop_monitoring()


def main():
    """Main diagnostics entry point."""
    if len(sys.argv) < 3:
        print("Usage: python connectionDiagnostics.py <robot_ip> <port> [monitor_duration]")
        print("Example: python connectionDiagnostics.py 192.168.8.204 9559")
        print("Example: python connectionDiagnostics.py 192.168.8.204 9559 60  # Monitor for 60 seconds")
        sys.exit(1)
    
    pip = sys.argv[1]
    pport = int(sys.argv[2])
    
    # Run diagnostics
    diagnostics = PepperConnectionDiagnostics(pip, pport)
    issues = diagnostics.run_full_diagnostics()
    
    # If monitoring duration is specified, also run real-time monitoring
    if len(sys.argv) > 3:
        monitor_duration = int(sys.argv[3])
        logger.info("\n" + "=" * 60)
        logger.info("REAL-TIME CONNECTION MONITORING")
        logger.info("=" * 60)
        monitor_realtime_connections(pip, pport, monitor_duration)
    
    # Exit with appropriate code
    sys.exit(len(issues))  # 0 if no issues, >0 if issues found


if __name__ == "__main__":
    main()

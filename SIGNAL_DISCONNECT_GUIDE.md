# Signal Disconnect Detection and Recovery Guide

This guide explains how to detect and recover from signal disconnects in your Pepper robot application.

## Overview

Your Pepper robot application can experience several types of signal disconnects:

1. **Network Connection Loss**: Lost connection to the robot
2. **Service Module Failures**: Individual NAOqi services becoming unavailable
3. **Event Subscription Issues**: SignalLink errors and event system failures
4. **Module Destruction**: Services being destroyed during runtime

## New Components

### 1. ConnectionMonitor (`connectionMonitor.py`)

A comprehensive monitoring system that:
- Continuously monitors all Pepper service connections
- Automatically detects disconnects
- Attempts automatic recovery
- Provides callbacks for custom handling
- Tracks connection status and retry attempts

**Key Features:**
- Real-time connection monitoring
- Automatic reconnection logic
- Safe proxy retrieval with error handling
- Configurable retry attempts and intervals

### 2. SafeEventHandler

Provides robust event subscription management:
- Safe event subscription/unsubscription
- Automatic resubscription after reconnection
- Graceful cleanup during shutdown
- Protection against "module destroyed" errors

### 3. RobustALModule

Base class for AL modules with built-in disconnect handling:
- Inherits from ALModule with added robustness
- Safe proxy access
- Error-resistant event handling
- Automatic recovery integration

### 4. ImprovedMain (`improvedMain.py`)

Enhanced main application featuring:
- Integrated connection monitoring
- Robust error handling throughout
- Graceful shutdown procedures
- Enhanced logging and diagnostics

### 5. Connection Diagnostics (`connectionDiagnostics.py`)

Diagnostic utility that:
- Tests all Pepper service connections
- Identifies common issues
- Provides recovery recommendations
- Real-time connection monitoring

## Usage

### Quick Start

1. **Replace your main.py with the improved version:**
   ```python
   python improvedMain.py
   ```

2. **Run diagnostics before starting your application:**
   ```bash
   python connectionDiagnostics.py 192.168.8.204 9559
   ```

### Detailed Usage

#### 1. Running Diagnostics

```bash
# Basic diagnostics
python connectionDiagnostics.py <robot_ip> <port>

# Diagnostics with real-time monitoring
python connectionDiagnostics.py <robot_ip> <port> <monitor_duration_seconds>

# Example
python connectionDiagnostics.py 192.168.8.204 9559 60
```

#### 2. Using Connection Monitoring in Your Code

```python
from connectionMonitor import create_robust_pepper_system, RobustALModule

# Create monitoring system
connection_monitor, event_handler = create_robust_pepper_system(PIP, PPORT)

# Get a safe proxy
try:
    tts = connection_monitor.get_proxy("ALTextToSpeech")
    tts.say("Hello, I'm protected from disconnects!")
except RuntimeError as e:
    print(f"Could not get TTS proxy: {e}")

# Check connection status
if connection_monitor.is_connected("ALTextToSpeech"):
    print("TTS is connected")
```

#### 3. Creating Robust AL Modules

```python
class MyRobustModule(RobustALModule):
    def __init__(self, name, connection_monitor, event_handler):
        super(MyRobustModule, self).__init__(name, connection_monitor, event_handler)
        
        # Safe event subscription
        self.safe_subscribe("SomeEvent", "myEventHandler")
    
    def myEventHandler(self, key, value, message):
        try:
            # Your event handling logic here
            tts = self.get_safe_proxy("ALTextToSpeech")
            tts.say("Event received!")
        except Exception as e:
            logger.error(f"Error in event handler: {e}")
```

#### 4. Adding Disconnect Callbacks

```python
def on_tts_disconnect(proxy_type):
    print(f"TTS disconnected! Attempting recovery...")

# Add callback
connection_monitor.add_disconnect_callback("ALTextToSpeech", on_tts_disconnect)
```

## Common Issues and Solutions

### Issue 1: "SignalLink not found" Warnings

**Symptoms:**
```
[W] qitype.signal: disconnect: No subscription found for SignalLink 13.
```

**Solution:**
- Use `SafeEventHandler` for all event subscriptions
- Ensure proper cleanup in shutdown procedures
- The improved main handles this automatically

### Issue 2: "Module Destroyed" Runtime Errors

**Symptoms:**
```
RuntimeError: ALMemory::unsubscribeToEvent module destroyed
```

**Solution:**
- Use `graceful_shutdown()` function
- Check connection status before unsubscribing
- The improved main includes proper shutdown handling

### Issue 3: Connection Timeouts

**Symptoms:**
- Intermittent proxy failures
- Services becoming unavailable

**Solution:**
- Enable connection monitoring: `connection_monitor.start_monitoring()`
- Use `get_proxy()` instead of direct `ALProxy` creation
- Implement retry logic in your application

### Issue 4: Event Resubscription After Reconnection

**Symptoms:**
- Events stop working after network interruption
- No event callbacks received

**Solution:**
- Use `SafeEventHandler` which automatically resubscribes
- Add ALMemory disconnect callback for manual resubscription

## Configuration Options

### ConnectionMonitor Parameters

```python
ConnectionMonitor(pip, pport, monitoring_interval=5)
```

- `monitoring_interval`: How often to check connections (seconds)
- `max_reconnect_attempts`: Maximum retry attempts per service
- Add custom callbacks for specific services

### Logging Configuration

```python
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
```

Adjust log level for more/less verbose output:
- `DEBUG`: Detailed connection information
- `INFO`: General status updates (recommended)
- `WARNING`: Only warnings and errors
- `ERROR`: Only critical errors

## Best Practices

### 1. Always Use Safe Proxies
```python
# Bad
tts = ALProxy("ALTextToSpeech", PIP, PPORT)

# Good
tts = connection_monitor.get_proxy("ALTextToSpeech")
```

### 2. Implement Proper Error Handling
```python
try:
    tts = connection_monitor.get_proxy("ALTextToSpeech")
    tts.say("Hello")
except RuntimeError as e:
    logger.error(f"TTS not available: {e}")
    # Implement fallback behavior
```

### 3. Use Graceful Shutdown
```python
def signal_handler(sig, frame):
    graceful_shutdown()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
```

### 4. Monitor Critical Services
```python
# Check if critical services are available
critical_services = ["ALTextToSpeech", "ALMotion", "ALMemory"]
for service in critical_services:
    if not connection_monitor.is_connected(service):
        logger.warning(f"Critical service {service} not available")
```

## Troubleshooting

### Running Diagnostics

If you're experiencing connection issues, run the diagnostic tool:

```bash
python connectionDiagnostics.py 192.168.8.204 9559
```

This will:
1. Test basic network connectivity
2. Check all Pepper services
3. Test event subscription system
4. Provide specific recovery recommendations

### Common Recovery Steps

1. **Network Issues:**
   - Check if Pepper is powered on
   - Verify IP address and port
   - Test network connectivity with ping

2. **Service Issues:**
   - Restart NAOqi services on robot
   - Reboot the robot
   - Check robot logs for errors

3. **Event System Issues:**
   - Use SafeEventHandler
   - Implement proper cleanup
   - Add automatic resubscription

4. **Module Lifecycle Issues:**
   - Use connection monitoring
   - Implement proper error handling
   - Add automatic recovery logic

## Migration from Original Code

To migrate from your original `main.py`:

1. **Replace event handling:**
   ```python
   # Old
   self.memory.subscribeToEvent("EventName", self.getName(), "method")
   
   # New
   self.safe_subscribe("EventName", "method")
   ```

2. **Replace proxy creation:**
   ```python
   # Old
   tts = ALProxy("ALTextToSpeech", PIP, PPORT)
   
   # New
   tts = connection_monitor.get_proxy("ALTextToSpeech")
   ```

3. **Add proper shutdown:**
   ```python
   # Old
   except KeyboardInterrupt:
       print("Stopping...")
   
   # New
   except KeyboardInterrupt:
       graceful_shutdown()
   ```

4. **Use the improved main:**
   - Copy your application-specific logic to `improvedMain.py`
   - The structure is the same but with added robustness

## Testing

### 1. Test Normal Operation
```bash
python improvedMain.py
```

### 2. Test Disconnect Recovery
- Temporarily disconnect network during operation
- Observer automatic reconnection in logs
- Verify functionality resumes after reconnection

### 3. Test Graceful Shutdown
- Press Ctrl+C during operation
- Verify clean shutdown without error messages
- Check that all events are properly unsubscribed

This comprehensive solution should eliminate the signal disconnect issues you were experiencing and provide a much more robust Pepper robot application.

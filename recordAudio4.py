import pyaudio
import wave
import os
import time
import numpy as np
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import math
import sharedVars
#NEW IMPORTS
try:
    import OverrideBtn
    OVERRIDE_BTN_AVAILABLE = True
except ImportError:
    OVERRIDE_BTN_AVAILABLE = False
import threading

# CONSTANTS:
CHUNK = 1024  # Number of audio frames per buffer
FORMAT = pyaudio.paInt16  # Format for the audio (16-bit int)
CHANNELS = 1  # Mono audio
RATE = 44100  # Sample rate (samples per second 44100)
BACKGROUNDTHRESHOLD = 60
AMBIENT_RMS = 3
NUMBER_OF_CHECKS = 4
OUTPUT_FILE = "recorded_audio.wav"
OUTPUT_FILE_WITH_PATH = ""
AMBIENT_CHECK_SECONDS = 2 #get average of ambient 
AMBIENT_PERCENT_OVER_DIFF = 0.2 #% of the difference over ambient_rms
# Function to compute RMS (Root Mean Square) power of audio signal.
# This gives us an indication of the volume.

CHAT_STATE_NEW = ""
CHAT_STATE_OLD = ""



class manageAudio():
    def __init__(self):

        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()

    def mad(self, data):
        # Assuming 'data' contains your audio samples
        # Calculate the median of the squared data
        data = np.array(data, dtype=float)
        median_squared = np.median(np.square(data))


        # Calculate the MAD by taking the square root of the median of squared data
        mad = np.sqrt(median_squared)

        return mad

    def rms(self, data):
        try:
            audioSignal = np.sqrt(np.mean(np.square(data))) #np.sqrt(np.mean(np.square(data)))
            #print(audioSignal)
            return audioSignal
        except RuntimeWarning:
            print("Warning: Unable to compute RMS for the given data. Returning 0.")
            return 0

    def ambient_sound_check(self):
        print("AMBIENT_SOUND_CHECK")
        # Collect ambient noise to set a threshold
        print("Please remain silent for ambient noise sampling...")
            
        # Calculate the average RMS power of ambient noise only once
        global BACKGROUNDTHRESHOLD
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
        while True: 
            
            frames_ambient = []
            for _ in range(0, int(RATE / CHUNK * AMBIENT_CHECK_SECONDS)):  # seconds of ambient noise
                data = stream.read(CHUNK)
                frames_ambient.append(data)

            #loop until we get a real number and not a "nan"
            global AMBIENT_RMS
            
            #AMBIENT_RMS = np.mean([self.mad(np.frombuffer(frame, dtype=np.int16)) for frame in frames_ambient])
            AMBIENT_RMS = np.median([self.mad(np.frombuffer(frame, dtype=np.int16)) for frame in frames_ambient])
            
            if AMBIENT_RMS < 3: #to give it a more realistic ambient bottom level.
                AMBIENT_RMS = 3

            print("Ambient threshold of %s set." % AMBIENT_RMS)
            if np.isnan(AMBIENT_RMS) == False:
                BACKGROUNDTHRESHOLD = ((100 - AMBIENT_RMS) * AMBIENT_PERCENT_OVER_DIFF) + AMBIENT_RMS #30% of the difference over ambient_rms
                print("BACKGROUNDTHRESHOLD " + str(BACKGROUNDTHRESHOLD))
                break
           

    # Function to handle the recording logic
    def record_audio(self):
        global CHAT_STATE_OLD
        global CHAT_STATE_NEW

        if sharedVars.ISNEAR: #this variable is controled by the main.py file.
            try:
                p = pyaudio.PyAudio()
                stream = p.open(format=FORMAT,
                                channels=CHANNELS,
                                rate=RATE,
                                input=True,
                                frames_per_buffer=CHUNK)
                
                global OUTPUT_FILE_WITH_PATH 
                OUTPUT_FILE_WITH_PATH = self.get_root_Dir() + OUTPUT_FILE
                #print(OUTPUT_FILE_WITH_PATH)

                hasStartedTalking = 0
            
                frames_speech = []
                silence_count = 0
                while True:
                    
                    data = stream.read(CHUNK)
                    #1/1/24 frames_speech.append(data)
                    current_rms = self.mad(np.frombuffer(data, dtype=np.int16))

                    #loop until you get a solid value
                    if np.isnan(current_rms) == False :

                        rms_difference_percentage = ( current_rms - AMBIENT_RMS)
                        #print("The difference is %s" % rms_difference_percentage)


                        # Check if the current chunk's volume is close to ambient volume
                        if rms_difference_percentage < BACKGROUNDTHRESHOLD and hasStartedTalking == NUMBER_OF_CHECKS  : 
                            #person was talking but went silent
                            frames_speech.append(data)
                            #print("STOPPED TALKING - DIFF = %s BkTh = %s CRNT = %s | AMB = %s" % (math.ceil(rms_difference_percentage),math.ceil(BACKGROUNDTHRESHOLD),math.ceil(current_rms),math.ceil(AMBIENT_RMS)) )
                            silence_count += 1
                            if CHAT_STATE_OLD != "WILL RESPOND" :
                                CHAT_STATE_NEW = "WILL RESPOND"

                        elif rms_difference_percentage > BACKGROUNDTHRESHOLD : #or rms_difference_percentage < (BACKGROUNDTHRESHOLD * -1) :

                            if hasStartedTalking < NUMBER_OF_CHECKS :
                                #maybe person was talking but need to wait for a few more to be sure
                                hasStartedTalking += 1
                                frames_speech.append(data)
                                #print(hasStartedTalking)
                                #print("NOISE? %s - DIFF = %s BkTh = %s =  CRNT = %s | AMB = %s" % (math.ceil(hasStartedTalking),math.ceil(rms_difference_percentage),math.ceil(BACKGROUNDTHRESHOLD),math.ceil(current_rms),math.ceil(AMBIENT_RMS)) )
                                if CHAT_STATE_OLD != "HEARD SOMETHING" :
                                    CHAT_STATE_NEW = "HEARD SOMETHING"
                            else : 
                                # person is talking
                                frames_speech.append(data)
                                #print("IS TALKING - DIFF = %s BkTh = %s =  CRNT = %s | AMB = %s" % (math.ceil(rms_difference_percentage),math.ceil(BACKGROUNDTHRESHOLD),math.ceil(current_rms),math.ceil(AMBIENT_RMS)) )
                                if CHAT_STATE_OLD != "ACTIVE LISTENING" :
                                    CHAT_STATE_NEW = "ACTIVE LISTENING"
                            silence_count = 0
                        
                        else :
                            # initial quiet. waiting for person to talk.
                            #print("WAITING - DIFF = %s BkTh = %s =  CRNT = %s | AMB = %s" % (math.ceil(rms_difference_percentage),math.ceil(BACKGROUNDTHRESHOLD),math.ceil(current_rms),math.ceil(AMBIENT_RMS)) )
                            
                            hasStartedTalking = 0
                            if CHAT_STATE_OLD != "PASSIVE LISTENING" :
                                CHAT_STATE_NEW = "PASSIVE LISTENING"

                        # Stop recording after 1 seconds of silence
                        if silence_count > int(RATE / CHUNK * 1) and sharedVars.ISRECORDING == False:
                            break
                
                    if CHAT_STATE_NEW != CHAT_STATE_OLD : # Only want to see when the chat state changes
                        CHAT_STATE_OLD = CHAT_STATE_NEW
                        print(CHAT_STATE_NEW)

                # Convert the speech frames to an audio segment for further processing
                audio_data = b''.join(frames_speech)
                audio_segment = AudioSegment(data=audio_data, sample_width=2, channels=CHANNELS, frame_rate=RATE)

                # Use pydub's detect_nonsilent to find non-silent parts and trim the beginning silence
                nonsilent_parts = detect_nonsilent(audio_segment, silence_thresh=audio_segment.dBFS-14)
                if nonsilent_parts:
                    start_time = max(nonsilent_parts[0][0] - 250, 0)  # Ensure start_time doesn't go negative
                    end_time = nonsilent_parts[-1][1] + 250  # Add 1 second to the end time
                    audio_segment = audio_segment[start_time:end_time]  # Trim the audio_segment with the 1 second buffer


                # Save the cleaned audio segment
                filename = OUTPUT_FILE_WITH_PATH
                audio_segment.export(filename, format="wav")
                #print("Saved as %s" % filename)

            finally:
                stream.stop_stream()
                stream.close()
                p.terminate()

            return OUTPUT_FILE_WITH_PATH
        

    def get_root_Dir(self):
            # Get the current working directory
            current_dir = os.getcwd()
            print("--- RECORDAUDIO1 -> GET_ROOT_DIR")
            #print("current_dir - " + current_dir)

            # Go one level up to the project_folder
            project_folder = os.path.dirname(current_dir)

            #print("project_folder - " + project_folder)

            # Now you can reference files or folders inside the project_folder
            audio_folder = os.path.join(current_dir, "audio")
            audio_folder = audio_folder + "\\"
            #print("audio_folder - " + audio_folder)

            return audio_folder
    
    def delete_file(self, file_path):
        print("--- RECORDAUDIO1 -> DELETE_FILE -> FILE_PATH = " + str(file_path))

        try:
            os.remove(file_path)
            return True
        except OSError as e:
            # OSError is raised if there's an issue with the file (e.g., it doesn't exist or permissions are insufficient).
            # You can handle specific errors if you want.
            print("Error: ", e)
            return False
        



if __name__ == "__main__":

    # Ensure safe handling of audio resources using try..finally

    manageaudio = manageAudio()
    manageaudio.ambient_sound_check()

    overridebtn = OverrideBtn.ovrBtn()
    buttonThread = threading.Thread(target=overridebtn.openButton)
    buttonThread.daemon = True
    buttonThread.start()

    audioFilePath = manageaudio.record_audio()




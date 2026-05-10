import pyaudiowpatch as pyaudio

def list_devices():
    p = pyaudio.PyAudio()
    try:
        print(f"PyAudio version: {pyaudio.get_portaudio_version_text()}")
        print("\nAvailable devices:")
        
        # Get default WASAPI host api info
        wasapi_info = None
        for i in range(p.get_host_api_count()):
            api_info = p.get_host_api_info_by_index(i)
            if api_info["name"].find("Windows WASAPI") != -1:
                wasapi_info = api_info
                break
        
        if wasapi_info is None:
            print("Windows WASAPI not found.")
            return

        for i in range(p.get_device_count()):
            dev_info = p.get_device_info_by_index(i)
            # Only show devices for WASAPI
            if dev_info["hostApi"] == wasapi_info["index"]:
                is_input = dev_info["maxInputChannels"] > 0
                is_output = dev_info["maxOutputChannels"] > 0
                is_loopback = p.get_host_api_info_by_index(dev_info["hostApi"])["name"].find("WASAPI") != -1 and dev_info["maxInputChannels"] > 0 and dev_info.get("isLoopbackDevice", False)
                
                print(f"ID {i}: {dev_info['name']}")
                print(f"  Channels: In={dev_info['maxInputChannels']}, Out={dev_info['maxOutputChannels']}")
                print(f"  Loopback: {dev_info.get('isLoopbackDevice', False)}")
                print("-" * 20)
                
    finally:
        p.terminate()

if __name__ == "__main__":
    list_devices()

import pyaudio
import numpy as np

# Set up audio stream
# reduce chunk size and sampling rate for lower latency
CHUNK_SIZE = 1024  # Number of audio frames per buffer
FORMAT = pyaudio.paInt16  # Audio format
CHANNELS = 1  # Mono audio
RATE = 44100  # Audio sampling rate (Hz)
p = pyaudio.PyAudio()

VOLUME_THRESHOLD = 20

# print info about audio devices
# let user select audio device
info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')

for i in range(0, numdevices):
    if (p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
        print("Input Device id ", i, " - ", p.get_device_info_by_host_api_device_index(0, i).get('name'))

print('select audio device:')
input_device = int(input())

# open audio input stream
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
                input_device_index=input_device)


def get_dominant_frequency(data, rate):
    fft_data = np.fft.fft(data)
    freqs = np.fft.fftfreq(len(data), 1 / rate)

    positive_freqs = freqs[:len(freqs)//2]
    fft_magnitude = np.abs(fft_data[:len(fft_data)//2])

    dominant_freq = positive_freqs[np.argmax(fft_magnitude)]
    return dominant_freq

def get_frequency():
    # Read audio data from stream
    data = stream.read(CHUNK_SIZE)

    # Convert audio data to numpy array
    data = np.frombuffer(data, dtype=np.int16)

    #Berechne den Lautstärkepegel des Signals (RMS-Wert)
    rms = np.sqrt(np.mean(np.square(data)))

    # Wenn die Lautstärke über dem Schwellenwert liegt, berechne die Frequenz
    if rms > VOLUME_THRESHOLD:
        dominant_frequency = get_dominant_frequency(data, RATE)
        return dominant_frequency
        #print(f"RMS: {rms:.2f}")
        #print(f"Dominante Frequenz: {dominant_frequency:.2f} Hz")
    else:
        return 0
        #print("Kein Signal über dem Schwellenwert.")


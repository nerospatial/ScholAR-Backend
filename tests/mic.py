import sounddevice as sd, wave

sr = 16000
print("Recording from PulseAudio/PipeWire…")
audio = sd.rec(int(sr*3), samplerate=sr, channels=1, dtype="int16")  # or "pipewire"
sd.wait()

with wave.open("pulse_test.wav", "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sr)
    wf.writeframes(audio.tobytes())

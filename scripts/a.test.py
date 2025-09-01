import sounddevice as sd

for i, d in enumerate(sd.query_devices()):
    print(f"{i:>3} | in:{d['max_input_channels']} out:{d['max_output_channels']} | {d['name']}")
print("Default devices (in, out):", sd.default.device)

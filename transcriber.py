import json
from pathlib import Path
from dataclasses import asdict

from faster_whisper import WhisperModel

model_size = "tiny"
model = WhisperModel(model_size, device="cpu", compute_type="int8")

def transcribe_audio(audio_path: Path):
	segments, info = model.transcribe(str(audio_path))

	result_data = {
		"info": asdict(info),
		"segments": [asdict(s) for s in segments]
	}
	json_str = json.dumps(result_data, indent=4)
	return json_str


# tts.py
import os
from google.cloud import texttospeech
from config import RU_AUDIO_DIR, EN_AUDIO_DIR

def get_audio_files(ru_texts, en_texts, use_google_tts):
    ru_audio_files = []
    en_audio_files = []
    os.makedirs(RU_AUDIO_DIR, exist_ok=True)
    os.makedirs(EN_AUDIO_DIR, exist_ok=True)

    for idx in range(len(ru_texts)):
        ru_path = os.path.join(RU_AUDIO_DIR, f"ru_{(idx + 1):03d}.mp3")
        en_path = os.path.join(EN_AUDIO_DIR, f"en_{(idx + 1):03d}.mp3")
        if use_google_tts:
            client = texttospeech.TextToSpeechClient.from_service_account_json(os.getenv("GOOGLE_TTS_KEY_PATH", "keys/anki-tts-key_2.json"))
            # Русский
            synthesis_input = texttospeech.SynthesisInput(text=ru_texts[idx])
            voice = texttospeech.VoiceSelectionParams(language_code="ru-RU", name="ru-RU-Standard-A")
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
            response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
            with open(ru_path, "wb") as out:
                out.write(response.audio_content)
            # Английский y
            synthesis_input = texttospeech.SynthesisInput(text=en_texts[idx])
            voice = texttospeech.VoiceSelectionParams(language_code="en-US", name="en-US-Standard-B")
            response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
            with open(en_path, "wb") as out:
                out.write(response.audio_content)
        ru_audio_files.append(ru_path if os.path.exists(ru_path) else "")
        en_audio_files.append(en_path if os.path.exists(en_path) else "")

    return ru_audio_files, en_audio_files
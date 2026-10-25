import subprocess
import shutil
import os
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
import streamlit as st

st.set_page_config(page_title="Meu Playback Pro", page_icon="🎵", layout="centered")

st.title("🎵 Meu Playback Pro")
st.write("Envie uma música para criar uma versão sem bateria.")
st.info("Para testar, use primeiro um trecho curto (até 1 minuto). O processamento pode demorar e o plano gratuito pode ter limite de memória.")

uploaded = st.file_uploader(
    "Escolha um arquivo de áudio",
    type=["mp3", "wav", "flac", "m4a", "ogg", "aac"]
)

def run_command(command):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=1800
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout or "Erro sem detalhes")[-5000:]
        raise RuntimeError(details)
    return result

if uploaded is not None:
    shutil.which("ffmpeg") is None:
    st.error("FFmpeg não foi instalado no servidor.")
    st.write("PATH:", os.environ.get("PATH", ""))
    st.stop()
    st.button("Remover bateria", type="primary"):
        with st.spinner("Preparando o áudio e separando os instrumentos. Isso pode levar alguns minutos..."):
            try:
                with tempfile.TemporaryDirectory(prefix="meu_playback_") as temp_name:
                    work = Path(temp_name)
                    original = work / f"entrada.{uploaded.name.rsplit('.', 1)[-1].lower()}"
                    original.write_bytes(uploaded.getvalue())

                    wav_input = work / "entrada_convertida.wav"
                    # Re-encode the upload to a clean WAV before passing it to Demucs.
                    run_command([
                        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                        "-i", str(original), "-vn", "-ac", "2", "-ar", "44100",
                        "-c:a", "pcm_s16le", str(wav_input)
                    ])

                    separated_dir = work / "separado"
                    run_command([
                        "python", "-m", "demucs",
                        "-n", "htdemucs",
                        "--device", "cpu",
                        "--out", str(separated_dir),
                        str(wav_input)
                    ])

                    stems_dir = separated_dir / "htdemucs" / wav_input.stem
                    vocals_path = stems_dir / "vocals.wav"
                    bass_path = stems_dir / "bass.wav"
                    other_path = stems_dir / "other.wav"

                    missing = [p.name for p in (vocals_path, bass_path, other_path) if not p.exists()]
                    if missing:
                        raise RuntimeError("O Demucs terminou, mas não encontrei estas faixas: " + ", ".join(missing))

                    vocals, sr = sf.read(vocals_path, dtype="float32", always_2d=True)
                    bass, _ = sf.read(bass_path, dtype="float32", always_2d=True)
                    other, _ = sf.read(other_path, dtype="float32", always_2d=True)

                    length = min(len(vocals), len(bass), len(other))
                    mix = vocals[:length] + bass[:length] + other[:length]
                    # Avoid clipping after summing the stems.
                    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
                    if peak > 0.99:
                        mix = mix * (0.99 / peak)

                    output_path = work / "Meu_Playback_sem_bateria.wav"
                    sf.write(output_path, mix, sr, subtype="PCM_16")

                    audio_bytes = output_path.read_bytes()
                    st.success("Pronto! A versão sem bateria foi criada.")
                    st.audio(audio_bytes, format="audio/wav")
                    st.download_button(
                        "⬇️ Baixar playback sem bateria",
                        data=audio_bytes,
                        file_name="Meu_Playback_sem_bateria.wav",
                        mime="audio/wav"
                    )
            except subprocess.TimeoutExpired:
                st.error("O processamento passou de 30 minutos e foi interrompido. Tente um trecho menor.")
            except FileNotFoundError as exc:
                st.error(f"Não encontrei um programa necessário: {exc}. Confira se packages.txt contém ffmpeg e se o app foi reiniciado.")
            except Exception as exc:
                st.error("Não foi possível processar esse áudio.")
                with st.expander("Ver detalhes técnicos do erro"):
                    st.code(str(exc))
                st.caption("Se continuar falhando, teste um arquivo curto em MP3 ou WAV. O servidor gratuito pode não ter memória suficiente para músicas longas.")

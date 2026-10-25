import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import soundfile as sf
import streamlit as st

st.set_page_config(page_title="Meu Playback Pro", page_icon="🎵", layout="centered")
st.title("🎵 Meu Playback Pro")
st.write("Envie uma música para criar uma versão sem bateria.")
st.info("Teste primeiro com um trecho curto. A separação pode demorar e o servidor gratuito pode ter limite de memória.")

uploaded = st.file_uploader("Escolha um arquivo de áudio", type=["mp3", "wav", "flac", "m4a", "ogg", "aac"])

def run_command(command):
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=1800)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Erro sem detalhes")[-5000:])
    return result

if uploaded is not None:
    st.audio(uploaded)
    if st.button("Remover bateria", type="primary"):
        with st.spinner("Preparando o áudio e separando os instrumentos. Isso pode levar alguns minutos..."):
            try:
                with tempfile.TemporaryDirectory(prefix="meu_playback_") as temp_name:
                    work = Path(temp_name)
                    suffix = Path(uploaded.name).suffix.lower() or ".audio"
                    original = work / f"entrada{suffix}"
                    original.write_bytes(uploaded.getvalue())
                    wav_input = work / "entrada_convertida.wav"
                    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                    run_command([ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-y", "-i", str(original), "-vn", "-ac", "2", "-ar", "44100", "-c:a", "pcm_s16le", str(wav_input)])
                    separated_dir = work / "separado"
                    run_command([sys.executable, "-m", "demucs", "-n", "htdemucs", "--device", "cpu", "--out", str(separated_dir), str(wav_input)])
                    stems_dir = separated_dir / "htdemucs" / wav_input.stem
                    stems = [stems_dir / name for name in ("vocals.wav", "bass.wav", "other.wav")]
                    missing = [p.name for p in stems if not p.exists()]
                    if missing:
                        raise RuntimeError("Não encontrei as faixas: " + ", ".join(missing))
                    vocals, sr = sf.read(stems[0], dtype="float32", always_2d=True)
                    bass, _ = sf.read(stems[1], dtype="float32", always_2d=True)
                    other, _ = sf.read(stems[2], dtype="float32", always_2d=True)
                    length = min(len(vocals), len(bass), len(other))
                    mix = vocals[:length] + bass[:length] + other[:length]
                    peak = float(np.max(np.abs(mix))) if mix.size else 0.0
                    if peak > 0.99:
                        mix *= 0.99 / peak
                    output_path = work / "Meu_Playback_sem_bateria.wav"
                    sf.write(output_path, mix, sr, subtype="PCM_16")
                    audio_bytes = output_path.read_bytes()
                    st.success("Pronto! A versão sem bateria foi criada.")
                    st.audio(audio_bytes, format="audio/wav")
                    st.download_button("⬇️ Baixar playback sem bateria", data=audio_bytes, file_name="Meu_Playback_sem_bateria.wav", mime="audio/wav")
            except subprocess.TimeoutExpired:
                st.error("O processamento passou de 30 minutos. Tente um trecho menor.")
            except Exception as exc:
                st.error("Não foi possível processar esse áudio.")
                with st.expander("Ver detalhes técnicos do erro"):
                    st.code(str(exc))
                st.caption("Se o erro mencionar memória, tente um trecho menor. O servidor gratuito pode não conseguir processar músicas longas.")

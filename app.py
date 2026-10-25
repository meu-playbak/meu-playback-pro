import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
import streamlit as st

st.set_page_config(page_title="Meu Playback Pro", page_icon="🎵", layout="centered")

st.markdown("""
<style>
.stApp {background: linear-gradient(160deg, #100b24 0%, #211044 55%, #090914 100%); color: white;}
h1, h2, h3, p, label {color: white !important;}
div[data-testid="stFileUploader"] {background: rgba(255,255,255,.06); padding: 14px; border-radius: 14px;}
.stButton button {background:#8b5cf6;color:white;border:0;border-radius:12px;font-weight:700;}
</style>
""", unsafe_allow_html=True)

st.title("🎵 Meu Playback Pro")
st.write("Retire a bateria de uma música e crie um playback para cantar.")
st.info("Envie um arquivo de áudio que você tem direito de usar. O processamento pode demorar e exige memória do servidor.")

uploaded = st.file_uploader("Escolha uma música", type=["mp3", "wav", "flac", "ogg", "m4a"])
st.caption("Formatos aceitos: MP3, WAV, FLAC, OGG e M4A. Arquivos grandes podem falhar em hospedagens gratuitas.")

if uploaded is not None:
    st.audio(uploaded)
    if st.button("🥁 Retirar bateria", use_container_width=True):
        with st.spinner("Processando a música com inteligência artificial. Aguarde..."):
            try:
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    input_path = root / f"entrada_{Path(uploaded.name).name}"
                    input_path.write_bytes(uploaded.getvalue())
                    out_dir = root / "separado"
                    cmd = [
                        sys.executable, "-m", "demucs",
                        "-n", "htdemucs",
                        "--device", "cpu",
                        "--segment", "5",
                        "--out", str(out_dir),
                        str(input_path),
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
                    if result.returncode != 0:
                        details = (result.stderr or result.stdout or "Erro sem detalhes")[-2500:]
                        st.error("Não foi possível processar este arquivo. O servidor pode não ter memória suficiente.")
                        st.code(details)
                        st.stop()

                    candidates = list(out_dir.rglob("drums.wav"))
                    if not candidates:
                        st.error("O processamento terminou, mas as faixas separadas não foram encontradas.")
                        st.stop()
                    drums_path = candidates[0]
                    stem_dir = drums_path.parent
                    needed = ["vocals.wav", "bass.wav", "other.wav"]
                    missing = [name for name in needed if not (stem_dir / name).exists()]
                    if missing:
                        st.error("Não foram encontradas todas as faixas necessárias: " + ", ".join(missing))
                        st.stop()

                    tracks = []
                    sample_rate = None
                    for name in needed:
                        audio, sr = sf.read(stem_dir / name, dtype="float32", always_2d=True)
                        if sample_rate is None:
                            sample_rate = sr
                        if sr != sample_rate:
                            st.error("As faixas ficaram com taxas de amostragem diferentes.")
                            st.stop()
                        tracks.append(audio)
                    min_len = min(len(track) for track in tracks)
                    mix = np.sum([track[:min_len] for track in tracks], axis=0)
                    peak = float(np.max(np.abs(mix))) if mix.size else 0
                    if peak > 1:
                        mix = mix / peak * 0.98
                    result_path = root / "playback_sem_bateria.wav"
                    sf.write(result_path, mix, sample_rate, subtype="PCM_16")
                    audio_bytes = result_path.read_bytes()

                st.success("Pronto! A bateria foi separada da música.")
                st.audio(audio_bytes, format="audio/wav")
                st.download_button(
                    "⬇️ Baixar playback sem bateria",
                    data=audio_bytes,
                    file_name="playback_sem_bateria.wav",
                    mime="audio/wav",
                    use_container_width=True,
                )
            except subprocess.TimeoutExpired:
                st.error("O processamento demorou demais. Tente um arquivo menor.")
            except Exception as exc:
                st.error("Ocorreu um erro durante o processamento.")
                st.code(str(exc))
st.divider()
st.caption("Meu Playback Pro • A separação por IA pode deixar pequenos resíduos de bateria. O áudio enviado é processado temporariamente durante a sessão.")

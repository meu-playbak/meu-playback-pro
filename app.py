import os
import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import soundfile as sf
import streamlit as st

# Reduz o paralelismo para tentar evitar picos de uso de CPU no servidor gratuito.
THREADS = "2"
os.environ["OMP_NUM_THREADS"] = THREADS
os.environ["MKL_NUM_THREADS"] = THREADS
os.environ["OPENBLAS_NUM_THREADS"] = THREADS
os.environ["NUMEXPR_NUM_THREADS"] = THREADS

st.set_page_config(page_title="Meu Playback Pro", page_icon="🎵", layout="centered")
st.title("🎵 Meu Playback Pro")
st.write("Envie uma música para criar uma versão sem bateria.")
st.info("Para ajudar o servidor gratuito, teste primeiro com um trecho de 1 a 3 minutos. Músicas longas podem demorar ou atingir os limites da hospedagem.")

uploaded = st.file_uploader("Escolha um arquivo de áudio", type=["mp3", "wav", "flac", "m4a", "ogg", "aac"])
st.subheader("🎚️ Escolha os instrumentos")

manter = {
    "Voz": st.checkbox("Manter voz", value=True),
    "Bateria": st.checkbox("Manter bateria", value=False),
    "Baixo": st.checkbox("Manter baixo", value=True),
    "Outros instrumentos": st.checkbox(
        "Manter outros instrumentos", value=True
    ),
}

st.subheader("🔊 Volume de cada instrumento")

volumes = {
    "Voz": st.slider("Volume da voz", 0.0, 2.0, 1.0, 0.1),
    "Bateria": st.slider("Volume da bateria", 0.0, 2.0, 1.0, 0.1),
    "Baixo": st.slider("Volume do baixo", 0.0, 2.0, 1.0, 0.1),
    "Outros instrumentos": st.slider(
        "Volume dos outros instrumentos", 0.0, 2.0, 1.0, 0.1
    ),
}

def run_command(command, env=None):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=1800,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Erro sem detalhes")[-5000:])
    return result

if uploaded is not None:
    st.audio(uploaded)
    if st.button("Remover bateria", type="primary"):
        with st.spinner("Separando os instrumentos. Isso pode levar alguns minutos..."):
            try:
                with tempfile.TemporaryDirectory(prefix="meu_playback_") as temp_name:
                    work = Path(temp_name)
                    suffix = Path(uploaded.name).suffix.lower() or ".audio"
                    original = work / f"entrada{suffix}"
                    original.write_bytes(uploaded.getvalue())

                    wav_input = work / "entrada_convertida.wav"
                    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                    run_command([
                        ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-y",
                        "-i", str(original), "-vn", "-ac", "2", "-ar", "44100",
                        "-c:a", "pcm_s16le", str(wav_input)
                    ])

                    separated_dir = work / "separado"
                    env = os.environ.copy()
                    run_command([
                        sys.executable, "-m", "demucs",
                        "-n", "htdemucs",
                        "--device", "cpu",
                        "--shifts", "1",
                        "--overlap", "0.1",
                        "--out", str(separated_dir),
                        str(wav_input),
                    ], env=env)
                    stems_dir = separated_dir / "htdemucs" / wav_input.stem

                    nomes = {
                        "Voz": "vocals.wav",
                        "Bateria": "drums.wav",
                        "Baixo": "bass.wav",
                        "Outros instrumentos": "other.wav",
                    }

                    mix = None
                    sr = None

                    for instrumento, arquivo in nomes.items():
                        if manter[instrumento]:
                            caminho = stems_dir / arquivo

                            if not caminho.exists():
                                raise RuntimeError(
                                    f"Não encontrei a faixa {arquivo}"
                                )

                            audio, taxa = sf.read(
                                caminho, dtype="float32", always_2d=True
                            )

                            if mix is None:
                                mix = audio * volumes[instrumento]
                                sr = taxa
                            else:
                                tamanho = min(len(mix), len(audio))
                                mix = mix[:tamanho] + (
                                    audio[:tamanho] * volumes[instrumento]
                                )

                    if mix is None:
                        raise RuntimeError(
                            "Selecione pelo menos um instrumento para manter."
                        )

                    peak = float(np.max(np.abs(mix))) if mix.size else 0.0

                    if peak > 0.99:
                        mix *= 0.99 / peak

                    output_path = work / "Meu_Playback_sem_bateria.wav"
                    sf.write(output_path, mix, sr, subtype="PCM_16")
                    audio_bytes = output_path.read_bytes()
                    st.success("Pronto! A versão sem bateria foi criada.")
                    st.audio(audio_bytes, format="audio/wav")
                    st.download_button(
                        "⬇️ Baixar playback sem bateria",
                        data=audio_bytes,
                        file_name="Meu_Playback_sem_bateria.wav",
                        mime="audio/wav",
                    )
            except subprocess.TimeoutExpired:
                st.error("O processamento passou de 30 minutos. Tente um trecho menor.")
            except Exception as exc:
                st.error("Não foi possível processar esse áudio.")
                with st.expander("Ver detalhes técnicos do erro"):
                    st.code(str(exc))
                st.caption("Se o erro mencionar memória ou recursos, tente um trecho menor. A hospedagem gratuita tem limites.")


import os
import subprocess
import sys
import tempfile
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import soundfile as sf
import streamlit as st

THREADS = "2"
os.environ["OMP_NUM_THREADS"] = THREADS
os.environ["MKL_NUM_THREADS"] = THREADS
os.environ["OPENBLAS_NUM_THREADS"] = THREADS
os.environ["NUMEXPR_NUM_THREADS"] = THREADS

st.set_page_config(
    page_title="Meu Playback Pro",
    page_icon="🎵",
    layout="centered",
)

st.markdown("""
<style>
/* Fundo e largura da página */
.stApp {
    background: linear-gradient(180deg, #101326 0%, #191b35 100%);
    color: #f7f7ff;
}


.block-container {
max-width: 850px;
padding-top: 2rem;
padding-bottom: 3rem;
}

/* Títulos */
h1, h2, h3 {
color: #ffffff !important;
letter-spacing: -0.5px;
}

/* Cartões de avisos */
div[data-testid="stAlert"] {
border-radius: 14px;
border: 1px solid #393d65;
}

/* Campos para enviar áudio */
div[data-testid="stFileUploader"] {
background: #20233f;
border: 1px dashed #7779bc;
border-radius: 14px;
padding: 12px;
}

/* Botões */
.stButton > button,
.stDownloadButton > button {
width: 100%;
min-height: 48px;
border-radius: 12px;
border: none;
background: linear-gradient(90deg, #7665f7, #a15cf5);
color: white;
font-weight: 700;
transition: 0.2s ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
border: 1px solid #ffffff;
color: white;
filter: brightness(1.1);
}

/* Caixas e controles */
div[data-testid="stExpander"] {
border: 1px solid #393d65;
border-radius: 12px;
}

div[data-testid="stAudio"] {
width: 100%;
border-radius: 12px;
}

/* Espaçamento em celulares */
@media (max-width: 600px) {
.block-container {
padding: 1rem 0.8rem 2rem 0.8rem;
}

h1 {
font-size: 1.8rem !important;
}
}
</style>
""", unsafe_allow_html=True)


st.markdown("""
<div style="
    background: linear-gradient(135deg, #292c56, #54358a);
    padding: 28px 22px;
    border-radius: 20px;
    margin-bottom: 22px;
    border: 1px solid #6560a5;
">
    <div style="font-size: 38px;">🎵</div>
    <div style="
        font-size: 30px;
        font-weight: 800;
        color: white;
        margin-top: 6px;
    ">Meu Playback Pro</div>
    <div style="
        font-size: 15px;
        color: #e5e2ff;
        margin-top: 8px;
        line-height: 1.6;
    ">
        Seu som, do seu jeito.<br>
        Crie playbacks, controle instrumentos e misture áudios.
    </div>
</div>
""", unsafe_allow_html=True)

st.info(
    "💡 Dica: teste primeiro com músicas de 1 a 3 minutos. "
    "O processamento pode demorar na hospedagem gratuita."
)


tipos_audio = ["mp3", "wav", "flac", "m4a", "ogg", "aac"]

uploaded = st.file_uploader(
    "Escolha a música principal",
    type=tipos_audio,
    key="musica_principal",
)

st.markdown("### 🎚️ 1. Escolha os instrumentos")

manter = {
    "Voz": st.checkbox("Manter voz", value=True),
    "Bateria": st.checkbox("Manter bateria", value=False),
    "Baixo": st.checkbox("Manter baixo", value=True),
    "Outros instrumentos": st.checkbox(
        "Manter outros instrumentos", value=True
    ),
}

st.markdown("### 🔊 2. Ajuste os volumes")

volumes = {
    "Voz": st.slider("Volume da voz", 0.0, 2.0, 1.0, 0.1),
    "Bateria": st.slider("Volume da bateria", 0.0, 2.0, 1.0, 0.1),
    "Baixo": st.slider("Volume do baixo", 0.0, 2.0, 1.0, 0.1),
    "Outros instrumentos": st.slider(
        "Volume dos outros instrumentos", 0.0, 2.0, 1.0, 0.1
    ),
}

st.subheader("🎸 Adicionar outro instrumento")

instrumento_extra = st.file_uploader(
    "Envie o áudio do instrumento adicional (opcional)",
    type=tipos_audio,
    key="instrumento_extra",
)

volume_extra = st.slider(
    "Volume do instrumento adicionado",
    min_value=0.0,
    max_value=2.0,
    value=1.0,
    step=0.1,
)

inicio_extra = st.slider(
    "Quando o instrumento deve começar? (segundos)",
    min_value=0,
    max_value=600,
    value=0,
    step=1,
    help="0 significa começar junto com a música. "
         "Por exemplo, 30 significa entrar após 30 segundos.",
)

if instrumento_extra is not None:
    st.audio(instrumento_extra)
    st.caption(
        f"O instrumento entrará após {inicio_extra} segundo(s)."
    )


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
        raise RuntimeError(
            (result.stderr or result.stdout or "Erro sem detalhes")[-5000:]
        )
    return result


if uploaded is not None:
    st.audio(uploaded)

    if st.button("🎵 Criar meu playback", type="primary"):
        if not any(manter.values()):
            st.error("Selecione pelo menos um instrumento para manter.")
        else:
            with st.spinner(
                "Processando os áudios. Isso pode levar alguns minutos..."
            ):
                try:
                    with tempfile.TemporaryDirectory(
                        prefix="meu_playback_"
                    ) as temp_name:
                        work = Path(temp_name)
                        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

                        # Salva e converte a música principal.
                        suffix = (
                            Path(uploaded.name).suffix.lower() or ".audio"
                        )
                        original = work / f"entrada{suffix}"
                        original.write_bytes(uploaded.getvalue())

                        wav_input = work / "entrada_convertida.wav"

                        run_command([
                            ffmpeg_exe,
                            "-hide_banner", "-loglevel", "error", "-y",
                            "-i", str(original),
                            "-vn", "-ac", "2", "-ar", "44100",
                            "-c:a", "pcm_s16le", str(wav_input),
                        ])

                        # Separa voz, bateria, baixo e outros instrumentos.
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

                        stems_dir = (
                            separated_dir / "htdemucs" / wav_input.stem
                        )

                        nomes = {
                            "Voz": "vocals.wav",
                            "Bateria": "drums.wav",
                            "Baixo": "bass.wav",
                            "Outros instrumentos": "other.wav",
                        }

                        mix = None
                        sr = 44100

                        for nome, arquivo in nomes.items():
                            if not manter[nome]:
                                continue

                            caminho = stems_dir / arquivo
                            if not caminho.exists():
                                raise RuntimeError(
                                    f"Não encontrei a faixa {arquivo}"
                                )

                            audio, taxa = sf.read(
                                caminho,
                                dtype="float32",
                                always_2d=True,
                            )

                            if taxa != sr:
                                raise RuntimeError(
                                    "As faixas separadas têm taxas de "
                                    "amostragem diferentes."
                                )

                            if mix is None:
                                mix = audio * volumes[nome]
                            else:
                                tamanho = min(len(mix), len(audio))
                                mix = (
                                    mix[:tamanho]
                                    + audio[:tamanho] * volumes[nome]
                                )

                        if mix is None:
                            raise RuntimeError(
                                "Selecione pelo menos um instrumento."
                            )

                        # Converte o instrumento adicional e o posiciona.
                        if instrumento_extra is not None:
                            ext_suffix = (
                                Path(instrumento_extra.name).suffix.lower()
                                or ".audio"
                            )
                            extra_original = work / f"instrumento{ext_suffix}"
                            extra_original.write_bytes(
                                instrumento_extra.getvalue()
                            )

                            extra_wav = work / "instrumento_convertido.wav"

                            run_command([
                                ffmpeg_exe,
                                "-hide_banner", "-loglevel", "error", "-y",
                                "-i", str(extra_original),
                                "-vn", "-ac", "2", "-ar", str(sr),
                                "-c:a", "pcm_s16le", str(extra_wav),
                            ])

                            extra_audio, extra_sr = sf.read(
                                extra_wav,
                                dtype="float32",
                                always_2d=True,
                            )

                            if extra_sr != sr:
                                raise RuntimeError(
                                    "Não foi possível padronizar o áudio "
                                    "do instrumento adicional."
                                )

                            deslocamento = int(inicio_extra * sr)
                            tamanho_final = max(
                                len(mix),
                                deslocamento + len(extra_audio),
                            )

                            # Aumenta a duração se o instrumento terminar
                            # depois da música principal.
                            mix_com_extra = np.zeros(
                                (tamanho_final, 2), dtype=np.float32
                            )
                            mix_com_extra[:len(mix)] += mix

                            fim_extra = deslocamento + len(extra_audio)
                            mix_com_extra[deslocamento:fim_extra] += (
                                extra_audio * volume_extra
                            )

                            mix = mix_com_extra

                        # Evita clipping no arquivo final.
                        peak = (
                            float(np.max(np.abs(mix))) if mix.size else 0.0
                        )
                        if peak > 0.99:
                            mix *= 0.99 / peak

                        output_path = work / "Meu_Playback_Final.wav"
                        sf.write(output_path, mix, sr, subtype="PCM_16")
                        audio_bytes = output_path.read_bytes()

                        st.success("Playback criado com sucesso!")
                        st.audio(audio_bytes, format="audio/wav")
                        st.download_button(
                            "⬇️ Baixar playback final",
                            data=audio_bytes,
                            file_name="Meu_Playback_Final.wav",
                            mime="audio/wav",
                        )

                except subprocess.TimeoutExpired:
                    st.error(
                        "O processamento passou de 30 minutos. "
                        "Tente usar trechos menores."
                    )
                except Exception as exc:
                    st.error("Não foi possível processar esse áudio.")
                    with st.expander("Ver detalhes técnicos do erro"):
                        st.code(str(exc))
                    st.caption(
                        "Se o erro mencionar memória ou recursos, "
                        "tente um trecho menor. A hospedagem gratuita "
                        "tem limites."
                    )

import os
import tempfile
import logging
import grpc
import cv2
from concurrent import futures
from moviepy.editor import VideoFileClip, AudioFileClip

import sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "pb"))
import video_service_pb2, video_service_pb2_grpc

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHUNK_SIZE = 1024 * 64  # 64KB

def extract_audio(input_path: str) -> str:
    """
    Extrai o áudio do vídeo usando MoviePy e retorna o caminho do arquivo .mp3 gerado.
    """
    logger.info("Iniciando extração de áudio de %s", input_path)
    with VideoFileClip(input_path) as clip:
        if clip.audio:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_audio:
                clip.audio.write_audiofile(tmp_audio.name, verbose=False, logger=None)
                logger.info("Áudio extraído para %s", tmp_audio.name)
                return tmp_audio.name
    logger.info("Nenhum áudio encontrado em %s", input_path)
    return ""


def convert_to_gray(input_path: str) -> str:
    """
    Converte o vídeo para tons de cinza usando OpenCV e retorna o caminho do .mp4 gerado.
    """
    logger.info("Iniciando conversão para tons de cinza de %s", input_path)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_gray:
        gray_path = tmp_gray.name
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Não foi possível abrir: {input_path}")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
    out = cv2.VideoWriter(gray_path, fourcc, fps, (width, height), isColor=True)

    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        out.write(gray_bgr)
        frame_count += 1
    cap.release()
    out.release()
    logger.info("Conversão concluída: %d frames processados, saída em %s", frame_count, gray_path)
    return gray_path


def merge_audio_video(gray_path: str, audio_path: str) -> str:
    """
    Realiza a recombinação do vídeo em tons de cinza com o áudio extraído.
    Retorna o caminho do arquivo .mp4 final.
    """
    logger.info("Iniciando merge de %s com áudio %s", gray_path, audio_path)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_final:
        final_path = tmp_final.name

    with VideoFileClip(gray_path) as gray_clip, AudioFileClip(audio_path) as audio_clip:
        video_with_audio = gray_clip.set_audio(audio_clip)
        video_with_audio.write_videofile(
            final_path,
            codec="libx264",
            audio_codec="aac",
            verbose=False,
            logger=None
        )
    logger.info("Merge concluído, saída em %s", final_path)
    return final_path


class VideoServiceServicer(video_service_pb2_grpc.VideoServiceServicer):
    def ProcessVideo(self, request_iterator, context):
        logger.info("ProcessVideo chamada iniciada")
        orig_path = gray_path = audio_path = final_path = None
        try:

            # Recebe e salva vídeo de entrada
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
                total_bytes = 0
                for req in request_iterator:
                    tmp.write(req.chunk_data)
                    total_bytes += len(req.chunk_data)
                orig_path = tmp.name
            logger.info("Arquivo de entrada salvo em: %s (%d bytes)", orig_path, total_bytes)

            audio_path = extract_audio(orig_path)
            gray_path = convert_to_gray(orig_path)
            if audio_path:
                final_path = merge_audio_video(gray_path, audio_path)
            else:
                final_path = gray_path
                logger.info("Pular merge de áudio, usando vídeo em tons de cinza: %s", gray_path)

            # Streaming de saída

            logger.info("Iniciando streaming de saída do arquivo %s", final_path)
            with open(final_path, "rb") as f:
                chunk_count = 0
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    yield video_service_pb2.VideoResponse(chunk_data=chunk)
                    chunk_count += 1
            logger.info("Streaming concluído: %d chunks enviados", chunk_count)

        except Exception as e:
            logger.exception("Erro no ProcessVideo")
            context.abort(grpc.StatusCode.INTERNAL, f"Erro interno: {e}")
        finally:
            # Limpeza de arquivos temporários
            for path in (orig_path, gray_path, audio_path, final_path):
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                        logger.info("Arquivo temporário removido: %s", path)
                    except Exception:
                        logger.warning("Falha ao remover temporário: %s", path)


def serve():
    max_workers = int(os.getenv("GRPC_MAX_WORKERS", "4"))
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    video_service_pb2_grpc.add_VideoServiceServicer_to_server(VideoServiceServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    logger.info("gRPC server rodando em 0.0.0.0:50051 com max_workers=%d", max_workers)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()

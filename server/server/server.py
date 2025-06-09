import os
import tempfile
import traceback

import cv2
import grpc
from concurrent import futures
from moviepy.editor import VideoFileClip, AudioFileClip

import sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "pb"))

import video_service_pb2, video_service_pb2_grpc

CHUNK_SIZE = 1024 * 64  # 64KB, bate com o client

class VideoServiceServicer(video_service_pb2_grpc.VideoServiceServicer):

    def ProcessVideo(self, request_iterator, context):
        orig_path = None
        gray_path = None
        audio_path = None
        final_path = None

        try:
            orig_fd, orig_path = tempfile.mkstemp(suffix=".mp4")
            os.close(orig_fd)
            with open(orig_path, "wb") as f_orig:
                for req in request_iterator:
                    f_orig.write(req.chunk_data)

            clip = VideoFileClip(orig_path)
            audio = clip.audio
            if audio:
                audio_fd, audio_path = tempfile.mkstemp(suffix=".mp3")
                os.close(audio_fd)
                audio.write_audiofile(audio_path, verbose=False, logger=None)

            gray_fd, gray_path = tempfile.mkstemp(suffix=".mp4")
            os.close(gray_fd)

            cap = cv2.VideoCapture(orig_path)
            if not cap.isOpened():
                raise RuntimeError(f"Não foi possível abrir: {orig_path}")

            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 480)
            out = cv2.VideoWriter(gray_path, fourcc, fps, (width, height), isColor=True)

            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray_bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
                out.write(gray_bgr)

            cap.release()
            out.release()
            clip.reader.close()
            if audio:
                clip.audio.reader.close_proc()

            if audio and audio_path:
                gray_clip = VideoFileClip(gray_path)
                audio_clip = AudioFileClip(audio_path)

                final_fd, final_path = tempfile.mkstemp(suffix=".mp4")
                os.close(final_fd)

                video_with_audio = gray_clip.set_audio(audio_clip)
                video_with_audio.write_videofile(
                    final_path,
                    codec="libx264",
                    audio_codec="aac",
                    verbose=False,
                    logger=None
                )
                gray_clip.reader.close()
                audio_clip.reader.close_proc()
                video_with_audio.reader.close()

                with open(final_path, "rb") as f_final:
                    while True:
                        data = f_final.read(CHUNK_SIZE)
                        if not data:
                            break
                        yield video_service_pb2.VideoResponse(chunk_data=data)
            else:
                with open(gray_path, "rb") as f_gray:
                    while True:
                        data = f_gray.read(CHUNK_SIZE)
                        if not data:
                            break
                        yield video_service_pb2.VideoResponse(chunk_data=data)

        except Exception as e:
            print("Erro no servidor ProcessVideo:", e)
            traceback.print_exc()
            context.set_details(f"Erro interno: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            return
        finally:
            # Limpa temporários
            for path in (orig_path, gray_path, audio_path, final_path):
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    video_service_pb2_grpc.add_VideoServiceServicer_to_server(VideoServiceServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print(">>> Servidor gRPC rodando em 0.0.0.0:50051")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()

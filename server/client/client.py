# client.py
import grpc
from pb import video_service_pb2, video_service_pb2_grpc
import sys

# Deve bater com o servidor
CHUNK_SIZE = 1024 * 64

def generate_chunks(file_path):
    """ Lê o arquivo local em pedaços de CHUNK_SIZE e gera VideoRequest. """
    with open(file_path, "rb") as f:
        while True:
            data = f.read(CHUNK_SIZE)
            if not data:
                break
            yield video_service_pb2.VideoRequest(chunk_data=data)

def main():
    if len(sys.argv) != 3:
        print(sys.argv)
        print("Uso: python client.py <video_entrada.mp4> <video_saida.mp4>")
        return

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    # 1) Cria canal e stub gRPC
    channel = grpc.insecure_channel("localhost:50051")
    stub = video_service_pb2_grpc.VideoServiceStub(channel)

    # 2) Chama o metodo ProcessVideo enviando o gerador de chunks
    response_iterator = stub.ProcessVideo(generate_chunks(input_path))

    # 3) Grava cada chunk de resposta num arquivo local de saída
    with open(output_path, "wb") as f_out:
        for resp in response_iterator:
            f_out.write(resp.chunk_data)

    print(f"Vídeo processado salvo em: {output_path}")

if __name__ == "__main__":
    main()

import { IncomingForm, File as FormidableFile } from "formidable";
import fs from "fs";
import type { NextApiRequest, NextApiResponse } from "next";
import client from "../../services/grpcClient";
import { VideoRequest, VideoResponse } from "../../pb/video_service";

export const config = { api: { bodyParser: false } };
const CHUNK_SIZE = 1024 * 64;

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Método não permitido" });
  }

  let file: FormidableFile;
  try {
    file = await new Promise<FormidableFile>((resolve, reject) => {
      const form = new IncomingForm();
      form.parse(req, (_err, _fields, files) => {
        const raw = (files as any).video;
        if (!raw) return reject(new Error("Nenhum vídeo enviado"));
        resolve(Array.isArray(raw) ? raw[0] : raw);
      });
    });
  } catch (e: any) {
    return res.status(400).json({ error: e.message });
  }

  const videoStream = fs.createReadStream(file.filepath, { highWaterMark: CHUNK_SIZE });
  const call = client.processVideo();

  await new Promise<void>((resolve, reject) => {
    const respBuffers: Buffer[] = [];

    call.on("data", (msg: VideoResponse) => {
      respBuffers.push(msg.chunkData);
    });

    call.on("error", err => {
      if (!res.headersSent) res.status(500).json({ error: err.message });
      reject(err);
    });

    call.on("end", () => {
      const finalBuffer = Buffer.concat(respBuffers);
      res.setHeader("Content-Type", "application/octet-stream");
      res.setHeader("Content-Disposition", 'attachment; filename="processed_video.mp4"');
      res.send(finalBuffer);
      resolve();
    });

    // Envia chunks tipados
    videoStream.on("data", chunk => {
      call.write({ chunkData: chunk } as VideoRequest);
    });
    videoStream.on("error", e => {
      if (!res.headersSent) res.status(500).json({ error: e.message });
      call.end();
      reject(e);
    });
    videoStream.on("end", () => {
      call.end();
    });
  });

  fs.unlink(file.filepath, () => {});
}
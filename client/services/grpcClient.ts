import { VideoServiceClient } from "../pb/video_service";
import { credentials } from "@grpc/grpc-js";

export const client = new VideoServiceClient(
  "127.0.0.1:50051",
  credentials.createInsecure()
);

export default client;

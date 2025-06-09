import path from "path";
import grpc from "@grpc/grpc-js";
import protoLoader from "@grpc/proto-loader";

const PROTO_PATH = path.resolve(process.cwd(), "proto/video_service.proto");

const packageDef = protoLoader.loadSync(PROTO_PATH, {
  keepCase: true,
  longs: String,
  enums: String,
  defaults: true,
  oneofs: true,
});
const grpcObj = grpc.loadPackageDefinition(packageDef) as any;
const videoProto = grpcObj.video;

const client = new videoProto.VideoService(
  "localhost:50051",
  grpc.credentials.createInsecure()
);

export default client;

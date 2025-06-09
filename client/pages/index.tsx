import React, { useState, ChangeEvent, FormEvent } from "react";

export default function Home() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    setErrorMsg(null);
    setDownloadUrl(null);
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFile(e.target.files[0]);
    } else {
      setSelectedFile(null);
    }
  };

  const handleUpload = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMsg("Selecione primeiro um arquivo de vídeo.");
      return;
    }

    setIsProcessing(true);
    setErrorMsg(null);
    setDownloadUrl(null);

    try {
      const formData = new FormData();
      formData.append("video", selectedFile);

      const response = await fetch("/api/process-video", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const texto = await response.text();
        throw new Error(`Erro ${response.status}: ${texto}`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setDownloadUrl(url);
    } catch (err: any) {
      console.error("Falha no upload:", err);
      setErrorMsg(err.message || "Erro ao processar vídeo.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        backgroundColor: "#f5f5f5",
        padding: "1rem",
      }}
    >
      <div
        style={{
          width: "600px",
          background: "#fff",
          padding: "2rem",
          borderRadius: "8px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
        }}
      >
        <h2 style={{ textAlign: "center", marginBottom: "1rem" }}>
          Upload de Vídeo para Filtro P&B (Streaming)
        </h2>

        <form onSubmit={handleUpload}>
          <div style={{ marginBottom: "1rem" }}>
            <input
              type="file"
              accept="video/*"
              onChange={handleFileChange}
            />
          </div>

          {errorMsg && (
            <p style={{ color: "red", marginBottom: "1rem" }}>
              {errorMsg}
            </p>
          )}

          <button
            type="submit"
            disabled={isProcessing || !selectedFile}
            style={{
              padding: "0.5rem 1rem",
              backgroundColor:
                isProcessing || !selectedFile ? "#ccc" : "#007bff",
              color: "#fff",
              border: "none",
              borderRadius: "4px",
              cursor:
                isProcessing || !selectedFile ? "not-allowed" : "pointer",
            }}
          >
            {isProcessing ? "Processando…" : "Upload"}
          </button>
        </form>

        {isProcessing && (
          <div style={{ marginTop: "1rem", textAlign: "center" }}>
            <p>Processando vídeo, aguarde…</p>
          </div>
        )}

        {downloadUrl && !isProcessing && (
          <div style={{ marginTop: "1.5rem" }}>
            <h3>Vídeo Processado (P&B):</h3>
            <video
              width="100%"
              controls
              src={downloadUrl}
              style={{
                marginTop: "0.5rem",
                borderRadius: "6px",
                boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
              }}
            />
            <div style={{ textAlign: "right", marginTop: "0.5rem" }}>
              <a
                href={downloadUrl}
                download="processed_video.mp4"
                style={{
                  padding: "0.5rem 1rem",
                  backgroundColor: "#28a745",
                  color: "#fff",
                  textDecoration: "none",
                  borderRadius: "4px",
                }}
              >
                Baixar Vídeo
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

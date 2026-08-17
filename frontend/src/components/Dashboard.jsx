import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

export default function Dashboard() {
  const [documents, setDocuments] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState("");
  const fileInput = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/documents").then((res) => setDocuments(res.data));
  }, []);

  const uploadFile = async (file) => {
    if (!file || !file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported");
      return;
    }
    setError("");
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await api.post("/documents/upload", form);
      setDocuments((prev) => [res.data, ...prev]);
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    uploadFile(file);
  };

  const handleDelete = async (id) => {
    await api.delete(`/documents/${id}`);
    setDocuments((prev) => prev.filter((d) => d.id !== id));
  };

  return (
    <div className="dashboard">
      <h2>Your Documents</h2>

      <div
        className={`upload-zone ${dragOver ? "drag-over" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInput.current.click()}
      >
        <input
          ref={fileInput}
          type="file"
          accept=".pdf"
          hidden
          onChange={(e) => uploadFile(e.target.files[0])}
        />
        {uploading ? "Uploading..." : "Drop a PDF here or click to upload"}
      </div>

      {error && <p className="form-error">{error}</p>}

      {documents.length === 0 && !uploading && (
        <p className="empty-msg">No documents yet. Upload a PDF to get started.</p>
      )}

      <div className="doc-list">
        {documents.map((doc) => (
          <div key={doc.id} className="doc-card">
            <div className="doc-info">
              <h3>{doc.filename}</h3>
              <span>{doc.page_count} pages</span>
            </div>
            <div className="doc-actions">
              <button onClick={() => navigate(`/documents/${doc.id}`)}>Ask questions</button>
              <button className="btn-danger" onClick={() => handleDelete(doc.id)}>Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

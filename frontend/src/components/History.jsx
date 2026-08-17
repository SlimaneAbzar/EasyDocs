import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

export default function History() {
  const [sessions, setSessions] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/history/sessions").then((res) => setSessions(res.data));
  }, []);

  return (
    <div className="history-page">
      <h2>Chat History</h2>

      {sessions.length === 0 && (
        <p className="empty-msg">No chats yet. Upload a document and ask a question.</p>
      )}

      <div className="session-list">
        {sessions.map((s) => (
          <div
            key={s.id}
            className="session-card"
            onClick={() => navigate(`/documents/${s.document_id}?session=${s.id}`)}
          >
            <div className="session-title">{s.title}</div>
            <div className="session-meta">
              {new Date(s.created_at).toLocaleDateString(undefined, {
                month: "short", day: "numeric", year: "numeric",
                hour: "2-digit", minute: "2-digit",
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

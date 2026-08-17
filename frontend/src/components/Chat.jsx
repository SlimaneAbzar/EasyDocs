import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import Markdown from "react-markdown";
import api from "../api";

export default function Chat() {
  const { id } = useParams();
  const [searchParams] = useSearchParams();
  const resumeSessionId = searchParams.get("session");

  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(resumeSessionId ? Number(resumeSessionId) : null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(!resumeSessionId);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (!resumeSessionId) return;
    api.get(`/sessions/${resumeSessionId}`).then((res) => {
      const history = res.data.messages.flatMap((m) => [
        { role: "user", text: m.question },
        { role: "assistant", text: m.answer },
      ]);
      setMessages(history);
      setSessionId(Number(resumeSessionId));
      setReady(true);
    }).catch(() => setReady(true));
  }, [resumeSessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setInput("");
    setLoading(true);

    try {
      const payload = { question };
      if (sessionId) payload.session_id = sessionId;

      const res = await api.post(`/documents/${id}/ask`, payload);

      if (!sessionId && res.data.session_id) {
        setSessionId(res.data.session_id);
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: res.data.answer,
          sources: res.data.sources,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Something went wrong. Try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-page">
      <div className="chat-messages">
        {ready && messages.length === 0 && (
          <p className="empty-msg">Ask a question about this document in any language.</p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`msg ${msg.role}`}>
            <div className="msg-text">
              {msg.role === "assistant" ? <Markdown>{msg.text}</Markdown> : msg.text}
            </div>
            {msg.sources && (
              <div className="msg-sources">
                {[...new Set(msg.sources.map((s) => s.page_number))].map((page) => (
                  <span key={page} className="source-badge">Page {page}</span>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="msg assistant">
            <div className="msg-text loading-dots">Thinking...</div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question in any language..."
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>Send</button>
      </form>
    </div>
  );
}

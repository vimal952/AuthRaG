import { useState, useEffect, useRef } from "react";
import { chatApi } from "../services/api";

function CodeBlock({ language, code }) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="markdown-code-block">
      <div className="code-block-header">
        <span className="code-lang">{language}</span>
        <button onClick={copyToClipboard} className="copy-btn">
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre>
        <code>{code}</code>
      </pre>
    </div>
  );
}

function parseInlineStyles(text) {
  if (typeof text !== "string") return text;
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
  const parts = text.split(regex);
  if (parts.length === 1) return text;
  return parts.map((part, idx) => {
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={idx} className="inline-code">{part.slice(1, -1)}</code>;
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={idx}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return <em key={idx}>{part.slice(1, -1)}</em>;
    }
    return part;
  });
}

function parseTextBlocks(blockText, blockIndex) {
  const lines = blockText.split("\n");
  const elements = [];
  let currentList = null;
  let currentTable = null;

  const flushList = (key) => {
    if (currentList) {
      const Tag = currentList.type;
      elements.push(
        <Tag key={key} className={Tag === "ul" ? "markdown-ul" : "markdown-ol"}>
          {currentList.items.map((item, idx) => (
            <li key={idx}>{parseInlineStyles(item)}</li>
          ))}
        </Tag>
      );
      currentList = null;
    }
  };

  const flushTable = (key) => {
    if (currentTable) {
      elements.push(
        <div className="table-responsive" key={key}>
          <table className="markdown-table">
            <thead>
              <tr>
                {currentTable.headers.map((h, idx) => (
                  <th key={idx}>{parseInlineStyles(h)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {currentTable.rows.map((row, rIdx) => (
                <tr key={rIdx}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx}>{parseInlineStyles(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      currentTable = null;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      flushList(`list-${blockIndex}-${i}`);
      const cells = trimmed.split("|").slice(1, -1).map(c => c.trim());
      const isSeparator = cells.every(c => /^[:-]+$/.test(c));
      if (isSeparator) {
        continue;
      }
      if (!currentTable) {
        currentTable = { headers: cells, rows: [] };
      } else {
        currentTable.rows.push(cells);
      }
      continue;
    } else {
      flushTable(`table-${blockIndex}-${i}`);
    }

    if (trimmed.startsWith("#")) {
      flushList(`list-${blockIndex}-${i}`);
      const match = trimmed.match(/^(#{1,6})\s+(.*)$/);
      if (match) {
        const level = Math.min(match[1].length, 6);
        const text = match[2];
        const Tag = `h${level}`;
        elements.push(<Tag key={`h-${blockIndex}-${i}`} className={`markdown-h${level}`}>{parseInlineStyles(text)}</Tag>);
        continue;
      }
    }

    const bulletMatch = line.match(/^(\s*)[-*+]\s+(.*)$/);
    if (bulletMatch) {
      const text = bulletMatch[2];
      if (!currentList || currentList.type !== "ul") {
        flushList(`list-${blockIndex}-${i}`);
        currentList = { type: "ul", items: [text] };
      } else {
        currentList.items.push(text);
      }
      continue;
    }

    const numMatch = line.match(/^(\s*)\d+\.\s+(.*)$/);
    if (numMatch) {
      const text = numMatch[2];
      if (!currentList || currentList.type !== "ol") {
        flushList(`list-${blockIndex}-${i}`);
        currentList = { type: "ol", items: [text] };
      } else {
        currentList.items.push(text);
      }
      continue;
    }

    if (trimmed === "") {
      flushList(`list-${blockIndex}-${i}`);
      continue;
    }

    flushList(`list-${blockIndex}-${i}`);
    elements.push(<p key={`p-${blockIndex}-${i}`} className="markdown-p">{parseInlineStyles(line)}</p>);
  }

  flushList(`list-end-${blockIndex}`);
  flushTable(`table-end-${blockIndex}`);
  return elements;
}

function Markdown({ text }) {
  if (!text) return null;
  const parts = text.split(/(```[\s\S]*?```)/g);
  return (
    <div className="markdown-body">
      {parts.map((part, index) => {
        if (part.startsWith("```")) {
          const lines = part.split("\n");
          const firstLine = lines[0] || "```";
          const lang = firstLine.slice(3).trim() || "code";
          const code = lines.slice(1, -1).join("\n");
          return <CodeBlock key={index} language={lang} code={code} />;
        } else {
          return parseTextBlocks(part, index);
        }
      })}
    </div>
  );
}

function ThinkingBubble() {
  return (
    <div className="message assistant">
      <div className="thinking-container">
        <div className="thinking-title">AuthRAG is thinking</div>
        <div className="thinking">
          <span /><span /><span />
        </div>
      </div>
    </div>
  );
}

function Message({ msg }) {
  return (
    <div className={`message ${msg.role}`}>
      <div className="message-avatar">
        {msg.role === "user" ? "U" : "AI"}
      </div>
      <div className="message-content-wrapper">
        <div className="message-bubble">
          <Markdown text={msg.content} />
        </div>
        {msg.sources?.length > 0 && (
          <div className="message-sources">
            <span className="source-label">Sources:</span>
            {msg.sources.map((s, idx) => (
              <span key={s.document_id || idx} className="source-tag" title={s.filename}>
                {s.title}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatPage() {
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    chatApi.listConversations().then((r) => setConversations(r.data)).catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const loadConversation = async (id) => {
    setActiveConvId(id);
    try {
      const { data } = await chatApi.getConversation(id);
      setMessages(data.messages);
    } catch {
      setMessages([]);
    }
  };

  const startNewChat = () => {
    setActiveConvId(null);
    setMessages([]);
  };

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    try {
      const { data } = await chatApi.query({ message: text, conversation_id: activeConvId });
      setActiveConvId(data.conversation_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer, sources: data.sources },
      ]);
      setConversations((prev) => {
        const exists = prev.find((c) => c.id === data.conversation_id);
        if (!exists) {
          return [{ id: data.conversation_id, last_message: text, created_at: new Date() }, ...prev];
        }
        const updated = prev.map((c) =>
          c.id === data.conversation_id ? { ...c, last_message: text } : c
        );
        return [
          updated.find((c) => c.id === data.conversation_id),
          ...updated.filter((c) => c.id !== data.conversation_id),
        ];
      });
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error: " + (err.response?.data?.detail || "Failed to get response.") },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-page">
      <div className="chat-history-panel">
        <h3>Conversations</h3>
        <button className="new-chat-btn" onClick={startNewChat}>+ New Chat</button>
        {conversations.map((c) => (
          <button
            key={c.id}
            className={`conv-item ${activeConvId === c.id ? "active" : ""}`}
            onClick={() => loadConversation(c.id)}
          >
            {c.last_message || "Conversation"}
          </button>
        ))}
      </div>

      <div className="chat-main">
        <div className="chat-messages">
          {messages.length === 0 && !loading ? (
            <div className="chat-empty">
              <h2>Ask anything about your documents</h2>
              <p>Type a question below to get started</p>
            </div>
          ) : (
            <>
              {messages.map((m, i) => <Message key={i} msg={m} />)}
              {loading && <ThinkingBubble />}
            </>
          )}
          <div ref={bottomRef} />
        </div>
        <div className="chat-input-area">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question... (Enter to send, Shift+Enter for newline)"
            rows={1}
          />
          <button onClick={sendMessage} disabled={loading || !input.trim()}>Send</button>
        </div>
      </div>
    </div>
  );
}

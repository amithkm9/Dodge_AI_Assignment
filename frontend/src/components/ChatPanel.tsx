"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import type { Message } from "@/types";

interface ChatPanelProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  onStop: () => void;
  isLoading: boolean;
}

const SUGGESTED_QUESTIONS = [
  "Show top products by billing count",
  "Find orders delivered but not billed",
  "Which customer has most sales orders?",
];

/** Render inline markdown: **bold** */
function renderInline(text: string) {
  return text.split(/(\*\*.*?\*\*)/g).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i} className="font-semibold text-gray-900">{part.slice(2, -2)}</strong>;
    }
    return <span key={i}>{part}</span>;
  });
}

/** Parse a pipe-delimited row into cells, stripping leading/trailing pipes. */
function parseRow(row: string) {
  return row.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
}

/** Full markdown renderer: tables + bold + paragraphs. */
function renderContent(content: string) {
  // The backend sometimes returns inline pipes without newlines.
  // Re-insert newlines before every | that starts a new row.
  const normalised = content
    .replace(/\| \|/g, "|\n|")
    .replace(/\|\s*\n\s*\|/g, "|\n|");

  const lines = normalised.split("\n");
  const blocks: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i].trim();

    if (line.startsWith("|") && line.endsWith("|")) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        tableLines.push(lines[i].trim());
        i++;
      }

      const headerRow = tableLines[0];
      const hasSep = tableLines.length > 1 && /^[\|\-\s:]+$/.test(tableLines[1]);
      const dataRows = hasSep ? tableLines.slice(2) : tableLines.slice(1);

      blocks.push(
        <div key={`tbl-${blocks.length}`} className="my-3 overflow-x-auto rounded-xl border border-gray-200 shadow-sm">
          <table className="w-full text-sm text-left border-collapse">
            {hasSep && (
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  {parseRow(headerRow).map((cell, ci) => (
                    <th key={ci} className="px-4 py-2.5 text-xs font-semibold text-gray-600 uppercase tracking-wide whitespace-nowrap">
                      {renderInline(cell)}
                    </th>
                  ))}
                </tr>
              </thead>
            )}
            <tbody>
              {dataRows.map((row, ri) => (
                <tr key={ri} className={`border-b border-gray-100 last:border-0 ${ri % 2 === 0 ? "bg-white" : "bg-gray-50/50"}`}>
                  {parseRow(row).map((cell, ci) => (
                    <td key={ci} className="px-4 py-2.5 text-[13.5px] text-gray-700 whitespace-nowrap">
                      {renderInline(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    if (line !== "") {
      blocks.push(
        <p key={`p-${blocks.length}`} className="text-[15px] leading-[1.75] text-gray-800 break-words mb-1">
          {renderInline(line)}
        </p>
      );
    }
    i++;
  }

  return blocks;
}

export default function ChatPanel({ messages, onSendMessage, onStop, isLoading }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [openCypher, setOpenCypher] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height =
        Math.min(inputRef.current.scrollHeight, 160) + "px";
    }
  }, [input]);

  const handleSubmit = () => {
    if (input.trim() && !isLoading) {
      onSendMessage(input.trim());
      setInput("");
      if (inputRef.current) inputRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const showSuggestions = messages.length <= 1 && !isLoading;

  return (
    <div className="flex h-full flex-col bg-white">

      {/* ── Scrollable messages ── */}
      <div className="flex-1 overflow-y-auto px-5 py-6 space-y-6">
        {messages.map((msg, i) => (
          <div key={i}>
            {msg.role === "assistant" ? (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-gray-900 flex items-center justify-center text-white text-xs font-bold flex-shrink-0 mt-0.5">
                  D
                </div>
                <div className="flex-1 min-w-0 space-y-1.5">
                  <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Dodge AI</p>
                  <div>{renderContent(msg.content)}</div>
                  {msg.cypher && (
                    <div className="pt-1">
                      <button
                        onClick={() => setOpenCypher(openCypher === i ? null : i)}
                        className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-700 transition-colors"
                      >
                        <svg
                          className={`w-3 h-3 transition-transform duration-200 ${openCypher === i ? "rotate-90" : ""}`}
                          fill="none" stroke="currentColor" viewBox="0 0 24 24"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                        View Cypher Query
                      </button>
                      {openCypher === i && (
                        <pre className="mt-2 p-3.5 bg-gray-950 text-emerald-400 text-xs rounded-xl overflow-x-auto font-mono leading-relaxed border border-gray-800">
                          {msg.cypher}
                        </pre>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex justify-end">
                <div className="max-w-[82%] bg-gray-900 text-white text-[15px] leading-[1.65] px-4 py-3 rounded-2xl rounded-tr-sm shadow-sm">
                  {msg.content}
                </div>
              </div>
            )}
          </div>
        ))}

        {/* Typing indicator */}
        {isLoading && (
          <div className="flex gap-3 items-end">
            <div className="w-8 h-8 rounded-full bg-gray-900 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
              D
            </div>
            <div className="bg-gray-100 px-4 py-3.5 rounded-2xl rounded-bl-sm flex gap-1.5 items-center">
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-[bounce_1s_ease-in-out_infinite_0ms]" />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-[bounce_1s_ease-in-out_infinite_200ms]" />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-[bounce_1s_ease-in-out_infinite_400ms]" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── Suggested questions — pinned above input, hidden once conversation starts ── */}
      {showSuggestions && (
        <div className="px-5 pb-4 flex-shrink-0">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
            Suggested questions
          </p>
          <div className="flex flex-col gap-2">
            {SUGGESTED_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => onSendMessage(q)}
                className="group w-full text-left bg-gray-50 border border-gray-200 hover:border-gray-800 hover:bg-gray-900 rounded-xl px-4 py-3.5 transition-all duration-150 flex items-center justify-between gap-3"
              >
                <span className="text-[15px] font-medium leading-snug text-gray-700 group-hover:text-white transition-colors">
                  {q}
                </span>
                <svg
                  className="w-4 h-4 text-gray-300 group-hover:text-white flex-shrink-0 transition-colors"
                  fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Input bar ── */}
      <div className="px-5 pb-5 pt-2 flex-shrink-0 border-t border-gray-100">
        <div className="flex items-end gap-3 border border-gray-200 rounded-2xl bg-white px-4 py-3 shadow-sm focus-within:border-gray-400 focus-within:shadow-[0_2px_14px_rgba(0,0,0,0.08)] transition-all duration-150">

          {/* Textarea */}
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message Dodge AI…"
            disabled={isLoading}
            rows={1}
            className="flex-1 resize-none text-base text-gray-800 placeholder:text-gray-400 focus:outline-none disabled:opacity-60 bg-transparent leading-relaxed self-center"
            style={{ minHeight: "28px", maxHeight: "160px" }}
          />

          {/* Send / Stop — circular button */}
          {isLoading ? (
            <button
              onClick={onStop}
              title="Stop generating"
              className="flex-shrink-0 w-9 h-9 rounded-full bg-gray-900 hover:bg-red-500 flex items-center justify-center transition-all duration-150 active:scale-90 shadow-sm self-end"
            >
              <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                <rect x="4" y="4" width="12" height="12" rx="2" />
              </svg>
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!input.trim()}
              title="Send message"
              className="flex-shrink-0 w-9 h-9 rounded-full bg-gray-900 hover:bg-gray-700 disabled:bg-gray-200 flex items-center justify-center transition-all duration-150 active:scale-90 disabled:cursor-not-allowed shadow-sm self-end"
            >
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>
          )}
        </div>

        <p className="text-center text-xs text-gray-300 mt-2 select-none">
          ⏎ to send · Shift+⏎ for new line
        </p>
      </div>

    </div>
  );
}

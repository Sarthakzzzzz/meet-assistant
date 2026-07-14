"use client";
import { useState, useRef, useEffect } from "react";
import { GlassPane } from "./ui/GlassPane";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Bot, User } from "lucide-react";
import { Message } from "../hooks/useMeetingWebSocket";

interface CopilotChatProps {
  messages: Message[];
  isLoading: boolean;
  onSendMessage: (text: string) => void;
}

export function CopilotChat({ messages, isLoading, onSendMessage }: CopilotChatProps) {
  const [input, setInput] = useState("");
  const chatContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll only the chat container, never the browser viewport
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSend = () => {
    if (!input.trim() || isLoading) return;
    onSendMessage(input);
    setInput("");
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden relative">
      {/* Top glare line */}
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/10 to-transparent z-10" />
      {/* Header */}
      <div className="h-16 border-b border-white/10 flex items-center px-6 shrink-0 bg-white/[0.02]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center border border-indigo-500/30">
            <Bot size={18} className="text-indigo-400" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-zinc-100">Meeting Copilot</h1>
            <p className="text-xs text-zinc-500">Powered by LangChain & ChromaDB</p>
          </div>
        </div>
      </div>

      {/* Message List */}
      <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-6 scroll-smooth">
        <div className="flex flex-col gap-6 max-w-3xl mx-auto pb-10">
          <AnimatePresence initial={false}>
            {messages.map((msg, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
              >
                {/* Avatar */}
                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 border ${
                  msg.role === "user" 
                    ? "bg-zinc-800 border-zinc-700" 
                    : "bg-indigo-900/50 border-indigo-500/30"
                }`}>
                  {msg.role === "user" ? <User size={14} className="text-zinc-400" /> : <Bot size={14} className="text-indigo-400" />}
                </div>

                {/* Bubble */}
                <div className={`px-5 py-3.5 rounded-2xl max-w-[85%] text-sm leading-relaxed shadow-sm ${
                  msg.role === "user"
                    ? "bg-zinc-800/80 text-zinc-100 rounded-tr-sm border border-white/5"
                    : "bg-black/60 text-zinc-300 rounded-tl-sm border border-white/10"
                }`}>
                  {msg.text}
                </div>
              </motion.div>
            ))}
            
            {isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-4 flex-row"
              >
                <div className="w-8 h-8 rounded-full bg-indigo-900/50 border border-indigo-500/30 flex items-center justify-center shrink-0">
                  <Bot size={14} className="text-indigo-400" />
                </div>
                <div className="px-5 py-4 rounded-2xl rounded-tl-sm bg-black/60 border border-white/10 flex items-center gap-2">
                  <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" />
                  <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Input Area */}
      <div className="p-6 pt-0 shrink-0 max-w-3xl mx-auto w-full">
        <div className="relative group">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask about the meeting..."
            rows={1}
            className="w-full bg-zinc-900/50 backdrop-blur-xl border border-white/10 rounded-2xl px-5 py-4 pr-16 text-zinc-200 text-sm outline-none focus:border-indigo-500/50 focus:bg-zinc-900/80 transition-all resize-none shadow-lg group-hover:border-white/20"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="absolute right-2.5 bottom-2.5 p-2 bg-white text-black hover:bg-zinc-200 disabled:bg-zinc-800 disabled:text-zinc-600 rounded-xl transition-colors"
          >
            <Send size={16} />
          </button>
        </div>
        <p className="text-center text-[11px] text-zinc-600 mt-3 font-medium">
          Meet Assistant can make mistakes. Verify important context.
        </p>
      </div>
    </div>
  );
}

"use client";
import { LiveContextPane } from "./LiveContextPane";
import { CopilotChat } from "./CopilotChat";
import { useMeetingWebSocket } from "../hooks/useMeetingWebSocket";
import Link from "next/link";
import { ChevronLeft } from "lucide-react";

export function MeetingDashboard() {
  const { 
    messages, 
    isRecording, 
    isLoading,
    activeSlidePath,
    captions,
    handleStartRecording, 
    sendMessage 
  } = useMeetingWebSocket();

  return (
    <div className="flex h-screen bg-black text-zinc-100 overflow-hidden font-sans relative">
      
      {/* Subtle Background Glows */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-indigo-500/10 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-emerald-500/10 blur-[120px] rounded-full pointer-events-none" />

      {/* Main Container — full screen, 2 panes */}
      <div className="flex w-full h-full relative z-10 p-3 gap-3">
        
        {/* Left Context Pane — fixed width */}
        <div className="w-[360px] shrink-0 flex flex-col gap-3 min-h-0">
          
          {/* Back Button */}
          <div className="shrink-0">
            <Link 
              href="/dashboard" 
              className="group inline-flex items-center gap-2 text-sm font-medium text-zinc-500 hover:text-zinc-200 transition-colors"
            >
              <div className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center group-hover:bg-white/10 transition-colors">
                <ChevronLeft size={16} />
              </div>
              Back to Dashboard
            </Link>
          </div>

          {/* Context pane takes remaining height */}
          <div className="flex-1 min-h-0">
            <LiveContextPane 
              isRecording={isRecording}
              onStartRecording={handleStartRecording}
              activeSlidePath={activeSlidePath}
              captions={captions}
            />
          </div>
        </div>

        {/* Right Chat Pane — fills remaining width, glass styled */}
        <div className="flex-1 min-w-0 glass-pane flex flex-col overflow-hidden">
          <CopilotChat 
            messages={messages}
            isLoading={isLoading}
            onSendMessage={sendMessage}
          />
        </div>
        
      </div>
    </div>
  );
}

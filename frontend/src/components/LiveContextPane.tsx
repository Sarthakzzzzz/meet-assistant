"use client";
import { GlassPane } from "./ui/GlassPane";
import { motion, AnimatePresence } from "framer-motion";
import { MonitorPlay, Radio, Activity } from "lucide-react";

import { getBackendUrl } from "@/lib/utils";

interface LiveContextPaneProps {
  isRecording: boolean;
  onStartRecording: () => void;
  activeSlidePath?: string | null;
  captions: { speaker: string; text: string }[];
}

export function LiveContextPane({ isRecording, onStartRecording, activeSlidePath, captions }: LiveContextPaneProps) {
  return (
    <div className="flex flex-col h-full gap-3 overflow-hidden">
      
      {/* Controls & Status */}
      <GlassPane delay={0.1} className="p-4 flex flex-col gap-3 shrink-0">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold tracking-widest text-zinc-400 uppercase flex items-center gap-2">
            <MonitorPlay size={14} className="text-indigo-400" />
            Controls
          </h2>
          
          {isRecording && (
            <div className="flex items-center gap-1.5 bg-emerald-500/10 text-emerald-400 px-2 py-1 rounded-full text-xs font-medium border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Live
            </div>
          )}
        </div>

        {!isRecording ? (
          <button 
            onClick={onStartRecording}
            className="w-full relative overflow-hidden group bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2.5 px-4 rounded-xl transition-all shadow-lg shadow-indigo-500/20 active:scale-[0.98] text-sm"
          >
            <span className="flex items-center justify-center gap-2">
              <Radio size={16} />
              Start Recording
            </span>
          </button>
        ) : (
          <div className="w-full bg-zinc-800/50 border border-emerald-500/30 text-emerald-300 font-medium py-2.5 px-4 rounded-xl flex items-center justify-center gap-2 text-sm">
            <Activity size={16} className="animate-pulse" />
            Recording Active
          </div>
        )}
      </GlassPane>

      {/* Active Slide Display */}
      <GlassPane delay={0.2} className="flex-1 min-h-0 flex flex-col relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full p-3 z-10 bg-gradient-to-b from-black/80 to-transparent">
          <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest">Current Slide</h3>
        </div>
        
        <div className="flex-1 w-full bg-zinc-950 flex items-center justify-center">
          <AnimatePresence mode="wait">
            {activeSlidePath ? (
              <motion.img
                key={activeSlidePath}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 1.05 }}
                transition={{ duration: 0.5 }}
                src={`${getBackendUrl()}/data/${activeSlidePath.split("data/")[1] ?? activeSlidePath}`}
                alt="Active Slide"
                className="w-full h-full object-contain"
              />
            ) : (
              <motion.div 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-zinc-700 flex flex-col items-center gap-2"
              >
                <MonitorPlay size={28} className="opacity-50" />
                <span className="text-xs font-medium">Waiting for slides...</span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </GlassPane>

      {/* Live Transcript */}
      <GlassPane delay={0.3} className="flex-1 min-h-0 max-h-[220px] flex flex-col overflow-hidden">
        <div className="px-4 py-3 border-b border-white/10 shrink-0">
          <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-widest">Live Transcript</h3>
        </div>
        <div className="p-4 overflow-y-auto flex-1 flex flex-col gap-2 font-mono text-xs">
          {captions.length === 0 ? (
            <p className="text-zinc-700 text-center mt-4 italic">No captions yet...</p>
          ) : (
            captions.map((cap, i) => (
              <motion.div 
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex flex-col"
              >
                <span className="text-indigo-400 text-[10px]">{cap.speaker}</span>
                <span className="text-zinc-400">{cap.text}</span>
              </motion.div>
            ))
          )}
        </div>
      </GlassPane>

    </div>
  );
}

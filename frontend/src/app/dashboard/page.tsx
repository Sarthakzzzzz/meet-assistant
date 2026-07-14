"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { GlassPane } from "../../components/ui/GlassPane";
import { Video, ArrowRight, Loader2 } from "lucide-react";

export default function Dashboard() {
  const [url, setUrl] = useState("");
  const [isJoining, setIsJoining] = useState(false);
  const router = useRouter();

  const handleJoin = async () => {
    if (!url.trim()) return;
    setIsJoining(true);
    try {
      // Meeting link goes to Playwright automation on port 8081
      await fetch(`${process.env.NEXT_PUBLIC_PLAYWRIGHT_URL}/api/start-meeting`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url })
      });
      // Small delay to allow playwright to launch before navigation
      setTimeout(() => {
        router.push(`/meeting/current`);
      }, 1000);
    } catch (e) {
      console.error(e);
      setIsJoining(false);
    }
  };

  return (
    <div className="flex h-screen items-center justify-center bg-black text-zinc-100 font-sans relative overflow-hidden">
      {/* Background glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-600/10 blur-[150px] rounded-full pointer-events-none" />

      <GlassPane className="w-full max-w-md p-8 flex flex-col gap-6 z-10">
        
        <div className="flex flex-col items-center text-center gap-4">
          <div className="w-16 h-16 rounded-3xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 flex items-center justify-center shadow-lg shadow-indigo-500/10">
            <Video size={32} className="text-indigo-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight mb-2 premium-gradient-text">Meet Assistant</h1>
            <p className="text-sm text-zinc-400 leading-relaxed">
              Paste your Google Meet or Teams link below to deploy your AI Copilot.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-4 mt-4">
          <input 
            type="text" 
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="https://meet.google.com/..."
            className="w-full glass-input px-5 py-4 text-sm text-zinc-200 placeholder:text-zinc-600 shadow-inner"
            onKeyDown={e => e.key === "Enter" && handleJoin()}
          />
          
          <button 
            onClick={handleJoin}
            disabled={!url.trim() || isJoining}
            className="w-full relative overflow-hidden group bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-500 text-white font-medium py-4 rounded-xl transition-all shadow-xl shadow-indigo-500/20 active:scale-[0.98] disabled:active:scale-100 disabled:shadow-none flex items-center justify-center gap-2"
          >
            {isJoining ? (
              <Loader2 className="animate-spin" size={20} />
            ) : (
              <>
                <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]" />
                Deploy Copilot
                <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
              </>
            )}
          </button>
        </div>

      </GlassPane>
    </div>
  );
}

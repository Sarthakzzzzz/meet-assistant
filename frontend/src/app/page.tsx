"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const [url, setUrl] = useState("");
  const router = useRouter();

  const handleJoin = () => {
    if (url.trim()) {
      localStorage.setItem("pendingMeetingUrl", url.trim());
    }
    router.push("/login");
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24 relative overflow-hidden">
      {/* Background Gradients */}
      <div className="absolute top-[10%] left-[20%] w-[30%] h-[30%] rounded-full bg-cyan-600/20 blur-[100px]" />
      
      <div className="z-10 flex flex-col items-center max-w-2xl w-full text-center">
        <h1 className="text-5xl font-extrabold mb-6 tracking-tight">
          Supercharge your <br />
          <span className="bg-gradient-to-r from-cyan-400 to-purple-500 bg-clip-text text-transparent">
            Meetings with AI
          </span>
        </h1>
        <p className="text-xl text-slate-400 mb-12">
          Paste your Google Meet or Microsoft Teams link below to start capturing notes and chatting with the assistant in real-time.
        </p>

        <div className="w-full bg-slate-800/60 p-2 rounded-2xl border border-slate-700/50 backdrop-blur-md shadow-2xl flex items-center mb-8 focus-within:border-cyan-500/50 transition-colors">
          <input 
            type="text" 
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://meet.google.com/xxx-xxxx-xxx" 
            className="w-full bg-transparent border-none outline-none text-slate-200 px-6 py-4 placeholder-slate-500"
          />
          <button 
            onClick={handleJoin}
            className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-white font-semibold py-4 px-8 rounded-xl transition-all shadow-lg shadow-cyan-500/20 flex-shrink-0"
          >
            Join Meeting
          </button>
        </div>

        <div className="flex gap-4 text-sm text-slate-500">
          <Link href="/login" className="hover:text-cyan-400 transition-colors underline underline-offset-4">Sign In directly</Link>
          <span>•</span>
          <Link href="/dashboard" className="hover:text-cyan-400 transition-colors underline underline-offset-4">Go to Dashboard</Link>
        </div>
      </div>
    </div>
  );
}

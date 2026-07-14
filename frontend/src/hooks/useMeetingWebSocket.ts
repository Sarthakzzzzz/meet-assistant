import { useState, useEffect, useRef } from "react";

export type Message = {
  role: "ai" | "user";
  text: string;
};

export type Caption = {
  speaker: string;
  text: string;
};

export function useMeetingWebSocket() {
  const [messages, setMessages] = useState<Message[]>([
    { role: "ai", text: "Hello! I'm your Meeting Copilot. Once you log in and join the meeting, click 'Start Recording' to activate my visual and auditory sensors." }
  ]);
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [activeSlidePath, setActiveSlidePath] = useState<string | null>(null);
  const [captions, setCaptions] = useState<Caption[]>([]);
  
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // WebSocket connects to Playwright on 8081 for live events
    const ws = new WebSocket(`${process.env.NEXT_PUBLIC_WS_URL}/ws`);
    ws.onopen = () => console.log("Connected to Meet Assistant Backend");
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === "chat" && data.data.source === "ai") {
          setIsLoading(false);
          setMessages(prev => [...prev, { role: "ai", text: data.data.text }]);
        }
        
        if (data.type === "slide_changed") {
          setActiveSlidePath(data.data.filepath);
        }
        
        if (data.type === "caption") {
          setCaptions(prev => [...prev, { 
            speaker: data.data.speaker, 
            text: data.data.text 
          }]);
        }

      } catch (e) {
        console.error("WS parsing error", e);
      }
    };
    wsRef.current = ws;
    return () => ws.close();
  }, []);

  const handleStartRecording = () => {
    // Start recording via Playwright on 8081
    fetch(`${process.env.NEXT_PUBLIC_PLAYWRIGHT_URL}/api/start-recording`, { method: "POST" })
      .then(res => res.json())
      .then(() => {
        setIsRecording(true);
        setMessages(prev => [...prev, { role: "ai", text: "Sensors activated! I am now analyzing live captions and presentation slides in real-time." }]);
      })
      .catch(console.error);
  };

  const sendMessage = (text: string) => {
    if (!text.trim()) return;
    setMessages(prev => [...prev, { role: "user", text }]);
    setIsLoading(true);
    
    // Chat queries go to FastAPI RAG backend on 8000
    fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text })
    })
    .then(res => res.json())
    .then(data => {
      setIsLoading(false);
      if (data.status === "success") {
        setMessages(prev => [...prev, { role: "ai", text: data.response }]);
      }
    })
    .catch(() => setIsLoading(false));
  };

  return {
    messages,
    isRecording,
    isLoading,
    activeSlidePath,
    captions,
    handleStartRecording,
    sendMessage
  };
}

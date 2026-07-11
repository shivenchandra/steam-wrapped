"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, Download, Loader2, Gamepad2, ChevronRight } from "lucide-react";

export default function Home() {
  const [steamId, setSteamId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [results, setResults] = useState<{
    profile: { name: string; avatar: string };
    images: string[];
  } | null>(null);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!steamId.trim()) return;

    setLoading(true);
    setError("");
    setResults(null);

    try {
      const apiUrl = process.env.NODE_ENV === "development" 
        ? "http://127.0.0.1:5328/api/generate" 
        : "/api/generate";

      const res = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ steam_id: steamId.trim() }),
      });

      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || "Failed to generate Wrapped.");
      }

      setResults({ profile: data.profile, images: data.images });
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (base64Str: string, filename: string) => {
    const link = document.createElement("a");
    link.href = base64Str;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadAll = () => {
    if (!results) return;
    handleDownload(results.images[0], "steam_wrapped_overview.png");
    setTimeout(() => {
      handleDownload(results.images[1], "steam_wrapped_games.png");
    }, 200);
    setTimeout(() => {
      handleDownload(results.images[2], "steam_wrapped_stats.png");
    }, 400);
  };

  return (
    <main className="min-h-screen bg-[var(--background)] text-[var(--foreground)] relative overflow-hidden flex flex-col items-center">
      {/* Background Decor */}
      <div className="absolute inset-0 bg-grid opacity-20 pointer-events-none" />
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-[var(--primary)] rounded-full blur-[150px] opacity-[0.15] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[40%] h-[40%] bg-blue-500 rounded-full blur-[150px] opacity-[0.1] pointer-events-none" />

      <div className="max-w-6xl w-full px-6 py-20 relative z-10 flex flex-col items-center text-center">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <div className="flex items-center justify-center gap-3 mb-4">
            <Gamepad2 size={40} className="text-[var(--primary)]" />
            <h1 className="text-5xl font-black tracking-tight">Steam Wrapped</h1>
          </div>
          <p className="text-xl text-gray-400 max-w-2xl mx-auto">
            Discover your ultimate gaming year. Enter your Steam ID or Vanity URL to generate your personalized stats cards.
          </p>
        </motion.div>

        {/* Search Bar */}
        <motion.form
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.1 }}
          onSubmit={handleGenerate}
          className="w-full max-w-2xl flex flex-col sm:flex-row gap-4 mb-16"
        >
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Enter Steam ID (e.g. 76561198... or vanity_name)"
              value={steamId}
              onChange={(e) => setSteamId(e.target.value)}
              disabled={loading}
              className="w-full bg-[#1a1a1a] border border-[#333333] rounded-xl py-4 pl-12 pr-4 text-lg focus:outline-none focus:border-[var(--primary)] transition-colors disabled:opacity-50"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !steamId.trim()}
            className="bg-[var(--primary)] text-white px-8 py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2 hover:bg-[#0097e6] transition-colors disabled:opacity-50 disabled:cursor-not-allowed glow-primary"
          >
            {loading ? (
              <>
                <Loader2 size={24} className="animate-spin" />
                Generating...
              </>
            ) : (
              <>
                Generate <ChevronRight size={20} />
              </>
            )}
          </button>
        </motion.form>

        {/* Error Message */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="bg-red-500/10 border border-red-500/50 text-red-400 px-6 py-4 rounded-xl mb-12 max-w-2xl w-full"
            >
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Loading State */}
        <AnimatePresence>
          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center py-20"
            >
              <div className="relative w-24 h-24 mb-6">
                <div className="absolute inset-0 border-4 border-[var(--primary)] border-t-transparent rounded-full animate-spin"></div>
                <div className="absolute inset-2 border-4 border-blue-500 border-b-transparent rounded-full animate-spin animate-reverse"></div>
              </div>
              <h3 className="text-2xl font-bold mb-2">Analyzing Your Library...</h3>
              <p className="text-gray-400">Fetching game data, calculating stats, and painting the canvas.</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Results */}
        <AnimatePresence>
          {results && !loading && (
            <motion.div
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full flex flex-col items-center"
            >
              <div className="flex items-center gap-4 mb-10 bg-[#1a1a1a] p-4 rounded-2xl border border-[#333333]">
                {results.profile.avatar && (
                  <img
                    src={results.profile.avatar}
                    alt="Avatar"
                    className="w-16 h-16 rounded-full border-2 border-[var(--primary)]"
                  />
                )}
                <div className="text-left">
                  <p className="text-gray-400 text-sm font-medium uppercase tracking-wider">Ready for</p>
                  <h2 className="text-2xl font-bold">{results.profile.name}</h2>
                </div>
              </div>

              {/* Cards Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12 w-full">
                {results.images.map((imgSrc, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: idx * 0.15 }}
                    className="flex flex-col items-center group"
                  >
                    <div className="relative rounded-2xl overflow-hidden glow-card border border-[#333333] transition-transform duration-300 group-hover:-translate-y-2 group-hover:border-[var(--primary)]">
                      <img
                        src={imgSrc}
                        alt={`Steam Wrapped Card ${idx + 1}`}
                        className="w-full h-auto object-cover"
                      />
                      <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <button
                          onClick={() => handleDownload(imgSrc, `steam_wrapped_card_${idx + 1}.png`)}
                          className="bg-white text-black px-6 py-3 rounded-full font-bold flex items-center gap-2 transform translate-y-4 group-hover:translate-y-0 transition-transform"
                        >
                          <Download size={18} />
                          Download
                        </button>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* Action Buttons */}
              <button
                onClick={handleDownloadAll}
                className="bg-[var(--primary)] text-white px-10 py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-3 hover:bg-[#0097e6] transition-all hover:scale-105 glow-primary"
              >
                <Download size={24} />
                Download All Cards
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}

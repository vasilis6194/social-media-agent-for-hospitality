import React, { useState } from 'react';
import { Camera, Globe, Sparkles, Copy, ExternalLink, Image as ImageIcon, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';

// --- Backend configuration ---
// Prefer Vite env var if set, otherwise fall back to local dev API.
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// --- Components ---

const Card = ({ children, className = "" }) => (
  <div className={`bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden ${className}`}>
    {children}
  </div>
);

const Button = ({ children, onClick, disabled, variant = "primary", className = "" }) => {
  const baseStyle = "px-4 py-2 rounded-lg font-medium transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed";
  const variants = {
    primary: "bg-blue-600 hover:bg-blue-700 text-white shadow-md hover:shadow-lg",
    secondary: "bg-white hover:bg-slate-50 text-slate-700 border border-slate-300",
    ghost: "hover:bg-slate-100 text-slate-600"
  };
  return (
    <button 
      onClick={onClick} 
      disabled={disabled} 
      className={`${baseStyle} ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  );
};

const InputGroup = ({ label, icon: Icon, ...props }) => (
  <div className="space-y-1.5">
    <label className="block text-sm font-medium text-slate-700">{label}</label>
    <div className="relative">
      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
        <Icon size={18} />
      </div>
      <input
        className="block w-full pl-10 pr-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm transition-shadow"
        {...props}
      />
    </div>
  </div>
);

const Badge = ({ children }) => (
  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
    {children}
  </span>
);

// --- Main Application ---

export default function App() {
  const [bookingUrl, setBookingUrl] = useState('');
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [useMock, setUseMock] = useState(false);

  // Mock data for demo purposes
  const mockData = [
    {
      image_url: "https://images.unsplash.com/photo-1571896349842-6e53ce41e8f2?q=80&w=1000&auto=format&fit=crop",
      caption: "Dive into relaxation at our pristine poolside oasis. 🌊 Whether you're soaking up the sun or taking a refreshing dip, our luxury pool area is designed for your ultimate comfort. Experience the perfect blend of tranquility and style.",
      hashtags: ["#LuxuryTravel", "#PoolsideVibes", "#SummerVacation", "#HotelLife", "#Relaxation"]
    },
    {
      image_url: "https://images.unsplash.com/photo-1590490360182-c33d57733427?q=80&w=1000&auto=format&fit=crop",
      caption: "Wake up to breathtaking views and unparalleled comfort. 🛏️ Our suite interiors are crafted to provide a sanctuary of peace after your adventures. Every detail is curated to ensure your stay is nothing short of magical.",
      hashtags: ["#SuiteLife", "#HotelInteriors", "#TravelGoals", "#Comfort", "#DreamStay"]
    },
    {
      image_url: "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?q=80&w=1000&auto=format&fit=crop",
      caption: "Escape to a tropical paradise where the palm trees sway and the ocean breeze whispers. 🌴 Our resort offers a secluded getaway perfect for reconnecting with nature and yourself. Book your stay today!",
      hashtags: ["#TropicalGetaway", "#ResortLife", "#NatureLovers", "#ParadiseFound", "#TravelGram"]
    }
  ];

  const handleGenerate = async () => {
    if (!bookingUrl && !useMock) {
      setError("Please enter a Booking.com URL");
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    if (useMock) {
      // Simulate API delay
      setTimeout(() => {
        setResults(mockData);
        setLoading(false);
      }, 2000);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          booking_url: bookingUrl,
          website_url: websiteUrl || null 
        }),
      });

      if (!response.ok) {
        const errorText = await response.text().catch(() => '');
        throw new Error(
          errorText || `Backend returned HTTP ${response.status}`
        );
      }

      const data = await response.json();

      if (data.status === 'success') {
        setResults(data.data);
      } else {
        throw new Error(data.message || 'Failed to generate content');
      }
    } catch (err) {
      // Log full error to help debug network / CORS issues
      // eslint-disable-next-line no-console
      console.error("Error calling backend /generate:", err);
      setError(err.message || "Could not connect to the agent. Ensure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text, index) => {
    // Internal helper for the fallback mechanism
    const legacyCopy = (t) => {
      try {
        const textArea = document.createElement("textarea");
        textArea.value = t;
        
        // Ensure element is in DOM but invisible to user interactions
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        textArea.style.top = "0";
        document.body.appendChild(textArea);
        
        textArea.focus();
        textArea.select();
        
        const successful = document.execCommand('copy');
        document.body.removeChild(textArea);
        return successful;
      } catch (err) {
        console.error("Fallback copy failed:", err);
        return false;
      }
    };

    // Try modern API first
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text)
        .then(() => {
          setCopiedIndex(index);
          setTimeout(() => setCopiedIndex(null), 2000);
        })
        .catch(err => {
          console.warn("Clipboard API blocked/failed, trying fallback...", err);
          // If modern API fails, try legacy method
          if (legacyCopy(text)) {
            setCopiedIndex(index);
            setTimeout(() => setCopiedIndex(null), 2000);
          }
        });
    } else {
      // If navigator.clipboard doesn't exist, use legacy directly
      if (legacyCopy(text)) {
        setCopiedIndex(index);
        setTimeout(() => setCopiedIndex(null), 2000);
      }
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900 pb-12">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Sparkles className="text-white" size={20} />
            </div>
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
              Hospitality Social Agent
            </h1>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer hover:text-slate-900">
              <input 
                type="checkbox" 
                checked={useMock} 
                onChange={(e) => setUseMock(e.target.checked)}
                className="rounded border-slate-300 text-blue-600 focus:ring-blue-500" 
              />
              Demo Mode
            </label>
            <a href="#" className="text-slate-400 hover:text-slate-600">
              <AlertCircle size={20} />
            </a>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8 space-y-8">
        
        {/* Input Section */}
        <section className="max-w-3xl mx-auto">
          <Card className="p-6 md:p-8">
            <div className="mb-6 text-center">
              <h2 className="text-2xl font-bold text-slate-800 mb-2">Generate Social Content</h2>
              <p className="text-slate-500">Enter your hotel details to automatically generate engaging posts.</p>
            </div>

            <div className="space-y-6">
              <InputGroup 
                label="Booking.com URL" 
                icon={Globe} 
                placeholder="https://www.booking.com/hotel/..." 
                value={bookingUrl}
                onChange={(e) => setBookingUrl(e.target.value)}
              />
              
              <InputGroup 
                label="Official Website (Optional)" 
                icon={ExternalLink} 
                placeholder="https://www.my-hotel.com" 
                value={websiteUrl}
                onChange={(e) => setWebsiteUrl(e.target.value)}
              />

              {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3 text-red-700 text-sm">
                  <AlertCircle size={18} className="mt-0.5 shrink-0" />
                  <p>{error}</p>
                </div>
              )}

              <Button 
                onClick={handleGenerate} 
                disabled={loading} 
                className="w-full py-3 text-lg shadow-blue-200"
              >
                {loading ? (
                  <>
                    <Loader2 className="animate-spin" />
                    Analyzing & Generating...
                  </>
                ) : (
                  <>
                    <Sparkles size={18} />
                    Generate Posts
                  </>
                )}
              </Button>
            </div>
          </Card>
        </section>

        {/* Results Section */}
        {results && (
          <section className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                Generated Posts <Badge>{results.length}</Badge>
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {results.map((post, idx) => (
                <Card key={idx} className="flex flex-col h-full group hover:border-blue-300 transition-colors">
                  {/* Image Area */}
                  <div className="relative aspect-[4/3] bg-slate-100 overflow-hidden">
                    {post.image_url ? (
                      <img 
                        src={post.image_url} 
                        alt="Hotel amenity" 
                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                        onError={(e) => {
                          e.target.onerror = null;
                          e.target.src = "https://placehold.co/600x400?text=Image+Not+Available";
                        }}
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-slate-400">
                        <ImageIcon size={48} />
                      </div>
                    )}
                    <div className="absolute top-3 right-3">
                       <a 
                        href={post.image_url} 
                        target="_blank" 
                        rel="noreferrer"
                        className="p-2 bg-black/50 hover:bg-black/70 text-white rounded-full backdrop-blur-sm transition-colors block"
                        title="View Original Image"
                       >
                         <ExternalLink size={16} />
                       </a>
                    </div>
                  </div>

                  {/* Content Area */}
                  <div className="p-5 flex-1 flex flex-col">
                    <div className="flex-1">
                      <p className="text-slate-700 leading-relaxed mb-4 text-sm">
                        {post.caption}
                      </p>
                      <div className="flex flex-wrap gap-2 mb-4">
                        {post.hashtags && post.hashtags.map((tag, tIdx) => (
                          <span key={tIdx} className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-1 rounded">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                      <span className="text-xs text-slate-400 font-medium">
                        Ready to post
                      </span>
                      <Button 
                        variant="secondary" 
                        className="text-xs px-3 py-1.5 h-8"
                        onClick={() => copyToClipboard(`${post.caption}\n\n${post.hashtags.join(' ')}`, idx)}
                      >
                        {copiedIndex === idx ? (
                          <>
                            <CheckCircle2 size={14} className="text-green-600" />
                            Copied!
                          </>
                        ) : (
                          <>
                            <Copy size={14} />
                            Copy
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

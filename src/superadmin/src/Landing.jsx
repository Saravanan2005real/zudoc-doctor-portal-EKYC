import { ShieldCheck, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function Landing() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900 flex flex-col relative overflow-hidden">
      {/* Background Gradients (Glassmorphism) */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-teal-400/20 blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[30%] h-[30%] rounded-full bg-cyan-500/20 blur-[100px] pointer-events-none"></div>

      {/* Navbar */}
      <nav className="flex justify-between items-center p-6 lg:px-12 relative z-10 border-b border-slate-200/50 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <ShieldCheck className="text-teal-600" size={32} />
          <span className="text-2xl font-extrabold tracking-tight">Verifyyy</span>
        </div>
        <div className="flex gap-4">
          <button 
            onClick={() => navigate('/dashboard')}
            className="px-6 py-2.5 rounded-full text-sm font-bold text-slate-600 hover:text-slate-900 transition-colors"
          >
            Documentation
          </button>
          <button 
            onClick={() => navigate('/dashboard')}
            className="px-6 py-2.5 rounded-full bg-teal-700 text-white text-sm font-bold shadow-soft hover:shadow-teal-glow hover:-translate-y-0.5 transition-all"
          >
            Admin Login
          </button>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="flex-1 flex flex-col justify-center items-center text-center px-4 relative z-10 -mt-10">
        <div className="inline-block px-4 py-1.5 rounded-full bg-teal-50 border border-teal-100 text-teal-700 text-xs font-bold uppercase tracking-wider mb-8">
          The Verification OS
        </div>
        
        <h1 className="text-5xl lg:text-7xl font-extrabold tracking-tight max-w-4xl leading-[1.1] mb-6">
          Your Platform. <br/>
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-600 to-cyan-500">
            Your Decisions. Your Edge.
          </span>
        </h1>
        
        <p className="text-lg text-slate-500 max-w-2xl mb-10 font-medium">
          The clinical curator for modern medicine. Reduce fraud and compliance overhead with an AI verification assistant that treats data as high-end intelligence.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4">
          <button 
            onClick={() => navigate('/dashboard')}
            className="flex items-center justify-center gap-2 px-8 py-4 rounded-full bg-teal-700 text-white font-bold text-lg shadow-teal-glow hover:bg-teal-800 hover:-translate-y-1 transition-all"
          >
            Access Dashboard <ArrowRight size={20} />
          </button>
          <button 
            className="px-8 py-4 rounded-full bg-white text-slate-700 border border-slate-200 font-bold text-lg shadow-soft hover:bg-slate-50 transition-colors"
          >
            View Demo
          </button>
        </div>
        
        {/* Mock Graphic */}
        <div className="mt-16 w-full max-w-5xl h-64 lg:h-96 bg-white/60 backdrop-blur-xl border border-white rounded-[2rem] shadow-2xl overflow-hidden relative">
            <div className="absolute inset-0 bg-gradient-to-b from-transparent to-slate-50/90 z-10"></div>
            <div className="w-full h-12 bg-slate-100/80 border-b border-slate-200 flex items-center px-6 gap-2">
                <div className="w-3 h-3 rounded-full bg-rose-400"></div>
                <div className="w-3 h-3 rounded-full bg-amber-400"></div>
                <div className="w-3 h-3 rounded-full bg-emerald-400"></div>
            </div>
            <div className="p-8 flex gap-6">
                <div className="w-1/3 h-40 bg-teal-50 rounded-2xl animate-pulse"></div>
                <div className="flex-1 space-y-4">
                    <div className="w-full h-8 bg-slate-100 rounded-lg animate-pulse"></div>
                    <div className="w-3/4 h-8 bg-slate-100 rounded-lg animate-pulse" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-1/2 h-8 bg-slate-100 rounded-lg animate-pulse" style={{ animationDelay: '300ms' }}></div>
                </div>
            </div>
        </div>
      </main>
    </div>
  );
}

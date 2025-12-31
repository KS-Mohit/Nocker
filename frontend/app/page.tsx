"use client"
import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  LayoutDashboard, 
  Briefcase, 
  FileText, 
  Settings, 
  Search, 
  Bell, 
  ChevronRight, 
  Upload, 
  CheckCircle, 
  XCircle, 
  Clock, 
  Linkedin,
  Cpu,
  Database,
  User,
  Bot,
  ChevronDown,
  ChevronUp,
  Terminal,
  Play,
  Pause,
  Globe,
  Loader2,
  Sparkles
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';

// --- MOCK DATA ---
const CHART_DATA = [
  { name: 'Mon', applied: 4, rejected: 1, interview: 0 },
  { name: 'Tue', applied: 3, rejected: 0, interview: 1 },
  { name: 'Wed', applied: 8, rejected: 2, interview: 0 },
  { name: 'Thu', applied: 6, rejected: 1, interview: 2 },
  { name: 'Fri', applied: 5, rejected: 3, interview: 1 },
  { name: 'Sat', applied: 2, rejected: 0, interview: 0 },
  { name: 'Sun', applied: 1, rejected: 0, interview: 0 },
];

const STATUS_DATA = [
  { name: 'Pending', value: 45, color: '#fbbf24' },
  { name: 'Applied', value: 120, color: '#3b82f6' },
  { name: 'Rejected', value: 25, color: '#ef4444' },
  { name: 'Interview', value: 10, color: '#10b981' },
];

const JOBS_DATA = [
  { id: 1, title: 'Senior Frontend Developer', company: 'TechNova', location: 'Remote', salary: '$120k - $150k', status: 'Applied', match: 95 },
  { id: 2, title: 'AI Engineer', company: 'DeepMindz', location: 'London, UK', salary: '£80k - £110k', status: 'Interview', match: 88 },
  { id: 3, title: 'Full Stack Engineer', company: 'StartUp Inc', location: 'New York, NY', salary: '$100k - $130k', status: 'Rejected', match: 60 },
  { id: 4, title: 'React Native Developer', company: 'MobileFirst', location: 'Berlin, DE', salary: '€70k - €90k', status: 'Pending', match: 75 },
  { id: 5, title: 'Backend Architect', company: 'CloudScale', location: 'San Francisco, CA', salary: '$160k - $200k', status: 'Offer', match: 92 },
];

const LOGS_MOCK = [
  { time: '10:42:01', type: 'info', message: 'Initializing Nocker Agent v2.1...' },
  { time: '10:42:05', type: 'success', message: 'Connected to LinkedIn Securely.' },
  { time: '10:42:12', type: 'info', message: 'Scanning feed for "Frontend Engineer"...' },
  { time: '10:42:15', type: 'action', message: 'Found match: Senior React Dev at Vercel (98% Match)' },
  { time: '10:42:18', type: 'action', message: 'Analyzing job description requirements...' },
  { time: '10:42:22', type: 'info', message: 'Generating custom cover letter...' },
];

// --- COMPONENTS ---

// 1. Antigravity Particle Background
const ParticleBackground = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let particles: { x: number; y: number; vx: number; vy: number; size: number; color: string }[] = [];
    const particleCount = 60;

    const resize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', resize);
    resize();

    // Init particles
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        size: Math.random() * 2 + 1,
        color: Math.random() > 0.5 ? 'rgba(59, 130, 246, 0.5)' : 'rgba(139, 92, 246, 0.5)' // Blue or Purple
      });
    }

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      particles.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;

        // "Antigravity" float - gently push up occasionally
        if (Math.random() < 0.01) p.vy -= 0.05;

        // Bounce off edges
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.fill();
      });

      // Connect particles
      ctx.strokeStyle = 'rgba(100, 116, 139, 0.1)';
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 100) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.stroke();
          }
        }
      }

      requestAnimationFrame(animate);
    };
    animate();

    return () => window.removeEventListener('resize', resize);
  }, []);

  return <canvas ref={canvasRef} className="fixed inset-0 pointer-events-none z-0 opacity-40" />;
};

// 2. Custom Logo (The "Machli Dusri")
const FishLogo = () => (
  <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg" className="text-blue-600">
    <path d="M4 20C4 20 10 10 20 10C30 10 36 20 36 20C36 20 30 30 20 30C10 30 4 20 4 20Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <circle cx="20" cy="20" r="4" fill="currentColor" />
    <path d="M36 20L39 17M36 20L39 23" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M14 26C14 26 16 28 20 28C24 28 26 26 26 26" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

// 3. Status Timeline Component
const StatusTimeline = ({ status }: { status: string }) => {
  const stages = ['Applied', 'Screening', 'Interview', 'Offer'];
  // Map status to index. 'Pending' treats as 0 but maybe different color. 'Rejected' stops at current.
  
  let currentIndex = stages.indexOf(status);
  if (currentIndex === -1) currentIndex = 0; // Default to first if unknown
  if (status === 'Pending') currentIndex = 0;
  if (status === 'Rejected') currentIndex = 1; // Example: Rejected after screening

  const getStatusColor = (idx: number) => {
    if (status === 'Rejected' && idx === currentIndex) return 'bg-red-500 border-red-500';
    if (idx < currentIndex) return 'bg-blue-600 border-blue-600';
    if (idx === currentIndex) return 'bg-blue-600 border-blue-600 animate-pulse';
    return 'bg-white border-slate-300';
  };

  const getTextColor = (idx: number) => {
    if (status === 'Rejected' && idx === currentIndex) return 'text-red-600 font-bold';
    if (idx <= currentIndex) return 'text-blue-600 font-bold';
    return 'text-slate-400';
  };

  return (
    <div className="flex items-center w-full max-w-xs">
      {stages.map((stage, idx) => (
        <div key={stage} className="flex-1 relative flex flex-col items-center group">
           {/* Line Connector */}
           {idx !== 0 && (
             <div className={`absolute top-1.5 right-[50%] w-full h-[2px] -z-10 ${
               idx <= currentIndex ? (status === 'Rejected' && idx === currentIndex ? 'bg-red-200' : 'bg-blue-200') : 'bg-slate-200'
             }`} />
           )}
           {/* Dot */}
           <div className={`w-3 h-3 rounded-full border-2 ${getStatusColor(idx)} z-10 transition-colors duration-300`} />
           {/* Label Tooltip (visible on hover or active) */}
           <span className={`text-[10px] mt-1 absolute top-4 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity ${getTextColor(idx)}`}>
             {stage}
           </span>
        </div>
      ))}
    </div>
  );
};


// 4. Main App Component
export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  
  // Dashboard specific state
  const [isActivityCollapsed, setIsActivityCollapsed] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  
  // Auto Apply specific state
  const [agentStatus, setAgentStatus] = useState<'idle' | 'running' | 'paused'>('idle');
  const [logs, setLogs] = useState(LOGS_MOCK);

  // Filter jobs based on search
  const filteredJobs = useMemo(() => {
    if (!searchQuery) return JOBS_DATA;
    const lower = searchQuery.toLowerCase();
    return JOBS_DATA.filter(j => 
      j.title.toLowerCase().includes(lower) || 
      j.company.toLowerCase().includes(lower) ||
      j.status.toLowerCase().includes(lower)
    );
  }, [searchQuery]);

  // --- Views ---

  const DashboardView = () => (
    <div className="space-y-6 animate-fade-in">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Total Jobs Applied', value: '156', icon: <Briefcase className="w-5 h-5 text-blue-600" />, trend: '+12%' },
          { label: 'Interviews Scheduled', value: '8', icon: <CheckCircle className="w-5 h-5 text-emerald-600" />, trend: '+2%' },
          { label: 'Rejections', value: '24', icon: <XCircle className="w-5 h-5 text-red-600" />, trend: '-5%' },
          { label: 'Pending Response', value: '45', icon: <Clock className="w-5 h-5 text-amber-600" />, trend: '+8%' },
        ].map((stat, idx) => (
          <div key={idx} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
            <div className="flex justify-between items-start mb-4">
              <div className="p-2 bg-slate-50 rounded-lg">{stat.icon}</div>
              <span className={`text-xs font-medium px-2 py-1 rounded-full ${stat.trend.startsWith('+') ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'}`}>
                {stat.trend}
              </span>
            </div>
            <h3 className="text-slate-500 text-sm font-medium">{stat.label}</h3>
            <p className="text-2xl font-bold text-slate-800 mt-1">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Collapsible Charts Section */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden transition-all duration-300">
        <button 
          onClick={() => setIsActivityCollapsed(!isActivityCollapsed)}
          className="w-full p-4 flex items-center justify-between hover:bg-slate-50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-slate-800">Application Analytics</h2>
            <span className="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
              {isActivityCollapsed ? 'Click to Expand' : 'Active'}
            </span>
          </div>
          {isActivityCollapsed ? <ChevronDown className="text-slate-400" /> : <ChevronUp className="text-slate-400" />}
        </button>
        
        {!isActivityCollapsed && (
          <div className="p-6 border-t border-slate-100 grid grid-cols-1 lg:grid-cols-3 gap-6 animate-in slide-in-from-top-4 duration-300">
             {/* Main Area Chart */}
            <div className="lg:col-span-2">
              <h3 className="text-sm font-medium text-slate-500 mb-4">Activity Volume</h3>
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={CHART_DATA}>
                    <defs>
                      <linearGradient id="colorApplied" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.1}/>
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 12}} />
                    <YAxis axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 12}} />
                    <Tooltip 
                      contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'}} 
                      cursor={{stroke: '#cbd5e1', strokeWidth: 1}}
                    />
                    <Area type="monotone" dataKey="applied" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorApplied)" />
                    <Area type="monotone" dataKey="rejected" stroke="#ef4444" strokeWidth={3} fill="none" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Status Pie Chart */}
            <div>
              <h3 className="text-sm font-medium text-slate-500 mb-4">Outcome Distribution</h3>
              <div className="h-[300px] w-full relative">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={STATUS_DATA}
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {STATUS_DATA.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-slate-800">200</p>
                    <p className="text-xs text-slate-500">Total</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Applied Jobs Section (Smart Search + Timeline) */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-center gap-4">
          <h2 className="text-lg font-bold text-slate-800">Applied Jobs</h2>
          
          {/* Smart Search Bar */}
          <div className="relative w-full sm:w-auto">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
            <input 
              type="text" 
              placeholder="Search companies, roles, status..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-4 py-2 w-full sm:w-80 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 text-sm transition-all"
            />
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50 text-slate-500 font-medium">
              <tr>
                <th className="px-6 py-4">Role & Company</th>
                <th className="px-6 py-4">Match</th>
                <th className="px-6 py-4 text-center">Application Timeline</th>
                <th className="px-6 py-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredJobs.length > 0 ? filteredJobs.map((job) => (
                <tr key={job.id} className="hover:bg-slate-50/50 transition-colors group">
                  <td className="px-6 py-4">
                    <div className="font-medium text-slate-800">{job.title}</div>
                    <div className="text-slate-500 text-xs">{job.company} • {job.location}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      job.match > 80 ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
                    }`}>
                      {job.match}%
                    </span>
                  </td>
                  <td className="px-6 py-4 flex justify-center">
                    <StatusTimeline status={job.status} />
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button className="text-slate-400 hover:text-blue-600">
                      <ChevronRight className="w-5 h-5 ml-auto" />
                    </button>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center text-slate-400">
                    No jobs found matching "{searchQuery}"
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  const AutoApplyView = () => (
    <div className="flex flex-col lg:flex-row h-[calc(100vh-140px)] gap-6 animate-fade-in">
       {/* Agent Console (Left Panel) */}
       <div className="flex-1 bg-slate-900 rounded-2xl overflow-hidden shadow-xl flex flex-col border border-slate-700">
         <div className="p-4 bg-slate-800 border-b border-slate-700 flex justify-between items-center">
            <div className="flex items-center gap-2 text-white">
              <Bot className="w-5 h-5 text-emerald-400" />
              <span className="font-mono font-bold">Nocker Agent v2.1</span>
            </div>
            <div className="flex gap-2">
               {agentStatus === 'running' ? (
                 <button onClick={() => setAgentStatus('paused')} className="p-2 bg-amber-500/20 text-amber-500 rounded hover:bg-amber-500/30">
                   <Pause className="w-4 h-4" />
                 </button>
               ) : (
                 <button onClick={() => setAgentStatus('running')} className="p-2 bg-emerald-500/20 text-emerald-500 rounded hover:bg-emerald-500/30">
                   <Play className="w-4 h-4" />
                 </button>
               )}
            </div>
         </div>
         
         {/* Terminal Output */}
         <div className="flex-1 p-4 font-mono text-sm overflow-y-auto space-y-3 custom-scrollbar">
            {logs.map((log, i) => (
              <div key={i} className="flex gap-3 items-start animate-fade-in-up">
                <span className="text-slate-500 shrink-0">{log.time}</span>
                {log.type === 'info' && <span className="text-blue-400">ℹ {log.message}</span>}
                {log.type === 'success' && <span className="text-emerald-400">✓ {log.message}</span>}
                {log.type === 'action' && <span className="text-amber-400">⚡ {log.message}</span>}
                {log.type === 'error' && <span className="text-red-400">✗ {log.message}</span>}
              </div>
            ))}
            {agentStatus === 'running' && (
              <div className="flex gap-3 items-center text-slate-400 animate-pulse">
                <span className="text-slate-500">{new Date().toLocaleTimeString()}</span>
                <span>Using Resume_v2.pdf to fill details...</span>
              </div>
            )}
         </div>

         {/* Stats Footer */}
         <div className="p-3 bg-slate-800 border-t border-slate-700 grid grid-cols-3 text-center text-xs text-slate-400">
            <div>
              <span className="block text-white font-bold text-lg">12</span>
              Applications
            </div>
            <div>
              <span className="block text-white font-bold text-lg">1.4m</span>
              Tokens Used
            </div>
            <div>
              <span className="block text-emerald-400 font-bold text-lg">98%</span>
              Success Rate
            </div>
         </div>
       </div>

       {/* Browser Preview (Right Panel) */}
       <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-200 flex flex-col overflow-hidden relative">
          <div className="h-10 bg-slate-100 border-b border-slate-200 flex items-center px-4 gap-2">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-400" />
              <div className="w-3 h-3 rounded-full bg-amber-400" />
              <div className="w-3 h-3 rounded-full bg-emerald-400" />
            </div>
            <div className="flex-1 bg-white mx-4 h-6 rounded flex items-center px-3 text-xs text-slate-500 shadow-sm">
              <Globe className="w-3 h-3 mr-2 text-slate-400" />
              linkedin.com/jobs/view/38102...
            </div>
          </div>
          
          <div className="flex-1 relative bg-slate-50 p-4 overflow-hidden">
             {/* Simulating LinkedIn Job Page */}
             <div className="w-full h-full bg-white shadow-sm rounded border border-slate-200 p-6 opacity-90 blur-[0.5px]">
                <div className="h-8 w-1/3 bg-slate-200 rounded mb-4 animate-pulse" />
                <div className="h-4 w-1/4 bg-slate-100 rounded mb-8 animate-pulse" />
                
                <div className="space-y-3">
                   <div className="h-4 w-full bg-slate-100 rounded animate-pulse" />
                   <div className="h-4 w-full bg-slate-100 rounded animate-pulse" />
                   <div className="h-4 w-3/4 bg-slate-100 rounded animate-pulse" />
                </div>

                {/* AI Cursor Overlay */}
                {agentStatus === 'running' && (
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-2 z-10">
                    <div className="w-12 h-12 bg-blue-600/20 rounded-full flex items-center justify-center animate-ping absolute" />
                    <div className="bg-blue-600 text-white px-4 py-2 rounded-full text-sm font-medium shadow-lg flex items-center gap-2">
                       <Sparkles className="w-4 h-4" />
                       AI is Auto-Filling...
                    </div>
                  </div>
                )}
             </div>
          </div>
       </div>
    </div>
  );

  const JobsView = () => (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-slate-800">Job Feed</h2>
        <div className="flex gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4" />
            <input 
              type="text" 
              placeholder="Search roles..." 
              className="pl-10 pr-4 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 text-sm w-64"
            />
          </div>
          <button className="bg-blue-600 text-white px-4 py-2 rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors">
            Auto Apply All
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {JOBS_DATA.map((job) => (
          <div key={job.id} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center justify-between hover:shadow-md transition-all group">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center text-blue-600 font-bold text-lg">
                {job.company[0]}
              </div>
              <div>
                <h3 className="font-bold text-slate-800 group-hover:text-blue-600 transition-colors">{job.title}</h3>
                <div className="flex items-center gap-3 text-sm text-slate-500 mt-1">
                  <span>{job.company}</span>
                  <span>•</span>
                  <span>{job.location}</span>
                  <span>•</span>
                  <span>{job.salary}</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-6">
              <div className="text-right">
                <div className="text-xs text-slate-400 uppercase font-semibold mb-1">AI Match</div>
                <div className="text-lg font-bold text-emerald-600">{job.match}%</div>
              </div>
              <button className="p-2 hover:bg-slate-100 rounded-full text-slate-400 hover:text-blue-600 transition-colors">
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const KnowledgeView = () => (
    <div className="max-w-4xl mx-auto space-y-8 animate-fade-in">
      <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 text-center border-dashed border-2 border-slate-200">
        <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
          <Upload className="w-8 h-8" />
        </div>
        <h3 className="text-lg font-bold text-slate-800">Upload your Resume</h3>
        <p className="text-slate-500 mt-2 mb-6 max-w-md mx-auto">
          AI will parse your resume to autofill applications. Supports PDF, DOCX (Max 5MB).
        </p>
        <button className="bg-slate-900 text-white px-6 py-3 rounded-xl font-medium hover:bg-slate-800 transition-colors">
          Select File
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <div className="flex items-center gap-3 mb-4">
            <User className="w-5 h-5 text-blue-600" />
            <h3 className="font-bold text-slate-800">Personal Info</h3>
          </div>
          <div className="space-y-4">
             <div className="h-10 bg-slate-50 rounded-lg w-full animate-pulse" />
             <div className="h-10 bg-slate-50 rounded-lg w-full animate-pulse" />
             <div className="h-24 bg-slate-50 rounded-lg w-full animate-pulse" />
          </div>
        </div>
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <div className="flex items-center gap-3 mb-4">
            <Database className="w-5 h-5 text-purple-600" />
            <h3 className="font-bold text-slate-800">Experience Data</h3>
          </div>
           <div className="space-y-4">
             <div className="h-24 bg-slate-50 rounded-lg w-full animate-pulse" />
             <div className="h-24 bg-slate-50 rounded-lg w-full animate-pulse" />
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans selection:bg-blue-100 overflow-hidden flex relative">
      <ParticleBackground />
      
      {/* Sidebar */}
      <aside className={`fixed md:relative z-20 h-screen bg-white border-r border-slate-200 transition-all duration-300 ${isSidebarOpen ? 'w-64' : 'w-20'}`}>
        <div className="h-20 flex items-center justify-center border-b border-slate-100">
          <div className="flex items-center gap-3">
             <FishLogo />
             {isSidebarOpen && <span className="font-bold text-xl tracking-tight text-slate-800">Nocker<span className="text-blue-600">.ai</span></span>}
          </div>
        </div>

        <nav className="p-4 space-y-2 mt-4">
          {[
            { id: 'dashboard', icon: <LayoutDashboard />, label: 'Dashboard' },
            { id: 'auto-apply', icon: <Bot className={agentStatus === 'running' ? 'text-emerald-500 animate-pulse' : ''} />, label: 'Auto Agent' },
            { id: 'jobs', icon: <Briefcase />, label: 'Jobs Feed' },
            { id: 'applications', icon: <FileText />, label: 'Applications' },
            { id: 'knowledge', icon: <Database />, label: 'Knowledge Base' },
            { id: 'settings', icon: <Settings />, label: 'Settings' },
          ].map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 ${
                activeTab === item.id 
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30' 
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900'
              }`}
            >
              <span className="w-5 h-5">{item.icon}</span>
              {isSidebarOpen && <span className="font-medium text-sm">{item.label}</span>}
            </button>
          ))}
        </nav>

        <div className="absolute bottom-8 left-0 w-full px-4">
           {isSidebarOpen ? (
             <div className="bg-slate-900 text-white p-4 rounded-xl relative overflow-hidden">
               <div className="relative z-10">
                 <p className="text-xs font-medium text-slate-400 uppercase mb-1">Tokens Left</p>
                 <p className="text-xl font-bold">12,450</p>
                 <div className="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
                   <div className="bg-emerald-400 h-full w-[70%]" />
                 </div>
               </div>
               {/* Decorative Circle */}
               <div className="absolute -right-4 -top-4 w-20 h-20 bg-blue-600 rounded-full opacity-20 blur-xl" />
             </div>
           ) : (
             <div className="flex justify-center">
               <div className="w-2 h-2 bg-emerald-400 rounded-full ring-4 ring-emerald-400/20" />
             </div>
           )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 h-screen overflow-y-auto relative z-10 scrollbar-hide">
        {/* Header */}
        <header className="h-20 bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-20 px-8 flex justify-between items-center">
          <h1 className="text-xl font-bold text-slate-800 capitalize">{activeTab.replace('-', ' ')}</h1>
          <div className="flex items-center gap-6">
            <button className="relative p-2 text-slate-400 hover:text-blue-600 transition-colors">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-500 border-2 border-white rounded-full" />
            </button>
            <div className="flex items-center gap-3 pl-6 border-l border-slate-200">
              <div className="text-right hidden md:block">
                <p className="text-sm font-bold text-slate-800">Alex Designer</p>
                <p className="text-xs text-slate-500">Pro Plan</p>
              </div>
              <div className="w-10 h-10 bg-slate-200 rounded-full overflow-hidden border-2 border-white shadow-sm">
                <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Alex" alt="User" />
              </div>
            </div>
          </div>
        </header>

        {/* Content Area */}
        <div className="p-8 pb-20">
          {activeTab === 'dashboard' && <DashboardView />}
          {activeTab === 'auto-apply' && <AutoApplyView />}
          {activeTab === 'jobs' && <JobsView />}
          {activeTab === 'knowledge' && <KnowledgeView />}
          {activeTab === 'settings' && (
            <div className="max-w-2xl mx-auto bg-white p-8 rounded-2xl shadow-sm border border-slate-100 animate-fade-in">
              <h2 className="text-lg font-bold mb-6 flex items-center gap-2">
                <Linkedin className="w-5 h-5 text-blue-700" /> 
                LinkedIn Integration
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                  <input type="email" className="w-full px-4 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-blue-500/20 outline-none" placeholder="linkedin@email.com" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
                  <input type="password" class="w-full px-4 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-blue-500/20 outline-none" placeholder="••••••••" />
                </div>
                <button className="w-full bg-blue-600 text-white py-2.5 rounded-lg font-medium hover:bg-blue-700 transition-colors mt-4">
                  Connect Account
                </button>
              </div>
            </div>
          )}
          {activeTab === 'applications' && (
             <div className="text-center py-20 animate-fade-in">
               <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4 text-slate-400">
                 <FileText className="w-10 h-10" />
               </div>
               <h3 className="text-lg font-bold text-slate-700">Application Tracker</h3>
               <p className="text-slate-500">Your kanban board is being configured...</p>
             </div>
          )}
        </div>
      </main>
    </div>
  );
}
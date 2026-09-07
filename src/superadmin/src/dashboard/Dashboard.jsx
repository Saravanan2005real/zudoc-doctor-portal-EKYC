import { useState, useEffect } from 'react';
import { Users, Building2, CheckCircle2, AlertCircle } from 'lucide-react';

export default function Dashboard() {
  const [stats, setStats] = useState({
    total_companies: 0,
    active_clients: 0,
    verified_today: 0,
    manual_review: 0,
    service_utilization: []
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('/api/v1/admin/dashboard-stats');
        if (response.ok) {
          const data = await response.json();
          setStats(data);
        }
      } catch (err) {
        console.error("Failed to fetch dashboard stats", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchStats();
  }, []);

  return (
    <div className="max-w-6xl mx-auto font-sans">
      <h1 className="text-3xl font-extrabold text-slate-900 mb-8 tracking-tight">Platform Overview</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-10">
        <div className="bg-white p-8 rounded-3xl border border-slate-100 shadow-soft transition-all duration-300 hover:shadow-teal-glow hover:-translate-y-1">
          <div className="flex items-center gap-3 text-slate-500 mb-4">
            <div className="p-2 bg-teal-50 rounded-xl text-teal-600">
              <Building2 size={24} />
            </div>
            <h3 className="font-semibold text-sm tracking-wide uppercase">Total Companies</h3>
          </div>
          <p className="text-4xl font-extrabold text-slate-900">
            {loading ? '...' : (stats?.total_companies || 0)}
          </p>
        </div>
        
        <div className="bg-white p-8 rounded-3xl border border-slate-100 shadow-soft transition-all duration-300 hover:shadow-teal-glow hover:-translate-y-1">
          <div className="flex items-center gap-3 text-slate-500 mb-4">
            <div className="p-2 bg-teal-50 rounded-xl text-teal-600">
              <Users size={24} />
            </div>
            <h3 className="font-semibold text-sm tracking-wide uppercase">Active Clients</h3>
          </div>
          <p className="text-4xl font-extrabold text-slate-900">
            {loading ? '...' : (stats?.active_clients || 0)}
          </p>
        </div>
        
        <div className="bg-white p-8 rounded-3xl border border-slate-100 shadow-soft transition-all duration-300 hover:shadow-teal-glow hover:-translate-y-1">
          <div className="flex items-center gap-3 text-slate-500 mb-4">
            <div className="p-2 bg-teal-50 rounded-xl text-teal-600">
              <CheckCircle2 size={24} />
            </div>
            <h3 className="font-semibold text-sm tracking-wide uppercase">Verified (Today)</h3>
          </div>
          <p className="text-4xl font-extrabold text-slate-900">
            {loading ? '...' : (stats?.verified_today || 0).toLocaleString()}
          </p>
        </div>
        
        <div className="bg-white p-8 rounded-3xl border border-slate-100 shadow-soft transition-all duration-300 hover:shadow-teal-glow hover:-translate-y-1">
          <div className="flex items-center gap-3 text-slate-500 mb-4">
            <div className="p-2 bg-rose-50 rounded-xl text-rose-500">
              <AlertCircle size={24} />
            </div>
            <h3 className="font-semibold text-sm tracking-wide uppercase">Manual Review</h3>
          </div>
          <p className="text-4xl font-extrabold text-slate-900">
            {loading ? '...' : (stats?.manual_review || 0)}
          </p>
        </div>
      </div>

      <div className="bg-white p-8 rounded-3xl border border-slate-100 shadow-soft">
        <h2 className="text-xl font-extrabold text-slate-900 mb-6 tracking-tight">Service Utilization</h2>
        <div className="space-y-5">
          {loading ? (
            <p className="text-slate-500">Loading metrics...</p>
          ) : (stats?.service_utilization?.length || 0) > 0 ? (
            stats.service_utilization.map((service, idx) => (
              <div key={idx}>
                <div className="flex justify-between text-sm mb-2">
                  <span className="font-bold text-slate-700">{service?.name || 'Unknown'}</span>
                  <span className="text-slate-500 font-semibold">{service?.percentage || 0}%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-3">
                  <div className="bg-teal-500 h-3 rounded-full transition-all duration-1000" style={{ width: `${service?.percentage || 0}%` }}></div>
                </div>
              </div>
            ))
          ) : (
             <p className="text-slate-500 font-medium">No utilization data available.</p>
          )}
        </div>
      </div>
    </div>
  );
}

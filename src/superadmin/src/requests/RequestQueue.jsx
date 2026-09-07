import { useState, useEffect } from 'react';
import axios from 'axios';
import { Activity, CheckCircle, Mail, Building, FileText, Settings } from 'lucide-react';

export default function RequestQueue() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [approving, setApproving] = useState(null);
  const [apiKeyModal, setApiKeyModal] = useState(null);

  const fetchRequests = async () => {
    try {
      const response = await axios.get('/api/v1/b2b/admin/requests');
      setRequests(response.data.data || []);
    } catch (e) {
      console.error('Failed to load requests:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const handleApprove = async (id) => {
    if (!window.confirm('Are you sure you want to approve this company and grant API access?')) return;
    
    setApproving(id);
    try {
      const response = await axios.post(`/api/v1/b2b/admin/requests/${id}/approve`, {});
      setApiKeyModal(response.data.api_key);
      fetchRequests();
    } catch (err) {
      alert('Failed to approve: ' + (err.response?.data?.detail || err.message));
    } finally {
      setApproving(null);
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Activity className="text-teal-600" /> Pipeline Requests
        </h1>
        <button onClick={fetchRequests} className="text-sm font-medium text-teal-600 hover:text-teal-800">
          Refresh List
        </button>
      </div>

      {loading ? (
        <div className="p-8 text-center text-gray-500">Loading requests...</div>
      ) : requests.length === 0 ? (
        <div className="p-8 text-center bg-white rounded-2xl border border-slate-200 text-slate-500">
          No pipeline requests found.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {requests.map(req => (
            <div key={req.id} className="bg-white rounded-3xl border border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-4">
                <h3 className="font-bold text-lg text-slate-900">{req.company_name}</h3>
                <span className={`px-2 py-1 text-xs font-bold rounded-lg ${req.status === 'PENDING' ? 'bg-amber-100 text-amber-700' : 'bg-teal-100 text-teal-700'}`}>
                  {req.status}
                </span>
              </div>
              
              <div className="space-y-3 mb-6">
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <Mail size={16} className="text-slate-400" />
                  <span>{req.contact_name} ({req.contact_email})</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <Building size={16} className="text-slate-400" />
                  <span>{req.industry}</span>
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <Activity size={16} className="text-slate-400" />
                  <span>Vol: {req.expected_volume}/mo</span>
                </div>
              </div>

              <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100 mb-6">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-2">
                  <Settings size={16} className="text-slate-400" />
                  Pipeline Requirements
                </div>
                <p className="text-sm text-slate-600 whitespace-pre-wrap font-mono bg-white p-2 border border-slate-200 rounded-lg max-h-32 overflow-auto">
                  {req.requirements || 'No specific requirements provided.'}
                </p>
              </div>

              {req.status === 'PENDING' && (
                <button
                  onClick={() => handleApprove(req.id)}
                  disabled={approving === req.id}
                  className="w-full bg-teal-600 hover:bg-teal-700 text-white font-semibold py-2 px-4 rounded-xl transition-colors disabled:opacity-50 flex justify-center items-center gap-2"
                >
                  {approving === req.id ? 'Approving...' : <><CheckCircle size={18} /> Approve & Generate Key</>}
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* API Key Modal */}
      {apiKeyModal && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex justify-center items-center z-50 p-4">
          <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl border border-slate-200 text-center relative">
            <div className="mx-auto w-16 h-16 bg-teal-100 rounded-full flex items-center justify-center mb-4">
              <CheckCircle className="text-teal-600" size={32} />
            </div>
            <h3 className="text-2xl font-extrabold text-slate-900 mb-2">Pipeline Approved!</h3>
            <p className="text-slate-500 mb-6">Company account created and LIVE key generated.</p>
            
            <div className="bg-slate-900 p-4 rounded-2xl mb-6 relative group">
              <p className="text-xs text-slate-400 font-semibold mb-2 uppercase tracking-wider text-left">API Key (Live)</p>
              <code className="text-teal-400 text-lg break-all font-mono">{apiKeyModal}</code>
            </div>
            
            <button 
              onClick={() => setApiKeyModal(null)}
              className="w-full bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold py-3 rounded-xl transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

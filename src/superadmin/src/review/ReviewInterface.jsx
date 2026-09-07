import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { CheckCircle2, XCircle, ArrowLeft, User, FileText, AlertCircle } from 'lucide-react';

export default function ReviewInterface() {
  const { appId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const submitDecision = async (decision) => {
    setLoading(true);
    try {
      await axios.post(`/api/v1/review/applications/${appId}/decide`, { decision, reason: 'Manual review' });
      navigate('/review');
    } catch (e) {
      // Mock success for UI demo
      alert(`Decision ${decision} submitted (Mock)!`);
      navigate('/review');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto h-[calc(100vh-6rem)] flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <Link to="/review" className="text-gray-500 hover:text-gray-900">
            <ArrowLeft size={20} />
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Review Application APP{appId.toString().padStart(3, '0')}</h1>
        </div>
      </div>

      <div className="flex-1 flex gap-6 overflow-hidden">
        {/* Document Viewer Area */}
        <div className="flex-1 bg-gray-900 rounded-lg overflow-hidden flex items-center justify-center relative">
          <div className="text-gray-500 flex flex-col items-center">
            <FileText size={48} className="mb-4 opacity-50" />
            <p>Document Viewer (Mock)</p>
          </div>
          <div className="absolute bottom-4 right-4 flex gap-2">
             <button className="bg-gray-800 text-white px-3 py-1 rounded text-sm hover:bg-gray-700">Aadhaar Front</button>
             <button className="bg-gray-800 text-white px-3 py-1 rounded text-sm hover:bg-gray-700">Aadhaar Back</button>
             <button className="bg-gray-800 text-white px-3 py-1 rounded text-sm hover:bg-gray-700">Selfie</button>
          </div>
        </div>

        {/* Verification Context & Decision Area */}
        <div className="w-96 flex flex-col gap-4">
          <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm flex-1 overflow-y-auto">
            <h2 className="text-lg font-bold text-gray-900 mb-4 border-b pb-2">Verification Context</h2>
            
            <div className="space-y-4">
              <div>
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Automated Results</h3>
                <div className="bg-green-50 text-green-800 p-3 rounded-md text-sm mb-2 flex items-center gap-2 border border-green-100">
                  <CheckCircle2 size={16} /> Aadhaar Verification Passed
                </div>
                <div className="bg-red-50 text-red-800 p-3 rounded-md text-sm mb-2 flex items-start gap-2 border border-red-100">
                  <AlertCircle size={16} className="mt-0.5" /> 
                  <div>
                    <span className="font-bold block">Face Match Failed</span>
                    <span className="text-xs">Confidence: 45% (Threshold: 85%)</span>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Extracted Data</h3>
                <div className="space-y-2 text-sm bg-gray-50 p-3 rounded-md border border-gray-100">
                  <div className="flex justify-between border-b border-gray-200 pb-1">
                    <span className="text-gray-500">Name</span>
                    <span className="font-medium">John Doe</span>
                  </div>
                  <div className="flex justify-between border-b border-gray-200 pb-1">
                    <span className="text-gray-500">DOB</span>
                    <span className="font-medium">1990-01-01</span>
                  </div>
                  <div className="flex justify-between border-b border-gray-200 pb-1">
                    <span className="text-gray-500">Gender</span>
                    <span className="font-medium">Male</span>
                  </div>
                  <div className="flex justify-between pb-1">
                    <span className="text-gray-500">Aadhaar Number</span>
                    <span className="font-medium">XXXX XXXX 1234</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white p-5 rounded-lg border border-gray-200 shadow-sm">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Final Decision</h2>
            <div className="flex flex-col gap-3">
              <button 
                onClick={() => submitDecision('APPROVED')}
                disabled={loading}
                className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-4 rounded-md flex items-center justify-center gap-2 transition-colors"
              >
                <CheckCircle2 size={18} /> APPROVE
              </button>
              <button 
                onClick={() => submitDecision('REJECTED')}
                disabled={loading}
                className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-4 rounded-md flex items-center justify-center gap-2 transition-colors"
              >
                <XCircle size={18} /> REJECT
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

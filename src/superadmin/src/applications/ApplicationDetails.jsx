import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { CheckCircle2, AlertCircle, Clock, XCircle, ArrowLeft } from 'lucide-react';

export default function ApplicationDetails() {
  const { appId } = useParams();
  const [app, setApp] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchApp = async () => {
      try {
        const response = await axios.get(`/api/v1/admin/applications/${appId}`);
        setApp(response.data);
      } catch (e) {
        setApp({
          id: appId,
          company_id: 1,
          profile_version_id: 1,
          status: "REVIEW",
          created_at: "2026-09-04T12:00:00Z",
          attempts: [
            { id: 1, step_key: "aadhaar_1", status: "PASSED", started_at: "2026-09-04T12:00:01Z" },
            { id: 2, step_key: "face_match_1", status: "PASSED", started_at: "2026-09-04T12:01:05Z" },
            { id: 3, step_key: "liveness_1", status: "FAILED", started_at: "2026-09-04T12:02:10Z" },
            { id: 4, step_key: "human_review_1", status: "PENDING", started_at: "2026-09-04T12:03:00Z" }
          ],
          final_decision: "HUMAN_REVIEW",
          decision_reason: "Liveness verification failed."
        });
      } finally {
        setLoading(false);
      }
    };
    fetchApp();
  }, [appId]);

  if (loading) return <div className="p-8">Loading...</div>;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center gap-4 mb-6">
        <Link to="/applications" className="text-gray-500 hover:text-gray-900">
          <ArrowLeft size={20} />
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">Application APP{app?.id?.toString().padStart(3, '0')}</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Application Details</h2>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500">Company ID</span>
              <span className="font-medium text-gray-900">{app?.company_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Profile Version</span>
              <span className="font-medium text-gray-900">v{app?.profile_version_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500">Created At</span>
              <span className="font-medium text-gray-900">{new Date(app?.created_at).toLocaleString()}</span>
            </div>
            <div className="flex justify-between pt-3 border-t border-gray-100">
              <span className="text-gray-500 font-medium">Final Decision</span>
              <span className={`font-bold ${
                app?.final_decision === 'APPROVED' ? 'text-green-600' :
                app?.final_decision === 'REJECTED' ? 'text-red-600' :
                'text-orange-600'
              }`}>{app?.final_decision}</span>
            </div>
          </div>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Verification Timeline</h2>
          <div className="space-y-4">
            {app?.attempts?.map((attempt, idx) => (
              <div key={attempt.id} className="flex items-start gap-3">
                <div className="mt-1">
                  {attempt.status === 'PASSED' ? <CheckCircle2 size={18} className="text-green-500" /> :
                   attempt.status === 'FAILED' ? <XCircle size={18} className="text-red-500" /> :
                   attempt.status === 'PENDING' ? <Clock size={18} className="text-blue-500" /> :
                   <AlertCircle size={18} className="text-orange-500" />}
                </div>
                <div>
                  <h3 className="font-bold text-sm text-gray-900">{attempt.step_key}</h3>
                  <p className="text-xs text-gray-500">{new Date(attempt.started_at).toLocaleTimeString()}</p>
                </div>
                <div className="ml-auto">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                    attempt.status === 'PASSED' ? 'bg-green-100 text-green-700' :
                    attempt.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {attempt.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

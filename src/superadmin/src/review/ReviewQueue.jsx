import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Users, AlertTriangle, Clock, ArrowRight } from 'lucide-react';

export default function ReviewQueue() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchQueue = async () => {
      try {
        const response = await axios.get('/api/v1/review/queue');
        setQueue(response.data);
      } catch (e) {
        setQueue([
          { id: 2, company_id: 2, profile_version_id: 2, status: "REVIEW", created_at: "2026-09-04T12:05:00Z", priority: 'HIGH' },
          { id: 7, company_id: 1, profile_version_id: 1, status: "REVIEW", created_at: "2026-09-04T12:08:00Z", priority: 'MEDIUM' },
        ]);
      } finally {
        setLoading(false);
      }
    };
    fetchQueue();
  }, []);

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Human Verification Center</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500 mb-1">Total Pending</p>
            <p className="text-3xl font-bold text-gray-900">{queue.length}</p>
          </div>
          <div className="p-3 bg-blue-50 text-blue-600 rounded-full">
            <Users size={24} />
          </div>
        </div>
        <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-500 mb-1">High Priority</p>
            <p className="text-3xl font-bold text-red-600">1</p>
          </div>
          <div className="p-3 bg-red-50 text-red-600 rounded-full">
            <AlertTriangle size={24} />
          </div>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        <table className="w-full text-left text-sm text-gray-600">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900">App ID</th>
              <th className="px-6 py-4 font-medium text-gray-900">Company ID</th>
              <th className="px-6 py-4 font-medium text-gray-900">Wait Time</th>
              <th className="px-6 py-4 font-medium text-gray-900">Priority</th>
              <th className="px-6 py-4 font-medium text-gray-900 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan="5" className="text-center py-8">Loading...</td></tr>
            ) : queue.map(app => (
              <tr key={app.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-6 py-4 font-bold text-gray-900">APP{app.id.toString().padStart(3, '0')}</td>
                <td className="px-6 py-4">{app.company_id}</td>
                <td className="px-6 py-4 flex items-center gap-2">
                  <Clock size={16} className="text-gray-400"/> 12 mins
                </td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                    app.priority === 'HIGH' ? 'bg-red-100 text-red-700' :
                    app.priority === 'MEDIUM' ? 'bg-orange-100 text-orange-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {app.priority || 'NORMAL'}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <Link to={`/review/${app.id}`} className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 font-medium bg-blue-50 px-3 py-1.5 rounded-md">
                    Start Review <ArrowRight size={16} />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

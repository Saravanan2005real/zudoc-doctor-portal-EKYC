import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { FileText, ArrowRight } from 'lucide-react';

export default function ApplicationList() {
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchApps = async () => {
      try {
        const response = await axios.get('/api/v1/admin/applications');
        setApplications(response.data);
      } catch (e) {
        setApplications([
          { id: 1, company_id: 1, profile_version_id: 1, status: "APPROVED", created_at: "2026-09-04T12:00:00Z" },
          { id: 2, company_id: 2, profile_version_id: 2, status: "REVIEW", created_at: "2026-09-04T12:05:00Z" },
          { id: 3, company_id: 1, profile_version_id: 1, status: "PENDING", created_at: "2026-09-04T12:10:00Z" },
          { id: 4, company_id: 3, profile_version_id: 1, status: "REJECTED", created_at: "2026-09-04T12:15:00Z" },
        ]);
      } finally {
        setLoading(false);
      }
    };
    fetchApps();
  }, []);

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Applications</h1>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        <table className="w-full text-left text-sm text-gray-600">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900">App ID</th>
              <th className="px-6 py-4 font-medium text-gray-900">Company ID</th>
              <th className="px-6 py-4 font-medium text-gray-900">Profile Version</th>
              <th className="px-6 py-4 font-medium text-gray-900">Status</th>
              <th className="px-6 py-4 font-medium text-gray-900 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan="5" className="text-center py-8">Loading...</td></tr>
            ) : applications.map(app => (
              <tr key={app.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-6 py-4 font-medium text-gray-900 flex items-center gap-3">
                  <div className="p-2 bg-indigo-100 text-indigo-600 rounded-lg">
                    <FileText size={16} />
                  </div>
                  APP{app.id.toString().padStart(3, '0')}
                </td>
                <td className="px-6 py-4">{app.company_id}</td>
                <td className="px-6 py-4">{app.profile_version_id}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded-full text-xs font-semibold ${
                    app.status === 'APPROVED' ? 'bg-green-100 text-green-700' :
                    app.status === 'REJECTED' ? 'bg-red-100 text-red-700' :
                    app.status === 'REVIEW' ? 'bg-orange-100 text-orange-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {app.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <Link to={`/applications/${app.id}`} className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 font-medium">
                    View <ArrowRight size={16} />
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

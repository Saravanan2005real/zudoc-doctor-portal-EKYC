import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { Workflow, Plus, Edit2, Play, FileText } from 'lucide-react';

export default function CompanyDetails() {
  const { companyId } = useParams();
  const [company, setCompany] = useState(null);
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const compRes = await axios.get(`/api/v1/admin/companies/${companyId}`);
        const profRes = await axios.get(`/api/v1/admin/companies/${companyId}/profiles`);
        setCompany(compRes.data);
        setProfiles(profRes.data);
      } catch (e) {
        // Mock fallback
        setCompany({ id: companyId, name: "ABC Healthcare", status: "ACTIVE" });
        setProfiles([
          { id: 1, name: "Doctor KYC", versions: [{ version_number: 1, status: "PUBLISHED" }] }
        ]);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [companyId]);

  if (loading) return <div className="p-8">Loading...</div>;

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex items-center gap-2 text-sm text-gray-500 mb-4">
        <Link to="/companies" className="hover:text-gray-900">Companies</Link>
        <span>/</span>
        <span className="font-medium text-gray-900">{company?.name}</span>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6 mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">{company?.name}</h1>
        <p className="text-gray-500 mb-4">Manage verification profiles, applications, and settings for this tenant.</p>
        <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-bold">
          Status: {company?.status}
        </span>
      </div>

      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold text-gray-900">Verification Profiles</h2>
        <button className="bg-blue-600 text-white px-3 py-1.5 rounded-md text-sm font-medium flex items-center gap-2 hover:bg-blue-700">
          <Plus size={16} /> New Profile
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {profiles.map(profile => (
          <div key={profile.id} className="bg-white border border-gray-200 rounded-lg p-5 shadow-sm">
            <div className="flex justify-between items-start mb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-50 text-indigo-600 rounded-md">
                  <Workflow size={20} />
                </div>
                <div>
                  <h3 className="font-bold text-gray-900">{profile.name}</h3>
                  <p className="text-sm text-gray-500">ID: {profile.id}</p>
                </div>
              </div>
            </div>
            
            <div className="space-y-3 mb-5">
              <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Versions</h4>
              {profile.versions?.map(v => (
                <div key={v.version_number} className="flex justify-between items-center p-3 bg-gray-50 rounded-md border border-gray-100">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">v{v.version_number}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                      v.status === 'PUBLISHED' ? 'bg-green-100 text-green-700' :
                      v.status === 'DRAFT' ? 'bg-orange-100 text-orange-700' : 'bg-gray-200 text-gray-700'
                    }`}>
                      {v.status}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    <Link to={`/companies/${companyId}/profiles/${profile.id}/versions/${v.version_number}/flow`} className="text-blue-600 hover:bg-blue-50 p-1.5 rounded-md transition-colors" title="Flow Builder">
                      {v.status === 'DRAFT' ? <Edit2 size={16} /> : <FileText size={16} />}
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

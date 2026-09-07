import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Building2, Plus, ArrowRight } from 'lucide-react';

export default function CompanyList() {
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In V1, mock fetching from API if backend isn't up, otherwise use axios
    const fetchCompanies = async () => {
      try {
        const response = await axios.get('/api/v1/admin/companies');
        setCompanies(response.data);
      } catch (e) {
        // Mock data fallback for demonstration
        setCompanies([
          { id: 1, name: "ABC Healthcare", industry: "Medical", status: "ACTIVE" },
          { id: 2, name: "City Hospital", industry: "Medical", status: "ACTIVE" }
        ]);
      } finally {
        setLoading(false);
      }
    };
    fetchCompanies();
  }, []);

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Companies</h1>
        <button className="bg-blue-600 text-white px-4 py-2 rounded-md font-medium flex items-center gap-2 hover:bg-blue-700">
          <Plus size={18} /> Add Company
        </button>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
        <table className="w-full text-left text-sm text-gray-600">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-4 font-medium text-gray-900">Company Name</th>
              <th className="px-6 py-4 font-medium text-gray-900">Industry</th>
              <th className="px-6 py-4 font-medium text-gray-900">Status</th>
              <th className="px-6 py-4 font-medium text-gray-900 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan="4" className="text-center py-8">Loading...</td></tr>
            ) : companies.map(company => (
              <tr key={company.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-6 py-4 font-medium text-gray-900 flex items-center gap-3">
                  <div className="p-2 bg-blue-100 text-blue-600 rounded-lg">
                    <Building2 size={16} />
                  </div>
                  {company.name}
                </td>
                <td className="px-6 py-4">{company.industry}</td>
                <td className="px-6 py-4">
                  <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-semibold">
                    {company.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <Link to={`/companies/${company.id}`} className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 font-medium">
                    Manage <ArrowRight size={16} />
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

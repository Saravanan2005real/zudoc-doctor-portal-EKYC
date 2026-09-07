import { BrowserRouter, Routes, Route, Link, Outlet } from 'react-router-dom';
import { LayoutDashboard, Building2, Workflow, FileText, CheckSquare, ShieldCheck, Activity } from 'lucide-react';
import Dashboard from './dashboard/Dashboard';
import CompanyList from './companies/CompanyList';
import CompanyDetails from './companies/CompanyDetails';
import FlowBuilder from './flow-builder/FlowBuilder';
import ApplicationList from './applications/ApplicationList';
import ApplicationDetails from './applications/ApplicationDetails';
import ServiceList from './services/ServiceList';
import ReviewQueue from './review/ReviewQueue';
import ReviewInterface from './review/ReviewInterface';
import RequestQueue from './requests/RequestQueue';
import Landing from './Landing';

function Layout() {
  return (
    <div className="flex h-screen bg-slate-50 font-sans">
      {/* Sidebar - Sleek White Floating */}
      <div className="w-64 bg-white/80 backdrop-blur-xl border-r border-slate-200 flex flex-col m-4 rounded-3xl shadow-soft">
        <div className="p-6 border-b border-slate-100">
          <h1 className="text-2xl font-extrabold flex items-center gap-2 text-slate-900 tracking-tight">
            <ShieldCheck className="text-teal-600" size={28} />
            Verifyyy
          </h1>
          <p className="text-xs text-slate-500 mt-1 font-medium tracking-wide uppercase">Admin Platform</p>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          <Link to="/dashboard" className="flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-2xl hover:bg-teal-50 text-slate-600 hover:text-teal-700 transition-colors">
            <LayoutDashboard size={20} /> Dashboard
          </Link>
          <Link to="/dashboard/companies" className="flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-2xl hover:bg-teal-50 text-slate-600 hover:text-teal-700 transition-colors">
            <Building2 size={20} /> Companies
          </Link>
          <Link to="/dashboard/services" className="flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-2xl hover:bg-teal-50 text-slate-600 hover:text-teal-700 transition-colors">
            <Workflow size={20} /> Services
          </Link>
          <Link to="/dashboard/applications" className="flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-2xl hover:bg-teal-50 text-slate-600 hover:text-teal-700 transition-colors">
            <FileText size={20} /> Applications
          </Link>
          <Link to="/dashboard/requests" className="flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-2xl hover:bg-teal-50 text-slate-600 hover:text-teal-700 transition-colors">
            <Activity size={20} /> Pipeline Requests
          </Link>
          <Link to="/dashboard/review" className="flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-2xl hover:bg-teal-50 text-slate-600 hover:text-teal-700 transition-colors">
            <CheckSquare size={20} /> Human Review
          </Link>
          <Link to="/dashboard/analytics" className="flex items-center gap-3 px-4 py-3 text-sm font-semibold rounded-2xl hover:bg-teal-50 text-slate-600 hover:text-teal-700 transition-colors">
            <Activity size={20} /> Analytics
          </Link>
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto bg-slate-50 rounded-l-[3rem]">
        <main className="p-10 max-w-7xl mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/dashboard" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="companies" element={<CompanyList />} />
          <Route path="companies/:companyId" element={<CompanyDetails />} />
          <Route path="services" element={<ServiceList />} />
          <Route path="companies/:companyId/profiles/:profileId/versions/:versionId/flow" element={<FlowBuilder />} />
          <Route path="applications" element={<ApplicationList />} />
          <Route path="applications/:appId" element={<ApplicationDetails />} />
          <Route path="requests" element={<RequestQueue />} />
          <Route path="review" element={<ReviewQueue />} />
          <Route path="review/:appId" element={<ReviewInterface />} />
          <Route path="*" element={<div className="p-4 text-gray-500">Coming Soon</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

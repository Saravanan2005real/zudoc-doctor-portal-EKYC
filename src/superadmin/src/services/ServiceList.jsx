import { FileText, Eye, Volume2, ShieldCheck, UserCheck } from 'lucide-react';

export default function ServiceList() {
  const services = [
    {
      id: 'doc-ocr',
      name: 'Document OCR & Verification',
      description: 'Uses PaddleOCR and RetinaFace to extract text, cross-match names, and verify format integrity of Aadhaar and PAN cards.',
      icon: <FileText size={28} className="text-teal-600" />,
      status: 'Active',
      type: 'Automated ML'
    },
    {
      id: 'liveness-webgazer',
      name: 'WebGazer Liveness',
      description: 'In-browser eye tracking to ensure human presence by calibrating and tracking the users gaze against targets.',
      icon: <Eye size={28} className="text-blue-500" />,
      status: 'Active',
      type: 'Client-Side ML'
    },
    {
      id: 'liveness-audio',
      name: 'Audio-Guided Liveness (Accessibility)',
      description: 'Alternative liveness check for visually impaired users. Uses speech synthesis and MediaPipe head-turn/blink detection.',
      icon: <Volume2 size={28} className="text-purple-500" />,
      status: 'Active',
      type: 'Client-Side ML'
    },
    {
      id: 'gaze-fginet',
      name: 'FGI-Net Eye Tracker',
      description: 'Advanced standalone gaze estimation module using Fusion Global Information to predict precise gaze direction (Top/Bottom/Left/Right).',
      icon: <UserCheck size={28} className="text-rose-500" />,
      status: 'Experimental',
      type: 'Microservice'
    },
    {
      id: 'manual-review',
      name: 'Professional Credential Review',
      description: 'Manual fallback for verifying medical licenses, clinic details, and qualifications when AI confidence is low.',
      icon: <ShieldCheck size={28} className="text-amber-500" />,
      status: 'Active',
      type: 'Human-in-the-Loop'
    }
  ];

  return (
    <div className="font-sans">
      <h1 className="text-3xl font-extrabold text-slate-900 mb-2 tracking-tight">Verification Products</h1>
      <p className="text-slate-500 font-medium mb-8">Manage and monitor the verification services offered by the Verifyyy platform.</p>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {services.map(service => (
          <div key={service.id} className="bg-white p-8 rounded-3xl border border-slate-100 shadow-soft transition-all duration-300 hover:shadow-teal-glow hover:-translate-y-1 flex flex-col h-full">
            <div className="flex justify-between items-start mb-6">
              <div className="p-3 bg-slate-50 rounded-2xl">
                {service.icon}
              </div>
              <span className={`px-3 py-1 text-xs font-bold uppercase tracking-wider rounded-full ${
                service.status === 'Active' ? 'bg-teal-50 text-teal-700' : 'bg-amber-50 text-amber-700'
              }`}>
                {service.status}
              </span>
            </div>
            
            <h3 className="text-xl font-bold text-slate-900 mb-3">{service.name}</h3>
            <p className="text-slate-500 text-sm leading-relaxed mb-6 flex-grow">{service.description}</p>
            
            <div className="mt-auto pt-4 border-t border-slate-100 flex justify-between items-center">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{service.type}</span>
              <button className="text-sm font-bold text-teal-600 hover:text-teal-800 transition-colors">Configure &rarr;</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

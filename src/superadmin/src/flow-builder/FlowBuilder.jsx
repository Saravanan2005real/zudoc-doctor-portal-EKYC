import { useState, useCallback, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Handle,
  Position,
  Panel
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import axios from 'axios';
import { Save, Play, Settings, AlertCircle, ArrowLeft } from 'lucide-react';

// Custom Node for Services
function ServiceNode({ data, isConnectable }) {
  return (
    <div className="bg-white border-2 border-blue-500 rounded-md shadow-md w-48">
      <Handle type="target" position={Position.Top} isConnectable={isConnectable} />
      <div className="bg-blue-500 text-white p-2 text-sm font-bold text-center rounded-t-sm flex items-center justify-center gap-2">
        {data.label}
      </div>
      <div className="p-3 text-xs text-gray-600 bg-gray-50 flex flex-col gap-2">
        {data.config && Object.keys(data.config).map(key => (
          <div key={key} className="flex justify-between">
            <span className="font-medium">{key}:</span>
            <span>{data.config[key]}</span>
          </div>
        ))}
        {!data.config && <div className="text-center italic text-gray-400">Default settings</div>}
      </div>
      <Handle type="source" position={Position.Bottom} id="success" style={{ left: '30%', background: '#22c55e' }} isConnectable={isConnectable} />
      <Handle type="source" position={Position.Bottom} id="failure" style={{ left: '70%', background: '#ef4444' }} isConnectable={isConnectable} />
    </div>
  );
}

// Custom Node for Decision
function DecisionNode({ data, isConnectable }) {
  return (
    <div className="bg-white border-2 border-purple-500 rounded-md shadow-md w-40">
      <Handle type="target" position={Position.Top} isConnectable={isConnectable} />
      <div className="bg-purple-500 text-white p-2 text-sm font-bold text-center rounded-t-sm">
        DECISION
      </div>
      <div className="p-2 text-center text-sm font-bold text-gray-800 bg-gray-50">
        {data.decision}
      </div>
    </div>
  );
}

const nodeTypes = {
  serviceNode: ServiceNode,
  decisionNode: DecisionNode
};

const initialNodes = [
  { id: 'start', position: { x: 250, y: 50 }, data: { label: 'START' }, type: 'input' },
];
const initialEdges = [];

export default function FlowBuilder() {
  const { companyId, profileId, versionId } = useParams();
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [status, setStatus] = useState('DRAFT');
  const [loading, setLoading] = useState(false);
  const [services, setServices] = useState([]);

  useEffect(() => {
    // Mock fetching services and existing graph
    const fetchGraph = async () => {
      try {
        const srvRes = await axios.get('/api/v1/admin/verification-services');
        setServices(srvRes.data);
      } catch (e) {
        setServices([
          { id: 1, name: "AADHAAR", description: "Aadhaar OCR" },
          { id: 2, name: "FACE_MATCH", description: "Face Match" },
          { id: 3, name: "HUMAN_REVIEW", description: "Manual Human Review" },
        ]);
      }
      
      // Load mock flow for V1 demonstration
      setNodes([
        { id: 'start', position: { x: 250, y: 50 }, data: { label: 'START' }, type: 'input' },
        { id: 'aadhaar_1', type: 'serviceNode', position: { x: 250, y: 150 }, data: { label: 'Aadhaar Verification', config: null } },
        { id: 'face_match_1', type: 'serviceNode', position: { x: 100, y: 300 }, data: { label: 'Face Match', config: { threshold: 85 } } },
        { id: 'human_review_1', type: 'serviceNode', position: { x: 400, y: 300 }, data: { label: 'Human Review', config: null } },
        { id: 'approve_1', type: 'decisionNode', position: { x: 100, y: 450 }, data: { decision: 'APPROVED' } },
        { id: 'reject_1', type: 'decisionNode', position: { x: 400, y: 450 }, data: { decision: 'REJECTED' } },
      ]);
      setEdges([
        { id: 'e-start-aadhaar', source: 'start', target: 'aadhaar_1', type: 'smoothstep' },
        { id: 'e-aadhaar-face', source: 'aadhaar_1', target: 'face_match_1', sourceHandle: 'success', label: 'SUCCESS', type: 'smoothstep' },
        { id: 'e-aadhaar-human', source: 'aadhaar_1', target: 'human_review_1', sourceHandle: 'failure', label: 'FAILURE', type: 'smoothstep' },
        { id: 'e-face-approve', source: 'face_match_1', target: 'approve_1', sourceHandle: 'success', label: 'SUCCESS', type: 'smoothstep' },
        { id: 'e-face-human', source: 'face_match_1', target: 'human_review_1', sourceHandle: 'failure', label: 'FAILURE', type: 'smoothstep' },
        { id: 'e-human-reject', source: 'human_review_1', target: 'reject_1', sourceHandle: 'failure', label: 'FAILURE', type: 'smoothstep' },
      ]);
    };
    fetchGraph();
  }, [companyId, profileId, versionId]);

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge({ ...params, type: 'smoothstep', label: params.sourceHandle?.toUpperCase() || '' }, eds)),
    [setEdges],
  );

  const saveFlow = async () => {
    setLoading(true);
    try {
      // In production, this would serialize the React Flow graph into the DTOs
      // and PUT /api/v1/admin/profiles/{profileId}/versions/{versionId}/steps
      await new Promise(r => setTimeout(r, 1000));
      alert("Flow graph saved successfully.");
    } finally {
      setLoading(false);
    }
  };

  const publishFlow = async () => {
    setLoading(true);
    try {
      // POST /api/v1/admin/profiles/{profileId}/versions/{versionId}/publish
      await new Promise(r => setTimeout(r, 1000));
      setStatus('PUBLISHED');
      alert("Flow published! It is now immutable.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <div className="flex justify-between items-center bg-white p-4 border-b border-gray-200">
        <div className="flex items-center gap-4">
          <Link to={`/companies/${companyId}`} className="text-gray-500 hover:text-gray-900">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Visual Flow Builder</h1>
            <p className="text-sm text-gray-500">Profile ID: {profileId} • Version: {versionId}</p>
          </div>
          <span className={`ml-4 px-2 py-1 text-xs font-bold rounded-full ${status === 'PUBLISHED' ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
            {status}
          </span>
        </div>
        
        <div className="flex gap-2">
          {status !== 'PUBLISHED' && (
            <>
              <button 
                onClick={saveFlow}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 font-medium rounded-md hover:bg-gray-200"
              >
                <Save size={16} /> Save Draft
              </button>
              <button 
                onClick={publishFlow}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700"
              >
                <Play size={16} /> Publish Flow
              </button>
            </>
          )}
          {status === 'PUBLISHED' && (
            <div className="flex items-center gap-2 text-sm text-gray-500 bg-gray-100 px-3 py-2 rounded-md">
              <AlertCircle size={16} /> Immutable (Duplicate to edit)
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 flex">
        {/* Toolbox Sidebar */}
        <div className="w-64 bg-white border-r border-gray-200 p-4 flex flex-col gap-4">
          <h2 className="font-bold text-gray-800 flex items-center gap-2">
            <Settings size={18} /> Available Services
          </h2>
          <div className="space-y-2">
            {services.map(s => (
              <div 
                key={s.id} 
                className="p-3 bg-blue-50 border border-blue-200 text-blue-700 rounded-md cursor-grab text-sm font-medium hover:bg-blue-100"
                draggable
              >
                {s.name}
              </div>
            ))}
            <div className="p-3 bg-gray-50 border border-gray-200 text-gray-400 rounded-md text-sm font-medium">
              PAN Verification (Coming Soon)
            </div>
            <div className="p-3 bg-gray-50 border border-gray-200 text-gray-400 rounded-md text-sm font-medium">
              Liveness (Coming Soon)
            </div>
          </div>
          
          <h2 className="font-bold text-gray-800 mt-6">Decisions</h2>
          <div className="space-y-2">
            <div className="p-3 bg-green-50 border border-green-200 text-green-700 rounded-md cursor-grab text-sm font-medium">APPROVED</div>
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-md cursor-grab text-sm font-medium">REJECTED</div>
          </div>
        </div>

        {/* React Flow Canvas */}
        <div className="flex-1 bg-gray-50">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
          >
            <Controls />
            <MiniMap />
            <Background variant="dots" gap={12} size={1} />
          </ReactFlow>
        </div>
      </div>
    </div>
  );
}

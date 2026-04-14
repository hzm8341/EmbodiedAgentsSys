import React, { useState, useEffect } from 'react';
import JointControl from './JointControl';
import IKChatPanel from './IKChatPanel';

interface URDFViewerProps {
  robotId: string;
  vuerPort: number;
}

const URDFViewer: React.FC<URDFViewerProps> = ({ robotId, vuerPort }) => {
  const [showGrid, setShowGrid] = useState(true);
  const [isPerspective, setIsPerspective] = useState(true);
  const [iframeKey, setIframeKey] = useState(0);
  const [showControls, setShowControls] = useState(true);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'joints' | 'ik'>('joints');

  // Force iframe reload when robot changes
  useEffect(() => {
    setIframeKey(prev => prev + 1);
  }, [robotId]);

  const resetView = () => {
    // Post message to Vuer iframe
  };

  const toggleGrid = () => {
    setShowGrid(!showGrid);
  };

  const togglePerspective = () => {
    setIsPerspective(!isPerspective);
  };

  return (
    <div className="urdf-viewer" style={{ display: 'flex', flexDirection: 'column', height: '100%', border: '1px solid #ddd', borderRadius: '8px', overflow: 'hidden' }}>
      <div className="viewer-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 16px', background: '#f5f5f5', borderBottom: '1px solid #ddd' }}>
        <h3>3D Viewer</h3>
        <div className="controls" style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button onClick={resetView} style={{ padding: '4px 12px', border: '1px solid #ccc', borderRadius: '4px', background: 'white', cursor: 'pointer' }}>
            Reset
          </button>
          <button onClick={toggleGrid} style={{ padding: '4px 12px', border: '1px solid #ccc', borderRadius: '4px', background: 'white', cursor: 'pointer' }}>
            Grid: {showGrid ? 'ON' : 'OFF'}
          </button>
          <button onClick={togglePerspective} style={{ padding: '4px 12px', border: '1px solid #ccc', borderRadius: '4px', background: 'white', cursor: 'pointer' }}>
            {isPerspective ? 'Perspective' : 'Orthographic'}
          </button>
          <button
            onClick={() => setShowControls(!showControls)}
            style={{
              padding: '4px 12px',
              border: '1px solid #ccc',
              borderRadius: '4px',
              background: showControls ? '#e3f2fd' : 'white',
              cursor: 'pointer'
            }}
          >
            Controls: {showControls ? 'ON' : 'OFF'}
          </button>
        </div>
      </div>

      <div className="viewer-main" style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* 3D Vuer iframe */}
        <div className="viewer-content" style={{ flex: 1, position: 'relative' }}>
          <iframe
            key={iframeKey}
            src={`http://localhost:${vuerPort}?robot=${robotId}`}
            className="vuer-iframe"
            style={{ width: '100%', height: '100%', border: 'none' }}
            allow="xr-spatial-tracking"
            title="Vuer 3D Viewer"
          />
        </div>

        {/* Control panel sidebar */}
        {showControls && (
          <div className="control-panel" style={{ width: '320px', borderLeft: '1px solid #ddd', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            {/* Model Tree */}
            <div className="model-tree-section" style={{ flex: 1, overflow: 'hidden', borderBottom: '1px solid #ddd' }}>
              <ModelTreeInline robotId={robotId} selectedNode={selectedNode} onNodeSelect={setSelectedNode} />
            </div>

            {/* Tab switcher */}
            <div className="tab-switcher" style={{ display: 'flex', borderBottom: '1px solid #ddd' }}>
              <button
                onClick={() => setActiveTab('joints')}
                style={{
                  flex: 1,
                  padding: '8px',
                  border: 'none',
                  background: activeTab === 'joints' ? '#e3f2fd' : '#f5f5f5',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontWeight: activeTab === 'joints' ? 'bold' : 'normal'
                }}
              >
                Joints
              </button>
              <button
                onClick={() => setActiveTab('ik')}
                style={{
                  flex: 1,
                  padding: '8px',
                  border: 'none',
                  background: activeTab === 'ik' ? '#e3f2fd' : '#f5f5f5',
                  cursor: 'pointer',
                  fontSize: '12px',
                  fontWeight: activeTab === 'ik' ? 'bold' : 'normal'
                }}
              >
                IK Control
              </button>
            </div>

            {/* Tab content */}
            <div className="tab-content" style={{ height: '45%', overflow: 'hidden' }}>
              {activeTab === 'joints' && <JointControl robotId={robotId} />}
              {activeTab === 'ik' && <IKChatPanel robotId={robotId} vuerPort={vuerPort} />}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Inline ModelTree component with node selection support
// Note: React is already imported at the top

interface LinkInfo {
  name: string;
  visual_geometry?: string;
  collision_geometry?: string;
  material_color?: number[];
  inertial_mass?: number;
}

interface JointInfo {
  name: string;
  type: string;
  parent: string;
  child: string;
  axis?: number[];
  origin_xyz?: number[];
  origin_rpy?: number[];
  limit_lower?: number;
  limit_upper?: number;
}

interface URDFModel {
  name: string;
  links: LinkInfo[];
  joints: JointInfo[];
}

interface ModelTreeInlineProps {
  robotId: string;
  selectedNode: string | null;
  onNodeSelect: (name: string | null) => void;
}

const ModelTreeInline: React.FC<ModelTreeInlineProps> = ({ robotId, selectedNode, onNodeSelect }) => {
  const [model, setModel] = useState<URDFModel | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [hiddenNodes, setHiddenNodes] = useState<Set<string>>(new Set());

  useEffect(() => {
    const loadModel = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/urdf/${robotId}`);
        if (!response.ok) throw new Error('Failed to load model');
        const data = await response.json();
        setModel(data);
        if (data.links && data.links.length > 0) {
          setExpandedNodes(new Set([data.links[0].name]));
        }
      } catch (e) {
        setError('Failed to load model');
      } finally {
        setLoading(false);
      }
    };
    loadModel();
  }, [robotId]);

  const toggleNode = (name: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  const toggleVisibility = (name: string) => {
    setHiddenNodes(prev => {
      const next = new Set(prev);
      if (next.has(name)) {
        next.delete(name);
      } else {
        next.add(name);
      }
      return next;
    });
  };

  const rootLinks = model?.links.filter(link => {
    return !model?.joints.some(joint => joint.child === link.name);
  }) || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: '#f5f5f5', borderBottom: '1px solid #ddd' }}>
        <h4 style={{ margin: 0, fontSize: '13px' }}>Model Tree</h4>
        {selectedNode && (
          <button
            onClick={() => onNodeSelect(null)}
            style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '3px', border: '1px solid #ccc', background: 'white', cursor: 'pointer' }}
          >
            Clear
          </button>
        )}
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
        {loading && <div style={{ padding: '16px', textAlign: 'center', color: '#666' }}>Loading...</div>}
        {error && <div style={{ padding: '16px', textAlign: 'center', color: '#d32f2f' }}>{error}</div>}
        {!loading && !error && model && rootLinks.map(link => (
          <TreeNodeComponent
            key={link.name}
            node={link}
            depth={0}
            expandedNodes={expandedNodes}
            hiddenNodes={hiddenNodes}
            allNodes={model.links}
            allJoints={model.joints}
            onToggle={toggleNode}
            onVisibility={toggleVisibility}
            onSelect={onNodeSelect}
            selectedNode={selectedNode}
          />
        ))}
      </div>
    </div>
  );
};

interface TreeNodeComponentProps {
  node: LinkInfo;
  depth: number;
  expandedNodes: Set<string>;
  hiddenNodes: Set<string>;
  allNodes: LinkInfo[];
  allJoints: JointInfo[];
  onToggle: (name: string) => void;
  onVisibility: (name: string) => void;
  onSelect: (name: string | null) => void;
  selectedNode: string | null;
}

const TreeNodeComponent: React.FC<TreeNodeComponentProps> = ({
  node,
  depth,
  expandedNodes,
  hiddenNodes,
  allNodes,
  allJoints,
  onToggle,
  onVisibility,
  onSelect,
  selectedNode
}) => {
  const childJoints = allJoints.filter(j => j.parent === node.name);
  const hasChildren = childJoints.length > 0;
  const isExpanded = expandedNodes.has(node.name);
  const isHidden = hiddenNodes.has(node.name);
  const isSelected = selectedNode === node.name;

  const childLinks = childJoints
    .map(j => allNodes.find(l => l.name === j.child))
    .filter(Boolean) as LinkInfo[];

  return (
    <div>
      <div
        style={{
          paddingLeft: `${depth * 12}px`,
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          padding: '4px 0',
          cursor: 'pointer',
          background: isSelected ? '#e3f2fd' : 'transparent',
          borderRadius: '4px'
        }}
        onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = '#f0f0f0'; }}
        onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
        onClick={() => onSelect(isSelected ? null : node.name)}
      >
        <span
          onClick={(e) => { e.stopPropagation(); hasChildren && onToggle(node.name); }}
          style={{ width: '16px', fontSize: '10px', color: '#666', cursor: hasChildren ? 'pointer' : 'default' }}
        >
          {hasChildren ? (isExpanded ? '▼' : '▶') : ''}
        </span>
        <input
          type="checkbox"
          checked={!isHidden}
          onChange={() => onVisibility(node.name)}
          onClick={(e) => e.stopPropagation()}
        />
        <span style={{ fontSize: '12px' }}>{node.name}</span>
        {hasChildren && (
          <span style={{ fontSize: '9px', color: '#999', marginLeft: '4px' }}>
            ({childJoints.length})
          </span>
        )}
      </div>
      {hasChildren && isExpanded && childLinks.map(child => (
        <TreeNodeComponent
          key={child.name}
          node={child}
          depth={depth + 1}
          expandedNodes={expandedNodes}
          hiddenNodes={hiddenNodes}
          allNodes={allNodes}
          allJoints={allJoints}
          onToggle={onToggle}
          onVisibility={onVisibility}
          onSelect={onSelect}
          selectedNode={selectedNode}
        />
      ))}
    </div>
  );
};

export default URDFViewer;
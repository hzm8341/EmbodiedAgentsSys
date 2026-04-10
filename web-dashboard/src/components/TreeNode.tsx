import React from 'react';

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

interface TreeNodeProps {
  node: LinkInfo;
  depth: number;
  expanded: boolean;
  hidden: boolean;
  allNodes: LinkInfo[];
  allJoints: JointInfo[];
  onToggle: (name: string) => void;
  onVisibility: (name: string) => void;
}

const TreeNode: React.FC<TreeNodeProps> = ({
  node,
  depth,
  expanded,
  hidden,
  allNodes,
  allJoints,
  onToggle,
  onVisibility,
}) => {
  // Find joints where this link is parent
  const childJoints = allJoints.filter(j => j.parent === node.name);
  const hasChildren = childJoints.length > 0;

  // Find child links
  const childLinks = childJoints
    .map(j => allNodes.find(l => l.name === j.child))
    .filter(Boolean) as LinkInfo[];

  return (
    <div className="tree-node">
      <div
        className="node-label"
        style={{ paddingLeft: `${depth * 16}px`, display: 'flex', alignItems: 'center', gap: '4px', padding: '4px 0', cursor: 'pointer' }}
        onMouseEnter={(e) => (e.currentTarget.style.background = '#f0f0f0')}
        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
      >
        {hasChildren ? (
          <span
            className="expand-icon"
            onClick={() => onToggle(node.name)}
            style={{ width: '16px', fontSize: '10px', color: '#666', cursor: 'pointer' }}
          >
            {expanded ? '▼' : '▶'}
          </span>
        ) : (
          <span className="expand-icon spacer" style={{ width: '16px', visibility: 'hidden' }}>▶</span>
        )}
        <input
          type="checkbox"
          checked={!hidden}
          onChange={() => onVisibility(node.name)}
        />
        <span className="node-name" style={{ fontSize: '13px' }}>{node.name}</span>
      </div>
      {hasChildren && expanded && (
        <div className="node-children">
          {childLinks.map(child => (
            <TreeNode
              key={child.name}
              node={child}
              depth={depth + 1}
              expanded={expanded}
              hidden={hidden}
              allNodes={allNodes}
              allJoints={allJoints}
              onToggle={onToggle}
              onVisibility={onVisibility}
            />
          ))}
        </div>
      )}
    </div>
  );
};

interface ModelTreeProps {
  robotId: string;
}

const ModelTree: React.FC<ModelTreeProps> = ({ robotId }) => {
  const [model, setModel] = React.useState<URDFModel | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [expandedNodes, setExpandedNodes] = React.useState<Set<string>>(new Set());
  const [hiddenNodes, setHiddenNodes] = React.useState<Set<string>>(new Set());

  React.useEffect(() => {
    const loadModel = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/urdf/${robotId}`);
        if (!response.ok) throw new Error('Failed to load model');
        const data = await response.json();
        setModel(data);
        // Expand root nodes by default
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

  const showAll = () => {
    setHiddenNodes(new Set());
  };

  const hideAll = () => {
    if (model) {
      setHiddenNodes(new Set(model.links.map(l => l.name)));
    }
  };

  // Find root links (links that are not children of any joint)
  const rootLinks = model?.links.filter(link => {
    return !model?.joints.some(joint => joint.child === link.name);
  }) || [];

  return (
    <div className="model-tree" style={{ display: 'flex', flexDirection: 'column', height: '100%', border: '1px solid #ddd', borderRadius: '8px', overflow: 'hidden' }}>
      <div className="tree-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 16px', background: '#f5f5f5', borderBottom: '1px solid #ddd' }}>
        <h3>Model Tree</h3>
        <div className="tree-actions" style={{ display: 'flex', gap: '8px' }}>
          <button onClick={showAll} style={{ padding: '4px 8px', border: '1px solid #ccc', borderRadius: '4px', background: 'white', cursor: 'pointer', fontSize: '12px' }}>
            Show All
          </button>
          <button onClick={hideAll} style={{ padding: '4px 8px', border: '1px solid #ccc', borderRadius: '4px', background: 'white', cursor: 'pointer', fontSize: '12px' }}>
            Hide All
          </button>
        </div>
      </div>
      <div className="tree-content" style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
        {loading && <div style={{ padding: '16px', textAlign: 'center', color: '#666' }}>Loading...</div>}
        {error && <div style={{ padding: '16px', textAlign: 'center', color: '#d32f2f' }}>{error}</div>}
        {!loading && !error && model && rootLinks.map(link => (
          <TreeNode
            key={link.name}
            node={link}
            depth={0}
            expanded={expandedNodes.has(link.name)}
            hidden={hiddenNodes.has(link.name)}
            allNodes={model.links}
            allJoints={model.joints}
            onToggle={toggleNode}
            onVisibility={toggleVisibility}
          />
        ))}
      </div>
    </div>
  );
};

export default ModelTree;

import React, { useState, useEffect } from 'react';

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

interface LinkInfo {
  name: string;
}

interface URDFModel {
  name: string;
  links: LinkInfo[];
  joints: JointInfo[];
}

interface JointControlProps {
  robotId: string;
}

const JointControl: React.FC<JointControlProps> = ({ robotId }) => {
  const [joints, setJoints] = useState<JointInfo[]>([]);
  const [jointValues, setJointValues] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedJoint, setSelectedJoint] = useState<string | null>(null);

  // Load URDF model to get joint information
  useEffect(() => {
    const loadModel = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/urdf/${robotId}`);
        if (!response.ok) throw new Error('Failed to load model');
        const data: URDFModel = await response.json();

        // Filter to only controllable joints (non-fixed)
        const controllableJoints = data.joints.filter(
          j => j.type !== 'fixed' && j.limit_lower !== undefined && j.limit_upper !== undefined
        );
        setJoints(controllableJoints);

        // Initialize joint values at mid-range
        const initialValues: Record<string, number> = {};
        controllableJoints.forEach(joint => {
          const mid = ((joint.limit_lower ?? 0) + (joint.limit_upper ?? 0)) / 2;
          initialValues[joint.name] = mid;
        });
        setJointValues(initialValues);
      } catch (e) {
        setError('Failed to load joint information');
      } finally {
        setLoading(false);
      }
    };
    loadModel();
  }, [robotId]);

  // Handle slider change
  const handleJointChange = (jointName: string, value: number) => {
    setJointValues(prev => ({
      ...prev,
      [jointName]: value
    }));
  };

  // Send joint state to Vuer server for 3D visualization
  const sendJointState = async () => {
    try {
      const jointsArray = Object.entries(jointValues).map(([name, position]) => ({
        joint_name: name,
        position,
        velocity: null
      }));

      // Send to backend (FastAPI) for joint state
      await fetch(`/api/state/${robotId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          robot_id: robotId,
          joints: jointsArray,
          timestamp: Date.now() / 1000
        })
      });
    } catch (e) {
      console.error('Failed to send joint state:', e);
    }
  };

  // Auto-send on value change (debounced)
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (Object.keys(jointValues).length > 0) {
        sendJointState();
      }
    }, 100);
    return () => clearTimeout(timeout);
  }, [jointValues, robotId]);

  // Get joint type display name
  const getJointTypeLabel = (type: string) => {
    switch (type) {
      case 'revolute': return 'Revolute';
      case 'prismatic': return 'Prismatic';
      case 'continuous': return 'Continuous';
      default: return type;
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '16px', textAlign: 'center', color: '#666' }}>
        Loading joints...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '16px', textAlign: 'center', color: '#d32f2f' }}>
        {error}
      </div>
    );
  }

  if (joints.length === 0) {
    return (
      <div style={{ padding: '16px', textAlign: 'center', color: '#666' }}>
        No controllable joints found
      </div>
    );
  }

  return (
    <div className="joint-control" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto' }}>
      <div className="joint-header" style={{ padding: '8px 12px', background: '#f5f5f5', borderBottom: '1px solid #ddd' }}>
        <h4 style={{ margin: 0, fontSize: '13px' }}>Joint Controls</h4>
        <span style={{ fontSize: '11px', color: '#666' }}>{joints.length} joints</span>
      </div>
      <div className="joint-list" style={{ padding: '8px' }}>
        {joints.map(joint => {
          const min = joint.limit_lower ?? -Math.PI;
          const max = joint.limit_upper ?? Math.PI;
          const value = jointValues[joint.name] ?? (min + max) / 2;
          const isSelected = selectedJoint === joint.name;

          return (
            <div
              key={joint.name}
              className={`joint-item ${isSelected ? 'selected' : ''}`}
              style={{
                marginBottom: '12px',
                padding: '8px',
                borderRadius: '4px',
                background: isSelected ? '#e3f2fd' : '#fafafa',
                border: `1px solid ${isSelected ? '#2196f3' : '#e0e0e0'}`,
                cursor: 'pointer'
              }}
              onClick={() => setSelectedJoint(isSelected ? null : joint.name)}
            >
              <div className="joint-header-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span className="joint-name" style={{ fontWeight: 600, fontSize: '12px' }}>
                  {joint.name}
                </span>
                <span className="joint-type" style={{ fontSize: '10px', color: '#666', background: '#eee', padding: '2px 6px', borderRadius: '3px' }}>
                  {getJointTypeLabel(joint.type)}
                </span>
              </div>

              <div className="joint-value" style={{ fontSize: '11px', color: '#666', marginBottom: '4px' }}>
                {value.toFixed(3)} rad
              </div>

              <input
                type="range"
                min={min}
                max={max}
                step={(max - min) / 100}
                value={value}
                onChange={(e) => handleJointChange(joint.name, parseFloat(e.target.value))}
                onClick={(e) => e.stopPropagation()}
                style={{
                  width: '100%',
                  height: '4px',
                  borderRadius: '2px',
                  background: `linear-gradient(to right, #2196f3 0%, #2196f3 ${((value - min) / (max - min)) * 100}%, #e0e0e0 ${((value - min) / (max - min)) * 100}%, #e0e0e0 100%)`,
                  outline: 'none',
                  WebkitAppearance: 'none',
                  cursor: 'pointer'
                }}
              />

              <div className="joint-limits" style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9px', color: '#999', marginTop: '2px' }}>
                <span>{min.toFixed(2)}</span>
                <span>{max.toFixed(2)}</span>
              </div>

              {isSelected && (
                <div className="joint-details" style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #e0e0e0', fontSize: '10px', color: '#666' }}>
                  <div>Parent: {joint.parent}</div>
                  <div>Child: {joint.child}</div>
                  {joint.axis && <div>Axis: [{joint.axis.join(', ')}]</div>}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default JointControl;
import React, { useState } from 'react';

interface URDFViewerProps {
  robotId: string;
  vuerPort: number;
}

const URDFViewer: React.FC<URDFViewerProps> = ({ robotId, vuerPort }) => {
  const [showGrid, setShowGrid] = useState(true);
  const [isPerspective, setIsPerspective] = useState(true);
  const vuerUrl = `http://localhost:${vuerPort}`;

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
        <div className="controls" style={{ display: 'flex', gap: '8px' }}>
          <button onClick={resetView} style={{ padding: '4px 12px', border: '1px solid #ccc', borderRadius: '4px', background: 'white', cursor: 'pointer' }}>
            Reset
          </button>
          <button onClick={toggleGrid} style={{ padding: '4px 12px', border: '1px solid #ccc', borderRadius: '4px', background: 'white', cursor: 'pointer' }}>
            Grid: {showGrid ? 'ON' : 'OFF'}
          </button>
          <button onClick={togglePerspective} style={{ padding: '4px 12px', border: '1px solid #ccc', borderRadius: '4px', background: 'white', cursor: 'pointer' }}>
            {isPerspective ? 'Perspective' : 'Orthographic'}
          </button>
        </div>
      </div>
      <div className="viewer-content" style={{ flex: 1, position: 'relative' }}>
        <iframe
          src={vuerUrl}
          className="vuer-iframe"
          style={{ width: '100%', height: '100%', border: 'none' }}
          allow="xr-spatial-tracking"
          title="Vuer 3D Viewer"
        />
      </div>
    </div>
  );
};

export default URDFViewer;

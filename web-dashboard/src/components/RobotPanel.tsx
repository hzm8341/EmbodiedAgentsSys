import React, { useState, useEffect } from 'react';
import URDFViewer from './URDFViewer';
import ModelTree from './TreeNode';

interface RobotInfo {
  robot_id: string;
  name: string;
  urdf_path: string;
}

const RobotPanel: React.FC = () => {
  const [robots, setRobots] = useState<RobotInfo[]>([]);
  const [selectedRobot, setSelectedRobot] = useState<string>('');

  useEffect(() => {
    const loadRobots = async () => {
      try {
        const response = await fetch('/api/urdf/list');
        const data = await response.json();
        setRobots(data);
        if (data.length > 0) {
          setSelectedRobot(data[0].robot_id);
        }
      } catch (e) {
        console.error('Failed to load robots:', e);
      }
    };
    loadRobots();
  }, []);

  return (
    <div style={{ display: 'flex', height: '100%', gap: '16px', padding: '16px' }}>
      <div style={{ width: '320px', flexShrink: 0 }}>
        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500 }}>Robot:</label>
          <select
            value={selectedRobot}
            onChange={(e) => setSelectedRobot(e.target.value)}
            style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
          >
            {robots.map(robot => (
              <option key={robot.robot_id} value={robot.robot_id}>
                {robot.name}
              </option>
            ))}
          </select>
        </div>
        {selectedRobot && <ModelTree robotId={selectedRobot} />}
      </div>
      <div style={{ flex: 1 }}>
        <URDFViewer robotId={selectedRobot} vuerPort={8012} />
      </div>
    </div>
  );
};

export default RobotPanel;

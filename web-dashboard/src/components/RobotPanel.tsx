import React, { useState, useEffect } from 'react';
import URDFViewer from './URDFViewer';

interface RobotInfo {
  robot_id: string;
  name: string;
  urdf_path: string;
}

const RobotPanel: React.FC = () => {
  const [_robots, setRobots] = useState<RobotInfo[]>([]);
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
      <div style={{ flex: 1 }}>
        {selectedRobot ? <URDFViewer robotId={selectedRobot} vuerPort={8012} /> : <div style={{ padding: 20, color: '#666' }}>Loading...</div>}
      </div>
    </div>
  );
};

export default RobotPanel;

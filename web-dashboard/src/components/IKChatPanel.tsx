import React, { useState } from 'react';

interface Position {
  x: number;
  y: number;
  z: number;
}

interface JointSolution {
  name: string;
  position: number;
}

interface IKResult {
  status: string;
  joints: JointSolution[];
  target_position: Position;
  current_position: Position;
  iterations: number;
  error: number;
}

interface Message {
  role: 'user' | 'system';
  content: string;
}

interface IKChatPanelProps {
  robotId: string;
}

const IKChatPanel: React.FC<IKChatPanelProps> = ({ robotId }) => {
  const [inputText, setInputText] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parseInput = (text: string): { arm: string; position: Position } | null => {
    // Support patterns:
    // "左臂移动到 X=10 Y=0 Z=20"
    // "left_arm to x=0.5 y=0.2 z=0.8"
    // "移动左手到 10, 0, 20"

    const leftArmPatterns = ['左臂', 'left_arm', 'l_arm', '左手', 'left_hand', 'l_hand'];
    const rightArmPatterns = ['右臂', 'right_arm', 'r_arm', '右手', 'right_hand', 'r_hand'];

    let arm = 'left'; // default

    // Detect arm
    const lowerText = text.toLowerCase();
    if (rightArmPatterns.some(p => lowerText.includes(p))) {
      arm = 'right';
    } else if (!leftArmPatterns.some(p => lowerText.includes(p))) {
      return null; // Cannot determine arm
    }

    // Extract numbers
    // Pattern 1: X=10 Y=0 Z=20 or x=0.5 y=0.2 z=0.8
    const xyzPattern = /[xyz]=([-\d.]+)/gi;
    const matches = text.match(xyzPattern);

    if (matches && matches.length >= 3) {
      const x = parseFloat(matches[0].split('=')[1]);
      const y = parseFloat(matches[1].split('=')[1]);
      const z = parseFloat(matches[2].split('=')[1]);
      if (!isNaN(x) && !isNaN(y) && !isNaN(z)) {
        return { arm, position: { x, y, z } };
      }
    }

    // Pattern 2: "10, 0, 20" format
    const numPattern = /([-\d.]+)\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)/;
    const numMatch = text.match(numPattern);
    if (numMatch) {
      return {
        arm,
        position: {
          x: parseFloat(numMatch[1]),
          y: parseFloat(numMatch[2]),
          z: parseFloat(numMatch[3])
        }
      };
    }

    return null;
  };

  const handleSend = async () => {
    if (!inputText.trim()) return;

    const userMessage: Message = { role: 'user', content: inputText };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const parsed = parseInput(inputText);

      if (!parsed) {
        setError('无法解析输入格式。请使用: "左臂移动到 X=10 Y=0 Z=20"');
        setIsLoading(false);
        return;
      }

      const response = await fetch('/api/ik/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          robot_id: robotId,
          target_link: parsed.arm === 'left' ? 'left_hand_joint7' : 'right_hand_joint7',
          position: parsed.position,
          arm: parsed.arm
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      const result: IKResult = await response.json();

      const systemMessage: Message = {
        role: 'system',
        content: `已移动 ${parsed.arm === 'left' ? '左' : '右'}臂末端到 (${parsed.position.x.toFixed(3)}, ${parsed.position.y.toFixed(3)}, ${parsed.position.z.toFixed(3)})\n末端误差: ${result.error.toFixed(4)}m\n关节数: ${result.joints.length}`
      };
      setMessages(prev => [...prev, systemMessage]);

    } catch (e) {
      setError(`错误: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([]);
    setInputText('');
    setError(null);
  };

  return (
    <div className="ik-chat-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', border: '1px solid #ddd', borderRadius: '8px', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '12px 16px', background: '#f5f5f5', borderBottom: '1px solid #ddd' }}>
        <h4 style={{ margin: 0, fontSize: '14px' }}>IK Control</h4>
        <p style={{ margin: '4px 0 0', fontSize: '11px', color: '#666' }}>
          示例: 左臂移动到 X=0.5 Y=0 Z=0.3
        </p>
      </div>

      {/* Messages */}
      <div className="messages" style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
        {messages.length === 0 && !error && (
          <div style={{ textAlign: 'center', color: '#999', padding: '20px', fontSize: '12px' }}>
            输入末端目标位置，IK求解器将计算关节角度
          </div>
        )}
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`message ${msg.role}`}
            style={{
              marginBottom: '8px',
              padding: '8px 12px',
              borderRadius: '8px',
              background: msg.role === 'user' ? '#e3f2fd' : '#f5f5f5',
              fontSize: '12px',
              whiteSpace: 'pre-wrap'
            }}
          >
            <strong>{msg.role === 'user' ? '用户' : '系统'}:</strong> {msg.content}
          </div>
        ))}
        {error && (
          <div style={{ color: '#d32f2f', padding: '8px', fontSize: '12px' }}>
            {error}
          </div>
        )}
      </div>

      {/* Input */}
      <div className="input-area" style={{ padding: '12px', borderTop: '1px solid #ddd', display: 'flex', gap: '8px' }}>
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="左臂移动到 X=0.5 Y=0 Z=0.3"
          disabled={isLoading}
          style={{ flex: 1, padding: '8px 12px', border: '1px solid #ccc', borderRadius: '4px', fontSize: '12px' }}
        />
        <button
          onClick={handleSend}
          disabled={isLoading || !inputText.trim()}
          style={{
            padding: '8px 16px',
            background: isLoading ? '#ccc' : '#2196f3',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isLoading ? 'not-allowed' : 'pointer',
            fontSize: '12px'
          }}
        >
          {isLoading ? '求解中...' : '发送'}
        </button>
        <button
          onClick={handleClear}
          style={{
            padding: '8px 16px',
            background: '#f5f5f5',
            color: '#666',
            border: '1px solid #ccc',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          清除
        </button>
      </div>
    </div>
  );
};

export default IKChatPanel;

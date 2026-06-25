import React, { useState } from 'react';
import { Twin } from '../../../types';
import { cn } from '../../../utils';

interface InterestGraphProps {
  twin?: Twin;
  loading?: boolean;
}

interface InterestItem {
  id: string;
  label: string;
  weight: number;
}

const COLORS = ['#4F46E5', '#0EA5E9', '#8B5CF6', '#D946EF', '#10B981'];

export function InterestGraph({ twin, loading = false }: InterestGraphProps) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  if (loading) {
    return (
      <div className="h-[300px] w-full bg-card border rounded-lg p-6 flex flex-col justify-between animate-pulse">
        <div className="h-4 bg-muted rounded w-1/4"></div>
        <div className="h-48 bg-muted rounded w-full"></div>
      </div>
    );
  }

  // Fallback interest items if none built yet
  let nodes: InterestItem[] = [];
  
  if (twin?.interest_graph?.nodes) {
    nodes = twin.interest_graph.nodes.map(n => ({ id: n.id, label: n.label, weight: n.weight }));
  } else if (twin?.interests && twin.interests.length > 0) {
    nodes = twin.interests.map((item, idx) => ({ id: `int-${idx}`, label: item, weight: Math.max(10, 80 - idx * 15) }));
  } else {
    // High-fidelity fallback default categories
    nodes = [
      { id: 'cat-1', label: 'Premium Electronics', weight: 85 },
      { id: 'cat-2', label: 'Designer Shoes', weight: 70 },
      { id: 'cat-3', label: 'Casual Apparel', weight: 65 },
      { id: 'cat-4', label: 'Fitness Gear', weight: 45 },
      { id: 'cat-5', label: 'Smart Home Tech', weight: 30 },
    ];
  }

  // Width & height parameters
  const width = 400;
  const height = 240;
  const cx = width / 2;
  const cy = height / 2;
  const radius = 80;

  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm flex flex-col justify-between h-[340px]">
      <div>
        <h3 className="text-sm font-semibold tracking-tight text-foreground font-sans">Interest Affinity Graph</h3>
        <p className="text-[10px] text-muted-foreground font-mono">Edge links denote co-occurrence triggers</p>
      </div>

      <div className="flex items-center gap-6 flex-1 mt-4">
        {/* SVG Node Graph */}
        <div className="w-[200px] h-[200px] shrink-0 border border-zinc-200 dark:border-zinc-800 rounded bg-zinc-50/50 dark:bg-zinc-950/20 relative">
          <svg
            viewBox={`0 0 ${width} ${height}`}
            className="w-full h-full"
            xmlns="http://www.w3.org/2000/svg"
          >
            {/* Inner lines connecting nodes to the center */}
            {nodes.map((node, index) => {
              const angle = (index * 2 * Math.PI) / nodes.length;
              const nx = cx + radius * Math.cos(angle);
              const ny = cy + radius * Math.sin(angle);
              const thickness = Math.max(1, node.weight / 25);
              return (
                <line
                  key={`edge-${node.id}`}
                  x1={cx}
                  y1={cy}
                  x2={nx}
                  y2={ny}
                  stroke="#71717a"
                  strokeWidth={thickness}
                  strokeOpacity={0.25}
                />
              );
            })}

            {/* Central Node representing the Twin Core */}
            <circle cx={cx} cy={cy} r={20} fill="#09090B" stroke="#2563EB" strokeWidth={2} />
            <text x={cx} y={cy + 3} textAnchor="middle" fill="#FFFFFF" fontSize="8" fontWeight="bold">CORE</text>

            {/* Orbiting nodes */}
            {nodes.map((node, index) => {
              const angle = (index * 2 * Math.PI) / nodes.length;
              const nx = cx + radius * Math.cos(angle);
              const ny = cy + radius * Math.sin(angle);
              const nodeSize = Math.max(8, (node.weight / 100) * 20);
              const isHovered = hoveredNode === node.id;
              
              return (
                <g 
                  key={node.id}
                  onMouseEnter={() => setHoveredNode(node.id)}
                  onMouseLeave={() => setHoveredNode(null)}
                  className="cursor-pointer"
                >
                  <circle
                    cx={nx}
                    cy={ny}
                    r={nodeSize + (isHovered ? 4 : 0)}
                    fill={COLORS[index % COLORS.length]}
                    fillOpacity={0.85}
                    stroke={isHovered ? '#FFFFFF' : 'none'}
                    strokeWidth={1}
                    className="transition-all duration-150"
                  />
                  <text
                    x={nx}
                    y={ny + 2}
                    textAnchor="middle"
                    fill="#FFFFFF"
                    fontSize="7"
                    fontWeight="bold"
                    className="pointer-events-none select-none"
                  >
                    {Math.round(node.weight)}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Interactive Tooltip Overlay */}
          {hoveredNode && (
            <div className="absolute top-2 left-2 bg-zinc-950/95 text-zinc-50 border border-zinc-800 px-2 py-1 rounded text-[9px] font-mono shadow-md z-20">
              {(() => {
                const nd = nodes.find(n => n.id === hoveredNode);
                return `${nd?.label}: ${nd?.weight}%`;
              })()}
            </div>
          )}
        </div>

        {/* Categories List */}
        <div className="flex-1 space-y-2 max-h-[180px] overflow-y-auto pr-1">
          {nodes.map((item, idx) => (
            <div key={idx} className="flex justify-between items-center text-[10px] border-b pb-1 dark:border-zinc-800 last:border-b-0">
              <div className="flex items-center gap-1.5 truncate">
                <span 
                  className="h-1.5 w-1.5 rounded-full shrink-0" 
                  style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                ></span>
                <span className="font-semibold text-foreground truncate max-w-[100px]">{item.label}</span>
              </div>
              <span className="font-bold font-mono text-zinc-400">{Math.round(item.weight)}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
export default InterestGraph;

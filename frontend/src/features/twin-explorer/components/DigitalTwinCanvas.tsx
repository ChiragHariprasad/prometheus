import React, { useState } from 'react';
import { Twin, Customer } from '../../../types';
import { cn } from '../../../utils';
import { StatusBadge } from '../../../components/shared/StatusBadge';

interface DigitalTwinCanvasProps {
  customer?: Customer;
  twin?: Twin & { lastBuiltAt?: string };
  loading?: boolean;
}

export function DigitalTwinCanvas({
  customer,
  twin,
  loading = false,
}: DigitalTwinCanvasProps) {
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  if (loading) {
    return (
      <div className="h-[460px] w-full bg-card border rounded-lg flex items-center justify-center animate-pulse">
        <span className="text-xs text-muted-foreground font-mono">Building digital twin model...</span>
      </div>
    );
  }

  if (!customer || !twin) {
    return (
      <div className="h-[460px] w-full bg-card border border-dashed rounded-lg flex items-center justify-center">
        <span className="text-xs text-muted-foreground font-mono">Select a customer to visualize the digital twin</span>
      </div>
    );
  }

  // Dimensions
  const width = 600;
  const height = 400;
  const cx = width / 2;
  const cy = height / 2;

  // Concentric Rings Sizes
  const coreRadius = 45;
  const orbit1Radius = 90;
  const orbit2Radius = 140;

  // Scaled values
  const eng = twin.engagement_score ?? 60;
  const loy = twin.loyalty_score ?? 60;
  const conf = twin.confidence_score ?? 60;

  // Nodes positional layout around the center (angles in radians)
  const behaviorNodes = [
    { id: 'purchase', label: 'Purchase Frequency', val: `${formatValue(twin.lifetime_value)} LTV`, angle: 0, orbit: orbit1Radius, color: '#10B981' },
    { id: 'session', label: 'Session Depth', val: 'Dense Activity', angle: Math.PI / 3, orbit: orbit2Radius, color: '#2563EB' },
    { id: 'channel', label: 'Channel Affinity', val: 'Email Preferred', angle: (2 * Math.PI) / 3, orbit: orbit1Radius, color: '#0EA5E9' },
    { id: 'sentiment', label: 'Emotional State', val: `${twin.sentiment_score ?? 72}% Pos`, angle: Math.PI, orbit: orbit2Radius, color: '#8B5CF6' },
    { id: 'churn', label: 'Risk (Churn)', val: `${(twin.churn_probability ?? 0.08 * 100).toFixed(0)}% Prob`, angle: (4 * Math.PI) / 3, orbit: orbit1Radius, color: '#EF4444' },
    { id: 'staleness', label: 'Model Freshness', val: 'Updated Live', angle: (5 * Math.PI) / 3, orbit: orbit2Radius, color: '#F59E0B' },
  ];

  function formatValue(v?: number) {
    if (v === undefined) return '$380';
    return `$${v}`;
  }

  const initial = customer.first_name?.charAt(0) || customer.email.charAt(0).toUpperCase();

  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm flex flex-col justify-between h-[460px] relative overflow-hidden select-none">
      {/* Visual Header */}
      <div className="flex items-center justify-between pb-3 border-b border-zinc-200 dark:border-zinc-800 shrink-0">
        <div>
          <h3 className="text-sm font-semibold tracking-tight text-foreground font-sans">Behavioral DNA Visualization</h3>
          <p className="text-[10px] text-muted-foreground font-mono">Live SVG orbit mapping for twin node traits</p>
        </div>
        <StatusBadge type="twin" status={twin.status} />
      </div>

      {/* SVG Canvas Workspace */}
      <div className="flex-1 flex items-center justify-center relative min-h-0">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-full max-h-[340px]"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Concentric Orbits Grid Lines */}
          <circle cx={cx} cy={cy} r={orbit1Radius} fill="none" stroke="#e4e4e7" strokeDasharray="4 4" className="dark:stroke-zinc-800" />
          <circle cx={cx} cy={cy} r={orbit2Radius} fill="none" stroke="#e4e4e7" strokeDasharray="4 4" className="dark:stroke-zinc-800" />

          {/* Connection Lines from Orbit Nodes to Core */}
          {behaviorNodes.map((node) => {
            const nx = cx + node.orbit * Math.cos(node.angle);
            const ny = cy + node.orbit * Math.sin(node.angle);
            return (
              <line
                key={`line-${node.id}`}
                x1={cx}
                y1={cy}
                x2={nx}
                y2={ny}
                stroke="#e4e4e7"
                strokeWidth={1.5}
                className="dark:stroke-zinc-850"
              />
            );
          })}

          {/* Animated Memory Arcs (Dash Offset Effect) */}
          {behaviorNodes.map((node, index) => {
            const nx = cx + node.orbit * Math.cos(node.angle);
            const ny = cy + node.orbit * Math.sin(node.angle);
            return (
              <path
                key={`arc-${node.id}`}
                d={`M ${nx} ${ny} L ${cx} ${cy}`}
                fill="none"
                stroke={node.color}
                strokeWidth={2}
                strokeDasharray="10, 40"
                className="animate-[dash_3s_linear_infinite]"
                style={{
                  animationDelay: `${index * 0.5}s`,
                }}
              />
            );
          })}

          {/* Orbiting Nodes */}
          {behaviorNodes.map((node) => {
            const nx = cx + node.orbit * Math.cos(node.angle);
            const ny = cy + node.orbit * Math.sin(node.angle);
            const isHovered = hoveredNode === node.id;
            return (
              <g
                key={node.id}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                className="cursor-pointer group"
              >
                {/* Node Outer Halo Glow */}
                <circle
                  cx={nx}
                  cy={ny}
                  r={isHovered ? 14 : 8}
                  fill="none"
                  stroke={node.color}
                  strokeWidth={2}
                  strokeOpacity={0.4}
                  className="transition-all duration-200"
                />
                {/* Solid Core Dot */}
                <circle
                  cx={nx}
                  cy={ny}
                  r={isHovered ? 8 : 5}
                  fill={node.color}
                  className="transition-all duration-200"
                />
                {/* Label text */}
                <text
                  x={nx}
                  y={ny - (isHovered ? 20 : 12)}
                  textAnchor="middle"
                  fill="#71717a"
                  fontSize={isHovered ? 11 : 9}
                  fontWeight={isHovered ? 'bold' : 'normal'}
                  className="fill-zinc-400 font-sans pointer-events-none select-none transition-all duration-200"
                >
                  {node.label}
                </text>
              </g>
            );
          })}

          {/* Central Concentric Core Gauge */}
          {/* Ring 3: Confidence Circle (Outer) */}
          <circle cx={cx} cy={cy} r={coreRadius + 8} fill="none" stroke="#2563EB" strokeWidth={3} strokeDasharray={`${conf * 2.8}, 360`} strokeLinecap="round" />
          {/* Ring 2: Loyalty Circle */}
          <circle cx={cx} cy={cy} r={coreRadius + 3} fill="none" stroke="#10B981" strokeWidth={3} strokeDasharray={`${loy * 2.5}, 360`} strokeLinecap="round" />
          {/* Ring 1: Engagement Circle */}
          <circle cx={cx} cy={cy} r={coreRadius - 2} fill="none" stroke="#0EA5E9" strokeWidth={3} strokeDasharray={`${eng * 2.2}, 360`} strokeLinecap="round" />

          {/* Center Circle Face */}
          <circle cx={cx} cy={cy} r={coreRadius - 7} fill="#09090B" stroke="#18181B" strokeWidth={2} />
          
          {/* Customer Initials */}
          <text
            x={cx}
            y={cy + 5}
            textAnchor="middle"
            fill="#FFFFFF"
            fontSize="16"
            fontWeight="bold"
            fontFamily="sans-serif"
          >
            {initial}
          </text>
        </svg>

        {/* Small Overlay Signal Details */}
        {hoveredNode && (
          <div className="absolute bottom-4 left-4 bg-zinc-950/95 text-zinc-50 border border-zinc-800 p-2.5 rounded shadow-lg text-[10px] font-mono w-44 z-10 transition-opacity">
            {(() => {
              const nd = behaviorNodes.find(n => n.id === hoveredNode);
              return (
                <>
                  <p className="font-bold text-zinc-400 mb-0.5">{nd?.label}</p>
                  <p className="text-accent">Value: {nd?.val}</p>
                </>
              );
            })()}
          </div>
        )}
      </div>

      {/* Styled inline keyframes for memory pulse arcs */}
      <style>{`
        @keyframes dash {
          to {
            stroke-dashoffset: -50;
          }
        }
      `}</style>
    </div>
  );
}
export default DigitalTwinCanvas;

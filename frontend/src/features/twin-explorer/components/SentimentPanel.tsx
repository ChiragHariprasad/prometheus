import React from 'react';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip 
} from 'recharts';
import { cn } from '../../../utils';
import { Smile, Meh, Frown } from 'lucide-react';

interface SentimentPanelProps {
  sentimentScore?: number;
  sentimentTrend?: Array<{ date: string; score: number }>;
  loading?: boolean;
}

export function SentimentPanel({
  sentimentScore = 70,
  sentimentTrend = [],
  loading = false,
}: SentimentPanelProps) {
  if (loading) {
    return (
      <div className="h-[300px] w-full bg-card border rounded-lg p-6 flex flex-col justify-between animate-pulse">
        <div className="h-4 bg-muted rounded w-1/4"></div>
        <div className="h-48 bg-muted rounded w-full"></div>
      </div>
    );
  }

  // Pre-seed mock data if empty
  const chartData = sentimentTrend.length > 0 ? sentimentTrend : [
    { date: 'Jun 19', score: 62 },
    { date: 'Jun 20', score: 65 },
    { date: 'Jun 21', score: 58 },
    { date: 'Jun 22', score: 70 },
    { date: 'Jun 23', score: 78 },
    { date: 'Jun 24', score: 75 },
    { date: 'Jun 25', score: 72 },
  ];

  const getSentimentLabel = (score: number) => {
    if (score >= 75) return { label: 'POSITIVE', color: 'text-success border-success/20 bg-success/5', icon: <Smile className="h-4 w-4 text-success" /> };
    if (score >= 45) return { label: 'NEUTRAL', color: 'text-warning border-warning/20 bg-warning/5', icon: <Meh className="h-4 w-4 text-warning" /> };
    return { label: 'NEGATIVE', color: 'text-error border-error/20 bg-error/5', icon: <Frown className="h-4 w-4 text-error" /> };
  };

  const rating = getSentimentLabel(sentimentScore);

  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm flex flex-col justify-between h-[340px] font-sans">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold tracking-tight text-foreground">Emotional Sentiment Trend</h3>
          <p className="text-[10px] text-muted-foreground font-mono">Dynamic NLP analysis from channel activities</p>
        </div>
        <div className={cn("flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-bold", rating.color)}>
          {rating.icon}
          {rating.label}
        </div>
      </div>

      <div className="h-48 mt-4 flex-1">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 10, right: 0, left: -25, bottom: 0 }}>
            <defs>
              <linearGradient id="colorSentiment" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10B981" stopOpacity={0.2}/>
                <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e4e4e7" className="dark:stroke-zinc-800" />
            <XAxis dataKey="date" tick={{ fill: '#71717a', fontSize: 9 }} axisLine={false} tickLine={false} />
            <YAxis domain={[0, 100]} tick={{ fill: '#71717a', fontSize: 9 }} axisLine={false} tickLine={false} />
            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  return (
                    <div className="bg-zinc-950 text-zinc-50 border border-zinc-800 p-2 rounded shadow text-[10px] font-mono">
                      <p className="font-semibold">{payload[0].payload.date}</p>
                      <p className="text-success mt-0.5">Score: {payload[0].value}%</p>
                    </div>
                  );
                }
                return null;
              }}
            />
            <Area 
              type="monotone" 
              dataKey="score" 
              stroke="#10B981" 
              strokeWidth={2} 
              fillOpacity={1} 
              fill="url(#colorSentiment)" 
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
export default SentimentPanel;

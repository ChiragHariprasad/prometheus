import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../store/auth-store';
import { cn } from '../../utils';
import { Loader2, KeyRound } from 'lucide-react';

export function LoginPage() {
  const navigate = useNavigate();
  const { setAuth } = useAuthStore();
  const [email, setEmail] = useState('admin@prometheus.ai');
  const [password, setPassword] = useState('Test1234!');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    // Simulate API authorization response (since backend might not be online)
    setTimeout(() => {
      if (email === 'admin@prometheus.ai' && password === 'Test1234!') {
        setAuth('demo-token', {
          id: "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
          email: "admin@prometheus.ai",
          first_name: "Chirag",
          last_name: "Hariprasad",
          name: "Chirag Hariprasad",
          organization_id: "11782a90-7782-4a0b-b3ef-2ef1825f57fc",
          roles: ["admin"],
          permissions: ["*"]
        });
        navigate('/dashboard');
      } else {
        setError('Invalid credentials. For the demo, use prefilled credentials.');
        setLoading(false);
      }
    }, 800);
  };

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-zinc-950 font-sans">
      <div className="w-full max-w-sm p-6 bg-zinc-900 border border-zinc-800 rounded-lg shadow-2xl">
        <div className="flex flex-col items-center mb-6">
          <div className="h-10 w-10 bg-accent rounded-md flex items-center justify-center text-white mb-3">
            <KeyRound className="h-5 w-5" />
          </div>
          <h2 className="text-xl font-bold text-white tracking-wider">TWINCX</h2>
          <p className="text-xs text-zinc-400 mt-1">Sign in to your decision command center</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-zinc-400 mb-1.5 uppercase">Email Address</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full h-10 px-3 rounded border border-zinc-800 bg-zinc-950 text-white text-sm focus:outline-none focus:border-accent"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-zinc-400 mb-1.5 uppercase">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full h-10 px-3 rounded border border-zinc-800 bg-zinc-950 text-white text-sm focus:outline-none focus:border-accent"
              required
            />
          </div>

          {error && (
            <p className="text-xs text-error font-medium">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full h-10 bg-accent hover:bg-blue-700 text-white rounded text-sm font-semibold transition-colors flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Authenticate Session'}
          </button>
        </form>
      </div>
    </div>
  );
}
export default LoginPage;

import { useState } from 'react';
import { Activity, Terminal, Wifi, WifiOff, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useExecutionStore } from '@/store/useExecutionStore';

export default function ExecutionsPage() {
  const { logs, isConnected, connect, disconnect, clearLogs } = useExecutionStore();
  const [executionId, setExecutionId] = useState('');

  const handleConnect = () => {
    if (executionId) {
      disconnect();
      clearLogs();
      connect(executionId);
    }
  };

  const levelColors: Record<string, string> = {
    INFO: 'text-blue-400',
    WARN: 'text-amber-400',
    ERROR: 'text-red-400',
    DEBUG: 'text-slate-400',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Live Execution Monitor</h1>
          <p className="text-slate-400 mt-1">Real-time execution logs and agent activity</p>
        </div>
        <div className="flex items-center gap-2">
          {isConnected ? (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-green-500/20 rounded-full">
              <Wifi className="w-4 h-4 text-green-400" />
              <span className="text-xs text-green-400">Connected</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-500/20 rounded-full">
              <WifiOff className="w-4 h-4 text-slate-400" />
              <span className="text-xs text-slate-400">Disconnected</span>
            </div>
          )}
        </div>
      </div>

      {/* Connection Controls */}
      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-4">
          <div className="flex gap-3">
            <input
              type="text"
              placeholder="Enter Execution ID..."
              className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={executionId}
              onChange={(e) => setExecutionId(e.target.value)}
            />
            <Button
              onClick={handleConnect}
              className="bg-blue-600 hover:bg-blue-700"
              disabled={!executionId}
            >
              <Activity className="w-4 h-4 mr-2" />
              Connect
            </Button>
            <Button
              variant="outline"
              className="border-slate-700 text-slate-300 hover:text-white"
              onClick={() => {
                disconnect();
                clearLogs();
              }}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              Clear
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Live Logs */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white text-base flex items-center gap-2">
            <Terminal className="w-4 h-4 text-green-400" />
            Execution Logs
            {logs.length > 0 && (
              <span className="text-xs text-slate-500 ml-2">({logs.length} entries)</span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-slate-950 rounded-lg border border-slate-800 p-4 h-[500px] overflow-y-auto font-mono text-sm">
            {logs.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-slate-600">
                <Terminal className="w-8 h-8 mb-2" />
                <p>No logs yet</p>
                <p className="text-xs mt-1">Connect to an execution to see live logs</p>
              </div>
            ) : (
              <div className="space-y-1">
                {logs.map((log) => (
                  <div key={log.id} className="flex gap-3 py-1 hover:bg-slate-900/50 rounded">
                    <span className="text-slate-600 text-xs shrink-0 w-36">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </span>
                    <span className={`text-xs font-semibold w-14 shrink-0 ${levelColors[log.level] || 'text-slate-400'}`}>
                      {log.level}
                    </span>
                    <span className="text-slate-300">{log.message}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

import { useEffect } from 'react';
import {
  Bot,
  Workflow,
  Activity,
  Zap,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  Clock,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useAgentStore } from '@/store/useAgentStore';
import { useWorkflowStore } from '@/store/useWorkflowStore';

export default function Dashboard() {
  const { agents, fetchAgents } = useAgentStore();
  const { workflows, fetchWorkflows } = useWorkflowStore();

  useEffect(() => {
    fetchAgents();
    fetchWorkflows();
  }, [fetchAgents, fetchWorkflows]);

  const stats = [
    {
      title: 'Total Agents',
      value: agents.length,
      icon: Bot,
      color: 'text-blue-400',
      bg: 'bg-blue-500/10',
    },
    {
      title: 'Active Agents',
      value: agents.filter((a) => a.status === 'idle' || a.status === 'leader').length,
      icon: Zap,
      color: 'text-green-400',
      bg: 'bg-green-500/10',
    },
    {
      title: 'Workflows',
      value: workflows.length,
      icon: Workflow,
      color: 'text-purple-400',
      bg: 'bg-purple-500/10',
    },
    {
      title: 'Running Tasks',
      value: agents.filter((a) => a.status === 'busy').length,
      icon: Activity,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10',
    },
  ];

  const recentActivity = [
    { id: 1, event: 'Workflow "Code Review Pipeline" executed', time: '2 min ago', status: 'success' },
    { id: 2, event: 'Agent "Research-01" completed task', time: '5 min ago', status: 'success' },
    { id: 3, event: 'New agent "Coder-Pro" registered', time: '12 min ago', status: 'info' },
    { id: 4, event: 'Execution timeout in workflow "Data Pipeline"', time: '1 hr ago', status: 'warning' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-slate-400 mt-1">Overview of your agent swarm and platform metrics</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.title} className="bg-slate-900 border-slate-800">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-400">{stat.title}</p>
                    <p className="text-3xl font-bold text-white mt-2">{stat.value}</p>
                  </div>
                  <div className={`p-3 rounded-lg ${stat.bg}`}>
                    <Icon className={`w-6 h-6 ${stat.color}`} />
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Agent Status */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Bot className="w-5 h-5 text-blue-400" />
              Agent Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {agents.slice(0, 5).map((agent) => (
                <div
                  key={agent.id}
                  className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-2.5 h-2.5 rounded-full ${
                        agent.status === 'idle'
                          ? 'bg-green-500'
                          : agent.status === 'busy'
                            ? 'bg-amber-500'
                            : agent.status === 'leader'
                              ? 'bg-blue-500'
                              : agent.status === 'error'
                                ? 'bg-red-500'
                                : 'bg-slate-500'
                      }`}
                    />
                    <div>
                      <p className="text-sm font-medium text-white">{agent.name}</p>
                      <p className="text-xs text-slate-500">
                        {agent.agent_type} · {agent.llm_model}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`text-xs px-2 py-1 rounded-full capitalize ${
                      agent.status === 'idle'
                        ? 'bg-green-500/20 text-green-400'
                        : agent.status === 'busy'
                          ? 'bg-amber-500/20 text-amber-400'
                          : agent.status === 'leader'
                            ? 'bg-blue-500/20 text-blue-400'
                            : 'bg-slate-500/20 text-slate-400'
                    }`}
                  >
                    {agent.status}
                  </span>
                </div>
              ))}
              {agents.length === 0 && (
                <p className="text-slate-500 text-sm text-center py-4">No agents registered yet</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Activity className="w-5 h-5 text-purple-400" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {recentActivity.map((activity) => (
                <div key={activity.id} className="flex items-start gap-3 p-3 bg-slate-800/50 rounded-lg">
                  {activity.status === 'success' && (
                    <CheckCircle className="w-5 h-5 text-green-400 mt-0.5 shrink-0" />
                  )}
                  {activity.status === 'warning' && (
                    <AlertTriangle className="w-5 h-5 text-amber-400 mt-0.5 shrink-0" />
                  )}
                  {activity.status === 'info' && (
                    <TrendingUp className="w-5 h-5 text-blue-400 mt-0.5 shrink-0" />
                  )}
                  <div>
                    <p className="text-sm text-slate-300">{activity.event}</p>
                    <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {activity.time}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

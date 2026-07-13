import { useEffect, useState } from 'react';
import { Plus, Search, Bot, Settings, Power, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useAgentStore } from '@/store/useAgentStore';

const AGENT_TYPES = [
  'planner',
  'research',
  'coding',
  'reviewer',
  'testing',
  'memory',
  'tool',
  'custom',
];

const LLM_MODELS = [
  { value: 'gpt-4o', label: 'GPT-4o (OpenAI)' },
  { value: 'gpt-4o-mini', label: 'GPT-4o Mini (OpenAI)' },
  { value: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet (Anthropic)' },
  { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus (Anthropic)' },
];

export default function AgentsPage() {
  const { agents, fetchAgents, createAgent, deleteAgent, isLoading } = useAgentStore();
  const [search, setSearch] = useState('');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [newAgent, setNewAgent] = useState({
    name: '',
    description: '',
    agent_type: 'custom',
    team_id: '00000000-0000-0000-0000-000000000000',
    llm_model: 'gpt-4o',
    temperature: 0.7,
    system_prompt: '',
  });

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  const filteredAgents = agents.filter((a) =>
    a.name.toLowerCase().includes(search.toLowerCase()) ||
    a.agent_type.toLowerCase().includes(search.toLowerCase())
  );

  const handleCreate = async () => {
    await createAgent(newAgent);
    setIsDialogOpen(false);
    setNewAgent({
      name: '',
      description: '',
      agent_type: 'custom',
      team_id: '00000000-0000-0000-0000-000000000000',
      llm_model: 'gpt-4o',
      temperature: 0.7,
      system_prompt: '',
    });
  };

  const statusColors: Record<string, string> = {
    idle: 'bg-green-500',
    busy: 'bg-amber-500',
    leader: 'bg-blue-500',
    error: 'bg-red-500',
    paused: 'bg-slate-500',
    offline: 'bg-slate-700',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Agents</h1>
          <p className="text-slate-400 mt-1">Manage your AI agent swarm</p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-blue-600 hover:bg-blue-700">
              <Plus className="w-4 h-4 mr-2" />
              New Agent
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-slate-900 border-slate-800 text-white max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Bot className="w-5 h-5 text-blue-400" />
                Create New Agent
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-4">
              <div>
                <Label className="text-slate-300">Name</Label>
                <Input
                  className="bg-slate-800 border-slate-700 text-white mt-1"
                  placeholder="e.g., Research Assistant"
                  value={newAgent.name}
                  onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })}
                />
              </div>
              <div>
                <Label className="text-slate-300">Type</Label>
                <Select
                  value={newAgent.agent_type}
                  onValueChange={(v) => setNewAgent({ ...newAgent, agent_type: v })}
                >
                  <SelectTrigger className="bg-slate-800 border-slate-700 text-white mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-700">
                    {AGENT_TYPES.map((t) => (
                      <SelectItem key={t} value={t} className="text-white capitalize">
                        {t}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-slate-300">LLM Model</Label>
                <Select
                  value={newAgent.llm_model}
                  onValueChange={(v) => setNewAgent({ ...newAgent, llm_model: v })}
                >
                  <SelectTrigger className="bg-slate-800 border-slate-700 text-white mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-700">
                    {LLM_MODELS.map((m) => (
                      <SelectItem key={m.value} value={m.value} className="text-white">
                        {m.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-slate-300">System Prompt</Label>
                <textarea
                  className="w-full h-24 bg-slate-800 border border-slate-700 rounded-lg p-3 text-white text-sm mt-1 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Optional custom instructions for this agent..."
                  value={newAgent.system_prompt}
                  onChange={(e) => setNewAgent({ ...newAgent, system_prompt: e.target.value })}
                />
              </div>
              <Button onClick={handleCreate} className="w-full bg-blue-600 hover:bg-blue-700">
                Create Agent
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <Input
          className="pl-10 bg-slate-900 border-slate-800 text-white"
          placeholder="Search agents by name or type..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredAgents.map((agent) => (
            <Card key={agent.id} className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-colors">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <div className="w-10 h-10 bg-slate-800 rounded-lg flex items-center justify-center">
                        <Bot className="w-5 h-5 text-blue-400" />
                      </div>
                      <div
                        className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2 border-slate-900 ${
                          statusColors[agent.status] || 'bg-slate-500'
                        }`}
                      />
                    </div>
                    <div>
                      <CardTitle className="text-white text-base">{agent.name}</CardTitle>
                      <p className="text-xs text-slate-500 capitalize">{agent.agent_type}</p>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-white">
                      <Settings className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-slate-400 hover:text-red-400"
                      onClick={() => deleteAgent(agent.id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-slate-400 line-clamp-2 mb-3">
                  {agent.description || `Specialized ${agent.agent_type} agent powered by ${agent.llm_model}`}
                </p>
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span className="flex items-center gap-1">
                    <Power className="w-3 h-3" />
                    {agent.llm_model}
                  </span>
                  <span className="flex items-center gap-1">
                    Tasks: {agent.total_tasks_completed}
                  </span>
                </div>
              </CardContent>
            </Card>
          ))}

          {filteredAgents.length === 0 && (
            <div className="col-span-full text-center py-12">
              <Bot className="w-12 h-12 text-slate-700 mx-auto mb-3" />
              <p className="text-slate-500">No agents found</p>
              <p className="text-slate-600 text-sm mt-1">Create your first agent to get started</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

import { useEffect, useState } from 'react';
import { Plus, Search, Workflow, Play, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { useWorkflowStore } from '@/store/useWorkflowStore';

export default function WorkflowsPage() {
  const { workflows, executions, fetchWorkflows, createWorkflow, executeWorkflow, fetchExecutions } =
    useWorkflowStore();
  const [search, setSearch] = useState('');
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [newWorkflow, setNewWorkflow] = useState({
    name: '',
    description: '',
    team_id: '00000000-0000-0000-0000-000000000000',
    max_parallel_agents: 5,
  });

  useEffect(() => {
    fetchWorkflows();
  }, [fetchWorkflows]);

  useEffect(() => {
    if (selectedWorkflow) {
      fetchExecutions(selectedWorkflow);
    }
  }, [selectedWorkflow, fetchExecutions]);

  const filteredWorkflows = workflows.filter((w) =>
    w.name.toLowerCase().includes(search.toLowerCase())
  );

  const handleCreate = async () => {
    await createWorkflow(newWorkflow);
    setIsDialogOpen(false);
    setNewWorkflow({ name: '', description: '', team_id: '00000000-0000-0000-0000-000000000000', max_parallel_agents: 5 });
  };

  const statusColors: Record<string, string> = {
    draft: 'text-slate-400 bg-slate-500/20',
    running: 'text-blue-400 bg-blue-500/20',
    completed: 'text-green-400 bg-green-500/20',
    failed: 'text-red-400 bg-red-500/20',
    scheduled: 'text-purple-400 bg-purple-500/20',
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Workflows</h1>
          <p className="text-slate-400 mt-1">Design and execute agent workflows</p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-blue-600 hover:bg-blue-700">
              <Plus className="w-4 h-4 mr-2" />
              New Workflow
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-slate-900 border-slate-800 text-white max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Workflow className="w-5 h-5 text-purple-400" />
                Create Workflow
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-4">
              <div>
                <Label className="text-slate-300">Name</Label>
                <Input
                  className="bg-slate-800 border-slate-700 text-white mt-1"
                  placeholder="e.g., Code Review Pipeline"
                  value={newWorkflow.name}
                  onChange={(e) => setNewWorkflow({ ...newWorkflow, name: e.target.value })}
                />
              </div>
              <div>
                <Label className="text-slate-300">Description</Label>
                <textarea
                  className="w-full h-20 bg-slate-800 border border-slate-700 rounded-lg p-3 text-white text-sm mt-1 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="What does this workflow do?"
                  value={newWorkflow.description}
                  onChange={(e) => setNewWorkflow({ ...newWorkflow, description: e.target.value })}
                />
              </div>
              <div>
                <Label className="text-slate-300">Max Parallel Agents</Label>
                <Input
                  type="number"
                  className="bg-slate-800 border-slate-700 text-white mt-1"
                  value={newWorkflow.max_parallel_agents}
                  onChange={(e) =>
                    setNewWorkflow({ ...newWorkflow, max_parallel_agents: parseInt(e.target.value) || 5 })
                  }
                />
              </div>
              <Button onClick={handleCreate} className="w-full bg-blue-600 hover:bg-blue-700">
                Create Workflow
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <Input
          className="pl-10 bg-slate-900 border-slate-800 text-white"
          placeholder="Search workflows..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Workflow List */}
        <div className="lg:col-span-2 space-y-3">
          {filteredWorkflows.map((workflow) => (
            <Card
              key={workflow.id}
              className={`bg-slate-900 border-slate-800 cursor-pointer transition-colors ${
                selectedWorkflow === workflow.id ? 'border-blue-500' : 'hover:border-slate-700'
              }`}
              onClick={() => setSelectedWorkflow(workflow.id)}
            >
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center">
                      <Workflow className="w-5 h-5 text-purple-400" />
                    </div>
                    <div>
                      <h3 className="text-white font-medium">{workflow.name}</h3>
                      <p className="text-xs text-slate-500">{workflow.description || 'No description'}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`text-xs px-2 py-1 rounded-full capitalize ${
                        statusColors[workflow.status] || 'text-slate-400 bg-slate-500/20'
                      }`}
                    >
                      {workflow.status}
                    </span>
                    <Button
                      size="sm"
                      className="bg-green-600 hover:bg-green-700 h-8"
                      onClick={(e) => {
                        e.stopPropagation();
                        executeWorkflow(workflow.id);
                      }}
                    >
                      <Play className="w-3 h-3 mr-1" />
                      Run
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}

          {filteredWorkflows.length === 0 && (
            <div className="text-center py-12">
              <Workflow className="w-12 h-12 text-slate-700 mx-auto mb-3" />
              <p className="text-slate-500">No workflows found</p>
            </div>
          )}
        </div>

        {/* Execution History */}
        <div>
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader>
              <CardTitle className="text-white text-base flex items-center gap-2">
                <Clock className="w-4 h-4 text-slate-400" />
                Recent Executions
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {executions.slice(0, 10).map((exec) => (
                  <div
                    key={exec.id}
                    className="flex items-center justify-between p-2 bg-slate-800/50 rounded-lg"
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          exec.status === 'completed'
                            ? 'bg-green-500'
                            : exec.status === 'running'
                              ? 'bg-blue-500'
                              : exec.status === 'failed'
                                ? 'bg-red-500'
                                : 'bg-slate-500'
                        }`}
                      />
                      <span className="text-xs text-slate-300 capitalize">{exec.status}</span>
                    </div>
                    <span className="text-xs text-slate-500">{exec.triggered_by}</span>
                  </div>
                ))}
                {executions.length === 0 && (
                  <p className="text-slate-500 text-sm text-center py-4">No executions yet</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

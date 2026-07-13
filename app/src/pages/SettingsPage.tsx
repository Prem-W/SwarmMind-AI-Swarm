import { useState } from 'react';
import { Settings, Shield, Key, Database, Bell, Save } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';

export default function SettingsPage() {
  const [settings, setSettings] = useState({
    humanApproval: true,
    autoRetry: true,
    notifications: true,
    darkMode: true,
    maxParallelAgents: 5,
    taskTimeout: 300,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-slate-400 mt-1">Configure platform behavior and preferences</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* General Settings */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Settings className="w-5 h-5 text-blue-400" />
              General
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-slate-300">Human Approval Mode</Label>
                <p className="text-xs text-slate-500">Require approval for critical tasks</p>
              </div>
              <Switch
                checked={settings.humanApproval}
                onCheckedChange={(v) => setSettings({ ...settings, humanApproval: v })}
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-slate-300">Auto Retry Failed Tasks</Label>
                <p className="text-xs text-slate-500">Automatically retry failed tasks up to 3 times</p>
              </div>
              <Switch
                checked={settings.autoRetry}
                onCheckedChange={(v) => setSettings({ ...settings, autoRetry: v })}
              />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-slate-300">Notifications</Label>
                <p className="text-xs text-slate-500">Enable push notifications</p>
              </div>
              <Switch
                checked={settings.notifications}
                onCheckedChange={(v) => setSettings({ ...settings, notifications: v })}
              />
            </div>
          </CardContent>
        </Card>

        {/* Security */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Shield className="w-5 h-5 text-green-400" />
              Security
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-slate-300">API Key Management</Label>
                <p className="text-xs text-slate-500">Manage API keys for external integrations</p>
              </div>
              <Button variant="outline" size="sm" className="border-slate-700 text-slate-300">
                <Key className="w-4 h-4 mr-2" />
                Manage
              </Button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-slate-300">Session Timeout</Label>
                <p className="text-xs text-slate-500">Auto logout after 30 minutes of inactivity</p>
              </div>
              <Switch defaultChecked />
            </div>
          </CardContent>
        </Card>

        {/* Advanced */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Database className="w-5 h-5 text-purple-400" />
              Advanced
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <Label className="text-slate-300">Max Parallel Agents</Label>
              <p className="text-xs text-slate-500 mb-2">Maximum number of agents running simultaneously</p>
              <input
                type="number"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm"
                value={settings.maxParallelAgents}
                onChange={(e) =>
                  setSettings({ ...settings, maxParallelAgents: parseInt(e.target.value) || 5 })
                }
              />
            </div>
            <div>
              <Label className="text-slate-300">Task Timeout (seconds)</Label>
              <p className="text-xs text-slate-500 mb-2">Maximum time for a task to complete</p>
              <input
                type="number"
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-white text-sm"
                value={settings.taskTimeout}
                onChange={(e) =>
                  setSettings({ ...settings, taskTimeout: parseInt(e.target.value) || 300 })
                }
              />
            </div>
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Bell className="w-5 h-5 text-amber-400" />
              Notifications
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-slate-300">Execution Alerts</Label>
                <p className="text-xs text-slate-500">Get notified when workflows complete or fail</p>
              </div>
              <Switch defaultChecked />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-slate-300">Agent Status Changes</Label>
                <p className="text-xs text-slate-500">Notifications when agents go offline or error</p>
              </div>
              <Switch defaultChecked />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex justify-end">
        <Button className="bg-blue-600 hover:bg-blue-700">
          <Save className="w-4 h-4 mr-2" />
          Save Settings
        </Button>
      </div>
    </div>
  );
}

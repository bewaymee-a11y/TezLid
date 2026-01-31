import { useState, useEffect } from "react";
import axios from "axios";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { CheckCircle2, XCircle, Clock, Zap, Trash2, Plus, TestTube } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const IntegrationsPage = () => {
  const [integrations, setIntegrations] = useState([]);
  const [webhookLogs, setWebhookLogs] = useState([]);
  const [apiKeys, setApiKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNewIntegration, setShowNewIntegration] = useState(false);
  const [showNewApiKey, setShowNewApiKey] = useState(false);

  // New integration form
  const [newIntegration, setNewIntegration] = useState({
    name: "",
    type: "webhook",
    endpoint: "",
    method: "POST",
    webhookUrl: "",
    headers: {}
  });

  // New API key form
  const [newApiKey, setNewApiKey] = useState({
    name: "",
    permissions: ["read"],
    rate_limit: 1000
  });

  const [generatedKey, setGeneratedKey] = useState(null);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [integrationsRes, logsRes, keysRes] = await Promise.all([
        axios.get(`${API}/crm/integrations`),
        axios.get(`${API}/crm/webhooks/logs?limit=50`),
        axios.get(`${API}/api-keys`)
      ]);
      
      setIntegrations(integrationsRes.data.integrations || []);
      setWebhookLogs(logsRes.data.logs || []);
      setApiKeys(keysRes.data.keys || []);
    } catch (error) {
      console.error("Error loading data:", error);
    }
    setLoading(false);
  };

  const createIntegration = async () => {
    try {
      const config = {};
      
      if (newIntegration.type === "webhook") {
        config.endpoint = newIntegration.endpoint;
        config.method = newIntegration.method;
        config.headers = newIntegration.headers;
      } else if (newIntegration.type === "bitrix24") {
        config.webhook_url = newIntegration.webhookUrl;
      }

      await axios.post(`${API}/crm/integrations`, {
        name: newIntegration.name,
        integration_type: newIntegration.type,
        config: config,
        events: ["lead.created", "lead.updated"]
      });

      setShowNewIntegration(false);
      setNewIntegration({ name: "", type: "webhook", endpoint: "", method: "POST", webhookUrl: "", headers: {} });
      loadData();
    } catch (error) {
      console.error("Error creating integration:", error);
      alert("Error creating integration");
    }
  };

  const deleteIntegration = async (id) => {
    if (!confirm("Delete this integration?")) return;
    
    try {
      await axios.delete(`${API}/crm/integrations/${id}`);
      loadData();
    } catch (error) {
      console.error("Error deleting integration:", error);
    }
  };

  const testIntegration = async (id) => {
    try {
      const result = await axios.post(`${API}/crm/integrations/${id}/test`);
      if (result.data.success) {
        alert("Test successful!");
      } else {
        alert(`Test failed: ${result.data.error}`);
      }
      loadData();
    } catch (error) {
      console.error("Error testing integration:", error);
      alert("Test failed");
    }
  };

  const createApiKeyHandler = async () => {
    try {
      const result = await axios.post(`${API}/api-keys`, newApiKey);
      setGeneratedKey(result.data.key);
      setShowNewApiKey(false);
      setNewApiKey({ name: "", permissions: ["read"], rate_limit: 1000 });
      loadData();
    } catch (error) {
      console.error("Error creating API key:", error);
      alert("Error creating API key");
    }
  };

  const revokeApiKey = async (keyHash) => {
    if (!confirm("Revoke this API key?")) return;
    
    try {
      await axios.delete(`${API}/api-keys/${keyHash}`);
      loadData();
    } catch (error) {
      console.error("Error revoking key:", error);
    }
  };

  const getStatusBadge = (status) => {
    const badges = {
      success: <Badge className="bg-green-500"><CheckCircle2 className="h-3 w-3 mr-1" /> Success</Badge>,
      failed: <Badge className="bg-red-500"><XCircle className="h-3 w-3 mr-1" /> Failed</Badge>,
      pending: <Badge className="bg-yellow-500"><Clock className="h-3 w-3 mr-1" /> Pending</Badge>
    };
    return badges[status] || <Badge>{status}</Badge>;
  };

  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <div>
          <h1 className="text-4xl font-bold text-slate-900">CRM Integrations</h1>
          <p className="text-slate-600 mt-1">Manage external CRM integrations and API access</p>
        </div>

        <Tabs defaultValue="integrations" className="space-y-4">
          <TabsList className="grid w-full grid-cols-3 max-w-md">
            <TabsTrigger value="integrations">Integrations</TabsTrigger>
            <TabsTrigger value="logs">Webhook Logs</TabsTrigger>
            <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          </TabsList>

          {/* Integrations Tab */}
          <TabsContent value="integrations" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold">Active Integrations</h2>
              <Button onClick={() => setShowNewIntegration(true)}>
                <Plus className="h-4 w-4 mr-2" /> New Integration
              </Button>
            </div>

            {showNewIntegration && (
              <Card>
                <CardHeader>
                  <CardTitle>Create New Integration</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label>Name</Label>
                    <Input
                      value={newIntegration.name}
                      onChange={(e) => setNewIntegration({ ...newIntegration, name: e.target.value })}
                      placeholder="My CRM Integration"
                    />
                  </div>

                  <div>
                    <Label>Type</Label>
                    <Select value={newIntegration.type} onValueChange={(val) => setNewIntegration({ ...newIntegration, type: val })}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="webhook">Custom Webhook</SelectItem>
                        <SelectItem value="amocrm">AmoCRM</SelectItem>
                        <SelectItem value="bitrix24">Bitrix24</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {newIntegration.type === "webhook" && (
                    <>
                      <div>
                        <Label>Webhook URL</Label>
                        <Input
                          value={newIntegration.endpoint}
                          onChange={(e) => setNewIntegration({ ...newIntegration, endpoint: e.target.value })}
                          placeholder="https://your-crm.com/webhook"
                        />
                      </div>
                      <div>
                        <Label>Method</Label>
                        <Select value={newIntegration.method} onValueChange={(val) => setNewIntegration({ ...newIntegration, method: val })}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="POST">POST</SelectItem>
                            <SelectItem value="PUT">PUT</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </>
                  )}

                  {newIntegration.type === "bitrix24" && (
                    <div>
                      <Label>Bitrix24 Webhook URL</Label>
                      <Input
                        value={newIntegration.webhookUrl}
                        onChange={(e) => setNewIntegration({ ...newIntegration, webhookUrl: e.target.value })}
                        placeholder="https://your-company.bitrix24.com/rest/..."
                      />
                    </div>
                  )}

                  <div className="flex gap-2">
                    <Button onClick={createIntegration}>Create</Button>
                    <Button variant="outline" onClick={() => setShowNewIntegration(false)}>Cancel</Button>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="grid gap-4">
              {integrations.map((integration) => (
                <Card key={integration.id}>
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle>{integration.name}</CardTitle>
                        <CardDescription>
                          <Badge className="mt-2">{integration.type}</Badge>
                        </CardDescription>
                      </div>
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline" onClick={() => testIntegration(integration.id)}>
                          <TestTube className="h-4 w-4 mr-1" /> Test
                        </Button>
                        <Button size="sm" variant="destructive" onClick={() => deleteIntegration(integration.id)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="text-sm">
                        <span className="text-slate-600">Status:</span>{" "}
                        <Badge className={integration.enabled ? "bg-green-500" : "bg-gray-500"}>
                          {integration.enabled ? "Enabled" : "Disabled"}
                        </Badge>
                      </div>
                      <div className="text-sm">
                        <span className="text-slate-600">Events:</span> {integration.events?.join(", ")}
                      </div>
                      {integration.last_sync && (
                        <div className="text-sm text-slate-600">
                          Last sync: {new Date(integration.last_sync).toLocaleString()}
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}

              {integrations.length === 0 && (
                <Card>
                  <CardContent className="py-12 text-center text-slate-500">
                    No integrations configured. Click "New Integration" to get started.
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          {/* Webhook Logs Tab */}
          <TabsContent value="logs">
            <Card>
              <CardHeader>
                <CardTitle>Webhook Delivery Logs</CardTitle>
                <CardDescription>Recent webhook delivery attempts</CardDescription>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-[600px]">
                  <div className="space-y-2">
                    {webhookLogs.map((log, idx) => (
                      <Card key={idx} className="p-4">
                        <div className="flex justify-between items-start">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              {getStatusBadge(log.status)}
                              <Badge variant="outline">{log.event}</Badge>
                            </div>
                            <div className="text-sm text-slate-600">
                              Integration: {log.integration_id}
                            </div>
                            <div className="text-sm text-slate-600">
                              Lead ID: {log.lead_id}
                            </div>
                            {log.error && (
                              <div className="text-sm text-red-600">
                                Error: {log.error}
                              </div>
                            )}
                          </div>
                          <div className="text-xs text-slate-500">
                            {new Date(log.timestamp).toLocaleString()}
                          </div>
                        </div>
                      </Card>
                    ))}

                    {webhookLogs.length === 0 && (
                      <div className="text-center py-12 text-slate-500">
                        No webhook logs yet
                      </div>
                    )}
                  </div>
                </ScrollArea>
              </CardContent>
            </Card>
          </TabsContent>

          {/* API Keys Tab */}
          <TabsContent value="api-keys" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold">API Keys</h2>
              <Button onClick={() => setShowNewApiKey(true)}>
                <Plus className="h-4 w-4 mr-2" /> Generate API Key
              </Button>
            </div>

            {generatedKey && (
              <Card className="border-green-500 bg-green-50">
                <CardHeader>
                  <CardTitle className="text-green-700">API Key Generated!</CardTitle>
                  <CardDescription>Copy this key now - it won't be shown again</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="bg-white p-3 rounded border border-green-200 font-mono text-sm break-all">
                    {generatedKey}
                  </div>
                  <Button
                    className="mt-4"
                    onClick={() => {
                      navigator.clipboard.writeText(generatedKey);
                      alert("Copied to clipboard!");
                    }}
                  >
                    Copy to Clipboard
                  </Button>
                  <Button variant="outline" className="mt-4 ml-2" onClick={() => setGeneratedKey(null)}>
                    Close
                  </Button>
                </CardContent>
              </Card>
            )}

            {showNewApiKey && (
              <Card>
                <CardHeader>
                  <CardTitle>Generate New API Key</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label>Name</Label>
                    <Input
                      value={newApiKey.name}
                      onChange={(e) => setNewApiKey({ ...newApiKey, name: e.target.value })}
                      placeholder="My Application"
                    />
                  </div>

                  <div>
                    <Label>Permissions</Label>
                    <Select 
                      value={newApiKey.permissions[0]} 
                      onValueChange={(val) => setNewApiKey({ ...newApiKey, permissions: [val] })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="read">Read Only</SelectItem>
                        <SelectItem value="write">Read & Write</SelectItem>
                        <SelectItem value="admin">Full Access</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Rate Limit (requests/hour)</Label>
                    <Input
                      type="number"
                      value={newApiKey.rate_limit}
                      onChange={(e) => setNewApiKey({ ...newApiKey, rate_limit: parseInt(e.target.value) })}
                    />
                  </div>

                  <div className="flex gap-2">
                    <Button onClick={createApiKeyHandler}>Generate</Button>
                    <Button variant="outline" onClick={() => setShowNewApiKey(false)}>Cancel</Button>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="grid gap-4">
              {apiKeys.map((key) => (
                <Card key={key.id}>
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle>{key.name}</CardTitle>
                        <CardDescription className="mt-2">
                          <Badge>{key.permissions?.join(", ")}</Badge>
                        </CardDescription>
                      </div>
                      <Button size="sm" variant="destructive" onClick={() => revokeApiKey(key.key_hash)}>
                        Revoke
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 text-sm">
                      <div>
                        <span className="text-slate-600">Rate Limit:</span> {key.rate_limit} req/hour
                      </div>
                      <div>
                        <span className="text-slate-600">Usage:</span> {key.usage_count || 0} requests
                      </div>
                      {key.last_used && (
                        <div>
                          <span className="text-slate-600">Last Used:</span>{" "}
                          {new Date(key.last_used).toLocaleString()}
                        </div>
                      )}
                      <div>
                        <span className="text-slate-600">Expires:</span>{" "}
                        {new Date(key.expires_at).toLocaleDateString()}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}

              {apiKeys.length === 0 && (
                <Card>
                  <CardContent className="py-12 text-center text-slate-500">
                    No API keys generated yet
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

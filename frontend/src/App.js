import { useState, useEffect } from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import axios from "axios";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Activity, TrendingUp, Clock, Users } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const LeadsDashboard = () => {
  const [leads, setLeads] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  const fetchLeads = async () => {
    try {
      const response = await axios.get(`${API}/leads`);
      setLeads(response.data);
    } catch (e) {
      console.error('Error fetching leads:', e);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/stats`);
      setStats(response.data);
    } catch (e) {
      console.error('Error fetching stats:', e);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchLeads(), fetchStats()]);
      setLoading(false);
    };
    loadData();
    
    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchLeads();
      fetchStats();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  const updateLeadStatus = async (leadId, newStatus) => {
    try {
      await axios.put(`${API}/leads/${leadId}/status?status=${newStatus}`);
      fetchLeads();
      fetchStats();
    } catch (e) {
      console.error('Error updating lead status:', e);
    }
  };

  const getLeadBadgeColor = (type) => {
    switch(type) {
      case 'hot': return 'bg-red-500 hover:bg-red-600';
      case 'warm': return 'bg-orange-500 hover:bg-orange-600';
      case 'cold': return 'bg-blue-500 hover:bg-blue-600';
      default: return 'bg-gray-500 hover:bg-gray-600';
    }
  };

  const getUrgencyBadgeColor = (urgency) => {
    switch(urgency) {
      case 'high': return 'bg-red-600 hover:bg-red-700';
      case 'medium': return 'bg-yellow-500 hover:bg-yellow-600';
      case 'low': return 'bg-green-500 hover:bg-green-600';
      default: return 'bg-gray-500 hover:bg-gray-600';
    }
  };

  const getStatusBadgeColor = (status) => {
    switch(status) {
      case 'new': return 'bg-blue-500 hover:bg-blue-600';
      case 'contacted': return 'bg-purple-500 hover:bg-purple-600';
      case 'converted': return 'bg-green-600 hover:bg-green-700';
      case 'rejected': return 'bg-gray-500 hover:bg-gray-600';
      default: return 'bg-gray-500 hover:bg-gray-600';
    }
  };

  const filteredLeads = leads.filter(lead => {
    if (filter === 'all') return true;
    return lead.lead_type === filter;
  });

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-xl">Загрузка...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-6" data-testid="leads-dashboard">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold text-slate-900" data-testid="dashboard-title">Панель лидов</h1>
            <p className="text-slate-600 mt-1">Автоматическая обработка через Telegram</p>
          </div>
          <Button onClick={() => { fetchLeads(); fetchStats(); }} data-testid="refresh-button">
            Обновить
          </Button>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card data-testid="stat-card-total">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Всего лидов</CardTitle>
                <Users className="h-4 w-4 text-slate-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stats.total}</div>
              </CardContent>
            </Card>
            
            <Card data-testid="stat-card-hot">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Горячие</CardTitle>
                <TrendingUp className="h-4 w-4 text-red-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">{stats.by_type.hot}</div>
              </CardContent>
            </Card>
            
            <Card data-testid="stat-card-high-urgency">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Срочные</CardTitle>
                <Clock className="h-4 w-4 text-orange-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-orange-600">{stats.high_urgency}</div>
              </CardContent>
            </Card>
            
            <Card data-testid="stat-card-new">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Новые</CardTitle>
                <Activity className="h-4 w-4 text-blue-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-600">{stats.new_leads}</div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Filter Tabs */}
        <Card data-testid="leads-section">
          <CardHeader>
            <div className="flex justify-between items-center">
              <div>
                <CardTitle>Список лидов</CardTitle>
                <CardDescription>Все входящие запросы от клиентов</CardDescription>
              </div>
              <Tabs value={filter} onValueChange={setFilter} data-testid="filter-tabs">
                <TabsList>
                  <TabsTrigger value="all" data-testid="filter-all">Все</TabsTrigger>
                  <TabsTrigger value="hot" data-testid="filter-hot">Горячие</TabsTrigger>
                  <TabsTrigger value="warm" data-testid="filter-warm">Тёплые</TabsTrigger>
                  <TabsTrigger value="cold" data-testid="filter-cold">Холодные</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[600px] pr-4">
              {filteredLeads.length === 0 ? (
                <div className="text-center py-12 text-slate-500" data-testid="no-leads-message">
                  Лиды не найдены
                </div>
              ) : (
                <div className="space-y-4">
                  {filteredLeads.map((lead) => (
                    <Card key={lead.id} className="hover:shadow-md transition-shadow" data-testid={`lead-card-${lead.id}`}>
                      <CardHeader>
                        <div className="flex justify-between items-start">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <CardTitle className="text-lg">{lead.first_name || 'Клиент'}</CardTitle>
                              {lead.username && (
                                <span className="text-sm text-slate-500" data-testid={`lead-username-${lead.id}`}>@{lead.username}</span>
                              )}
                            </div>
                            <CardDescription data-testid={`lead-date-${lead.id}`}>{formatDate(lead.timestamp)}</CardDescription>
                          </div>
                          <div className="flex flex-col gap-2 items-end">
                            <div className="flex gap-2">
                              <Badge className={getLeadBadgeColor(lead.lead_type)} data-testid={`lead-type-${lead.id}`}>
                                {lead.lead_type === 'hot' ? 'Горячий' : lead.lead_type === 'warm' ? 'Тёплый' : 'Холодный'}
                              </Badge>
                              <Badge className={getUrgencyBadgeColor(lead.urgency)} data-testid={`lead-urgency-${lead.id}`}>
                                {lead.urgency === 'high' ? 'Срочно' : lead.urgency === 'medium' ? 'Средне' : 'Низко'}
                              </Badge>
                            </div>
                            <Badge className={getStatusBadgeColor(lead.status)} data-testid={`lead-status-${lead.id}`}>
                              {lead.status === 'new' ? 'Новый' : lead.status === 'contacted' ? 'Связались' : lead.status === 'converted' ? 'Конверсия' : 'Отклонён'}
                            </Badge>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div>
                          <span className="text-sm font-medium text-slate-700">Услуга: </span>
                          <span className="text-sm text-slate-600" data-testid={`lead-service-${lead.id}`}>{lead.service}</span>
                        </div>
                        <div>
                          <span className="text-sm font-medium text-slate-700">Сообщение: </span>
                          <p className="text-sm text-slate-600 mt-1" data-testid={`lead-message-${lead.id}`}>{lead.message}</p>
                        </div>
                        <div>
                          <span className="text-sm font-medium text-slate-700">Chat ID: </span>
                          <span className="text-sm text-slate-600 font-mono" data-testid={`lead-chatid-${lead.id}`}>{lead.client_id}</span>
                        </div>
                        <div className="flex gap-2 pt-2">
                          <Select
                            value={lead.status}
                            onValueChange={(value) => updateLeadStatus(lead.id, value)}
                          >
                            <SelectTrigger className="w-[180px]" data-testid={`lead-status-select-${lead.id}`}>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="new">Новый</SelectItem>
                              <SelectItem value="contacted">Связались</SelectItem>
                              <SelectItem value="converted">Конверсия</SelectItem>
                              <SelectItem value="rejected">Отклонён</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LeadsDashboard />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
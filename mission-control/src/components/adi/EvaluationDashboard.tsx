import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { Play, TrendingUp, TrendingDown, Minus, AlertTriangle, CheckCircle, Clock } from 'lucide-react';

interface TrendPoint {
  timestamp: string;
  pass_rate: number;
  total_cases: number;
  pack_version: string;
  run_id: string;
}

interface FailingCase {
  case_id: string;
  failure_count: number;
  last_failure: string;
  failure_types: string[];
  pack_versions: string[];
  details: any;
}

interface DeploymentConfidence {
  confidence_score: number;
  pass_rate_trend: 'improving' | 'stable' | 'declining';
  recent_pass_rate: number;
  baseline_pass_rate: number;
  recommendation: 'deploy' | 'hold' | 'rollback';
  factors: string[];
}

interface EvalSet {
  id: string;
  name: string;
  created_at: string;
  case_count: number;
  result_count: number;
  latest_pass_rate: number | null;
  latest_run: string | null;
}

interface EvaluationDashboardData {
  project_id: string;
  eval_sets: EvalSet[];
  recent_results: any[];
  trend_analysis: TrendPoint[];
  failing_cases: FailingCase[];
  deployment_confidence: DeploymentConfidence;
  summary_stats: {
    total_eval_sets: number;
    total_runs: number;
    average_pass_rate: number;
    total_cases_evaluated: number;
    period_days: number;
  };
}

interface EvaluationDashboardProps {
  projectId: string;
}

export const EvaluationDashboard: React.FC<EvaluationDashboardProps> = ({ projectId }) => {
  const [dashboardData, setDashboardData] = useState<EvaluationDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedDays, setSelectedDays] = useState('30');
  const [selectedEvalSet, setSelectedEvalSet] = useState<string>('all');

  useEffect(() => {
    fetchDashboardData();
  }, [projectId, selectedDays]);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/adi/evaluation/analytics/dashboard?project_id=${projectId}&days=${selectedDays}`);
      if (response.ok) {
        const data = await response.json();
        setDashboardData(data);
      }
    } catch (error) {
      console.error('Error fetching evaluation dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const executeEvalSet = async (evalSetId: string) => {
    try {
      const response = await fetch(`/api/adi/evaluation/sets/${evalSetId}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ async: false })
      });
      
      if (response.ok) {
        // Refresh dashboard data
        fetchDashboardData();
      }
    } catch (error) {
      console.error('Error executing evaluation set:', error);
    }
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'improving':
        return <TrendingUp className="w-4 h-4 text-green-500" />;
      case 'declining':
        return <TrendingDown className="w-4 h-4 text-red-500" />;
      default:
        return <Minus className="w-4 h-4 text-gray-500" />;
    }
  };

  const getRecommendationColor = (recommendation: string) => {
    switch (recommendation) {
      case 'deploy':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'rollback':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    }
  };

  const formatPassRate = (rate: number) => `${(rate * 100).toFixed(1)}%`;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">No evaluation data available</p>
      </div>
    );
  }

  const { eval_sets, trend_analysis, failing_cases, deployment_confidence, summary_stats } = dashboardData;

  // Prepare chart data
  const chartData = trend_analysis.map(point => ({
    timestamp: new Date(point.timestamp).toLocaleDateString(),
    pass_rate: point.pass_rate * 100,
    total_cases: point.total_cases,
    pack_version: point.pack_version
  }));

  const failingCasesChartData = failing_cases.slice(0, 10).map(case_item => ({
    case_id: case_item.case_id.substring(0, 8) + '...',
    failure_count: case_item.failure_count
  }));

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Evaluation Dashboard</h2>
        <div className="flex gap-4">
          <Select value={selectedDays} onValueChange={setSelectedDays}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">7 days</SelectItem>
              <SelectItem value="14">14 days</SelectItem>
              <SelectItem value="30">30 days</SelectItem>
              <SelectItem value="60">60 days</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Eval Sets</p>
                <p className="text-2xl font-bold">{summary_stats.total_eval_sets}</p>
              </div>
              <CheckCircle className="w-8 h-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Runs</p>
                <p className="text-2xl font-bold">{summary_stats.total_runs}</p>
              </div>
              <Play className="w-8 h-8 text-green-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Avg Pass Rate</p>
                <p className="text-2xl font-bold">{formatPassRate(summary_stats.average_pass_rate)}</p>
              </div>
              {getTrendIcon(deployment_confidence.pass_rate_trend)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Cases Evaluated</p>
                <p className="text-2xl font-bold">{summary_stats.total_cases_evaluated.toLocaleString()}</p>
              </div>
              <Clock className="w-8 h-8 text-purple-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Deployment Confidence */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Deployment Confidence
            <Badge className={getRecommendationColor(deployment_confidence.recommendation)}>
              {deployment_confidence.recommendation.toUpperCase()}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-gray-600">Confidence Score</p>
              <div className="flex items-center gap-2">
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className="bg-blue-600 h-2 rounded-full" 
                    style={{ width: `${deployment_confidence.confidence_score * 100}%` }}
                  ></div>
                </div>
                <span className="text-sm font-medium">
                  {(deployment_confidence.confidence_score * 100).toFixed(0)}%
                </span>
              </div>
            </div>
            
            <div>
              <p className="text-sm text-gray-600">Recent Pass Rate</p>
              <p className="text-lg font-semibold">{formatPassRate(deployment_confidence.recent_pass_rate)}</p>
            </div>
            
            <div>
              <p className="text-sm text-gray-600">Trend</p>
              <div className="flex items-center gap-1">
                {getTrendIcon(deployment_confidence.pass_rate_trend)}
                <span className="capitalize">{deployment_confidence.pass_rate_trend}</span>
              </div>
            </div>
          </div>
          
          <div className="mt-4">
            <p className="text-sm text-gray-600 mb-2">Factors:</p>
            <div className="flex flex-wrap gap-2">
              {deployment_confidence.factors.map((factor, index) => (
                <Badge key={index} variant="outline" className="text-xs">
                  {factor}
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Trend Analysis Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Pass Rate Trends</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" />
                <YAxis domain={[0, 100]} />
                <Tooltip 
                  formatter={(value: any, name: string) => [
                    name === 'pass_rate' ? `${value.toFixed(1)}%` : value,
                    name === 'pass_rate' ? 'Pass Rate' : 'Total Cases'
                  ]}
                />
                <Line 
                  type="monotone" 
                  dataKey="pass_rate" 
                  stroke="#2563eb" 
                  strokeWidth={2}
                  dot={{ fill: '#2563eb' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Evaluation Sets */}
        <Card>
          <CardHeader>
            <CardTitle>Evaluation Sets</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {eval_sets.map((evalSet) => (
                <div key={evalSet.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div>
                    <p className="font-medium">{evalSet.name}</p>
                    <p className="text-sm text-gray-600">
                      {evalSet.case_count} cases • {evalSet.result_count} runs
                    </p>
                    {evalSet.latest_pass_rate !== null && (
                      <p className="text-sm">
                        Latest: {formatPassRate(evalSet.latest_pass_rate)}
                      </p>
                    )}
                  </div>
                  <Button
                    size="sm"
                    onClick={() => executeEvalSet(evalSet.id)}
                    className="flex items-center gap-1"
                  >
                    <Play className="w-3 h-3" />
                    Run
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Failing Cases */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              Most Problematic Cases
            </CardTitle>
          </CardHeader>
          <CardContent>
            {failing_cases.length > 0 ? (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={failingCasesChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="case_id" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="failure_count" fill="#ef4444" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">No failing cases found</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default EvaluationDashboard;
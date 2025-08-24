import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { CheckCircle, XCircle, Clock, AlertTriangle, Eye, Download } from 'lucide-react';

interface EvalCaseResult {
  case_id: string;
  passed: boolean;
  checks: Record<string, boolean>;
  errors: string[];
  execution_time_ms: number;
  details?: Record<string, any>;
}

interface EvalExecutionResult {
  run_id: string;
  eval_set_id: string;
  pass_rate: number;
  total_cases: number;
  passed_cases: number;
  failed_cases: string[];
  case_results: EvalCaseResult[];
  execution_time_ms: number;
  pack_version: string;
  errors: string[];
}

interface EvaluationResultsViewerProps {
  evalSetId: string;
  runId?: string;
}

export const EvaluationResultsViewer: React.FC<EvaluationResultsViewerProps> = ({ 
  evalSetId, 
  runId 
}) => {
  const [results, setResults] = useState<EvalExecutionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCase, setSelectedCase] = useState<EvalCaseResult | null>(null);
  const [filterStatus, setFilterStatus] = useState<'all' | 'passed' | 'failed'>('all');

  useEffect(() => {
    if (runId) {
      fetchRunResults();
    } else {
      fetchLatestResults();
    }
  }, [evalSetId, runId]);

  const fetchRunResults = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/adi/evaluation/runs/${runId}`);
      if (response.ok) {
        const data = await response.json();
        setResults(data);
      }
    } catch (error) {
      console.error('Error fetching run results:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchLatestResults = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/adi/evaluation/sets/${evalSetId}/results?limit=1`);
      if (response.ok) {
        const data = await response.json();
        if (data.results && data.results.length > 0) {
          // Fetch detailed results for the latest run
          const latestResult = data.results[0];
          const detailResponse = await fetch(`/api/adi/evaluation/runs/${latestResult.run_id}`);
          if (detailResponse.ok) {
            const detailData = await detailResponse.json();
            setResults(detailData);
          }
        }
      }
    } catch (error) {
      console.error('Error fetching latest results:', error);
    } finally {
      setLoading(false);
    }
  };

  const exportResults = () => {
    if (!results) return;
    
    const exportData = {
      run_id: results.run_id,
      eval_set_id: results.eval_set_id,
      pass_rate: results.pass_rate,
      total_cases: results.total_cases,
      passed_cases: results.passed_cases,
      failed_cases: results.failed_cases,
      pack_version: results.pack_version,
      case_results: results.case_results
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `eval_results_${results.run_id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getFilteredCases = () => {
    if (!results) return [];
    
    switch (filterStatus) {
      case 'passed':
        return results.case_results.filter(c => c.passed);
      case 'failed':
        return results.case_results.filter(c => !c.passed);
      default:
        return results.case_results;
    }
  };

  const getCheckIcon = (passed: boolean) => {
    return passed ? (
      <CheckCircle className="w-4 h-4 text-green-500" />
    ) : (
      <XCircle className="w-4 h-4 text-red-500" />
    );
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500">No evaluation results available</p>
      </div>
    );
  }

  const filteredCases = getFilteredCases();

  return (
    <div className="space-y-6">
      {/* Results Header */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-start">
            <div>
              <CardTitle className="flex items-center gap-2">
                Evaluation Results
                <Badge variant={results.pass_rate >= 0.8 ? "default" : "destructive"}>
                  {(results.pass_rate * 100).toFixed(1)}% Pass Rate
                </Badge>
              </CardTitle>
              <p className="text-sm text-gray-600 mt-1">
                Run ID: {results.run_id} • Pack Version: {results.pack_version}
              </p>
            </div>
            <Button onClick={exportResults} variant="outline" size="sm">
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">{results.passed_cases}</p>
              <p className="text-sm text-gray-600">Passed</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-red-600">{results.failed_cases.length}</p>
              <p className="text-sm text-gray-600">Failed</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{results.total_cases}</p>
              <p className="text-sm text-gray-600">Total Cases</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{formatDuration(results.execution_time_ms)}</p>
              <p className="text-sm text-gray-600">Execution Time</p>
            </div>
          </div>
          
          {results.errors.length > 0 && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 text-red-500" />
                <span className="font-medium text-red-800">Execution Errors</span>
              </div>
              <ul className="text-sm text-red-700 space-y-1">
                {results.errors.map((error, index) => (
                  <li key={index}>• {error}</li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Case Results */}
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>Case Results</CardTitle>
            <div className="flex gap-2">
              <Button
                variant={filterStatus === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterStatus('all')}
              >
                All ({results.case_results.length})
              </Button>
              <Button
                variant={filterStatus === 'passed' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterStatus('passed')}
              >
                Passed ({results.passed_cases})
              </Button>
              <Button
                variant={filterStatus === 'failed' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setFilterStatus('failed')}
              >
                Failed ({results.failed_cases.length})
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Case ID</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Checks</TableHead>
                <TableHead>Execution Time</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCases.map((caseResult) => (
                <TableRow key={caseResult.case_id}>
                  <TableCell className="font-mono text-sm">
                    {caseResult.case_id.substring(0, 12)}...
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {getCheckIcon(caseResult.passed)}
                      <span className={caseResult.passed ? 'text-green-700' : 'text-red-700'}>
                        {caseResult.passed ? 'Passed' : 'Failed'}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-wrap gap-1">
                      {Object.entries(caseResult.checks).map(([check, passed]) => (
                        <Badge
                          key={check}
                          variant={passed ? "default" : "destructive"}
                          className="text-xs"
                        >
                          {check}
                        </Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-gray-400" />
                      {formatDuration(caseResult.execution_time_ms)}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedCase(caseResult)}
                    >
                      <Eye className="w-4 h-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Case Detail Modal */}
      {selectedCase && (
        <Card className="fixed inset-4 z-50 bg-white shadow-2xl overflow-auto">
          <CardHeader>
            <div className="flex justify-between items-start">
              <div>
                <CardTitle className="flex items-center gap-2">
                  Case Details
                  {getCheckIcon(selectedCase.passed)}
                </CardTitle>
                <p className="text-sm text-gray-600 font-mono">{selectedCase.case_id}</p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedCase(null)}
              >
                ×
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="checks">
              <TabsList>
                <TabsTrigger value="checks">Checks</TabsTrigger>
                <TabsTrigger value="details">Details</TabsTrigger>
                {selectedCase.errors.length > 0 && (
                  <TabsTrigger value="errors">Errors</TabsTrigger>
                )}
              </TabsList>
              
              <TabsContent value="checks" className="space-y-4">
                <div className="grid gap-3">
                  {Object.entries(selectedCase.checks).map(([check, passed]) => (
                    <div key={check} className="flex items-center justify-between p-3 border rounded-lg">
                      <span className="font-medium">{check}</span>
                      <div className="flex items-center gap-2">
                        {getCheckIcon(passed)}
                        <span className={passed ? 'text-green-700' : 'text-red-700'}>
                          {passed ? 'Passed' : 'Failed'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </TabsContent>
              
              <TabsContent value="details">
                <pre className="bg-gray-50 p-4 rounded-lg text-sm overflow-auto">
                  {JSON.stringify(selectedCase.details, null, 2)}
                </pre>
              </TabsContent>
              
              {selectedCase.errors.length > 0 && (
                <TabsContent value="errors">
                  <div className="space-y-2">
                    {selectedCase.errors.map((error, index) => (
                      <div key={index} className="p-3 bg-red-50 border border-red-200 rounded-lg">
                        <p className="text-red-700 text-sm">{error}</p>
                      </div>
                    ))}
                  </div>
                </TabsContent>
              )}
            </Tabs>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default EvaluationResultsViewer;
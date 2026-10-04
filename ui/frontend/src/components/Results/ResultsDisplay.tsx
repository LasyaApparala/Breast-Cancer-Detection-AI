import React from 'react';
import { 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  TrendingUp, 
  Eye,
  Activity,
  Info
} from 'lucide-react';
import { PredictionResult } from '../../types';

interface ResultsDisplayProps {
  result: PredictionResult;
  onReviewRequired?: () => void;
}

export const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ 
  result, 
  onReviewRequired 
}) => {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'Low':
        return 'severity-low';
      case 'Moderate':
        return 'severity-moderate';
      case 'High':
        return 'severity-high';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'Low':
        return <CheckCircle className="h-6 w-6 text-green-600" />;
      case 'Moderate':
        return <AlertTriangle className="h-6 w-6 text-yellow-600" />;
      case 'High':
        return <XCircle className="h-6 w-6 text-red-600" />;
      default:
        return <Info className="h-6 w-6 text-gray-600" />;
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.9) return 'text-green-600';
    if (confidence >= 0.8) return 'text-yellow-600';
    return 'text-red-600';
  };

  const formatContribution = (value: number) => {
    const sign = value >= 0 ? '+' : '';
    return `${sign}${value.toFixed(1)}%`;
  };

  return (
    <div className="space-y-6">
      {/* Main Result Card */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4">
            {getSeverityIcon(result.severity)}
            <div>
              <h2 className="text-2xl font-bold text-gray-900">
                {result.severity} Severity
              </h2>
              {result.stage && (
                <p className="text-lg text-gray-600">Stage: {result.stage}</p>
              )}
            </div>
          </div>
          <div className={`px-4 py-2 rounded-lg border ${getSeverityColor(result.severity)}`}>
            <span className="font-semibold">{result.severity}</span>
          </div>
        </div>

        {/* Confidence Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <TrendingUp className="h-4 w-4 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">Confidence</span>
            </div>
            <div className={`text-2xl font-bold ${getConfidenceColor(result.confidence)}`}>
              {(result.confidence * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Model confidence in prediction
            </div>
          </div>

          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="flex items-center space-x-2 mb-2">
              <Activity className="h-4 w-4 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">Uncertainty</span>
            </div>
            <div className="text-2xl font-bold text-gray-700">
              ±{(result.uncertainty * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-500 mt-1">
              Prediction uncertainty range
            </div>
          </div>
        </div>

        {/* Clinician Review Alert */}
        {result.auditTrail.clinicianReviewRequired && (
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg mb-6">
            <div className="flex items-center space-x-3">
              <Eye className="h-5 w-5 text-amber-600" />
              <div>
                <p className="text-sm font-medium text-amber-800">
                  Clinician Review Required
                </p>
                <p className="text-xs text-amber-700">
                  This case requires review by a qualified healthcare professional before final diagnosis.
                </p>
              </div>
            </div>
            {onReviewRequired && (
              <button
                onClick={onReviewRequired}
                className="mt-3 btn-secondary text-sm"
              >
                Request Clinical Review
              </button>
            )}
          </div>
        )}

        {/* Feature Contributions */}
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Key Contributing Factors
          </h3>
          <div className="space-y-3">
            {result.featureContributions.map((feature, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center space-x-3">
                  <div className={`w-2 h-2 rounded-full ${
                    feature.importance === 'high' ? 'bg-red-500' :
                    feature.importance === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                  }`} />
                  <span className="text-sm font-medium text-gray-900">
                    {feature.feature}
                  </span>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`text-sm font-semibold ${
                    feature.contribution > 0 ? 'text-red-600' : 'text-green-600'
                  }`}>
                    {formatContribution(feature.contribution)}
                  </span>
                  <span className={`text-xs px-2 py-1 rounded ${
                    feature.importance === 'high' ? 'bg-red-100 text-red-800' :
                    feature.importance === 'medium' ? 'bg-yellow-100 text-yellow-800' : 
                    'bg-green-100 text-green-800'
                  }`}>
                    {feature.importance}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Image Heatmap */}
        {result.imageHeatmap && (
          <div className="mt-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              AI Attention Map
            </h3>
            <div className="bg-gray-100 rounded-lg p-4">
              <img 
                src={result.imageHeatmap} 
                alt="AI attention heatmap showing regions of interest"
                className="w-full rounded-lg shadow-sm"
              />
              <p className="text-xs text-gray-500 mt-2 text-center">
                Grad-CAM visualization showing regions that influenced the AI decision
              </p>
            </div>
          </div>
        )}

        {/* Audit Trail */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h3 className="text-sm font-medium text-gray-700 mb-3">Audit Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
            <div>
              <span className="text-gray-500">Analysis Time:</span>
              <p className="text-gray-900">
                {new Date(result.auditTrail.timestamp).toLocaleString()}
              </p>
            </div>
            <div>
              <span className="text-gray-500">Model Version:</span>
              <p className="text-gray-900">{result.auditTrail.modelVersion}</p>
            </div>
            <div>
              <span className="text-gray-500">Input Hash:</span>
              <p className="text-gray-900 font-mono">
                {result.auditTrail.inputHash.substring(0, 12)}...
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <Info className="h-5 w-5 text-blue-600 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-blue-800">
              Medical Disclaimer
            </p>
            <p className="text-xs text-blue-700 mt-1">
              This AI-powered analysis is a decision support tool and should not replace professional medical judgment. 
              Always consult with qualified healthcare providers for diagnosis and treatment decisions.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

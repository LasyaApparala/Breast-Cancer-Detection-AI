import React, { useState } from 'react';
import { Header } from '../components/Layout/Header';
import { FileUpload } from '../components/Upload/FileUpload';
import { ClinicalDataForm } from '../components/Forms/ClinicalDataForm';
import { ResultsDisplay } from '../components/Results/ResultsDisplay';
import { UploadedFile, ClinicalData, PredictionResult } from '../types';
import { useAppStore } from '../store/useAppStore';

export const Dashboard: React.FC = () => {
  const { user, addAnalysis, setLoading, setError } = useAppStore();
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [clinicalData, setClinicalData] = useState<ClinicalData | null>(null);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentStep, setCurrentStep] = useState<'upload' | 'clinical' | 'results'>('upload');

  const handleFilesChange = (files: UploadedFile[]) => {
    setUploadedFiles(files);
  };

  const handleClinicalDataSubmit = async (data: ClinicalData) => {
    if (uploadedFiles.length === 0) {
      setError('Please upload at least one medical document before proceeding.');
      return;
    }

    setIsAnalyzing(true);
    setLoading(true);

    try {
      // Simulate API call for analysis
      const mockResult: PredictionResult = {
        id: Math.random().toString(36).substr(2, 9),
        severity: data.tumorSize > 3 || data.tumorGrade === 3 ? 'High' : 
                data.tumorSize > 1.5 || data.tumorGrade === 2 ? 'Moderate' : 'Low',
        confidence: 0.85 + Math.random() * 0.1,
        uncertainty: 0.05 + Math.random() * 0.05,
        stage: data.distantMetastasis ? 'Stage IV' :
               data.lymphNodeInvolvement ? 'Stage III' :
               data.tumorSize > 2 ? 'Stage II' : 'Stage I',
        featureContributions: [
          {
            feature: 'Tumor Size',
            contribution: data.tumorSize > 2 ? 15.2 : -8.5,
            importance: 'high'
          },
          {
            feature: 'Tumor Grade',
            contribution: data.tumorGrade === 3 ? 18.7 : data.tumorGrade === 2 ? 8.3 : -5.2,
            importance: 'high'
          },
          {
            feature: 'HER2 Status',
            contribution: data.her2Status === 'positive' ? 12.1 : -3.4,
            importance: 'medium'
          },
          {
            feature: 'Lymph Node Involvement',
            contribution: data.lymphNodeInvolvement ? 22.8 : -10.6,
            importance: 'high'
          },
          {
            feature: 'ER Status',
            contribution: data.erStatus === 'positive' ? -6.2 : 4.1,
            importance: 'medium'
          }
        ],
        auditTrail: {
          timestamp: new Date().toISOString(),
          modelVersion: 'BreastGuard-AI-v2.1.0',
          inputHash: Math.random().toString(36).substr(2, 16),
          clinicianReviewRequired: data.tumorGrade === 3 || data.distantMetastasis
        }
      };

      // Simulate processing delay
      await new Promise(resolve => setTimeout(resolve, 3000));

      setResult(mockResult);
      setClinicalData(data);
      setCurrentStep('results');

      // Add to analysis history
      addAnalysis({
        id: mockResult.id,
        patientId: 'current-patient',
        clinicalData: data,
        files: uploadedFiles,
        result: mockResult,
        status: mockResult.auditTrail.clinicianReviewRequired ? 'requires_review' : 'completed',
        createdAt: new Date().toISOString(),
        completedAt: new Date().toISOString()
      });

    } catch (error) {
      setError('Analysis failed. Please try again.');
    } finally {
      setIsAnalyzing(false);
      setLoading(false);
    }
  };

  const handleRequestReview = () => {
    // In a real app, this would send a notification to clinicians
    alert('Clinical review request has been sent to the medical team.');
  };

  const handleReset = () => {
    setUploadedFiles([]);
    setClinicalData(null);
    setResult(null);
    setCurrentStep('upload');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-white">
      <Header />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Progress Steps */}
        <div className="mb-8">
          <div className="flex items-center justify-center space-x-4">
            {[
              { step: 'upload', label: 'Upload Documents', icon: '📁' },
              { step: 'clinical', label: 'Clinical Data', icon: '📋' },
              { step: 'results', label: 'Analysis Results', icon: '📊' }
            ].map((item, index) => (
              <div key={item.step} className="flex items-center">
                <div className={`flex items-center space-x-2 px-4 py-2 rounded-lg ${
                  currentStep === item.step 
                    ? 'bg-primary-600 text-white' 
                    : currentStep === 'results' || 
                      (currentStep === 'clinical' && item.step === 'upload')
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-gray-100 text-gray-600'
                }`}>
                  <span className="text-lg">{item.icon}</span>
                  <span className="font-medium">{item.label}</span>
                </div>
                {index < 2 && (
                  <div className={`w-8 h-0.5 ${
                    currentStep === 'results' || 
                    (currentStep === 'clinical' && item.step === 'upload')
                    ? 'bg-green-400' : 'bg-gray-300'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Step Content */}
        <div className="animate-fade-in">
          {currentStep === 'upload' && (
            <div className="space-y-6">
              <div className="text-center mb-8">
                <h1 className="text-3xl font-bold text-gray-900 mb-4">
                  Upload Medical Documents
                </h1>
                <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                  Please upload mammograms, ultrasounds, MRI scans, pathology reports, 
                  or other relevant medical documents for analysis.
                </p>
              </div>
              
              <div className="max-w-3xl mx-auto">
                <FileUpload 
                  onFilesChange={handleFilesChange}
                  acceptedTypes={['image/*', '.pdf', '.doc', '.docx', '.dicom']}
                  maxFiles={10}
                />
              </div>

              {uploadedFiles.length > 0 && (
                <div className="text-center mt-8">
                  <button
                    onClick={() => setCurrentStep('clinical')}
                    className="btn-primary text-lg px-8 py-3"
                  >
                    Continue to Clinical Data ({uploadedFiles.length} files uploaded)
                  </button>
                </div>
              )}
            </div>
          )}

          {currentStep === 'clinical' && (
            <div className="space-y-6">
              <div className="text-center mb-8">
                <h1 className="text-3xl font-bold text-gray-900 mb-4">
                  Enter Clinical Information
                </h1>
                <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                  Please provide the clinical data to help our AI models make an accurate assessment.
                </p>
              </div>

              <div className="max-w-4xl mx-auto">
                <ClinicalDataForm
                  onSubmit={handleClinicalDataSubmit}
                  isLoading={isAnalyzing}
                />
              </div>
            </div>
          )}

          {currentStep === 'results' && result && (
            <div className="space-y-6">
              <div className="text-center mb-8">
                <h1 className="text-3xl font-bold text-gray-900 mb-4">
                  Analysis Complete
                </h1>
                <p className="text-lg text-gray-600">
                  AI-powered breast tumor severity assessment results
                </p>
              </div>

              <ResultsDisplay 
                result={result} 
                onReviewRequired={handleRequestReview}
              />

              <div className="text-center space-x-4">
                <button
                  onClick={handleReset}
                  className="btn-secondary"
                >
                  Start New Analysis
                </button>
                <button
                  onClick={() => window.print()}
                  className="btn-primary"
                >
                  Download Report
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Loading Overlay */}
        {isAnalyzing && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-8 max-w-md text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                Analyzing Medical Data
              </h3>
              <p className="text-gray-600">
                Our AI models are processing your documents and clinical data...
              </p>
              <div className="mt-4 space-y-2 text-sm text-gray-500">
                <p>✓ Image analysis with EfficientNet-B4</p>
                <p>✓ Clinical data processing with XGBoost</p>
                <p>✓ Report analysis with BioBERT</p>
                <p>✓ Ensemble fusion and uncertainty quantification</p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

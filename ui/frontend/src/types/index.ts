export interface Patient {
  id: string;
  name: string;
  age: number;
  patientId: string;
  createdAt: string;
}

export interface ClinicalData {
  tumorSize: number;
  tumorGrade: 1 | 2 | 3;
  erStatus: 'positive' | 'negative' | 'unknown';
  prStatus: 'positive' | 'negative' | 'unknown';
  her2Status: 'positive' | 'negative' | 'unknown';
  ki67Index?: number;
  lymphNodeInvolvement: boolean;
  distantMetastasis: boolean;
  biRadsScore?: number;
}

export interface UploadedFile {
  id: string;
  name: string;
  type: 'mammogram' | 'ultrasound' | 'mri' | 'pathology' | 'report';
  size: number;
  uploadedAt: string;
  url: string;
}

export interface PredictionResult {
  id: string;
  severity: 'Low' | 'Moderate' | 'High';
  confidence: number;
  uncertainty: number;
  stage?: 'Benign' | 'Stage I' | 'Stage II' | 'Stage III' | 'Stage IV';
  featureContributions: {
    feature: string;
    contribution: number;
    importance: 'high' | 'medium' | 'low';
  }[];
  imageHeatmap?: string;
  auditTrail: {
    timestamp: string;
    modelVersion: string;
    inputHash: string;
    clinicianReviewRequired: boolean;
  };
}

export interface Analysis {
  id: string;
  patientId: string;
  clinicalData: ClinicalData;
  files: UploadedFile[];
  result: PredictionResult;
  status: 'pending' | 'processing' | 'completed' | 'requires_review';
  createdAt: string;
  completedAt?: string;
  reviewedBy?: string;
  reviewedAt?: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  role: 'clinician' | 'admin' | 'researcher';
  department?: string;
  licenseNumber?: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

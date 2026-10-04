import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { ClinicalData } from '../../types';

const clinicalDataSchema = z.object({
  tumorSize: z.number().min(0.1).max(20),
  tumorGrade: z.enum(['1', '2', '3']).transform(Number),
  erStatus: z.enum(['positive', 'negative', 'unknown']),
  prStatus: z.enum(['positive', 'negative', 'unknown']),
  her2Status: z.enum(['positive', 'negative', 'unknown']),
  ki67Index: z.number().min(0).max(100).optional(),
  lymphNodeInvolvement: z.boolean(),
  distantMetastasis: z.boolean(),
  biRadsScore: z.number().min(1).max(6).optional(),
});

interface ClinicalDataFormProps {
  onSubmit: (data: ClinicalData) => void;
  initialData?: Partial<ClinicalData>;
  isLoading?: boolean;
}

export const ClinicalDataForm: React.FC<ClinicalDataFormProps> = ({
  onSubmit,
  initialData,
  isLoading = false,
}) => {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<ClinicalData>({
    resolver: zodResolver(clinicalDataSchema),
    defaultValues: initialData,
  });

  const distantMetastasis = watch('distantMetastasis');

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tumor Size (cm)
          </label>
          <input
            type="number"
            step="0.1"
            {...register('tumorSize', { valueAsNumber: true })}
            className="input-field"
            placeholder="e.g., 2.5"
          />
          {errors.tumorSize && (
            <p className="text-red-500 text-sm mt-1">{errors.tumorSize.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Tumor Grade
          </label>
          <select {...register('tumorGrade')} className="input-field">
            <option value="">Select grade</option>
            <option value="1">Grade 1 (Well differentiated)</option>
            <option value="2">Grade 2 (Moderately differentiated)</option>
            <option value="3">Grade 3 (Poorly differentiated)</option>
          </select>
          {errors.tumorGrade && (
            <p className="text-red-500 text-sm mt-1">{errors.tumorGrade.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            ER Status
          </label>
          <select {...register('erStatus')} className="input-field">
            <option value="unknown">Unknown</option>
            <option value="positive">Positive</option>
            <option value="negative">Negative</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            PR Status
          </label>
          <select {...register('prStatus')} className="input-field">
            <option value="unknown">Unknown</option>
            <option value="positive">Positive</option>
            <option value="negative">Negative</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            HER2 Status
          </label>
          <select {...register('her2Status')} className="input-field">
            <option value="unknown">Unknown</option>
            <option value="positive">Positive</option>
            <option value="negative">Negative</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Ki-67 Index (%)
          </label>
          <input
            type="number"
            step="0.1"
            {...register('ki67Index', { valueAsNumber: true })}
            className="input-field"
            placeholder="e.g., 15.5"
          />
          <p className="text-gray-500 text-xs mt-1">Optional: Cell proliferation marker</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            BI-RADS Score
          </label>
          <select {...register('biRadsScore', { valueAsNumber: true })} className="input-field">
            <option value="">Not assessed</option>
            <option value="1">1 - Negative</option>
            <option value="2">2 - Benign</option>
            <option value="3">3 - Probably benign</option>
            <option value="4">4 - Suspicious</option>
            <option value="5">5 - Highly suggestive of malignancy</option>
            <option value="6">6 - Known biopsy proven malignancy</option>
          </select>
        </div>

        <div className="md:col-span-2">
          <label className="flex items-center space-x-3">
            <input
              type="checkbox"
              {...register('lymphNodeInvolvement')}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <span className="text-sm font-medium text-gray-700">
              Lymph Node Involvement
            </span>
          </label>
          <p className="text-gray-500 text-xs mt-1 ml-7">
            Cancer cells found in nearby lymph nodes
          </p>
        </div>

        <div className="md:col-span-2">
          <label className="flex items-center space-x-3">
            <input
              type="checkbox"
              {...register('distantMetastasis')}
              className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
            />
            <span className="text-sm font-medium text-gray-700">
              Distant Metastasis
            </span>
          </label>
          <p className="text-gray-500 text-xs mt-1 ml-7">
            Cancer has spread to distant organs (Stage IV)
          </p>
        </div>
      </div>

      {distantMetastasis && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-800">
            <strong>Warning:</strong> Distant metastasis indicates Stage IV cancer. 
            This requires immediate specialist consultation and comprehensive treatment planning.
          </p>
        </div>
      )}

      <div className="flex justify-end space-x-3">
        <button
          type="button"
          className="btn-secondary"
          onClick={() => window.history.back()}
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isLoading}
          className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Processing...' : 'Analyze Tumor'}
        </button>
      </div>
    </form>
  );
};

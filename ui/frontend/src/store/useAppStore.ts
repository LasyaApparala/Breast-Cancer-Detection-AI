import { create } from 'zustand';
import { Patient, Analysis, User } from '../types';

interface AppState {
  user: User | null;
  currentPatient: Patient | null;
  analyses: Analysis[];
  currentAnalysis: Analysis | null;
  isLoading: boolean;
  error: string | null;
}

interface AppActions {
  setUser: (user: User | null) => void;
  setCurrentPatient: (patient: Patient | null) => void;
  setAnalyses: (analyses: Analysis[]) => void;
  addAnalysis: (analysis: Analysis) => void;
  setCurrentAnalysis: (analysis: Analysis | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
}

export const useAppStore = create<AppState & AppActions>((set, get) => ({
  user: null,
  currentPatient: null,
  analyses: [],
  currentAnalysis: null,
  isLoading: false,
  error: null,

  setUser: (user) => set({ user }),
  
  setCurrentPatient: (patient) => set({ currentPatient: patient }),
  
  setAnalyses: (analyses) => set({ analyses }),
  
  addAnalysis: (analysis) => set((state) => ({ 
    analyses: [analysis, ...state.analyses] 
  })),
  
  setCurrentAnalysis: (analysis) => set({ currentAnalysis: analysis }),
  
  setLoading: (loading) => set({ isLoading: loading }),
  
  setError: (error) => set({ error }),
  
  clearError: () => set({ error: null }),
}));

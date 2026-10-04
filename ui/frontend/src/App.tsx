import React from 'react';
import { Dashboard } from './pages/Dashboard';
import { useAppStore } from './store/useAppStore';
import './index.css';

function App() {
  const { user } = useAppStore();

  // Mock user for demo - in real app, this would come from authentication
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-white flex items-center justify-center">
        <div className="text-center">
          <div className="mb-8">
            <div className="h-16 w-16 bg-primary-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-white text-2xl font-bold">BG</span>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">BreastGuard AI</h1>
            <p className="text-lg text-gray-600">Clinical Decision Support System</p>
          </div>
          
          <div className="bg-white rounded-xl shadow-lg p-8 max-w-md mx-auto">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Medical Professional Login</h2>
            <p className="text-gray-600 mb-6">
              Access is restricted to licensed healthcare providers and medical researchers.
            </p>
            <button 
              onClick={() => {
                // Mock authentication
                useAppStore.setState({
                  user: {
                    id: 'demo-user',
                    email: 'demo@breastguard.ai',
                    name: 'Dr. Sarah Johnson',
                    role: 'clinician',
                    department: 'Oncology',
                    licenseNumber: 'MD123456'
                  }
                });
              }}
              className="w-full btn-primary text-lg py-3"
            >
              Demo Access (Development)
            </button>
            <p className="text-xs text-gray-500 mt-4">
              This is a development demo. Production requires proper authentication.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return <Dashboard />;
}

export default App;

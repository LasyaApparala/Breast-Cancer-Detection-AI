import React from 'react';
import { Brain, Stethoscope, User, LogOut } from 'lucide-react';
import { useAppStore } from '../../store/useAppStore';

export const Header: React.FC = () => {
  const { user, setUser } = useAppStore();

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('token');
  };

  return (
    <header className="bg-white shadow-sm border-b border-blue-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-3">
            <Brain className="h-8 w-8 text-primary-600" />
            <div>
              <h1 className="text-xl font-bold text-gray-900">BreastGuard AI</h1>
              <p className="text-xs text-gray-500">Clinical Decision Support System</p>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2 text-sm text-gray-600">
              <Stethoscope className="h-4 w-4" />
              <span>{user?.role === 'clinician' ? 'Dr. ' : ''}{user?.name}</span>
              {user?.department && <span className="text-gray-400">• {user.department}</span>}
            </div>
            
            <div className="flex items-center space-x-2">
              <div className="h-8 w-8 rounded-full bg-primary-100 flex items-center justify-center">
                <User className="h-4 w-4 text-primary-600" />
              </div>
              <button
                onClick={handleLogout}
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                title="Logout"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

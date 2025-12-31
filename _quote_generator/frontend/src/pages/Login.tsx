import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { FileText, Code } from 'lucide-react'
import api from '../services/api'

export default function Login() {
  const { user, login, isLoading, refetch } = useAuth()
  const navigate = useNavigate()
  const [devLoading, setDevLoading] = useState(false)

  useEffect(() => {
    if (user) {
      navigate('/', { replace: true })
    }
  }, [user, navigate])

  const handleDevLogin = async () => {
    setDevLoading(true)
    try {
      await api.post('/auth/dev-login')
      // Refetch user to update auth state
      await refetch()
      navigate('/', { replace: true })
    } catch (error) {
      console.error('Dev login failed:', error)
      alert('Dev login failed. Make sure the backend is running in development mode.')
    } finally {
      setDevLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <div className="mx-auto h-16 w-16 bg-primary-100 rounded-full flex items-center justify-center">
            <FileText className="h-8 w-8 text-primary-600" />
          </div>
          <h2 className="mt-6 text-3xl font-bold text-gray-900">Quote Generator</h2>
          <p className="mt-2 text-sm text-gray-600">
            Generate professional quotes and order forms
          </p>
        </div>

        <div className="mt-8 space-y-4">
          <button
            onClick={login}
            className="group relative w-full flex justify-center py-3 px-4 border border-gray-300 rounded-md shadow-sm bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
              <path
                fill="currentColor"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="currentColor"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="currentColor"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="currentColor"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Sign in with Google
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-gray-50 text-gray-500">Development only</span>
            </div>
          </div>

          <button
            onClick={handleDevLogin}
            disabled={devLoading}
            className="group relative w-full flex justify-center py-3 px-4 border border-orange-300 rounded-md shadow-sm bg-orange-50 text-sm font-medium text-orange-700 hover:bg-orange-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-orange-500 disabled:opacity-50"
          >
            <Code className="w-5 h-5 mr-2" />
            {devLoading ? 'Logging in...' : 'Dev Login (Test User)'}
          </button>

          <p className="text-center text-xs text-gray-500">
            By signing in, you agree to our Terms of Service and Privacy Policy
          </p>
        </div>
      </div>
    </div>
  )
}

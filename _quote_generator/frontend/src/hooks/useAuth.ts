import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { auth } from '../services/api'
import type { User } from '../types'

export function useAuth() {
  const queryClient = useQueryClient()

  const { data: user, isLoading, error, refetch } = useQuery<User>({
    queryKey: ['auth', 'me'],
    queryFn: auth.getCurrentUser,
    retry: false,
    staleTime: 1000 * 60 * 5, // 5 minutes
  })

  const logoutMutation = useMutation({
    mutationFn: auth.logout,
    onSuccess: () => {
      queryClient.setQueryData(['auth', 'me'], null)
      queryClient.clear()
      window.location.href = '/login'
    },
  })

  const login = async () => {
    const authUrl = await auth.getGoogleAuthUrl()
    window.location.href = authUrl
  }

  return {
    user,
    isLoading,
    error,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
    login,
    logout: logoutMutation.mutate,
    refetch,
  }
}

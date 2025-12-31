import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { users } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import { Shield, User } from 'lucide-react'

export default function Settings() {
  const { user, isAdmin } = useAuth()
  const queryClient = useQueryClient()

  const { data: usersData, isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: users.list,
    enabled: isAdmin,
  })

  const updateRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: 'admin' | 'user' }) =>
      users.updateRole(userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-500">Manage your account and team settings</p>
      </div>

      {/* Profile */}
      <div className="card">
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-medium text-gray-900">Your Profile</h2>
        </div>
        <div className="p-6">
          <div className="flex items-center gap-4">
            {user?.picture_url ? (
              <img src={user.picture_url} alt="" className="w-16 h-16 rounded-full" />
            ) : (
              <div className="w-16 h-16 bg-primary-100 rounded-full flex items-center justify-center">
                <span className="text-primary-700 text-xl font-medium">
                  {user?.name?.[0] || user?.email?.[0] || '?'}
                </span>
              </div>
            )}
            <div>
              <p className="text-lg font-medium text-gray-900">{user?.name || 'No name set'}</p>
              <p className="text-sm text-gray-500">{user?.email}</p>
              <span
                className={`inline-flex items-center gap-1 mt-1 px-2 py-1 text-xs font-medium rounded-full ${
                  user?.role === 'admin'
                    ? 'bg-purple-100 text-purple-800'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                {user?.role === 'admin' ? (
                  <Shield className="w-3 h-3" />
                ) : (
                  <User className="w-3 h-3" />
                )}
                {user?.role}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Team Management (Admin only) */}
      {isAdmin && (
        <div className="card">
          <div className="px-6 py-4 border-b">
            <h2 className="text-lg font-medium text-gray-900">Team Members</h2>
          </div>
          <div className="divide-y divide-gray-200">
            {isLoading ? (
              <div className="p-6 text-center text-gray-500">Loading...</div>
            ) : usersData?.users.length === 0 ? (
              <div className="p-6 text-center text-gray-500">No team members found</div>
            ) : (
              usersData?.users.map((teamUser) => (
                <div key={teamUser.id} className="px-6 py-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {teamUser.picture_url ? (
                      <img
                        src={teamUser.picture_url}
                        alt=""
                        className="w-10 h-10 rounded-full"
                      />
                    ) : (
                      <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                        <span className="text-gray-600 text-sm font-medium">
                          {teamUser.name?.[0] || teamUser.email?.[0] || '?'}
                        </span>
                      </div>
                    )}
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {teamUser.name || teamUser.email}
                      </p>
                      <p className="text-xs text-gray-500">{teamUser.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <select
                      value={teamUser.role}
                      onChange={(e) =>
                        updateRoleMutation.mutate({
                          userId: teamUser.id,
                          role: e.target.value as 'admin' | 'user',
                        })
                      }
                      disabled={teamUser.id === user?.id || updateRoleMutation.isPending}
                      className="input text-sm py-1"
                    >
                      <option value="user">User</option>
                      <option value="admin">Admin</option>
                    </select>
                    <span
                      className={`px-2 py-1 text-xs rounded-full ${
                        teamUser.is_active
                          ? 'bg-green-100 text-green-800'
                          : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {teamUser.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Google Integration Status */}
      <div className="card">
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-medium text-gray-900">Google Integration</h2>
        </div>
        <div className="p-6">
          <div className="flex items-center gap-3">
            <div
              className={`w-3 h-3 rounded-full ${
                user?.has_google_tokens ? 'bg-green-500' : 'bg-yellow-500'
              }`}
            />
            <span className="text-sm text-gray-700">
              {user?.has_google_tokens
                ? 'Connected - Google Drive and Gmail integration is active'
                : 'Not connected - Sign out and sign back in to enable Google integration'}
            </span>
          </div>
        </div>
      </div>

      {/* App Info */}
      <div className="card">
        <div className="px-6 py-4 border-b">
          <h2 className="text-lg font-medium text-gray-900">About</h2>
        </div>
        <div className="p-6 text-sm text-gray-600">
          <p>Quote Generator v1.0.0</p>
          <p className="mt-1">A tool for generating professional quotes and order forms.</p>
        </div>
      </div>
    </div>
  )
}

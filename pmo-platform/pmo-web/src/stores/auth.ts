import { create } from 'zustand'

interface UserInfo {
  id: number
  employee_no: string
  name: string
  email: string
  dept_id: number | null
  title: string
  roles: string[]
}

interface AuthState {
  token: string | null
  user: UserInfo | null
  setAuth: (token: string, user: UserInfo) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('pmo_token'),
  user: JSON.parse(localStorage.getItem('pmo_user') || 'null'),
  setAuth: (token, user) => {
    localStorage.setItem('pmo_token', token)
    localStorage.setItem('pmo_user', JSON.stringify(user))
    set({ token, user })
  },
  logout: () => {
    localStorage.removeItem('pmo_token')
    localStorage.removeItem('pmo_user')
    set({ token: null, user: null })
  },
}))

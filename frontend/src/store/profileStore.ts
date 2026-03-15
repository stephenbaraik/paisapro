import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UserFinancialProfile } from '../types'

interface ProfileStore {
  profile: UserFinancialProfile | null
  setProfile: (p: UserFinancialProfile) => void
  clearProfile: () => void
}

export const useProfileStore = create<ProfileStore>()(
  persist(
    (set) => ({
      profile: null,
      setProfile: (profile) => set({ profile }),
      clearProfile: () => set({ profile: null }),
    }),
    { name: 'user-profile' }
  )
)

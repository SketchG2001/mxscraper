import { useContext } from 'react'
import { AppAuthContext, type AppAuthValue } from '../contexts/AppAuthContext'

export function useAppAuth(): AppAuthValue {
  return useContext(AppAuthContext)
}

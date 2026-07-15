import { createContext, useContext, useState, useCallback } from 'react'
import { loadJSON, saveJSON, STORAGE_KEYS } from './storage.js'
import { getExerciseById, DEFAULT_EXERCISE } from '../exercises.js'

/* 선택한 운동 전역 상태 (localStorage 영속).
   운동 선택 화면에서 고른 운동을 앱 전역(운동 홈/카메라/실시간)에 흘린다.
   기존에는 dummy.js의 exercise(스쿼트 하드코딩)를 직접 import 했는데, 그 자리를
   이 Context로 대체한다.

   저장은 id만 한다(운동 목록은 코드에 있으므로). 새로고침/재진입해도 선택 유지. */
const ExerciseContext = createContext(null)

export function ExerciseProvider({ children }) {
  const [exerciseId, setExerciseId] = useState(() =>
    loadJSON(STORAGE_KEYS.exercise, null),
  )

  const selectExercise = useCallback((id) => {
    setExerciseId(id)
    saveJSON(STORAGE_KEYS.exercise, id)
  }, [])

  // 선택한 운동 객체(없으면 기본 운동 = 스쿼트로 폴백)
  const exercise = getExerciseById(exerciseId) ?? DEFAULT_EXERCISE

  return (
    <ExerciseContext.Provider
      value={{ exercise, exerciseId, selectExercise }}
    >
      {children}
    </ExerciseContext.Provider>
  )
}

export function useExercise() {
  const ctx = useContext(ExerciseContext)
  if (!ctx) throw new Error('useExercise must be used within ExerciseProvider')
  return ctx
}

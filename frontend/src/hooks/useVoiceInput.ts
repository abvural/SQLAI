import { useState, useEffect, useCallback, useRef } from 'react'

interface VoiceInputState {
  isListening: boolean
  transcript: string
  interimTranscript: string
  error: string | null
  confidence: number
  isSupported: boolean
}

// Extend Window interface for webkit speech recognition
interface IWindow extends Window {
  SpeechRecognition: any
  webkitSpeechRecognition: any
}

declare const window: IWindow

export const useVoiceInput = (options: {
  continuous?: boolean
  interimResults?: boolean
  language?: string
  maxAlternatives?: number
} = {}) => {
  const [state, setState] = useState<VoiceInputState>({
    isListening: false,
    transcript: '',
    interimTranscript: '',
    error: null,
    confidence: 0,
    isSupported: false
  })

  const recognitionRef = useRef<any>(null)
  const finalTranscriptRef = useRef<string>('')

  // Check browser support
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    
    if (SpeechRecognition) {
      setState(prev => ({ ...prev, isSupported: true }))
      
      // Create recognition instance
      const recognition = new SpeechRecognition()
      
      // Configure recognition
      recognition.continuous = options.continuous ?? false
      recognition.interimResults = options.interimResults ?? true
      recognition.lang = options.language ?? 'tr-TR' // Turkish by default
      recognition.maxAlternatives = options.maxAlternatives ?? 1
      
      // Event handlers
      recognition.onstart = () => {
        console.log('Voice recognition started')
        setState(prev => ({
          ...prev,
          isListening: true,
          error: null
        }))
      }
      
      recognition.onresult = (event: any) => {
        let interimTranscript = ''
        let finalTranscript = finalTranscriptRef.current
        let maxConfidence = 0
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i]
          const transcript = result[0].transcript
          const confidence = result[0].confidence || 0
          
          if (confidence > maxConfidence) {
            maxConfidence = confidence
          }
          
          if (result.isFinal) {
            finalTranscript += transcript + ' '
            finalTranscriptRef.current = finalTranscript
          } else {
            interimTranscript += transcript
          }
        }
        
        setState(prev => ({
          ...prev,
          transcript: finalTranscript.trim(),
          interimTranscript: interimTranscript,
          confidence: maxConfidence
        }))
      }
      
      recognition.onerror = (event: any) => {
        console.error('Voice recognition error:', event.error)
        
        let errorMessage = 'Ses tanıma hatası'
        
        switch (event.error) {
          case 'no-speech':
            errorMessage = 'Ses algılanamadı. Lütfen tekrar deneyin.'
            break
          case 'audio-capture':
            errorMessage = 'Mikrofon bulunamadı veya erişim engellendi.'
            break
          case 'not-allowed':
            errorMessage = 'Mikrofon erişimi reddedildi. Lütfen izin verin.'
            break
          case 'network':
            errorMessage = 'Ağ bağlantısı hatası.'
            break
          case 'aborted':
            errorMessage = 'Ses tanıma iptal edildi.'
            break
          default:
            errorMessage = `Ses tanıma hatası: ${event.error}`
        }
        
        setState(prev => ({
          ...prev,
          isListening: false,
          error: errorMessage
        }))
      }
      
      recognition.onend = () => {
        console.log('Voice recognition ended')
        setState(prev => ({
          ...prev,
          isListening: false
        }))
      }
      
      recognition.onspeechend = () => {
        console.log('Speech ended')
        if (!options.continuous) {
          recognition.stop()
        }
      }
      
      recognition.onnomatch = () => {
        console.log('No match found')
        setState(prev => ({
          ...prev,
          error: 'Konuşma anlaşılamadı. Lütfen tekrar deneyin.'
        }))
      }
      
      recognitionRef.current = recognition
    } else {
      setState(prev => ({
        ...prev,
        isSupported: false,
        error: 'Tarayıcınız ses tanıma özelliğini desteklemiyor.'
      }))
    }
    
    // Cleanup
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop()
        } catch (error) {
          // Ignore errors on cleanup
        }
      }
    }
  }, [options.continuous, options.interimResults, options.language, options.maxAlternatives])

  // Start listening
  const startListening = useCallback(() => {
    if (!state.isSupported) {
      setState(prev => ({
        ...prev,
        error: 'Ses tanıma desteklenmiyor'
      }))
      return
    }
    
    if (recognitionRef.current && !state.isListening) {
      try {
        // Reset transcripts
        finalTranscriptRef.current = ''
        setState(prev => ({
          ...prev,
          transcript: '',
          interimTranscript: '',
          error: null,
          confidence: 0
        }))
        
        // Start recognition
        recognitionRef.current.start()
      } catch (error) {
        console.error('Failed to start recognition:', error)
        setState(prev => ({
          ...prev,
          error: 'Ses tanıma başlatılamadı'
        }))
      }
    }
  }, [state.isSupported, state.isListening])

  // Stop listening
  const stopListening = useCallback(() => {
    if (recognitionRef.current && state.isListening) {
      try {
        recognitionRef.current.stop()
      } catch (error) {
        console.error('Failed to stop recognition:', error)
      }
    }
  }, [state.isListening])

  // Toggle listening
  const toggleListening = useCallback(() => {
    if (state.isListening) {
      stopListening()
    } else {
      startListening()
    }
  }, [state.isListening, startListening, stopListening])

  // Reset transcript
  const resetTranscript = useCallback(() => {
    finalTranscriptRef.current = ''
    setState(prev => ({
      ...prev,
      transcript: '',
      interimTranscript: '',
      confidence: 0
    }))
  }, [])

  // Clear error
  const clearError = useCallback(() => {
    setState(prev => ({
      ...prev,
      error: null
    }))
  }, [])

  return {
    // State
    isListening: state.isListening,
    transcript: state.transcript,
    interimTranscript: state.interimTranscript,
    error: state.error,
    confidence: state.confidence,
    isSupported: state.isSupported,
    
    // Actions
    startListening,
    stopListening,
    toggleListening,
    resetTranscript,
    clearError
  }
}
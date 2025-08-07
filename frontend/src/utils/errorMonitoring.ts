/**
 * Browser Console Error Monitoring
 * Captures and reports JavaScript runtime errors and unhandled promise rejections
 */

interface ErrorInfo {
  type: 'error' | 'unhandledrejection' | 'console'
  message: string
  stack?: string
  timestamp: Date
  url?: string
  line?: number
  column?: number
  userAgent: string
}

class ErrorMonitor {
  private errors: ErrorInfo[] = []
  private maxErrors = 100
  private isEnabled = true
  private originalConsoleError: typeof console.error

  constructor() {
    this.originalConsoleError = console.error
    this.setupErrorHandlers()
    this.setupConsoleInterceptor()
  }

  private setupErrorHandlers() {
    // Capture JavaScript errors
    window.addEventListener('error', (event: ErrorEvent) => {
      this.captureError({
        type: 'error',
        message: event.message,
        stack: event.error?.stack,
        url: event.filename,
        line: event.lineno,
        column: event.colno,
        timestamp: new Date(),
        userAgent: navigator.userAgent
      })

      // Log to console for development
      if (import.meta.env.DEV) {
        this.originalConsoleError('🔴 Runtime Error:', {
          message: event.message,
          file: event.filename,
          line: event.lineno,
          column: event.colno,
          error: event.error
        })
      }
    })

    // Capture unhandled promise rejections
    window.addEventListener('unhandledrejection', (event: PromiseRejectionEvent) => {
      this.captureError({
        type: 'unhandledrejection',
        message: event.reason?.message || String(event.reason),
        stack: event.reason?.stack,
        timestamp: new Date(),
        userAgent: navigator.userAgent
      })

      // Log to console for development
      if (import.meta.env.DEV) {
        this.originalConsoleError('🔴 Unhandled Promise Rejection:', event.reason)
      }
    })
  }

  private setupConsoleInterceptor() {
    // Intercept console.error calls
    console.error = (...args: any[]) => {
      // Call original console.error
      this.originalConsoleError.apply(console, args)

      // Capture the error
      const message = args
        .map(arg => {
          if (typeof arg === 'object') {
            try {
              return JSON.stringify(arg, null, 2)
            } catch {
              return String(arg)
            }
          }
          return String(arg)
        })
        .join(' ')

      this.captureError({
        type: 'console',
        message,
        timestamp: new Date(),
        userAgent: navigator.userAgent,
        stack: new Error().stack
      })
    }
  }

  private captureError(error: ErrorInfo) {
    if (!this.isEnabled) return

    // Add to errors array
    this.errors.push(error)

    // Limit array size
    if (this.errors.length > this.maxErrors) {
      this.errors.shift()
    }

    // Send to monitoring service in production
    if (import.meta.env.PROD) {
      this.sendToMonitoringService(error)
    }

    // Store in localStorage for debugging
    this.storeInLocalStorage(error)
  }

  private storeInLocalStorage(error: ErrorInfo) {
    try {
      const storedErrors = localStorage.getItem('app_errors')
      const errors = storedErrors ? JSON.parse(storedErrors) : []
      
      errors.push({
        ...error,
        timestamp: error.timestamp.toISOString()
      })

      // Keep only last 50 errors in localStorage
      if (errors.length > 50) {
        errors.splice(0, errors.length - 50)
      }

      localStorage.setItem('app_errors', JSON.stringify(errors))
    } catch (e) {
      // Ignore localStorage errors
    }
  }

  private async sendToMonitoringService(error: ErrorInfo) {
    // TODO: Implement sending to actual monitoring service
    // For now, just log that we would send it
    console.log('Would send error to monitoring service:', error)
  }

  // Public methods
  public getErrors(): ErrorInfo[] {
    return [...this.errors]
  }

  public clearErrors() {
    this.errors = []
    localStorage.removeItem('app_errors')
  }

  public enable() {
    this.isEnabled = true
  }

  public disable() {
    this.isEnabled = false
  }

  public getStoredErrors(): ErrorInfo[] {
    try {
      const stored = localStorage.getItem('app_errors')
      return stored ? JSON.parse(stored) : []
    } catch {
      return []
    }
  }

  public displayErrorSummary() {
    const errors = this.getErrors()
    if (errors.length === 0) {
      console.log('✅ No errors captured')
      return
    }

    console.group(`🔴 ${errors.length} Errors Captured`)
    errors.forEach((error, index) => {
      console.group(`Error ${index + 1}: ${error.type}`)
      console.log('Message:', error.message)
      if (error.url) console.log('URL:', error.url)
      if (error.line) console.log('Line:', error.line)
      if (error.stack) console.log('Stack:', error.stack)
      console.log('Time:', error.timestamp)
      console.groupEnd()
    })
    console.groupEnd()
  }
}

// Create singleton instance
const errorMonitor = new ErrorMonitor()

// Export for use in app
export default errorMonitor

// Make available on window for debugging
if (import.meta.env.DEV) {
  (window as any).errorMonitor = errorMonitor
  console.log('🔍 Error Monitor Active - Use window.errorMonitor to inspect')
}
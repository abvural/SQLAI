import { test, expect, Page } from '@playwright/test'

// Test configuration
const BASE_URL = 'http://localhost:3002'
const API_URL = 'http://localhost:8000'

test.describe('SQLAI Chat Interface Tests', () => {
  let page: Page
  let consoleErrors: string[] = []
  let networkErrors: string[] = []

  test.beforeEach(async ({ page: testPage }) => {
    page = testPage
    consoleErrors = []
    networkErrors = []

    // Capture console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
        console.error('❌ Console Error:', msg.text())
      }
    })

    // Capture page errors
    page.on('pageerror', error => {
      consoleErrors.push(error.message)
      console.error('❌ Page Error:', error.message)
    })

    // Capture network errors
    page.on('requestfailed', request => {
      networkErrors.push(`${request.method()} ${request.url()} - ${request.failure()?.errorText}`)
      console.error('❌ Network Error:', request.url(), request.failure()?.errorText)
    })

    // Navigate to app
    await page.goto(BASE_URL)
  })

  test.afterEach(async () => {
    // Check for errors
    if (consoleErrors.length > 0) {
      console.log('⚠️  Console errors detected:', consoleErrors)
    }
    if (networkErrors.length > 0) {
      console.log('⚠️  Network errors detected:', networkErrors)
    }
  })

  test('should load the application without errors', async () => {
    // Check page title
    await expect(page).toHaveTitle(/SQLAI/)
    
    // Check main components are visible
    await expect(page.locator('text=Query Interface')).toBeVisible()
    
    // No console errors
    expect(consoleErrors).toHaveLength(0)
    expect(networkErrors).toHaveLength(0)
  })

  test('should display Chat Interface tab', async () => {
    // Click on Chat Interface tab
    await page.click('text=Chat Interface')
    
    // Check chat container is visible
    await expect(page.locator('.chat-container')).toBeVisible()
    
    // Check AI Assistant title
    await expect(page.locator('text=AI Asistan')).toBeVisible()
  })

  test('should check WebSocket connection status', async () => {
    // Navigate to Chat Interface
    await page.click('text=Chat Interface')
    
    // Wait for WebSocket connection indicator
    await page.waitForSelector('.connection-status', { timeout: 5000 })
    
    // Check connection status
    const connectionStatus = await page.locator('.connection-status').textContent()
    console.log('📡 WebSocket Status:', connectionStatus)
    
    // Should show either "Bağlı" (connected) or "Bağlantı kesildi" (disconnected)
    expect(connectionStatus).toMatch(/Bağlı|Bağlantı kesildi/)
  })

  test('should send and receive chat messages', async () => {
    // Navigate to Chat Interface
    await page.click('text=Chat Interface')
    
    // Wait for chat input
    await page.waitForSelector('.chat-input-container textarea')
    
    // Type a message
    const testMessage = 'Test mesajı: kaç kullanıcı var?'
    await page.fill('.chat-input-container textarea', testMessage)
    
    // Send message (press Enter or click send button)
    await page.press('.chat-input-container textarea', 'Enter')
    
    // Wait for user message to appear
    await expect(page.locator('.user-message').last()).toContainText(testMessage)
    
    // Wait for AI response (with timeout)
    await page.waitForSelector('.ai-message', { timeout: 30000 })
    
    // Check AI message exists
    const aiMessage = await page.locator('.ai-message').last().textContent()
    console.log('🤖 AI Response:', aiMessage)
    expect(aiMessage).toBeTruthy()
  })

  test('should test voice input button', async () => {
    // Navigate to Chat Interface
    await page.click('text=Chat Interface')
    
    // Check if voice input button exists
    const voiceButton = page.locator('button[aria-label*="Sesli"]')
    
    // Voice button might not exist if browser doesn't support it
    const voiceButtonCount = await voiceButton.count()
    
    if (voiceButtonCount > 0) {
      console.log('🎤 Voice input button found')
      await expect(voiceButton).toBeVisible()
      
      // Check if clicking works (won't actually record in headless mode)
      await voiceButton.click()
      
      // Should not cause any errors
      expect(consoleErrors).toHaveLength(0)
    } else {
      console.log('⚠️  Voice input not supported in test browser')
    }
  })

  test('should monitor JavaScript errors during interaction', async () => {
    // Navigate through different tabs
    await page.click('text=Chat Interface')
    await page.waitForTimeout(1000)
    
    await page.click('text=Natural Language')
    await page.waitForTimeout(1000)
    
    await page.click('text=SQL Editor')
    await page.waitForTimeout(1000)
    
    // Check for any JavaScript errors
    expect(consoleErrors).toHaveLength(0)
    
    // Check error monitor in console
    const errorCount = await page.evaluate(() => {
      // Check if errorMonitor exists
      if ((window as any).errorMonitor) {
        const errors = (window as any).errorMonitor.getErrors()
        console.log('📊 Error Monitor Status:', errors.length, 'errors')
        return errors.length
      }
      return -1
    })
    
    if (errorCount >= 0) {
      console.log(`✅ Error Monitor Active: ${errorCount} errors captured`)
      expect(errorCount).toBe(0)
    } else {
      console.log('⚠️  Error Monitor not found')
    }
  })

  test('should check API health endpoint', async () => {
    // Check backend health
    const response = await page.request.get(`${API_URL}/api/health`)
    expect(response.ok()).toBeTruthy()
    
    const data = await response.json()
    expect(data.status).toBe('healthy')
    console.log('✅ Backend API Status:', data)
  })

  test('should test database selection', async () => {
    // Check database selector
    const dbSelector = page.locator('div.ant-select-selector')
    await expect(dbSelector).toBeVisible()
    
    // Click to open dropdown
    await dbSelector.click()
    
    // Check if options are visible
    await page.waitForSelector('.ant-select-item-option')
    
    const options = await page.locator('.ant-select-item-option').count()
    console.log(`📊 Found ${options} database options`)
    expect(options).toBeGreaterThan(0)
  })

  test('should verify message bubble features', async () => {
    // Navigate to Chat Interface
    await page.click('text=Chat Interface')
    
    // Send a test message
    await page.fill('.chat-input-container textarea', 'test query')
    await page.press('.chat-input-container textarea', 'Enter')
    
    // Wait for message bubble
    await page.waitForSelector('.message-bubble')
    
    // Check message bubble structure
    const messageBubble = page.locator('.message-bubble').first()
    await expect(messageBubble).toBeVisible()
    
    // Check for timestamp
    const hasTimestamp = await messageBubble.locator('[title*="2025"]').count()
    expect(hasTimestamp).toBeGreaterThan(0)
    
    console.log('✅ Message bubble features verified')
  })
})

test.describe('Performance Tests', () => {
  test('should measure page load time', async ({ page }) => {
    const startTime = Date.now()
    
    await page.goto(BASE_URL)
    await page.waitForLoadState('networkidle')
    
    const loadTime = Date.now() - startTime
    console.log(`⏱️  Page load time: ${loadTime}ms`)
    
    // Should load within 3 seconds
    expect(loadTime).toBeLessThan(3000)
  })

  test('should check memory usage', async ({ page }) => {
    await page.goto(BASE_URL)
    
    // Get memory usage if available
    const memory = await page.evaluate(() => {
      if ((performance as any).memory) {
        return {
          usedJSHeapSize: Math.round((performance as any).memory.usedJSHeapSize / 1048576),
          totalJSHeapSize: Math.round((performance as any).memory.totalJSHeapSize / 1048576),
          jsHeapSizeLimit: Math.round((performance as any).memory.jsHeapSizeLimit / 1048576)
        }
      }
      return null
    })
    
    if (memory) {
      console.log('💾 Memory Usage:')
      console.log(`   Used: ${memory.usedJSHeapSize} MB`)
      console.log(`   Total: ${memory.totalJSHeapSize} MB`)
      console.log(`   Limit: ${memory.jsHeapSizeLimit} MB`)
      
      // Check memory usage is reasonable (less than 100MB)
      expect(memory.usedJSHeapSize).toBeLessThan(100)
    }
  })
})
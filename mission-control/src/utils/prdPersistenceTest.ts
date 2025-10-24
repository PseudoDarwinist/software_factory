/**
 * PRD Persistence Test Utility
 * 
 * This utility helps test the PRD persistence functionality across browser refreshes
 * and component unmounting/remounting scenarios.
 */

export interface PRDPersistenceTestResult {
  success: boolean
  message: string
  details?: any
}

export class PRDPersistenceTest {
  /**
   * Test if PRD session data persists in localStorage
   */
  static testLocalStoragePersistence(sessionId: string): PRDPersistenceTestResult {
    try {
      // Check if session data exists in localStorage
      const sessionKey = `prd-session-${sessionId}`
      const storedData = localStorage.getItem(sessionKey)
      
      if (!storedData) {
        return {
          success: false,
          message: 'No session data found in localStorage',
          details: { sessionId, sessionKey }
        }
      }
      
      // Try to parse the stored data
      const sessionData = JSON.parse(storedData)
      
      // Validate required fields
      const requiredFields = ['sessionId', 'projectId', 'status', 'files', 'createdAt']
      const missingFields = requiredFields.filter(field => !(field in sessionData))
      
      if (missingFields.length > 0) {
        return {
          success: false,
          message: 'Session data missing required fields',
          details: { missingFields, sessionData }
        }
      }
      
      return {
        success: true,
        message: 'Session data successfully persisted in localStorage',
        details: { sessionData }
      }
      
    } catch (error) {
      return {
        success: false,
        message: 'Error testing localStorage persistence',
        details: { error: error instanceof Error ? error.message : 'Unknown error' }
      }
    }
  }
  
  /**
   * Test if PRD content is properly stored and retrievable
   */
  static testPRDContentPersistence(sessionId: string, expectedContent?: string): PRDPersistenceTestResult {
    try {
      const sessionKey = `prd-session-${sessionId}`
      const storedData = localStorage.getItem(sessionKey)
      
      if (!storedData) {
        return {
          success: false,
          message: 'No session data found for PRD content test'
        }
      }
      
      const sessionData = JSON.parse(storedData)
      
      if (!sessionData.prdContent) {
        return {
          success: false,
          message: 'No PRD content found in stored session',
          details: { sessionData }
        }
      }
      
      if (expectedContent && sessionData.prdContent !== expectedContent) {
        return {
          success: false,
          message: 'PRD content does not match expected content',
          details: { 
            expected: expectedContent.slice(0, 100) + '...',
            actual: sessionData.prdContent.slice(0, 100) + '...'
          }
        }
      }
      
      return {
        success: true,
        message: 'PRD content successfully persisted',
        details: { 
          contentLength: sessionData.prdContent.length,
          contentPreview: sessionData.prdContent.slice(0, 100) + '...'
        }
      }
      
    } catch (error) {
      return {
        success: false,
        message: 'Error testing PRD content persistence',
        details: { error: error instanceof Error ? error.message : 'Unknown error' }
      }
    }
  }
  
  /**
   * Test if file list persists correctly
   */
  static testFilesPersistence(sessionId: string, expectedFileCount?: number): PRDPersistenceTestResult {
    try {
      const sessionKey = `prd-session-${sessionId}`
      const storedData = localStorage.getItem(sessionKey)
      
      if (!storedData) {
        return {
          success: false,
          message: 'No session data found for files test'
        }
      }
      
      const sessionData = JSON.parse(storedData)
      
      if (!Array.isArray(sessionData.files)) {
        return {
          success: false,
          message: 'Files data is not an array',
          details: { files: sessionData.files }
        }
      }
      
      if (expectedFileCount !== undefined && sessionData.files.length !== expectedFileCount) {
        return {
          success: false,
          message: 'File count does not match expected count',
          details: { 
            expected: expectedFileCount,
            actual: sessionData.files.length,
            files: sessionData.files
          }
        }
      }
      
      return {
        success: true,
        message: 'Files data successfully persisted',
        details: { 
          fileCount: sessionData.files.length,
          files: sessionData.files.map(f => ({ name: f.name, type: f.type, progress: f.progress }))
        }
      }
      
    } catch (error) {
      return {
        success: false,
        message: 'Error testing files persistence',
        details: { error: error instanceof Error ? error.message : 'Unknown error' }
      }
    }
  }
  
  /**
   * Run a comprehensive persistence test
   */
  static runComprehensiveTest(sessionId: string): {
    overall: boolean
    results: Record<string, PRDPersistenceTestResult>
  } {
    const results = {
      localStorage: this.testLocalStoragePersistence(sessionId),
      prdContent: this.testPRDContentPersistence(sessionId),
      files: this.testFilesPersistence(sessionId)
    }
    
    const overall = Object.values(results).every(result => result.success)
    
    return { overall, results }
  }
  
  /**
   * Clean up test data
   */
  static cleanup(sessionId: string): void {
    try {
      localStorage.removeItem(`prd-session-${sessionId}`)
      
      // Also clean up from session list
      const sessionsList = localStorage.getItem('prd-sessions-list')
      if (sessionsList) {
        const sessions = JSON.parse(sessionsList)
        const filteredSessions = sessions.filter((id: string) => id !== sessionId)
        localStorage.setItem('prd-sessions-list', JSON.stringify(filteredSessions))
      }
      
      // Clean up active session if it matches
      const activeSession = localStorage.getItem('active-prd-session')
      if (activeSession === sessionId) {
        localStorage.removeItem('active-prd-session')
      }
      
    } catch (error) {
      console.error('Error during test cleanup:', error)
    }
  }
}

// Helper function for browser console testing
(window as any).testPRDPersistence = PRDPersistenceTest
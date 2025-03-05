import { Router } from 'express'
import { BskyAgent } from '@atproto/api'
import { NSID } from './mcp_server'

interface MCPServerRecord {
  name: string
  package: string
  type: string
  version?: string
  description?: string
  tools?: string[]
  createdAt: string
}

export function createApiRouter(agent: BskyAgent) {
  const router = Router()

  // Middleware to ensure agent is authenticated
  router.use(async (req, res, next) => {
    try {
      if (!agent.session) {
        // Re-authenticate if session is lost
        await agent.login({
          identifier: process.env.HANDLE || '',
          password: process.env.PASSWORD || ''
        })
      }
      next()
    } catch (error) {
      console.error('Authentication failed:', error)
      res.status(401).json({ error: 'Authentication failed' })
    }
  })

  // List MCP server records from our repo
  router.get('/servers', async (req, res) => {
    try {
      const { data: records } = await agent.api.com.atproto.repo.listRecords({
        repo: agent.session?.did || '',
        collection: NSID
      })

      const servers = records.records.map(record => ({
        uri: record.uri,
        value: record.value as MCPServerRecord
      }))

      res.json(servers)
    } catch (error) {
      console.error('Failed to fetch servers:', error)
      res.status(500).json({ error: 'Failed to fetch servers' })
    }
  })

  // Delete a server record by URI
  router.delete('/servers/:uri(*)', async (req, res) => {
    try {
      const uri = req.params.uri
      const [did, collection, rkey] = uri.split('/').slice(-3)

      // Only allow deletion if we own the record
      if (did !== agent.session?.did) {
        return res.status(403).json({ error: 'Not authorized to delete this server' })
      }

      await agent.api.com.atproto.repo.deleteRecord({
        repo: did,
        collection,
        rkey
      })
      
      res.status(204).send()
    } catch (error) {
      console.error('Failed to delete server:', error)
      res.status(500).json({ error: 'Failed to delete server' })
    }
  })

  // Health check
  router.get('/health', (req, res) => {
    res.json({ status: 'ok' })
  })

  return router
} 
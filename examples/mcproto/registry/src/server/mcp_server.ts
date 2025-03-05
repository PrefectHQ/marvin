import { LexiconDoc } from '@atproto/lexicon'

export const NSID = 'app.mcp.server'

export const lexicon: LexiconDoc = {
  lexicon: 1,
  id: NSID,
  description: 'A record representing an MCP server package',
  defs: {
    main: {
      type: 'record',
      key: 'main',
      record: {
        type: 'object',
        required: ['name', 'package', 'type', 'createdAt'],
        properties: {
          name: {
            type: 'string',
            description: 'Human-readable name of the MCP server'
          },
          package: {
            type: 'string',
            description: 'NPM package name or other identifier to install/run the server'
          },
          type: {
            type: 'string',
            description: 'Type identifier (e.g., app.mcp.server)'
          },
          version: {
            type: 'string',
            description: 'Package version'
          },
          description: {
            type: 'string',
            description: 'Description of server capabilities'
          },
          tools: {
            type: 'array',
            items: { type: 'string' },
            description: 'List of available tools'
          },
          createdAt: {
            type: 'string',
            format: 'datetime',
            description: 'Timestamp when this record was created'
          }
        }
      }
    }
  }
}

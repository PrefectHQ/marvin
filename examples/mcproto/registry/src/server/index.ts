import { BskyAgent } from '@atproto/api'
import { createServer } from './server'

async function main() {
    const agent = new BskyAgent({
        service: 'https://bsky.social'
    })

    // Login with credentials
    if (!process.env.HANDLE || !process.env.PASSWORD) {
        console.error('Missing HANDLE or PASSWORD environment variables')
        process.exit(1)
    }

    try {
        await agent.login({
            identifier: process.env.HANDLE,
            password: process.env.PASSWORD
        })
        
        await createServer(agent)
    } catch (error) {
        console.error('Failed to start server:', error)
        process.exit(1)
    }
}

main() 
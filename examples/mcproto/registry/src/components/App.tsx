import React, { useEffect, useState } from 'react'

interface MCPServerRecord {
    name: string
    package: string
    type: string
    version?: string
    description?: string
    tools?: string[]
    createdAt: string
    lastRegisteredAt: string
}

interface Server {
    uri: string
    value: MCPServerRecord
}

interface HandleCache {
    [did: string]: string | null
}

export function App() {
    const [servers, setServers] = useState<Server[]>([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        loadServers()
        const interval = setInterval(loadServers, 30000)
        return () => clearInterval(interval)
    }, [])

    async function loadServers() {
        try {
            const res = await fetch('/api/servers')
            const data = await res.json()
            setServers(data)
        } catch (error) {
            console.error('Failed to load servers:', error)
        } finally {
            setLoading(false)
        }
    }

    async function deleteServer(uri: string) {
        if (!confirm('Are you sure you want to delete this server record?')) {
            return
        }

        try {
            const res = await fetch(`/api/servers/${encodeURIComponent(uri)}`, {
                method: 'DELETE'
            })

            if (res.ok) {
                setServers(servers => servers.filter(s => s.uri !== uri))
            } else {
                const data = await res.json()
                alert(`Failed to delete server: ${data.error}`)
            }
        } catch (e) {
            alert('Failed to delete server. Make sure you own this server record.')
        }
    }

    if (loading) {
        return (
            <div className="container">
                <h1>MCP Server Registry</h1>
                <div className="loading">Loading servers...</div>
            </div>
        )
    }

    return (
        <div className="container">
            <h1>MCP Server Registry</h1>

            <div className="intro">
                <p>
                    This registry displays MCP servers discovered via AT Protocol.
                    Each server is published as a record in the app.mcp.server collection
                    and provides AI tools and services via the MCP standard.
                </p>
            </div>

            <div className="servers">
                {servers.length === 0 ? (
                    <div className="no-servers">
                        <p>No MCP servers found.</p>
                    </div>
                ) : (
                    servers.map(server => (
                        <ServerCard
                            key={server.uri}
                            server={server}
                            onDelete={deleteServer}
                        />
                    ))
                )}
            </div>
        </div>
    )
}

interface ServerCardProps {
    server: Server
    onDelete: (uri: string) => void
}

function ServerCard({ server, onDelete }: ServerCardProps) {
    // Extract DID from URI for profile link
    const did = server.uri.split('/')[2] // at://did/collection/rkey

    // Format date to be more readable
    const formatDate = (dateStr: string) => {
        const date = new Date(dateStr)
        return date.toLocaleString()
    }

    // Determine package type and installation command from package string
    const getPackageInfo = (pkg: string): { type: string, displayName: string, installCommand: string } => {
        if (pkg.startsWith('@')) {
            return {
                type: 'NPM package',
                displayName: pkg,
                installCommand: `npm install ${pkg}`
            }
        }
        if (pkg.includes('github.com')) {
            return {
                type: 'GitHub repository',
                displayName: pkg,
                installCommand: `uv run ${pkg}`
            }
        }
        return {
            type: 'Package',
            displayName: pkg,
            installCommand: pkg
        }
    }

    const { type: packageType, displayName, installCommand } = getPackageInfo(server.value.package)

    return (
        <div className="server">
            <div className="server-header">
                <div className="server-meta">
                    <a
                        href={`https://bsky.app/profile/${did}`}
                        target="_blank"
                        rel="noopener"
                        title="View publisher's profile"
                        className="publisher"
                    >
                        {did}
                    </a>
                    <div className="server-type" title="ATProto record collection type">
                        {server.value.type}
                    </div>
                </div>
                <button
                    className="delete-btn"
                    onClick={() => onDelete(server.uri)}
                    title="Delete this server record (only available to the publisher)"
                >
                    Delete
                </button>
            </div>

            <div className="server-content">
                <div className="server-name">
                    {server.value.name}
                    {server.value.version &&
                        <span className="version">v{server.value.version}</span>
                    }
                </div>

                <div className="package-info" style={{
                    overflow: 'hidden',
                    maxWidth: '100%'
                }}>
                    <div className="package-label">
                        {packageType}
                        <span className="help-text" title={`Install with: ${installCommand}`}>
                            ℹ️
                        </span>
                    </div>
                    <code className="package-name no-scrollbar" style={{
                        display: 'block',
                        overflowX: 'auto',
                        whiteSpace: 'nowrap',
                        padding: '0.5rem',
                        backgroundColor: 'rgba(0, 0, 0, 0.2)',
                        borderRadius: '4px',
                        msOverflowStyle: 'none',
                        scrollbarWidth: 'none'
                    }}>
                        {displayName}
                    </code>
                </div>

                {server.value.description && (
                    <div className="server-description">
                        {server.value.description}
                    </div>
                )}

                <div className="server-timestamps">
                    <div className="timestamp">
                        <span className="timestamp-label">Last Registered:</span>
                        <span className="timestamp-value" title={server.value.lastRegisteredAt}>
                            {formatDate(server.value.lastRegisteredAt)}
                        </span>
                    </div>
                </div>

                {server.value.tools && server.value.tools.length > 0 && (
                    <div className="tools-container">
                        <div className="tools-label">
                            Available Tools
                            <span className="help-text" title="Tools this MCP server provides to AI agents">
                                ℹ️
                            </span>
                        </div>
                        <div className="server-tools">
                            {server.value.tools.map(tool => (
                                <span key={tool} className="tool" title={`Tool: ${tool}`}>
                                    {tool}
                                </span>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
} 
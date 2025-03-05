import express from 'express';
import { Server } from 'http';
import path from 'path';
import { fileURLToPath } from 'url';
import { createApiRouter } from './api';
import { BskyAgent } from '@atproto/api';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isProduction = process.env.NODE_ENV === 'production';
const PORT = 3001;

export async function createServer(agent: BskyAgent) {
  const app = express();
  
  // API routes
  app.use('/api', createApiRouter(agent));

  if (isProduction) {
    // Serve static files from Vite build output
    app.use(express.static(path.join(__dirname, '..', 'dist')));

    // Serve index.html for all other routes in production
    app.get('*', (req, res) => {
      res.sendFile(path.join(__dirname, '..', 'dist', 'index.html'));
    });
  }

  const server = new Server(app);
  await new Promise<void>(resolve => server.listen(PORT, resolve));
  console.log(`Server listening on port ${PORT}`);
  return server;
} 